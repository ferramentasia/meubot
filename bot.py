import os
import logging
import requests
import hmac
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request, jsonify

# ========================================================
# CONFIGURAÇÕES INICIAIS
# ========================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Validação rigorosa das variáveis de ambiente
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

# Links dos PDFs (verificar permissões no Google Drive)
PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    "pdf2": "https://drive.google.com/file/d/1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp/view?usp=sharing",
    "pdf3": "https://drive.google.com/file/d/1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb/view?usp=sharing",
    "pdf4": "https://drive.google.com/file/d/1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac/view?usp=sharing",
    "pdf5": "https://drive.google.com/file/d/1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_/view?usp=sharing",
    "pdf6": "https://drive.google.com/file/d/1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN/view?usp=sharing"
}

# ========================================================
# INICIALIZAÇÃO DO FLASK E TELEGRAM BOT
# ========================================================
app = Flask(__name__)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# ========================================================
# ROTAS FLASK
# ========================================================
@app.route('/')
def home():
    return "✅ Bot em operação. Use /start no Telegram"

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return jsonify(success=True), 200

@app.route('/mercadopago_webhook', methods=['POST'])
def handle_mercadopago():
    try:
        # Validação de segurança
        signature = request.headers.get('X-Signature')
        payload = request.get_data()
        generated_hash = hmac.new(
            key=WEBHOOK_SECRET.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(f'sha256={generated_hash}', signature):
            logger.warning("Tentativa de acesso não autorizada!")
            return jsonify(status="Unauthorized"), 403

        # Processar notificação
        payment_id = request.json.get('data', {}).get('id')
        if not payment_id:
            return jsonify(status="Invalid data"), 400

        # Buscar detalhes do pagamento
        mp_response = requests.get(
            f'https://api.mercadopago.com/v1/payments/{payment_id}',
            headers={'Authorization': f'Bearer {MERCADOPAGO_TOKEN}'},
            timeout=10
        )
        mp_response.raise_for_status()
        payment_data = mp_response.json()

        if payment_data.get('status') == 'approved':
            user_id, pdf_id = payment_data['external_reference'].split(':')
            pdf_link = PDF_LINKS.get(pdf_id)
            
            if pdf_link:
                requests.post(
                    f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
                    json={
                        'chat_id': user_id,
                        'text': f'✅ Pagamento confirmado!\n\n🔗 Acesse seu PDF: {pdf_link}',
                        'parse_mode': 'Markdown',
                        'disable_web_page_preview': True
                    }
                )

        return jsonify(status="success"), 200

    except Exception as error:
        logger.error(f"Erro no webhook: {str(error)}")
        return jsonify(status="error"), 500

# ========================================================
# HANDLERS DO TELEGRAM
# ========================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Planilha Orçamento", callback_data='pdf1')],
        [InlineKeyboardButton("🛒 Guia Compras", callback_data='pdf2')],
        [InlineKeyboardButton("💡 Economia Energia", callback_data='pdf3')],
        [InlineKeyboardButton("🍲 Receitas Econômicas", callback_data='pdf4')],
        [InlineKeyboardButton("🚀 Sair das Dívidas", callback_data='pdf5')],
        [InlineKeyboardButton("🎯 Metas Financeiras", callback_data='pdf6')]
    ]
    await update.message.reply_text(
        "📚 *Materiais Disponíveis:*\nValor: R\$9,90 cada",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2"
    )

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        user_id = query.from_user.id
        pdf_id = query.data

        # Criar pagamento no Mercado Pago
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
                'description': f'PDF {pdf_id}',
                'external_reference': f'{user_id}:{pdf_id}',
                'notification_url': f'{DOMINIO}/mercadopago_webhook'
            },
            timeout=15
        )

        if response.status_code >= 400:
            logger.error(f"Erro MP: {response.text}")
            await query.edit_message_text("❌ Erro ao gerar pagamento")
            return

        payment_link = response.json()['point_of_interaction']['transaction_data']['ticket_url']
        await query.edit_message_text(
            f"💳 [Clique para pagar via PIX]({payment_link})\n\n"
            "Após a confirmação, seu PDF será enviado automaticamente!",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    except Exception as error:
        logger.error(f"Erro no bot: {str(error)}")
        await query.edit_message_text("⚠️ Ocorreu um erro. Tente novamente mais tarde.")

# ========================================================
# CONFIGURAÇÃO FINAL
# ========================================================
def main():
    # Registrar handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CallbackQueryHandler(handle_button_click))

    # Configurar webhook no startup
    async def setup_webhook(app):
        await app.bot.set_webhook(
            url=f'{DOMINIO}/telegram_webhook',
            secret_token=WEBHOOK_SECRET
        )

    application.post_init = setup_webhook

    # Iniciar servidor
    port = int(os.environ.get('PORT', 8080))
    application.run_webhook(
        listen='0.0.0.0',
        port=port,
        webhook_url=f'{DOMINIO}/telegram_webhook',
        secret_token=WEBHOOK_SECRET
    )

if __name__ == '__main__':
    main()
