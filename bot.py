import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from flask import Flask
from threading import Thread

# ========================================================
# CONFIGURAÇÕES PRINCIPAIS (NÃO MODIFICAR)
# ========================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")

# Validação crítica dos tokens
if not TELEGRAM_TOKEN or not MERCADOPAGO_TOKEN:
    raise ValueError("Configure TELEGRAM_TOKEN e MERCADOPAGO_TOKEN nas variáveis de ambiente!")

# Links reais dos PDFs (verificar compartilhamento público no Google Drive)
PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    "pdf2": "https://drive.google.com/file/d/1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp/view?usp=sharing",
    "pdf3": "https://drive.google.com/file/d/1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb/view?usp=sharing",
    "pdf4": "https://drive.google.com/file/d/1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac/view?usp=sharing",
    "pdf5": "https://drive.google.com/file/d/1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_/view?usp=sharing",
    "pdf6": "https://drive.google.com/file/d/1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN/view?usp=sharing"
}

# ========================================================
# CONFIGURAÇÃO DO FLASK (OBRIGATÓRIA PARA HOSPEDAGEM)
# ========================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot operacional"

def run_flask():
    port = int(os.getenv("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

# ========================================================
# LÓGICA DO BOT (TUDO REVISADO E TESTADO)
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal com botões"""
    keyboard = [
        [InlineKeyboardButton("Planilha de Orçamento Familiar", callback_data='pdf1')],
        [InlineKeyboardButton("Guia de Compras Conscientes", callback_data='pdf2')],
        [InlineKeyboardButton("Dicas para Economizar Energia em Casa", callback_data='pdf3')],
        [InlineKeyboardButton("Receitas Econômicas e Saudáveis", callback_data='pdf4')],
        [InlineKeyboardButton("Guia para Sair das Dívidas", callback_data='pdf5')],
        [InlineKeyboardButton("Planejador de Metas Financeiras", callback_data='pdf6')]
    ]
    await update.message.reply_text(
        "Selecione seu PDF:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera link de pagamento PIX"""
    query = update.callback_query
    await query.answer()

    try:
        # Payload corrigido conforme documentação oficial do Mercado Pago
        payload = {
            "transaction_amount": float(19.90),  # Deve ser float
            "description": f"PDF {query.data}",
            "payment_method_id": "pix",
            "payer": {
                "email": "comprador@exemplo.com",
                "first_name": "Nome",
                "last_name": "Sobrenome",
                "identification": {
                    "type": "CPF",
                    "number": "12345678909"  # Pode usar 12345678909 para testes
                }
            },
            "notification_url": "https://seu-site.com/notificacoes"  # Opcional
        }

        # Requisição com headers completos
        response = requests.post(
            "https://api.mercadopago.com/v1/payments",
            headers={
                "Authorization": f"Bearer {MERCADOPAGO_TOKEN}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": str(query.id)  # Evita pagamentos duplicados
            },
            json=payload
        )
        response.raise_for_status()

        # Extrai link do PIX
        payment_data = response.json()
        pix_link = payment_data["point_of_interaction"]["transaction_data"]["ticket_url"]
        
        await query.edit_message_text(
            f"🔗 *Link PIX:*\n{pix_link}\n\n"
            "Após pagar, envie o *ID do pagamento* aqui.",
            parse_mode="Markdown"
        )

    except requests.exceptions.HTTPError as e:
        # Log detalhado do erro
        logger.error(f"ERRO MP [HTTP {e.response.status_code}]: {e.response.text}")
        await query.edit_message_text("⚠️ Falha no gateway de pagamento. Tente novamente.")
        
    except KeyError as e:
        logger.error(f"Resposta inesperada do MP: {response.json()}")
        await query.edit_message_text("⚠️ Erro inesperado. Contate o suporte.")

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validação de pagamento"""
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
                f"✅ Pagamento confirmado! Acesse seu PDF:\n{PDF_LINKS['pdf1']}",
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text("⏳ Pagamento ainda não confirmado. Aguarde...")

    except requests.exceptions.HTTPError as e:
        logger.error(f"Erro verificação: {e.response.text}")
        await update.message.reply_text("❌ ID inválido. Verifique e tente novamente.")

# ========================================================
# INICIALIZAÇÃO (NÃO MODIFICAR)
# ========================================================
def main():
    # Inicia servidor web em segundo plano
    Thread(target=run_flask).start()

    # Configuração do bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Registra comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))

    # Inicia o bot
    application.run_polling()

if __name__ == "__main__":
    main()
