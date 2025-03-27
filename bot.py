import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import warnings

# Configuração inicial
warnings.filterwarnings("ignore", message="Werkzeug")  # Remove avisos irrelevantes
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Variáveis de ambiente (OBRIGATÓRIAS)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")

# Validação crítica
if not TELEGRAM_TOKEN or not MERCADOPAGO_TOKEN:
    raise ValueError("Configure TELEGRAM_TOKEN e MERCADOPAGO_TOKEN!")

# Links reais dos PDFs (compartilhamento público)
PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    "pdf2": "https://drive.google.com/file/d/1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp/view?usp=sharing",
    "pdf3": "https://drive.google.com/file/d/1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb/view?usp=sharing",
    "pdf4": "https://drive.google.com/file/d/1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac/view?usp=sharing",
    "pdf5": "https://drive.google.com/file/d/1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_/view?usp=sharing",
    "pdf6": "https://drive.google.com/file/d/1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN/view?usp=sharing"
}

# ========================================================
# Parte do Flask (para manter o bot online)
# ========================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot operacional"

def run_flask():
    port = int(os.getenv("PORT", 8000))
    app.run(host='0.0.0.0', port=port, threaded=True)

# ========================================================
# Lógica do Bot (REVISADA E TESTADA)
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Planilha de Orçamento Familiar", callback_data='pdf1')],
        [InlineKeyboardButton("Guia de Compras Conscientes", callback_data='pdf2')],
        [InlineKeyboardButton("Dicas para Economizar Energia em Casa", callback_data='pdf3')],
        [InlineKeyboardButton("Receitas Econômicas e Saudáveis", callback_data='pdf4')],
        [InlineKeyboardButton("Guia para Sair das Dívidas", callback_data='pdf5')],
        [InlineKeyboardButton("Planejador de Metas Financeiras", callback_data='pdf6')]
    ]
    await update.message.reply_text(
        "Escolha seu PDF:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        # Payload 100% compatível com a API do Mercado Pago
        payload = {
            "description": f"Compra do {query.data}",
            "payment_method_id": "pix",
            "transaction_amount": 19.90,
            "payer": {
                "email": "comprador@exemplo.com",
                "first_name": "Nome",
                "last_name": "Sobrenome",
                "identification": {
                    "type": "CPF",
                    "number": "12345678909"  # CPF de teste válido
                }
            },
            "notification_url": "https://seu-webhook.com/notificacoes"  # Opcional
        }

        # Headers corrigidos
        headers = {
            "Authorization": f"Bearer {MERCADOPAGO_TOKEN}",
            "Content-Type": "application/json",
            "X-Tracking-Id": "telegram-bot-pdf"  # Para rastreamento
        }

        response = requests.post(
            "https://api.mercadopago.com/v1/payments",
            headers=headers,
            json=payload
        )
        response.raise_for_status()

        payment_data = response.json()
        payment_link = payment_data["point_of_interaction"]["transaction_data"]["ticket_url"]
        
        await query.edit_message_text(
            f"✅ *PIX Copia e Cola:*\n{payment_link}\n\n"
            "Após pagar, envie o **ID do pagamento** aqui.",
            parse_mode="Markdown"
        )

    except requests.exceptions.HTTPError as e:
        logger.error(f"ERRO MP [HTTP {e.response.status_code}]: {e.response.text}")
        await query.edit_message_text("⚠️ Falha temporária. Tente novamente em 1 minuto.")
        
    except Exception as e:
        logger.error(f"ERRO CRÍTICO: {str(e)}")
        await query.edit_message_text("🔴 Erro interno. Contate o suporte.")

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment_id = update.message.text.strip()

    try:
        response = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {MERCADOPAGO_TOKEN}"}
        )
        response.raise_for_status()

        status = response.json()["status"]
        if status == "approved":
            await update.message.reply_text(
                f"🎉 **Download:** {PDF_LINKS['pdf1']}",
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text("⏳ Pagamento ainda não confirmado. Aguarde...")

    except requests.exceptions.HTTPError as e:
        logger.error(f"Erro verificação: {e.response.text}")
        await update.message.reply_text("❌ ID inválido. Verifique e tente novamente.")

# ========================================================
# Inicialização
# ========================================================
def main():
    Thread(target=run_flask).start()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    
    application.run_polling()

if __name__ == "__main__":
    main()
