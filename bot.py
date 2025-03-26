from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import requests
import os

# Configurações (Render.com vai gerenciar esses valores)
TOKEN = os.getenv("TOKEN")
MERCADO_PAGO_TOKEN = os.getenv("MERCADO_PAGO_TOKEN")
PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    "pdf2": "https://drive.google.com/file/d/1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp/view?usp=sharing",
    "pdf3": "https://drive.google.com/file/d/1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb/view?usp=sharing",
    "pdf4": "https://drive.google.com/file/d/1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac/view?usp=sharing",
    "pdf5": "https://drive.google.com/file/d/1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_/view?usp=sharing",
    "pdf6": "https://drive.google.com/file/d/1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN/view?usp=sharing",
}

# Iniciar o bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Planilha de Orçamento Familiar", callback_data='pdf1')],
        [InlineKeyboardButton("Guia de Compras Conscientes", callback_data='pdf2')],
        [InlineKeyboardButton("Dicas para Economizar Energia em Casa", callback_data='pdf3')],
        [InlineKeyboardButton("Receitas Econômicas e Saudáveis", callback_data='pdf4')],
        [InlineKeyboardButton("Guia para Sair das Dívidas", callback_data='pdf5')],
        [InlineKeyboardButton("Planejador de Metas Financeiras", callback_data='pdf6')],
    ]
    await update.message.reply_text(
        "Escolha um PDF:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Processar escolha do usuário
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pdf_id = query.data

    # Gerar link de pagamento via Mercado Pago
    response = requests.post(
        "https://api.mercadopago.com/v1/payments",
        headers={"Authorization": f"Bearer {MERCADO_PAGO_TOKEN}"},
        json={
            "transaction_amount": 10.00,
            "description": f"PDF {pdf_id}",
            "payment_method_id": "pix"
        }
    )

    if response.status_code == 200:
        link_pagamento = response.json()["point_of_interaction"]["transaction_data"]["ticket_url"]
        await query.message.reply_text(f"✅ Pague aqui: {link_pagamento}\n\nApós o pagamento, envie o ID aqui.")
    else:
        await query.message.reply_text("❌ Erro ao gerar o link. Tente novamente.")

# Verificar pagamento
async def handle_payment_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment_id = update.message.text
    response = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers={"Authorization": f"Bearer {MERCADO_PAGO_TOKEN}"}
    )
    
    if response.json().get("status") == "approved":
        await update.message.reply_text(f"🎉 Baixe seu PDF aqui: {PDF_LINKS['pdf1']}")  # Ajuste para o PDF correto
    else:
        await update.message.reply_text("⚠️ Pagamento não confirmado. Verifique e tente novamente.")

# Configurar e iniciar o bot
if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment_id))
    application.run_polling()

if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    
    # Encerra webhooks anteriores (se houver)
    await application.bot.delete_webhook()
    
    # Inicia o bot com polling
    application.run_polling()
    
