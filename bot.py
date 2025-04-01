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
# ======================== =================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Validação de variáveis
REQUIRED_ENV_VARS = [
    "TELEGRAM_TOKEN",
    "MERCADOPAGO_TOKEN",
    "TELEGRAM_WEBHOOK_SECRET",
    "MP_HMAC_SECRET",
    "RAILWAY_STATIC_URL"
]

missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Variáveis faltando: {', '.join(missing_vars)}")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")
TELEGRAM_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
MP_HMAC = os.getenv("MP_HMAC_SECRET")
DOMINIO = os.getenv("RAILWAY_STATIC_URL")

PDF_LINKS = {
    "pdf1": "https://drive.google.com/uc?export=download&id=1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF",
    "pdf2": "https://drive.google.com/uc?export=download&id=1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp",
    "pdf3": "https://drive.google.com/uc?export=download&id=1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb",
    "pdf4": "https://drive.google.com/uc?export=download&id=1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac",
    "pdf5": "https://drive.google.com/uc?export=download&id=1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_",
    "pdf6": "https://drive.google.com/uc?export=download&id=1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN"
}

# ========================================================
# HANDLERS PRINCIPAIS (DEVEM VIR ANTES DA CONFIGURAÇÃO)
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        logger.info(f"Novo usuário: {user.id} @{user.username}")
        
        keyboard = [
            [InlineKeyboardButton("📊 Planilha Orçamento", callback_data='pdf1')],
            [InlineKeyboardButton("🛒 Guia Compras", callback_data='pdf2')],
            [InlineKeyboardButton("💡 Economia Energia", callback_data='pdf3')],
            [InlineKeyboardButton("🍲 Receitas", callback_data='pdf4')],
            [InlineKeyboardButton("🚀 Dívidas", callback_data='pdf5')],
            [InlineKeyboardButton("🎯 Metas", callback_data='pdf6')]
        ]
        
        await update.message.reply_text(
            "📚 *Materiais Disponíveis*\nValor: R\$9,90 cada",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="MarkdownV2"
        )

    except Exception as e:
        logger.error(f"ERRO NO /start: {str(e)}")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        response = requests.post(
            'https://api.mercadopago.com/v1/payments',
            headers={
                'Authorization': f'Bearer {MERCADOPAGO_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'transaction_amount': 9.90,
                'payment_method_id': 'pix',
                'payer': {'email': 'user@example.com'},
                'description': f'PDF {query.data}',
                'external_reference': f'{query.from_user.id}:{query.data}',
                'notification_url': f'{DOMINIO}/mercadopago_webhook'
            },
            timeout=15
        )

        payment_url = response.json()['point_of_interaction']['transaction_data']['ticket_url']
        await query.edit_message_text(
            f"💳 [Pagar via PIX]({payment_url})",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"ERRO NO BOTÃO: {str(e)}")
        await query.edit_message_text("⚠️ Tente novamente mais tarde.")

# ========================================================
# CONFIGURAÇÃO DO FLASK
# ========================================================
app = Flask(__name__)
application = Application.builder().token(TELEGRAM_TOKEN).build()

@app.route('/', methods=['GET'])
def health_check():
    return "🚀 Bot Online! Use /start no Telegram", 200

@app.route('/telegram_webhook', methods=['POST'])
def handle_telegram():
    try:
        if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != TELEGRAM_SECRET:
            logger.warning("Acesso não autorizado!")
            return jsonify(status="forbidden"), 403

        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put(update)
        return jsonify(status="success"), 200

    except Exception as e:
        logger.error(f"ERRO: {str(e)}")
        return jsonify(status="error"), 500

@app.route('/mercadopago_webhook', methods=['POST'])
def handle_mercadopago():
    try:
        signature = request.headers.get('X-Signature', '')
        payload = request.get_data()
        computed_hash = hmac.new(MP_HMAC.encode(), payload, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(f'sha256={computed_hash}', signature):
            logger.warning("Assinatura inválida!")
            return jsonify(status="forbidden"), 403

        payment_id = request.json.get('data', {}).get('id')
        if not payment_id:
            return jsonify(status="bad request"), 400

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
        logger.error(f"ERRO MP: {str(e)}")
        return jsonify(status="error"), 500

# ========================================================
# INICIALIZAÇÃO CORRETA
# ========================================================
def main():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button))
    
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        webhook_url=f"{DOMINIO}/telegram_webhook",
        secret_token=TELEGRAM_SECRET
    )

if __name__ == '__main__':
    main()
