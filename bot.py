import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import BOT_TOKEN, ADMIN_CHAT_ID, SERVICES, WORK_HOURS
import db

logging.basicConfig(level=logging.INFO)
router = Router()


class Booking(StatesGroup):
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()


# ---------- helpers ----------

def services_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"service:{name}")]
        for name in SERVICES
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dates_keyboard() -> InlineKeyboardMarkup:
    today = datetime.now()
    buttons = []
    for i in range(7):
        day = today + timedelta(days=i)
        label = day.strftime("%d.%m (%a)")
        buttons.append(
            [InlineKeyboardButton(text=label, callback_data=f"date:{day.strftime('%Y-%m-%d')}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def times_keyboard(date_str: str) -> InlineKeyboardMarkup:
    taken = db.get_taken_slots(date_str)
    buttons = []
    row = []
    for hour in WORK_HOURS:
        slot = f"{hour}:00"
        if slot in taken:
            continue
        row.append(InlineKeyboardButton(text=slot, callback_data=f"time:{slot}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if not buttons:
        buttons.append([InlineKeyboardButton(text="Нет свободных слотов", callback_data="noop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:yes"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:no"),
            ]
        ]
    )


# ---------- handlers ----------

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Это бот записи. Выберите услугу:",
        reply_markup=services_keyboard(),
    )
    await state.set_state(Booking.choosing_service)


@router.callback_query(Booking.choosing_service, F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service = callback.data.split(":", 1)[1]
    await state.update_data(service=service)
    await callback.message.edit_text(
        f"Услуга: {service}\n\nВыберите дату:", reply_markup=dates_keyboard()
    )
    await state.set_state(Booking.choosing_date)
    await callback.answer()


@router.callback_query(Booking.choosing_date, F.data.startswith("date:"))
async def choose_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":", 1)[1]
    await state.update_data(date=date_str)
    await callback.message.edit_text(
        f"Дата: {date_str}\n\nВыберите время:", reply_markup=times_keyboard(date_str)
    )
    await state.set_state(Booking.choosing_time)
    await callback.answer()


@router.callback_query(Booking.choosing_time, F.data.startswith("time:"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split(":", 1)[1]
    await state.update_data(time=time_str)
    await callback.message.edit_text("Как к вам обращаться? Введите имя:")
    await state.set_state(Booking.entering_name)
    await callback.answer()


@router.message(Booking.entering_name)
async def enter_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Оставьте номер телефона для связи:")
    await state.set_state(Booking.entering_phone)


@router.message(Booking.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    summary = (
        f"Проверьте запись:\n\n"
        f"Услуга: {data['service']}\n"
        f"Дата: {data['date']}\n"
        f"Время: {data['time']}\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}"
    )
    await message.answer(summary, reply_markup=confirm_keyboard())
    await state.set_state(Booking.confirming)


@router.callback_query(Booking.confirming, F.data.startswith("confirm:"))
async def confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    choice = callback.data.split(":", 1)[1]
    if choice == "no":
        await callback.message.edit_text("Запись отменена. Наберите /start, чтобы начать заново.")
        await state.clear()
        await callback.answer()
        return

    data = await state.get_data()
    db.add_booking(
        user_id=callback.from_user.id,
        service=data["service"],
        date=data["date"],
        time=data["time"],
        name=data["name"],
        phone=data["phone"],
    )
    await callback.message.edit_text(
        "Готово! Вы записаны ✅\nМы свяжемся с вами для подтверждения."
    )
    if ADMIN_CHAT_ID:
        await bot.send_message(
            ADMIN_CHAT_ID,
            "🆕 Новая запись!\n\n"
            f"Услуга: {data['service']}\n"
            f"Дата: {data['date']} в {data['time']}\n"
            f"Имя: {data['name']}\n"
            f"Телефон: {data['phone']}\n"
            f"Telegram: @{callback.from_user.username or 'нет username'}",
        )
    await state.clear()
    await callback.answer()


@router.message(Command("my_bookings"))
async def my_bookings(message: Message):
    rows = db.get_user_bookings(message.from_user.id)
    if not rows:
        await message.answer("У вас пока нет записей.")
        return
    text = "Ваши записи:\n\n"
    for service, date, time in rows:
        text += f"• {service} — {date} в {time}\n"
    await message.answer(text)


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено. Наберите /start, чтобы начать заново.")


async def main():
    db.init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
