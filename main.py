import logging
from time import sleep
import requests
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright, Playwright

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("viandas.log"),
        logging.StreamHandler()
    ]
)

# Cargar variables de entorno
env_values = dotenv_values(".env")

EMAIL: str = env_values["EMAIL"]
PASSWORD: str = env_values["PASSWORD"]
TILE_NAME: str = 'Almuerzo'
DAYS: list = ['Martes', 'Jueves']
URL: str = "https://www.elepeservicios.com.ar/web/login"

def send_telegram_message(message: str) -> None:
    token = env_values["TELEGRAM_BOT_TOKEN"]
    chat_id = env_values["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    if not response.ok:
        logging.error(f"Error al enviar mensaje: {response.text}")
    else:
        logging.info("Mensaje enviado a Telegram correctamente.")

def build_telegram_message(lunch_by_day: dict) -> str:
    message_lines = ["🍽️ <b>Almuerzos disponibles</b> 🍽️"]
    for day, data in lunch_by_day.items():
        message_lines.append(f"\n📅 <b>{day}</b>\n📩 <i>{data['message']}</i>")
        message_lines.append("🍛 <u>Menúes:</u>")
        for i, lunch in enumerate(data["lunches"], start=1):
            message_lines.append(f"  {i}. {lunch}")
    full_message = "\n".join(message_lines)
    logging.debug("Mensaje construido para Telegram:\n" + full_message)
    return full_message

def run(playwright: Playwright) -> dict:
    logging.info("Iniciando navegador y autenticación...")
    browser = playwright.chromium.launch()
    page = browser.new_page()
    page.goto(url=URL)

    # Login
    page.fill('input#login', EMAIL)
    page.fill('input#password', PASSWORD)
    page.click('button[type=submit].btn.btn-primary')

    # Espera a menú principal con todos los tiles de Odoo
    page.is_visible('.col-3.col-md-2.o_draggable.mb-3.px-0')
    page.get_by_text(TILE_NAME).click()

    # Espera a que los elementos de "categoría" se carguen
    page.is_visible('div.o_search_panel.flex-grow-0.flex-shrink-0.h-100.pb-5.bg-view.overflow-auto.pe-1.ps-3')

    logging.info("Extrayendo menús por día...")
    lunch_by_day = {}
    for day in DAYS:
        lunch_by_day[day] = get_lunches_by_day(page, day)

    browser.close()
    logging.info("Cierre del navegador.")
    return lunch_by_day

def get_lunches_by_day(page, day) -> dict:
    checkbox = page.get_by_label(day)
    checkbox.click()
    sleep(2)

    lunch_elements = page.query_selector_all('div.o_kanban_record')
    lunches = []
    message = ""

    for i, lunch in enumerate(lunch_elements):
        try:
            if i == 0:
                from_to_days_text = lunch.query_selector('.text-muted p')
                if from_to_days_text:
                    message = from_to_days_text.inner_text().strip()

            name_span = lunch.query_selector('strong span')
            if name_span is None:
                continue

            name = name_span.inner_text().strip()
            lunches.append(name)
        except Exception as e:
            logging.warning(f"Error al procesar un almuerzo: {e}")

    checkbox.click()
    return {
        "message": message,
        "lunches": lunches
    }

# Ejecutar
if __name__ == "__main__":
    with sync_playwright() as playwright:
        try:
            lunch_by_day: dict = run(playwright)
            message: str = build_telegram_message(lunch_by_day)
            send_telegram_message(message=message)
        except Exception as e:
            logging.critical(f"Error inesperado: {e}")
