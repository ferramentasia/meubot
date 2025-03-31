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
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Validação de variáveis
REQUIRED_ENV_VARS = [
    "TELEGRAM_TOKEN",
    "MERCADOPAGO_TOKEN",
    "WEBHOOK_SECRET",
    "RAILWAY_STATIC_URL"
]

missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Variáveis faltando: {', '.join(missing_vars)}")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
DOMINIO = os.getenv("RAILWAY_STATIC_URL")

PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    # ... (outros PDFs)
}

# ========================================================
# INICIALIZAÇÃO
# ========================================================
app = Flask(__name__)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# ========================================================
# ROTAS FLASK
# ========================================================
@app.route('/')
def home():
    return "✅ Bot operacional. Use /start no Telegram"

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return jsonify(success=True), 200

@app.route('/mercadopago_webhook', methods=['POST'])
def mercadopago_webhook():
    try:
        # Validação HMAC
        signature = request.headers.get('X-Signature')
        payload = request.get_data()
        generated_hash = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(f'sha256={generated_hash}', signature):
            logger.warning("Assinatura inválida!")
            return jsonify(status="error"), 403

        # Processar pagamento
        payment_id = request.json.get('data', {}).get('id')
        if not payment_id:
            return jsonify(status="invalid"), 400

        # Buscar detalhes
        response = requests.get(
            f'https://api.mercadopago.com/v1/payments/{payment_id}',
            headers={'Authorization': f'Bearer {MERCADOPAGO_TOKEN}'},
            timeout=10
        )
        payment_data = response.json()

        if payment_data.get('status') == 'approved':
            user_id, pdf_id = payment_data['external_reference'].split(':')
            if pdf_link := PDF_LINKS.get(pdf_id):
                requests.post(
                    f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
                    json={
                        'chat_id': user_id,
                        'text': f'✅ Pagamento confirmado!\\nAcesse: {pdf_link}',
                        'parse_mode': 'Markdown'
                    }
                )

        return jsonify(status="success"), 200

    except Exception as e:
        logger.error(f"ERRO: {str(e)}")
        return jsonify(status="error"), 500

# ========================================================
# HANDLERS DO BOT
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Planilha", callback_data='pdf1')],
        # ... (outros botões)
    ]
    await update.message.reply_text(
        "📚 *Materiais Disponíveis:*\\nPreço: R\$9,90",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="
