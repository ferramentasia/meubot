import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request

# =============== CONFIGURAÇÃO INICIAL ===============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variáveis obrigatórias
TOKEN = os.environ['TELEGRAM_TOKEN']
SECRET = os.environ['TELEGRAM_SECRET']
URL = os.environ['RAILWAY_URL']

# =============== LÓGICA DO BOT ===============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [
            [InlineKeyboardButton("Comprar PDF 1", callback_data='pdf1')],
            [InlineKeyboardButton("Comprar PDF 2", callback_data='pdf2')]
        ]
        
        await update.message.reply_text(
            "Escolha seu material:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        
    except Exception as e:
        logger.error(f"Erro no /start: {str(e)}")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Pagamento em desenvolvimento...")

# =============== SERVIDOR WEB ===============
app = Flask(__name__)
bot_app = Application.builder().token(TOKEN).build()

@app.post('/webhook')
def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != SECRET:
        return 'Unauthorized', 403
    
    update = Update.de_json(request.get_json(), bot_app.bot)
    bot_app.update_queue.put(update)
    return 'OK', 200

# =============== DEPLOY ===============
if __name__ == '__main__':
    # Registra handlers
    bot_app.add_handler(CommandHandler('start', start))
    bot_app.add_handler(CallbackQueryHandler(handle_button))
    
    # Configuração do servidor
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
