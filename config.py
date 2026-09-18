import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# Список услуг — меняется под конкретного заказчика
SERVICES = [
    "Стрижка",
    "Маникюр",
    "Массаж",
]

# Рабочие часы (24ч формат) — тоже настраивается под клиента
WORK_HOURS = [10, 11, 12, 13, 14, 15, 16, 17, 18]
