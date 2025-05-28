# 🥗 Wrapper Viandas LP

Este proyecto automatiza la extracción de los almuerzos disponibles en el sistema Odoo de ELEPE Servicios y los envía como mensaje estilizado a un bot personal de Telegram.

## 🚀 Funcionalidades

- Inicia sesión en el portal web de ELEPE.
- Extrae los menús disponibles para los días martes y jueves.
- Agrupa los menús con su respectivo mensaje de pedido.
- Envía los resultados a Telegram usando la API del bot.

## 📦 Requisitos

- Python 3.8 o superior
- Archivo `.env` con las siguientes variables:
  ```env
  EMAIL=tu_correo@ejemplo.com
  PASSWORD=tu_contraseña
  TELEGRAM_BOT_TOKEN=tu_token_de_bot
  TELEGRAM_CHAT_ID=tu_chat_id
  ```
  
- Dependencias necesarias:
  ```bash
  pip install python-dotenv playwright requests
  playwright install
  ```
  
## 🧪 Ejecución
Instalar dependencias de manera rápida con

  ```bash
  pip install -r requirements.txt
  ```

Ejecuta el script principal con:

  ```bash
  python main.py
  ```
  Este abrirá un navegador en segundo plano, iniciará sesión en el sitio web, buscará los almuerzos y enviará el mensaje a Telegram.
  
📄 Estructura del mensaje en Telegram
El bot enviará un mensaje con este formato:

```markdown
📅 Almuerzos disponibles

🍽️ Pedir el viernes 23/05 para el martes 27/05
   1. Carne al horno con papas bravas
   2. Hamburguesas árabes con trigo burgol y puré de batata

🍽️ Pedir el lunes 26/05 para el jueves 29/05
   1. Albóndigas salseadas en arvejas y papas al horno
   2. Bombas de pollo en coles gratinado
```

## 🛠 Solución de Problemas (Troubleshooting)
### 🧪 Problemas comunes con Playwright
Error	Causa probable	Solución
TimeoutError: Page is not visible	El sitio demoró más de lo esperado en cargar	Aumentá el sleep() o usá page.wait_for_selector()
browserType.launch: Executable doesn't exist	Faltan los binarios de navegador	Ejecutá playwright install nuevamente
Error al procesar un almuerzo: NoneType has no attribute...	El DOM cambió y no encuentra el selector	Revisá con DevTools los nuevos selectores CSS

### 🤖 Errores comunes en Telegram Bot API
Error	Causa probable	Solución
400 Bad Request: chat not found	El TELEGRAM_CHAT_ID es incorrecto	Verificá que sea un número correcto y que el bot esté autorizado en el chat
401 Unauthorized	Token inválido	Revisá TELEGRAM_BOT_TOKEN en el .env

## ✅ To-Do Futuro
- Soporte para más días de la semana.
- Poder ordenar directamente desde el script
- Ejecutar automáticamente con Task Scheduler (Windows) y/o servidor.
- Alerta si no hay menúes cargados.
- Logs persistentes.
