import json
from time import sleep
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright, Playwright

env_values = dotenv_values(".env")

EMAIL: str = env_values["EMAIL"]
PASSWORD: str = env_values["PASSWORD"]
TILE_NAME: str = 'Almuerzo'
DAYS: list = ['Martes', 'Jueves']
URL: str = "https://www.elepeservicios.com.ar/web/login"

def run(playwright: Playwright):
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

    # Obtener almuerzos agrupados por día
    lunch_by_day = {}
    for day in DAYS:
        lunch_by_day[day] = get_lunches_by_day(page, day)

    browser.close()

    # print(json.dumps(lunch_by_day, indent=2, ensure_ascii=False))
    print("\n--- Almuerzos disponibles ---")
    for day, data in lunch_by_day.items():
        print(f"-{data['message']}")
        print("Menúes:")
        for i, lunch in enumerate(data['lunches'], start=1):
            print(f"{i}. {lunch}")



def get_lunches_by_day(page, day):
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
            print(f"Error al procesar un almuerzo: {e}")

    checkbox.click()
    return {
        "message": message,
        "lunches": lunches
    }

with sync_playwright() as playwright:
    run(playwright)
