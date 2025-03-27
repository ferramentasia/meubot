import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import warnings

# ========================================================
# CONFIGURAÇÕES INICIAIS
# ========================================================
warnings.filterwarnings("ignore", message="Werkzeug")
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variáveis de ambiente (OBRIGATÓRIAS)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")

if not TELEGRAM_TOKEN or not MERCADOPAGO_TOKEN:
    raise ValueError("Configure as variáveis de ambiente!")

# Links dos PDFs (substitua com seus links)
PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    "pdf2": "https://drive.google.com/file/d/1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp/view?usp=sharing",
    "pdf3": "https://drive.google.com/file/d/1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb/view?usp=sharing",
    "pdf4": "https://drive.google.com/file/d/1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac/view?usp=sharing",
    "pdf5": "https://drive.google.com/file/d/1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_/view?usp=sharing",
    "pdf6": "https://drive.google.com/file/d/1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN/view?usp=sharing"
}

# ========================================================
# MENSAGENS (FÁCIL DE PERSONALIZAR)
# ========================================================
MENSAGENS = {
    "start": (
        "👋 *Bem\-vindo ao Bot de PDFs\!*\n\n"
        "Aqui você encontra materiais exclusivos em formato digital\.\n"
        "Use o comando /menu para ver a lista completa de PDFs disponíveis\."
    ),
    "menu": (
        "📚 *Nossos PDFs Disponíveis:*\n"
        "Cada PDF custa R$ 9,90 e foi elaborado com muita pesquisa, carinho e dedicação 📖💛💡📚\n"
        "Ao clicar aqui vc irá para a página de pagamento do Mercadopago\n"
        "Selecione o que deseja adquirir:"
    ),
    "instrucoes_pagamento": (
        "✅ *Pagamento via PIX*\n\n"
        "1\. Acesse o link: [Clique aqui]({payment_link})\n"
        "2\. Realize o pagamento\n"
        "3\. Envie o *ID do pagamento* aqui\n\n"
        "4\. Você receberá o link do PDF\n"
        "⚠️ Link válido por 24 horas\."
    ),
    "pagamento_aprovado": (
        "🎉 *Pagamento confirmado\!*\n\n"
        "Acesse seu PDF aqui:\n"
        "{pdf_link}"
    ),
    "erro_generico": "🔧 Ocorreu um erro. Nossa equipe já foi notificada!"
}

# ========================================================
# CONFIGURAÇÃO DO FLASK
# ========================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot em operação"

def run_flask():
    port = int(os.getenv("PORT", 8000))
    app.run(host='0.0.0.0', port=port, threaded=True)

# ========================================================
# LÓGICA PRINCIPAL DO BOT
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boas-vindas inicial"""
    await update.message.reply_text(
        MENSAGENS["start"],
        parse_mode="MarkdownV2",
        disable_web_page_preview=True
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra menu de PDFs"""
    keyboard = [
        [InlineKeyboardButton("Planilha de Orçamento Familiar", callback_data='pdf1')],
        [InlineKeyboardButton("Guia de Compras Conscientes", callback_data='pdf2')],
        [InlineKeyboardButton("Dicas para Economizar Energia em Casa", callback_data='pdf3')],
        [InlineKeyboardButton("Receitas Econômicas e Saudáveis", callback_data='pdf4')],
        [InlineKeyboardButton("Guia para Sair das Dívidas", callback_data='pdf5')],
        [InlineKeyboardButton("Planejador de Metas Financeiras", callback_data='pdf6')]
    ]
    
    await update.message.reply_text(
        MENSAGENS["menu"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2"
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa seleção de PDF"""
    query = update.callback_query
    await query.answer()

    try:
        pdf_id = query.data
        if pdf_id not in PDF_LINKS:
            raise ValueError("PDF não encontrado")

        # Geração do pagamento
        payload = {
            "transaction_amount": 1.00,
            "payment_method_id": "pix",
            "payer": {
                "email": "comprador@exemplo.com",
                "first_name": "Nome",
                "last_name": "Sobrenome",
                "identification": {"type": "CPF", "number": "12345678909"}
            },
            "description": f"PDF {pdf_id}",
        }

        headers = {
            "Authorization": f"Bearer {MERCADOPAGO_TOKEN}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(query.id)
        }

        response = requests.post(
            "https://api.mercadopago.com/v1/payments",
            headers=headers,
            json=payload
        )
        response.raise_for_status()

        payment_data = response.json()
        payment_link = payment_data["point_of_interaction"]["transaction_data"]["ticket_url"]
        
        # Resposta formatada
        await query.edit_message_text(
            MENSAGENS["instrucoes_pagamento"].format(payment_link=payment_link),
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )

        # Armazena relação PDF-ID (para exemplo, use banco de dados em produção)
        context.user_data["ultimo_pdf"] = pdf_id

    except requests.exceptions.HTTPError as e:
        logger.error(f"ERRO MP: {e.response.text}")
        await query.edit_message_text(MENSAGENS["erro_generico"])
    except Exception as e:
        logger.error(f"ERRO: {str(e)}")
        await query.edit_message_text(MENSAGENS["erro_generico"])

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica pagamento e entrega PDF"""
    payment_id = update.message.text.strip()

    try:
        response = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {MERCADOPAGO_TOKEN}"}
        )
        response.raise_for_status()

        status = response.json()["status"]
        if status == "approved":
            pdf_id = context.user_data.get("ultimo_pdf", "pdf1")
            await update.message.reply_text(
                MENSAGENS["pagamento_aprovado"].format(pdf_link=PDF_LINKS[pdf_id]),
                parse_mode="MarkdownV2",
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text("⏳ Pagamento ainda não confirmado...")

    except Exception as e:
        logger.error(f"ERRO VERIFICAÇÃO: {str(e)}")
        await update.message.reply_text(MENSAGENS["erro_generico"])

# ========================================================
# INICIALIZAÇÃO
# ========================================================
def main():
    # Servidor web
    Thread(target=run_flask).start()
    
    # Configuração do bot
    application = Application.builder()\
        .token(TELEGRAM_TOKEN)\
        .read_timeout(30)\
        .write_timeout(30)\
        .connect_timeout(30)\
        .build()
    
    # Registra handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    
    application.run_polling()

if __name__ == "__main__":
    main()
