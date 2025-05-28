import logging
import sys
import io

def setup_logging():
    """
    Configura el logging para la aplicación.
    Intenta establecer la codificación de la consola a UTF-8 y configura
    los manejadores para archivos y la consola.
    """
    # --- Intento de configurar la codificación de la consola a UTF-8 (especialmente para Windows) ---
    try:
        if hasattr(sys.stderr, 'reconfigure') and isinstance(sys.stderr, io.TextIOBase) and sys.stderr.encoding.lower() != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')
        if hasattr(sys.stdout, 'reconfigure') and isinstance(sys.stdout, io.TextIOBase) and sys.stdout.encoding.lower() != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception as e:
        # Usar print aquí ya que el logger podría no estar completamente configurado o podría causar problemas.
        print(f"[ADVERTENCIA PRE-LOGGING] No se pudo reconfigurar la codificación de sys.stdout/sys.stderr a UTF-8: {e}", file=sys.stderr)

    # Configuración de Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)s %(name)s] - %(message)s",
        handlers=[
            logging.FileHandler("lunch_app.log", mode='w', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

if __name__ == "__main__":
    logger = logging.getLogger(__name__) # Obtener logger para este módulo
    logger.info("Configuración de logging completada desde logger_config.py.")