import logging
from playwright.sync_api import Playwright, Page, Browser, Locator
from config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class LunchScraper:
    """Realiza el scraping de los almuerzos de Odoo."""

    LOGIN_INPUT_SELECTOR = 'input#login'
    PASSWORD_INPUT_SELECTOR = 'input#password'
    SUBMIT_BUTTON_SELECTOR = 'button[type=submit].btn.btn-primary'
    ODOO_MAIN_MENU_TILES_CONTAINER_SELECTOR = '.col-3.col-md-2.o_draggable.mb-3.px-0' # Selector modificado por ti
    LAUNCH_PANEL_CATEGORIES_SELECTOR = 'div.o_search_panel.flex-grow-0.flex-shrink-0.h-100.pb-5.bg-view.overflow-auto.pe-1.ps-3' # Selector modificado por ti
    KANBAN_RECORD_SELECTOR = 'div.o_kanban_record'
    PERIOD_MESSAGE_SELECTOR = '.text-muted p'
    LUNCH_NAME_SELECTOR = 'strong span'

    def __init__(self, playwright_instance: Playwright, config: ConfigLoader):
        self.playwright = playwright_instance
        self.config = config
        self.browser: Browser | None = None
        self.page: Page | None = None

    def _launch_browser_and_navigate(self):
        logger.info("Iniciando navegador Chromium...")
        self.browser = self.playwright.chromium.launch()
        self.page = self.browser.new_page()
        logger.info("Navegando a %s", self.config.login_url)
        self.page.goto(self.config.login_url, timeout=60000)

    def _login(self):
        if not self.page:
            raise ConnectionError("La página no ha sido inicializada.")
        logger.info("Intentando iniciar sesión...")
        self.page.fill(self.LOGIN_INPUT_SELECTOR, self.config.email)
        self.page.fill(self.PASSWORD_INPUT_SELECTOR, self.config.password)
        self.page.click(self.SUBMIT_BUTTON_SELECTOR)
        # page.is_visible() con timeout espera hasta que el elemento sea visible o se agote el tiempo.
        self.page.is_visible(self.ODOO_MAIN_MENU_TILES_CONTAINER_SELECTOR, timeout=30000)
        logger.info("Login exitoso. Menú principal visible.")

    def _navigate_to_target_tile(self):
        if not self.page:
            raise ConnectionError("La página no ha sido inicializada.")
        logger.info("Buscando y haciendo clic en el tile: '%s'", self.config.target_tile_name)
        self.page.get_by_text(self.config.target_tile_name).click()
        self.page.is_visible(self.LAUNCH_PANEL_CATEGORIES_SELECTOR) # Considera añadir un timeout si es necesario
        logger.info("Navegación al tile '%s' completada.", self.config.target_tile_name)

    def _extract_lunches_for_day(self, day_name: str) -> dict:
        if not self.page:
            raise ConnectionError("La página no ha sido inicializada.")

        logger.info("Procesando día: %s", day_name)
        day_checkbox: Locator = self.page.get_by_label(day_name)
        result = {"period_message": "", "lunches": []}

        try:
            day_checkbox.wait_for(state="visible", timeout=10000)
            day_checkbox.check() 
            logger.debug("Checkbox para '%s' marcado.", day_name)

            self.page.wait_for_selector(f"{self.KANBAN_RECORD_SELECTOR}", timeout=15000, state="attached")
            self.page.wait_for_timeout(2000) 

            lunch_elements: list[Locator] = self.page.query_selector_all(self.KANBAN_RECORD_SELECTOR)
            logger.info("Encontrados %d elementos de almuerzo para %s.", len(lunch_elements), day_name)

            lunches: list[str] = []
            period_msg: str = ""

            for i, lunch_element in enumerate(lunch_elements):
                try:
                    if i == 0:
                        period_msg_element = lunch_element.query_selector(self.PERIOD_MESSAGE_SELECTOR)
                        if period_msg_element and period_msg_element.is_visible():
                            period_msg = period_msg_element.inner_text().strip()
                            logger.debug("Mensaje de período encontrado: '%s'", period_msg)

                    name_span = lunch_element.query_selector(self.LUNCH_NAME_SELECTOR)
                    if name_span and name_span.is_visible():
                        lunch_name = name_span.inner_text().strip()
                        if lunch_name:
                            lunches.append(lunch_name)
                        else:
                            logger.warning("Nombre de almuerzo vacío encontrado en el elemento %d para %s.", i + 1, day_name)
                except Exception as e:
                    logger.warning("Error procesando un elemento de almuerzo para %s: %s", day_name, e, exc_info=True)
            
            result["period_message"] = period_msg
            result["lunches"] = lunches
            logger.debug("Almuerzos para %s: %s", day_name, lunches)

        except Exception as e:
            logger.error("Fallo al procesar el día %s: %s", day_name, e, exc_info=True)
            result["period_message"] = f"Error al obtener datos para {day_name}"
            result["lunches"] = []
        finally:
            try:
                if day_checkbox.is_checked():
                    day_checkbox.uncheck()
                    logger.debug("Checkbox para '%s' desmarcado.", day_name)
                    self.page.wait_for_timeout(500)
            except Exception as e: # Ser más específico con la excepción si es posible (ej. playwright._impl._api_types.Error)
                logger.warning("No se pudo desmarcar el checkbox para %s o ya no era válido: %s", day_name, e)
        return result

    def scrape_lunches(self) -> dict:
        scraped_data = {}
        try:
            self._launch_browser_and_navigate()
            self._login()
            self._navigate_to_target_tile()

            logger.info("Extrayendo menus por día...")
            for day in self.config.target_days:
                scraped_data[day] = self._extract_lunches_for_day(day)
            
            return scraped_data
        except Exception as e:
            logger.critical("Fallo crítico durante el proceso de scraping: %s", e, exc_info=True)
            return {day: {"period_message": "Error general en scraping", "lunches": []} for day in self.config.target_days}
        finally:
            self.close_browser()

    def close_browser(self):
        if self.browser:
            try:
                self.browser.close()
                logger.info("Navegador cerrado correctamente.")
            except Exception as e:
                logger.error("Error al cerrar el navegador: %s", e, exc_info=True)
        self.browser = None
        self.page = None
