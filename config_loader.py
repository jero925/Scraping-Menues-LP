import logging
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Carga y gestiona la configuración de la aplicación."""
    def __init__(self, env_file_path: str = ".env"):
        self._env_values = dotenv_values(env_file_path)
        if not self._env_values:
            logger.warning("No se pudo cargar el archivo .env desde %s o está vacío.", env_file_path)

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
