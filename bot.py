import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request, jsonify
import hmac
import hashlib

# ========================================================
# CONFIGURAÇÕES
# ========================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
DOMINIO = os.getenv("RAILWAY_STATIC_URL")

# LINKS REAIS DOS PDFs (SUBSTITUA)
PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    "pdf2": "https://drive.google.com/file/d/1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp/view?usp=sharing",
    "pdf3": "https://drive.google.com/file/d/1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb/view?usp=sharing",
    "pdf4": "https://drive.google.com/file/d/1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac/view?usp=sharing",
    "pdf5": "https://drive.google.com/file/d/1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_/view?usp=sharing",
    "pdf6": "https://drive.google.com/file/d/1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN/view?usp=sharing"
}

# ========================================================
# INICIALIZAÇÃO DO BOT
# ========================================================
application = Application.builder().token(TELEGRAM_TOKEN).build()
app = Flask(__name__)

# ========================================================
# ROTAS FLASK
# ========================================================
@app.route('/')
def home():
    return "🚀 Bot operacional! Envie /start no Telegram."

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    """Recebe atualizações do Telegram"""
    try:
        update = Update.de_json(request.get_json(), application.bot)
        application.process_update(update)
        return 'OK', 200
    except Exception as e:
        logger.error(f"Erro Telegram webhook: {str(e)}")
        return 'Erro', 500

@app.route('/mercadopago_webhook', methods=['POST'])
def mercadopago_webhook():
    """Processa pagamentos do Mercado Pago"""
    try:
        # Valida HMAC
        signature = request.headers.get('X-Signature')
        payload = request.get_data()
        hash_obj = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256)
        
        if not hmac.compare_digest(signature, f"sha256={hash_obj.hexdigest()}"):
            logger.error("Assinatura inválida!")
            return jsonify({"status": "assinatura inválida"}), 403

        # Processa pagamento
        payment_id = request.json.get('data', {}).get('id')
        response = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {MERCADOPAGO_TOKEN}"}
        )
        payment_data = response.json()

        if payment_data.get('status') == 'approved':
            external_ref = payment_data.get('external_reference', '')
            if ':' in external_ref:
                user_id, pdf_id = external_ref.split(':')
                if pdf_link := PDF_LINKS.get(pdf_id):
                    application.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ *Pagamento Aprovado!*\n\nAcesse: {pdf_link}",
                        parse_mode="MarkdownV2",
                        disable_web_page_preview=True
                    )
        
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"Erro MP webhook: {str(e)}")
        return jsonify({"status": "error"}), 500

# ========================================================
# COMANDOS DO BOT
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bem-vindo! Use /menu para ver os PDFs",
        parse_mode="MarkdownV2"
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Planilha Orçamento", callback_data='pdf1'),
        [InlineKeyboardButton("🛒 Guia Compras", callback_data='pdf2'),
        [InlineKeyboardButton("💡 Economia Energia", callback_data='pdf3'),
        [InlineKeyboardButton("🍲 Receitas Econômicas", callback_data='pdf4'),
        [InlineKeyboardButton("🚀 Sair das Dívidas", callback_data='pdf5'),
        [InlineKeyboardButton("🎯 Metas Financeiras", callback_data='pdf6')]
    ]
    
    await update.message.reply_text(
        "📚 *PDFs Disponíveis:*\nValor: R\$9,90 • Pagamento via PIX",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2"
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    pdf_id = query.data
    
    payload = {
        "transaction_amount": 1.00,
        "payment_method_id": "pix",
        "payer": {"email": "user@exemplo.com"},
        "description": f"PDF {pdf_id}",
        "external_reference": f"{user_id}:{pdf_id}",
        "notification_url": f"{DOMINIO}/mercadopago_webhook"
    }
    
    try:
        response = requests.post(
            "https://api.mercadopago.com/v1/payments",
            headers={"Authorization": f"Bearer {MERCADOPAGO_TOKEN}"},
            json=payload
        )
        payment_data = response.json()
        payment_link = payment_data['point_of_interaction']['transaction_data']['ticket_url']
        
        await query.edit_message_text(
            f"💳 [PAGAR VIA PIX]({payment_link})\n\nApós pagar, o PDF será enviado automaticamente!",
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Erro pagamento: {str(e)}")
        await query.edit_message_text("❌ Erro ao gerar pagamento. Tente novamente.")

# ========================================================
# INICIALIZAÇÃO
# ========================================================
def main():
    # Registra handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(handle_button))
    
    # Configura webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        webhook_url=f"{DOMINIO}/telegram_webhook",
        secret_token=WEBHOOK_SECRET
    )
    
    # Inicia Flask
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()
