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

# Validação rigorosa das variáveis
REQUIRED_ENV_VARS = [
    "TELEGRAM_TOKEN",
    "MERCADOPAGO_TOKEN",
    "WEBHOOK_SECRET",      # Para Telegram
    "MP_HMAC_SECRET",      # Para Mercado Pago
    "RAILWAY_STATIC_URL"
]

missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Variáveis faltando: {', '.join(missing_vars)}")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")       # Usado no Telegram
MP_HMAC_SECRET = os.getenv("MP_HMAC_SECRET")       # Usado no Mercado Pago
DOMINIO = os.getenv("RAILWAY_STATIC_URL")

# Links diretos dos PDFs (formato correto para download)
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
# ROTAS FLASK
# ========================================================
@app.route('/')
def health_check():
    return "🚀 Bot Online! Use /start no Telegram", 200

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    # Validação do Secret Token do Telegram
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        logger.warning("Tentativa de acesso não autorizada ao webhook do Telegram!")
        return jsonify(status="forbidden"), 403
    
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put(update)
        return jsonify(status="success"), 200
    except Exception as e:
        logger.error(f"Erro no webhook Telegram: {str(e)}")
        return jsonify(status="error"), 500

@app.route('/mercadopago_webhook', methods=['POST'])
def mercadopago_webhook():
    try:
        # Validação HMAC do Mercado Pago
        signature = request.headers.get('X-Signature', '')
        payload = request.get_data()
        computed_hash = hmac.new(
            MP_HMAC_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(f'sha256={computed_hash}', signature):
            logger.warning("Tentativa de acesso não autorizada via MP!")
            return jsonify(status="forbidden"), 403

        # Processamento do pagamento
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
                        'text': f'✅ *Pagamento Aprovado!* \n\n📄 Acesse: {pdf_link}',
                        'parse_mode': 'Markdown',
                        'disable_web_page_preview': True
                    },
                    timeout=10
                )

        return jsonify(status="processed"), 200

    except Exception as e:
        logger.error(f"ERRO MP: {str(e)}")
        return jsonify(status="error"), 500

# ========================================================
# HANDLERS DO BOT
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info(f"/start acionado por: {update.effective_user.username}")
        keyboard = [
            [InlineKeyboardButton("📊 Planilha Orçamento", callback_data='pdf1')],
            [InlineKeyboardButton("🛒 Guia Compras", callback_data='pdf2')],
            [InlineKeyboardButton("💡 Economia Energia", callback_data='pdf3')],
            [InlineKeyboardButton("🍲 Receitas Econômicas", callback_data='pdf4')],
            [InlineKeyboardButton("🚀 Sair das Dívidas", callback_data='pdf5')],
            [InlineKeyboardButton("🎯 Metas Financeiras", callback_data='pdf6')]
        ]
        await update.message.reply_text(
            "📚 *Materiais Disponíveis* \nValor: R\$9,90 cada",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"ERRO NO /start: {str(e)}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                'payer': {
                    'email': 'comprador@exemplo.com',
                    'identification': {
                        'type': 'CPF',
                        'number': '12345678909'
                    }
                },
                'description': f'PDF {query.data}',
                'external_reference': f'{query.from_user.id}:{query.data}',
                'notification_url': f'{DOMINIO}/mercadopago_webhook'
            },
            timeout=15
        )

        payment_link = response.json()['point_of_interaction']['transaction_data']['ticket_url']
        await query.edit_message_text(
            f"💳 [Clique para pagar via PIX]({payment_link})\n\n"
            "Após a confirmação, o PDF será enviado automaticamente!",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"ERRO NO BOTÃO: {str(e)}")
        await query.edit_message_text("⚠️ Erro temporário. Tente novamente.")

# ========================================================
# CONFIGURAÇÃO FINAL
# ========================================================
def main():
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))

    async def post_init(app):
        await app.bot.set_webhook(
            url=f'{DOMINIO}/telegram_webhook',
            secret_token=WEBHOOK_SECRET
        )
        logger.info("✅ Webhook do Telegram configurado!")

    application.post_init = post_init
    application.run_webhook(
        listen='0.0.0.0',
        port=int(os.getenv('PORT', 8080)),
        webhook_url=f'{DOMINIO}/telegram_webhook',
        secret_token=WEBHOOK_SECRET
    )

if __name__ == '__main__':
    main()
