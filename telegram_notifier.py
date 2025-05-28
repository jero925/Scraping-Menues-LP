import logging
import requests

logger = logging.getLogger(__name__)

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

            if data.get('lunches'): 
                message_lines.append("🍛 <u>Menúes:</u>")
                for i, lunch_name in enumerate(data["lunches"], start=1):
                    message_lines.append(f"   {i}. {lunch_name}")
            else:
                message_lines.append("  <i>No hay menúes listados para este día o hubo un error.</i>")

        full_message = "\n".join(message_lines)
        logger.debug("Mensaje construido para Telegram:\n%s", full_message)
        return full_message

    def send_message(self, message_text: str) -> bool:
        """Envía un mensaje a Telegram."""
        payload = {
            "chat_id": self.chat_id,
            "text": message_text,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(self.send_url, data=payload, timeout=10)
            response.raise_for_status() 
            logger.info("Mensaje enviado a Telegram correctamente.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error("Error al enviar mensaje a Telegram: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                logger.error("Detalles de la respuesta: %s", e.response.text)
            return False