import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request, jsonify
from threading import Thread
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

# INSIRA SEUS LINKS REAIS AQUI
PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    "pdf2": "https://drive.google.com/file/d/1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp/view?usp=sharing",
    "pdf3": "https://drive.google.com/file/d/1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb/view?usp=sharing",
    "pdf4": "https://drive.google.com/file/d/1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac/view?usp=sharing",
    "pdf5": "https://drive.google.com/file/d/1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_/view?usp=sharing",
    "pdf6": "https://drive.google.com/file/d/1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN/view?usp=sharing"
}

# ========================================================
# CONFIGURAÇÃO DO FLASK (WEBSERVER)
# ========================================================
app = Flask(__name__)

# Rota principal para verificar se o servidor está online
@app.route('/')
def home():
    return "🚀 Bot em operação! Acesse via Telegram: t.me/seu_bot"

# Rota do webhook para processar pagamentos
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Validação de segurança
        signature = request.headers.get('X-Signature')
        payload = request.get_data()
        hash_obj = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256)
        
        if not hmac.compare_digest(signature, f"sha256={hash_obj.hexdigest()}"):
            logger.warning("Assinatura inválida!")
            return jsonify({"status": "error"}), 403

        payment_id = request.json.get('data', {}).get('id')
        if not payment_id:
            return jsonify({"status": "dados inválidos"}), 400

        # Busca detalhes do pagamento
        response = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {MERCADOPAGO_TOKEN}"}
        )
        payment_data = response.json()

        if payment_data.get('status') == 'approved':
            external_ref = payment_data.get('external_reference', '')
            if ':' in external_ref:
                user_id, pdf_id = external_ref.split(':')
                pdf_link = PDF_LINKS.get(pdf_id)
                
                if pdf_link:
                    # Envia o PDF via Telegram
                    application.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ *Pagamento Aprovado!*\n\nAcesse seu PDF: {pdf_link}",
                        parse_mode="MarkdownV2",
                        disable_web_page_preview=True
                    )
        
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return jsonify({"status": "error"}), 500

# ========================================================
# LÓGICA DO BOT TELEGRAM
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Bem-vindo à Loja de PDFs!*\n\nUse /menu para ver nossos produtos.",
        parse_mode="MarkdownV2"
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Planilha Orçamento Familiar", callback_data='pdf1')],
        [InlineKeyboardButton("🛒 Guia Compras Conscientes", callback_data='pdf2')],
        [InlineKeyboardButton("💡 Economia de Energia", callback_data='pdf3')],
        [InlineKeyboardButton("🍲 Receitas Econômicas", callback_data='pdf4')],
        [InlineKeyboardButton("🚀 Sair das Dívidas", callback_data='pdf5')],
        [InlineKeyboardButton("🎯 Planejador Metas Financeiras", callback_data='pdf6')]
    ]
    
    await update.message.reply_text(
        "📚 *Escolha seu PDF:*\n\n"
        "Todos por R\$9,90 • Pagamento via PIX\n"
        "Após a confirmação, enviaremos o link automaticamente!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2"
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    pdf_id = query.data
    user_id = query.from_user.id
    
    # Configuração do pagamento
    payload = {
        "transaction_amount": 1.00,
        "payment_method_id": "pix",
        "payer": {"email": "client@example.com"},
        "description": f"PDF {pdf_id}",
        "external_reference": f"{user_id}:{pdf_id}",
        "notification_url": f"{DOMINIO}/webhook"
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
            f"🔗 [Clique aqui para pagar via PIX]({payment_link})\n\n"
            "Após a confirmação do pagamento, enviaremos o PDF automaticamente!",
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Erro MP: {str(e)}")
        await query.edit_message_text("❌ Erro ao processar pagamento. Tente novamente.")

# ========================================================
# INICIALIZAÇÃO
# ========================================================
def run_flask():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8000)))

if __name__ == "__main__":
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Registra handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(handle_button))
    
    # Inicia servidor web em thread separada
    Thread(target=run_flask).start()
    
    # Inicia o bot
    application.run_polling()
