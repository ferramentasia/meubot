import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import requests

# Configuração básica
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Variáveis de ambiente (configure no Render)
TOKEN = os.getenv("TELEGRAM_TOKEN")
MP_TOKEN = os.getenv("MERCADOPAGO_TOKEN")
PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    "pdf2": "https://drive.google.com/file/d/1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp/view?usp=sharing",
    "pdf3": "https://drive.google.com/file/d/1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb/view?usp=sharing",
    "pdf4": "https://drive.google.com/file/d/1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac/view?usp=sharing",
    "pdf5": "https://drive.google.com/file/d/1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_/view?usp=sharing",
    "pdf6": "https://drive.google.com/file/d/1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN/view?usp=sharing"
}

# ----- Handlers -----
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
        "📚 Escolha o PDF que deseja comprar:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        # Cria pagamento no Mercado Pago
        response = requests.post(
            "https://api.mercadopago.com/v1/payments",
            headers={"Authorization": f"Bearer {MP_TOKEN}"},
            json={
                "transaction_amount": 19.90,
                "payment_method_id": "pix",
                "description": f"PDF {query.data}",
                "notification_url": "https://seu-webhook.com/notifications"  # Opcional
            }
        )
        response.raise_for_status()
        
        payment_link = response.json()["point_of_interaction"]["transaction_data"]["ticket_url"]
        await query.edit_message_text(f"✅ Pague com PIX aqui: {payment_link}\n\nApós o pagamento, envie o ID do pagamento.")
        
    except Exception as e:
        logger.error(f"Erro no Mercado Pago: {e}")
        await query.edit_message_text("❌ Erro ao processar. Tente novamente mais tarde.")

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment_id = update.message.text
    try:
        response = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {MP_TOKEN}"}
        )
        response.raise_for_status()
        
        if response.json()["status"] == "approved":
            await update.message.reply_text(f"🎉 Download aqui: {PDF_LINKS['pdf1']}")
        else:
            await update.message.reply_text("⚠️ Pagamento não confirmado. Verifique e tente novamente.")
            
    except Exception as e:
        logger.error(f"Erro na verificação: {e}")
        await update.message.reply_text("⚠️ Erro na verificação. Contate o suporte.")

# ----- Configuração do Bot -----
def main():
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    
    # Inicia em modo polling (simples para deploy)
    application.run_polling()

if __name__ == "__main__":
    main()
