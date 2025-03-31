import os
import logging
import requests
import hmac
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request, jsonify

# ========================================================
# CONFIGURAÇÕES ESSENCIAIS
# ========================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Validação crítica de variáveis de ambiente
REQUIRED_ENV_VARS = {
    "TELEGRAM_TOKEN": "Token do Bot do Telegram",
    "MERCADOPAGO_TOKEN": "Access Token do Mercado Pago",
    "WEBHOOK_SECRET": "Chave secreta para validação",
    "RAILWAY_STATIC_URL": "URL de deploy do Railway"
}

missing_vars = [var for var, desc in REQUIRED_ENV_VARS.items() if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Variáveis ausentes: {', '.join(missing_vars)}")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
DOMINIO = os.getenv("RAILWAY_STATIC_URL")

# Links diretos dos PDFs (verificar permissões no Google Drive)
PDF_LINKS = {
    "pdf1": "https://drive.google.com/uc?export=download&id=1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF",
    "pdf2": "https://drive.google.com/uc?export=download&id=1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp",
    "pdf3": "https://drive.google.com/uc?export=download&id=1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb",
    "pdf4": "https://drive.google.com/uc?export=download&id=1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac",
    "pdf5": "https://drive.google.com/uc?export=download&id=1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_",
    "pdf6": "https://drive.google.com/uc?export=download&id=1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN"
}

# ========================================================
# INICIALIZAÇÃO DO SISTEMA
# ========================================================
app = Flask(__name__)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# ========================================================
# ROTAS PRINCIPAIS
# ========================================================
@app.route('/')
def health_check():
    return "🚀 Bot Online! Use /start no Telegram", 200

@app.route('/telegram_webhook', methods=['POST'])
def handle_telegram_update():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put(update)
        return jsonify(status="success"), 200
    except Exception as e:
        logger.error(f"Erro no webhook Telegram: {str(e)}")
        return jsonify(status="error"), 500

@app.route('/mercadopago_webhook', methods=['POST'])
def handle_mercadopago_notification():
    try:
        # Validação HMAC
        signature = request.headers.get('X-Signature', '')
        payload = request.get_data()
        computed_hash = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(f'sha256={computed_hash}', signature):
            logger.warning("Tentativa de acesso não autorizada!")
            return jsonify(status="forbidden"), 403

        # Processamento do pagamento
        payment_id = request.json.get('data', {}).get('id')
        if not payment_id:
            return jsonify(status="invalid data"), 400

        # Consulta detalhada do pagamento
        response = requests.get(
            f'https://api.mercadopago.com/v1/payments/{payment_id}',
            headers={'Authorization': f'Bearer {MERCADOPAGO_TOKEN}'},
            timeout=10
        )
        payment_data = response.json()

        if payment_data.get('status') == 'approved':
            user_id, pdf_id = payment_data['external_reference'].split(':')
            if pdf_link := PDF_LINKS.get(pdf_id):
                # Envio do PDF via Telegram
                requests.post(
                    f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
                    json={
                        'chat_id': user_id,
                        'text': f'✅ *Pagamento Aprovado!* \n\n📄 Acesse seu material: {pdf_link}',
                        'parse_mode': 'Markdown',
                        'disable_web_page_preview': True
                    },
                    timeout=10
                )

        return jsonify(status="processed"), 200

    except Exception as e:
        logger.error(f"Falha crítica: {str(e)}")
        return jsonify(status="server error"), 500

# ========================================================
# LÓGICA DO BOT
# ========================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu = [
        [InlineKeyboardButton("📊 Planilha Orçamento", callback_data='pdf1')],
        [InlineKeyboardButton("🛒 Guia Compras Inteligentes", callback_data='pdf2')],
        [InlineKeyboardButton("💡 Economia de Energia", callback_data='pdf3')],
        [InlineKeyboardButton("🍲 Receitas Econômicas", callback_data='pdf4')],
        [InlineKeyboardButton("🚀 Eliminação de Dívidas", callback_data='pdf5')],
        [InlineKeyboardButton("🎯 Metas Financeiras", callback_data='pdf6')]
    ]
    await update.message.reply_text(
        "📚 *Biblioteca Digital - Materiais Exclusivos*\n💵 Valor: R\$9,90 por item",
        reply_markup=InlineKeyboardMarkup(menu),
        parse_mode="MarkdownV2"
    )

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        # Gerar pagamento no Mercado Pago
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

        # Extrair link de pagamento
        payment_info = response.json()
        payment_url = payment_info['point_of_interaction']['transaction_data']['ticket_url']
        
        await query.edit_message_text(
            f"🔗 [Clique para gerar QR Code PIX]({payment_url})\n\n"
            "Após a confirmação do pagamento, seu material será enviado automaticamente!",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        await query.edit_message_text("⚠️ Serviço temporariamente indisponível. Tente novamente em alguns minutos.")

# ========================================================
# CONFIGURAÇÃO DE DEPLOY
# ========================================================
def setup_application():
    # Registro de handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CallbackQueryHandler(handle_button_click))

    # Configuração automática do webhook
    async def initialize_webhook(app):
        await app.bot.set_webhook(
            url=f'{DOMINIO}/telegram_webhook',
            secret_token=WEBHOOK_SECRET
        )
        logger.info("✅ Webhook configurado com sucesso!")

    application.post_init = initialize_webhook

def run_server():
    setup_application()
    application.run_webhook(
        listen='0.0.0.0',
        port=int(os.getenv('PORT', 8080)),
        webhook_url=f'{DOMINIO}/telegram_webhook',
        secret_token=WEBHOOK_SECRET
    )

if __name__ == '__main__':
    run_server()
