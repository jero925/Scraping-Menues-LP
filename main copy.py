import logging
import requests
from time import sleep
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright, Playwright, Page, Browser, Locator

# --- Configuración de Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler("lunch_app.log"),  # Nombre de archivo de log cambiado
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Class de Configuración ---
class ConfigLoader:
    """Carga y gestiona la configuración de la aplicación."""
    def __init__(self, env_file_path: str = ".env"):
        self._env_values = dotenv_values(env_file_path)
        if not self._env_values:
            logger.warning(f"No se pudo cargar el archivo .env desde {env_file_path} o está vacío.")

        # Credenciales y tokens
        self.email: str = self._env_values.get("EMAIL", "")
        self.password: str = self._env_values.get("PASSWORD", "")
        self.telegram_bot_token: str = self._env_values.get("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id: str = self._env_values.get("TELEGRAM_CHAT_ID", "")

        # Configuración específica de la aplicación/scraping
        self.login_url: str = "https://www.elepeservicios.com.ar/web/login"
        self.target_tile_name: str = 'Almuerzo'
        self.target_days: list[str] = ['Martes', 'Jueves'] # Días de la semana para buscar

        self._validate_config()

    def _validate_config(self):
        required_fields = ['email', 'password', 'telegram_bot_token', 'telegram_chat_id']
        missing_fields = [field for field in required_fields if not getattr(self, field)]
        if missing_fields:
            error_msg = f"Configuración incompleta. Faltan las siguientes variables de entorno: {', '.join(missing_fields)}"
            logger.critical(error_msg)
            raise ValueError(error_msg)
        logger.info("Configuración cargada y validada correctamente.")


# --- Servicio de Notificación por Telegram ---
class TelegramNotifier:
    """Gestiona la construcción y envío de mensajes a Telegram."""
    BASE_TELEGRAM_API_URL = "https://api.telegram.org/bot"

    def __init__(self, bot_token: str, chat_id: str):
        if not bot_token or not chat_id:
            logger.error("Token o Chat ID de Telegram no proporcionados para TelegramNotifier.")
            raise ValueError("Token y Chat ID de Telegram son requeridos.")
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.send_url = f"{self.BASE_TELEGRAM_API_URL}{self.bot_token}/sendMessage"

    def format_lunches_message(self, daily_lunches_data: dict) -> str:
        """Construye el mensaje formateado para Telegram a partir de los datos de almuerzos."""
        if not daily_lunches_data:
            logger.info("No hay datos de almuerzos para formatear.")
            return "No se encontraron almuerzos disponibles para los días seleccionados."

        message_lines = ["🍽️ <b>Almuerzos disponibles esta semana</b> 🍽️"]
        for day, data in daily_lunches_data.items():
            message_lines.append(f"\n📅 <b>{day}</b>")
            if data.get('period_message'):
                message_lines.append(f"📩 <i>{data['period_message']}</i>")
            
            if data['lunches']:
                message_lines.append("🍛 <u>Menúes:</u>")
                for i, lunch_name in enumerate(data["lunches"], start=1):
                    message_lines.append(f"   {i}. {lunch_name}")
            else:
                message_lines.append("  <i>No hay menúes listados para este día.</i>")
        
        full_message = "\n".join(message_lines)
        logger.debug(f"Mensaje construido para Telegram:\n{full_message}")
        return full_message

    def send_notification(self, message_text: str) -> bool:
        """Envía un mensaje a Telegram."""
        payload = {
            "chat_id": self.chat_id,
            "text": message_text,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(self.send_url, data=payload, timeout=10)
            response.raise_for_status() # Lanza HTTPError para respuestas 4xx/5xx
            logger.info("Mensaje enviado a Telegram correctamente.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al enviar mensaje a Telegram: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Detalles de la respuesta: {e.response.text}")
            return False

# --- Servicio de Scraping Web ---
class ElepLunchScraper:
    """Realiza el scraping de los almuerzos del sitio Elep Servicios."""

    # Selectores CSS (podrían moverse a una clase/diccionario de constantes si son muchos)
    LOGIN_INPUT_SELECTOR = 'input#login'
    PASSWORD_INPUT_SELECTOR = 'input#password'
    SUBMIT_BUTTON_SELECTOR = 'button[type=submit].btn.btn-primary'
    ODOO_APP_TILE_SELECTOR_TEMPLATE = ".o_app[data-menu-xmlid*='{tile_xml_id_keyword}'] .o_app_title" # Asumiendo que el tile tiene un data-menu-xmlid, o ajustar
    ODOO_MAIN_MENU_TILES_CONTAINER_SELECTOR = '.o_apps' # Un selector más general para el contenedor de tiles
    SEARCH_PANEL_SELECTOR = 'div.o_search_panel' # Panel de búsqueda/categorías
    KANBAN_RECORD_SELECTOR = 'div.o_kanban_record' # Selector para cada "tarjeta" de menú
    PERIOD_MESSAGE_SELECTOR = '.text-muted p' # Selector para el mensaje de período
    LUNCH_NAME_SELECTOR = 'strong span' # Selector para el nombre del almuerzo

    def __init__(self, playwright_instance: Playwright, config: ConfigLoader):
        self.playwright = playwright_instance
        self.config = config
        self.browser: Browser | None = None
        self.page: Page | None = None

    def _launch_browser_and_navigate(self):
        """Inicia el navegador y navega a la URL de login."""
        logger.info("Iniciando navegador Chromium...")
        self.browser = self.playwright.chromium.launch() # Podrías añadir headless=False para debug
        self.page = self.browser.new_page()
        logger.info(f"Navegando a {self.config.login_url}")
        self.page.goto(self.config.login_url, timeout=60000) # Timeout aumentado

    def _login(self):
        """Realiza el proceso de login."""
        if not self.page:
            raise ConnectionError("La página no ha sido inicializada. Llama a _launch_browser_and_navigate primero.")
        logger.info("Intentando iniciar sesión...")
        self.page.fill(self.LOGIN_INPUT_SELECTOR, self.config.email)
        self.page.fill(self.PASSWORD_INPUT_SELECTOR, self.config.password)
        self.page.click(self.SUBMIT_BUTTON_SELECTOR)
        logger.info("Formulario de login enviado.")
        # Espera a que el login sea exitoso (ej. aparición del menú principal)
        self.page.wait_for_selector(self.ODOO_MAIN_MENU_TILES_CONTAINER_SELECTOR, timeout=30000)
        logger.info("Login exitoso. Menú principal visible.")

    def _navigate_to_target_tile(self):
        """Navega al tile específico de almuerzos."""
        if not self.page:
            raise ConnectionError("La página no ha sido inicializada.")
        logger.info(f"Buscando y haciendo clic en el tile: '{self.config.target_tile_name}'")
        
        # Es más robusto esperar por el texto y luego hacer clic.
        # El selector anterior '.col-3.col-md-2.o_draggable.mb-3.px-0' era muy genérico.
        # Intentaremos localizarlo por texto directamente.
        tile_locator = self.page.get_by_text(self.config.target_tile_name, exact=True)
        
        # Asegurarse que el tile es visible antes de hacer click
        tile_locator.wait_for(state="visible", timeout=20000)
        tile_locator.click()
        
        # Esperar a que se cargue el panel de búsqueda/categorías en la nueva vista
        self.page.wait_for_selector(self.SEARCH_PANEL_SELECTOR, state="visible", timeout=30000)
        logger.info(f"Navegación al tile '{self.config.target_tile_name}' completada.")

    def _extract_lunches_for_day(self, day_name: str) -> dict:
        """Extrae los almuerzos para un día específico."""
        if not self.page:
            raise ConnectionError("La página no ha sido inicializada.")

        logger.info(f"Procesando día: {day_name}")
        day_checkbox: Locator = self.page.get_by_label(day_name, exact=True)
        
        try:
            day_checkbox.check() # Usar check() es idempotente y más claro para checkboxes
            logger.debug(f"Checkbox para '{day_name}' marcado.")
            # Esperar a que los resultados se actualicen.
            # Esto podría ser un spinner que desaparece o que los kanban_records se actualicen.
            # Un sleep corto puede ser un último recurso, pero es mejor esperar por un cambio específico.
            self.page.wait_for_timeout(2500) # Reemplazar con una espera más robusta si es posible.
                                            # Por ejemplo: esperar que un loader desaparezca o
                                            # que el número de elementos kanban cambie o se estabilice.
                                            # self.page.wait_for_selector(f"{self.KANBAN_RECORD_SELECTOR}:not(.o_kanban_ghost)", timeout=10000)


            lunch_elements: list[Locator] = self.page.query_selector_all(self.KANBAN_RECORD_SELECTOR)
            logger.info(f"Encontrados {len(lunch_elements)} elementos de almuerzo para {day_name}.")
            
            lunches: list[str] = []
            period_msg: str = ""

            for i, lunch_element in enumerate(lunch_elements):
                try:
                    if i == 0: # Asumimos que el mensaje de período está en el primer elemento
                        period_msg_element = lunch_element.query_selector(self.PERIOD_MESSAGE_SELECTOR)
                        if period_msg_element:
                            period_msg = period_msg_element.inner_text().strip()
                            logger.debug(f"Mensaje de período encontrado: '{period_msg}'")

                    name_span = lunch_element.query_selector(self.LUNCH_NAME_SELECTOR)
                    if name_span:
                        lunch_name = name_span.inner_text().strip()
                        if lunch_name: # Asegurarse que no es un string vacío
                             lunches.append(lunch_name)
                        else:
                            logger.warning(f"Nombre de almuerzo vacío encontrado en el elemento {i+1} para {day_name}.")
                    else:
                        logger.warning(f"No se encontró el span del nombre del almuerzo en el elemento {i+1} para {day_name}.")
                
                except Exception as e:
                    logger.warning(f"Error procesando un elemento de almuerzo para {day_name}: {e}", exc_info=True)
            
            logger.debug(f"Almuerzos para {day_name}: {lunches}")
            return {"period_message": period_msg, "lunches": lunches}

        finally:
            if day_checkbox.is_checked(): # Solo desmarcar si estaba marcado
                day_checkbox.uncheck()
                logger.debug(f"Checkbox para '{day_name}' desmarcado.")
                self.page.wait_for_timeout(500) # Pequeña pausa para asegurar que la UI se actualiza tras desmarcar


    def scrape_lunches(self) -> dict:
        """
        Orquesta el proceso completo de scraping: login, navegación y extracción de almuerzos.
        Retorna un diccionario con los almuerzos por día.
        """
        scraped_data = {}
        try:
            self._launch_browser_and_navigate()
            self._login()
            self._navigate_to_target_tile()

            logger.info("Extrayendo menús por día...")
            for day in self.config.target_days:
                try:
                    scraped_data[day] = self._extract_lunches_for_day(day)
                except Exception as e:
                    logger.error(f"Error al extraer almuerzos para el día {day}: {e}", exc_info=True)
                    scraped_data[day] = {"period_message": "Error en extracción", "lunches": []}
            
            return scraped_data

        except Exception as e:
            logger.critical(f"Fallo crítico durante el proceso de scraping: {e}", exc_info=True)
            # Podrías querer re-lanzar la excepción o manejarla devolviendo datos vacíos
            # raise
            return {day: {"period_message": "Error general en scraping", "lunches": []} for day in self.config.target_days}
        finally:
            self.close_browser()

    def close_browser(self):
        """Cierra el navegador."""
        if self.browser:
            try:
                self.browser.close()
                logger.info("Navegador cerrado correctamente.")
            except Exception as e:
                logger.error(f"Error al cerrar el navegador: {e}", exc_info=True)
        self.browser = None
        self.page = None


# --- Punto de Entrada Principal ---
def main():
    """Función principal para ejecutar el script."""
    logger.info("🚀 Iniciando aplicación de notificación de almuerzos...")
    
    try:
        config = ConfigLoader()
        telegram_notifier = TelegramNotifier(
            bot_token=config.telegram_bot_token,
            chat_id=config.telegram_chat_id
        )
    except ValueError as e:
        logger.critical(f"Error de configuración inicial: {e}. Abortando.")
        return

    daily_lunches_data = {}
    with sync_playwright() as playwright_instance:
        scraper = ElepLunchScraper(playwright_instance, config)
        try:
            daily_lunches_data = scraper.scrape_lunches()
        except Exception as e: # Captura excepciones del propio scrape_lunches si no las maneja internamente
            logger.critical(f"Error durante la ejecución del scraper: {e}", exc_info=True)
            # Enviar un mensaje de error por Telegram si el scraping falla críticamente
            error_message = f"⚠️ Error crítico en el bot de almuerzos: {str(e)[:200]}" # Truncar mensaje de error
            telegram_notifier.send_notification(error_message)
            return # Salir si el scraping falla

    if not daily_lunches_data or all(not v['lunches'] and not v.get('period_message') for v in daily_lunches_data.values()):
        logger.info("No se encontraron datos de almuerzos o todos los días estaban vacíos/con error.")
        # Opcionalmente, enviar una notificación de "no hay almuerzos"
        # telegram_notifier.send_notification("No se encontraron almuerzos para los días configurados.")
    else:
        logger.info("Datos de almuerzos extraídos. Preparando para enviar notificación.")
        message_to_send = telegram_notifier.format_lunches_message(daily_lunches_data)
        telegram_notifier.send_notification(message_to_send)

    logger.info("🏁 Aplicación de notificación de almuerzos finalizada.")


if __name__ == "__main__":
    main()