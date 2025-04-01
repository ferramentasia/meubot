import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request

# Configuração básica
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variáveis de ambiente
TOKEN = os.environ['TELEGRAM_TOKEN']
SECRET = os.environ['TELEGRAM_SECRET']
URL = os.environ['RAILWAY_URL']

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [[InlineKeyboardButton("TESTAR BOTÃO", callback_data='test')]]
        await update.message.reply_text(
            "✅ Bot funcionando!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info("Comando /start recebido de %s", update.effective_user.id)
    except Exception as e:
        logger.error(f"ERRO: {str(e)}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🎉 Botão funcionando!")

# Configuração do Flask
app = Flask(__name__)
bot_app = Application.builder().token(TOKEN).build()

@app.post('/webhook')
def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != SECRET:
        return 'Acesso negado!', 403
    
    try:
        update = Update.de_json(request.get_json(), bot_app.bot)
        bot_app.update_queue.put(update)
        return 'OK', 200
    except Exception as e:
        logger.error(f"ERRO NO WEBHOOK: {str(e)}")
        return 'Erro', 500

if __name__ == '__main__':
    # Registra comandos
    bot_app.add_handler(CommandHandler('start', start))
    bot_app.add_handler(CallbackQueryHandler(button_handler))
    
    # Inicia servidor
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
