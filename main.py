import logging
import sys  # Añadido para sys.stderr/sys.stdout
import io  # Añadido para io.TextIOBase y reconfigure

from playwright.sync_api import sync_playwright

from config_loader import ConfigLoader
from telegram_notifier import TelegramNotifier
# Nombre de clase LunchScraper consistente con tu modificación
from lunch_scraper import LunchScraper

# --- Intento de configurar la codificación de la consola a UTF-8 (especialmente para Windows) ---
# Esto debe hacerse antes de que StreamHandler sea inicializado por basicConfig si usa el stderr por defecto.
# Puede que no funcione en todos los entornos o consolas, pero es un intento programático.
try:
    if hasattr(sys.stderr, 'reconfigure') and isinstance(sys.stderr, io.TextIOBase) and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')
    if hasattr(sys.stdout, 'reconfigure') and isinstance(sys.stdout, io.TextIOBase) and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception as e:
    # Usar print aquí ya que el logger podría no estar completamente configurado o podría causar problemas.
    print(
        f"[ADVERTENCIA PRE-LOGGING] No se pudo reconfigurar la codificación de sys.stdout/sys.stderr a UTF-8: {e}", file=sys.stderr)

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)s %(name)s] - %(message)s",
    handlers=[
        # Especificar UTF-8 para el archivo de log
        logging.FileHandler("lunch_app.log", encoding='utf-8'),
        # Usará sys.stderr (o stdout si se especifica) que intentamos reconfigurar
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Función principal para ejecutar el script."""
    logger.info("🚀 Iniciando aplicación de notificacion de almuerzos...")

    try:
        config = ConfigLoader()
        telegram_notifier = TelegramNotifier(
            bot_token=config.telegram_bot_token,
            chat_id=config.telegram_chat_id
        )
    except ValueError as e:
        logger.critical("Error de configuracion inicial: %s. Abortando.", e)
        return
    except Exception as e:
        logger.critical(
            "Error inesperado durante la inicializacion: %s. Abortando.", e, exc_info=True)
        return

    daily_lunches_data = {}
    with sync_playwright() as playwright_instance:
        scraper = LunchScraper(playwright_instance, config)
        try:
            daily_lunches_data = scraper.scrape_lunches()
        except Exception as e:
            logger.critical(
                "Error irrecuperable durante la ejecucion del scraper: %s", e, exc_info=True)
            error_message = f"⚠️ Error crítico en el bot de almuerzos. No se pudo completar el scraping. Detalles: {str(e)[:200]}"
            # Usando send_message como en tu código
            telegram_notifier.send_message(error_message)
            return

    if not daily_lunches_data:
        logger.warning("No se obtuvieron datos de almuerzos del scraper.")
        telegram_notifier.send_message(
            "No se pudo obtener informacion de los almuerzos hoy.")
    else:
        has_any_real_data = any(
            (day_data.get('lunches') or day_data.get('period_message')) and not (
                "Error" in day_data.get('period_message', ''))
            for day_data in daily_lunches_data.values()
        )

        if not has_any_real_data and not all(day_data.get('lunches') for day_data in daily_lunches_data.values()):
            logger.info(
                "No se encontraron almuerzos o todos los días tuvieron errores de extraccion.")
            # Considera enviar una notificación si lo deseas:
            # telegram_notifier.send_message("No se encontraron almuerzos disponibles o hubo problemas al obtenerlos.")
        else:
            logger.info(
                "Datos de almuerzos extraidos. Preparando para enviar notificacion.")
            message_to_send = telegram_notifier.format_lunches_message(
                daily_lunches_data)
            telegram_notifier.send_message(message_to_send)

    logger.info("🏁 Aplicacion de notificacion de almuerzos finalizada.")


if __name__ == "__main__":
    main()
