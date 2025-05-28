import logging
from time import sleep
from typing import Dict, List

import requests
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright, Playwright, Page

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("viandas.log"),
        logging.StreamHandler()
    ]
)

# Variables de entorno
env = dotenv_values(".env")


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_message(self, message: str) -> None:
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(self.api_url, data=payload)

        if not response.ok:
            logging.error(f"Error al enviar mensaje a Telegram: {response.text}")
        else:
            logging.info("Mensaje enviado a Telegram correctamente.")


class LunchScraper:
    LOGIN_URL = "https://www.elepeservicios.com.ar/web/login"
    TILE_NAME = "Almuerzo"
    DAYS = ['Martes', 'Jueves']

    def __init__(self, email: str, password: str) -> None:
        self.email = email
        self.password = password

    def _login(self, page: Page) -> None:
        page.goto(self.LOGIN_URL)
        page.fill('input#login', self.email)
        page.fill('input#password', self.password)
        page.click('button[type=submit].btn.btn-primary')
        page.is_visible('.col-3.col-md-2.o_draggable.mb-3.px-0')
        page.get_by_text(self.TILE_NAME).click()
        page.is_visible('div.o_search_panel.flex-grow-0.flex-shrink-0.h-100.pb-5.bg-view.overflow-auto.pe-1.ps-3')

    def scrape_lunches(self, playwright: Playwright) -> Dict[str, Dict[str, List[str]]]:
        logging.info("Iniciando navegador y autenticación...")
        browser = playwright.chromium.launch()
        page = browser.new_page()

        try:
            self._login(page)
            logging.info("Extrayendo menús por día...")

            lunch_by_day = {}
            for day in self.DAYS:
                lunch_by_day[day] = self._extract_lunches_by_day(page, day)

            return lunch_by_day
        finally:
            browser.close()
            logging.info("Navegador cerrado.")

    def _extract_lunches_by_day(self, page: Page, day: str) -> Dict[str, List[str]]:
        checkbox = page.get_by_label(day)
        checkbox.click()
        sleep(2)

        lunch_cards = page.query_selector_all('div.o_kanban_record')
        lunches = []
        message = ""

        for index, card in enumerate(lunch_cards):
            try:
                if index == 0:
                    message_element = card.query_selector('.text-muted p')
                    if message_element:
                        message = message_element.inner_text().strip()

                name_element = card.query_selector('strong span')
                if name_element:
                    name = name_element.inner_text().strip()
                    lunches.append(name)
            except Exception as e:
                logging.warning(f"Error al procesar un almuerzo: {e}")

        checkbox.click()
        return {"message": message, "lunches": lunches}


def format_telegram_message(lunch_by_day: Dict[str, Dict[str, List[str]]]) -> str:
    lines = ["🍽️ <b>Almuerzos disponibles</b> 🍽️"]
    for day, data in lunch_by_day.items():
        lines.append(f"\n📅 <b>{day}</b>\n📩 <i>{data['message']}</i>")
        lines.append("🍛 <u>Menúes:</u>")
        for i, lunch in enumerate(data["lunches"], start=1):
            lines.append(f"  {i}. {lunch}")
    full_message = "\n".join(lines)
    logging.debug("Mensaje para Telegram:\n" + full_message)
    return full_message


def main() -> None:
    email = env["EMAIL"]
    password = env["PASSWORD"]
    bot_token = env["TELEGRAM_BOT_TOKEN"]
    chat_id = env["TELEGRAM_CHAT_ID"]

    scraper = LunchScraper(email, password)
    notifier = TelegramNotifier(bot_token, chat_id)

    with sync_playwright() as playwright:
        try:
            lunch_data = scraper.scrape_lunches(playwright)
            message = format_telegram_message(lunch_data)
            notifier.send_message(message)
        except Exception as e:
            logging.critical(f"Error inesperado en ejecución principal: {e}")


if __name__ == "__main__":
    main()
