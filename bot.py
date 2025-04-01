import os
import logging
import requests
import hmac
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request, jsonify

# ========================================================
# CONFIGURAÇÕES
# ========================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Modo DEBUG ativado
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduzir ruído

# Validação rigorosa de variáveis
REQUIRED_ENV_VARS = {
    "TELEGRAM_TOKEN": "Token do Bot do Telegram",
    "MERCADOPAGO_TOKEN": "Access Token do Mercado Pago",
    "TELEGRAM_WEBHOOK_SECRET": "Chave secreta para webhook do Telegram",
    "MP_HMAC_SECRET": "HMAC do Mercado Pago",
    "RAILWAY_STATIC_URL": "URL de deploy",
    "PORT": "Porta do servidor"
}

missing_vars = [var for var, desc in REQUIRED_ENV_VARS.items() if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Variáveis ausentes: {', '.join(missing_vars)}")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")
TELEGRAM_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
MP_HMAC = os.getenv("MP_HMAC_SECRET")
DOMINIO = os.getenv("RAILWAY_STATIC_URL")
PORT = int(os.getenv("PORT", 8080))

# Links diretos dos PDFs (verificar permissões)
PDF_LINKS = {
    "pdf1": "https://drive.google.com/uc?export=download&id=1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF",
    "pdf2": "https://drive.google.com/uc?export=download&id=1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp",
    "pdf3": "https://drive.google.com/uc?export=download&id=1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb",
    "pdf4": "https://drive.google.com/uc?export=download&id=1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac",
    "pdf5": "https://drive.google.com/uc?export=download&id=1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_",
    "pdf6": "https://drive.google.com/uc?export=download&id=1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN"
}

# ========================================================
# INICIALIZAÇÃO
# ========================================================
app = Flask(__name__)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# ========================================================
# ROTAS CORRIGIDAS
# ========================================================
@app.route('/', methods=['GET'])
def health_check():
    """Endpoint de saúde"""
    logger.debug("Health check acessado")
    return "🚀 Bot Online! Use /start no Telegram", 200

@app.route('/telegram_webhook', methods=['POST'])
def handle_telegram():
    """Endpoint para webhook do Telegram"""
    try:
        # Validação do secret token
        if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != TELEGRAM_SECRET:
            logger.error("Acesso não autorizado ao webhook do Telegram!")
            return jsonify(status="forbidden"), 403

        logger.debug("Payload recebido: %s", request.json)
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put(update)
        return jsonify(status="success"), 200

    except Exception as e:
        logger.error(f"ERRO NO WEBHOOK TELEGRAM: {str(e)}", exc_info=True)
        return jsonify(status="error"), 500

# ... (Manter rotas do Mercado Pago conforme última versão)

# ========================================================
# HANDLERS REFORÇADOS
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do comando /start"""
    try:
        user = update.effective_user
        logger.info(f"Novo usuário: {user.id} @{user.username}")
        
        keyboard = [
            [InlineKeyboardButton("📊 Planilha Orçamento", callback_data='pdf1')],
            [InlineKeyboardButton("🛒 Guia Compras Inteligentes", callback_data='pdf2')],
            [InlineKeyboardButton("💡 Economia de Energia", callback_data='pdf3')],
            [InlineKeyboardButton("🍲 Receitas Econômicas", callback_data='pdf4')],
            [InlineKeyboardButton("🚀 Eliminação de Dívidas", callback_data='pdf5')],
            [InlineKeyboardButton("🎯 Metas Financeiras", callback_data='pdf6')]
        ]
        
        await update.message.reply_text(
            "📚 *Biblioteca Digital - Materiais Exclusivos*\n💵 Valor: R\$9,90 por item",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="MarkdownV2"
        )
        logger.debug("Resposta /start enviada com sucesso")

    except Exception as e:
        logger.error(f"FALHA CRÍTICA NO /start: {str(e)}", exc_info=True)
        if update.message:
            await update.message.reply_text("⚠️ Serviço temporariamente indisponível")

# ... (Manter outros handlers conforme última versão)

# ========================================================
# INICIALIZAÇÃO ROBUSTA
# ========================================================
def setup_application():
    """Configuração inicial da aplicação"""
    try:
        logger.info("Iniciando configuração...")
        
        # Handlers
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CallbackQueryHandler(handle_button))
        
        # Configuração do webhook
        application.run_webhook(
            listen='0.0.0.0',
            port=PORT,
            webhook_url=f"{DOMINIO}/telegram_webhook",
            secret_token=TELEGRAM_SECRET
        )
        logger.info("Aplicação iniciada com sucesso na porta %d", PORT)
        
    except Exception as e:
        logger.critical("FALHA NA INICIALIZAÇÃO: %s", str(e), exc_info=True)
        raise

if __name__ == '__main__':
    setup_application()
