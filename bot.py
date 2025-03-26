import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# Configuração básica
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variáveis de ambiente (configure no Render)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")
PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    "pdf2": "https://drive.google.com/file/d/1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp/view?usp=sharing",
    "pdf3": "https://drive.google.com/file/d/1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb/view?usp=sharing",
    "pdf4": "https://drive.google.com/file/d/1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac/view?usp=sharing",
    "pdf5": "https://drive.google.com/file/d/1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_/view?usp=sharing",
    "pdf6": "https://drive.google.com/file/d/1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN/view?usp=sharing"
}

# =================================================================
# Funções Principais
# =================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensagem inicial com botões de escolha"""
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
    

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a escolha do PDF e gera link de pagamento"""
    query = update.callback_query
    await query.answer()  # Confirma o clique
    
    try:
        # Dados OBRIGATÓRIOS para o Mercado Pago
        payload = {
            "transaction_amount": 19.90,  # Valor numérico (não usar string!)
            "payment_method_id": "pix",
            "payer": {
                "email": "comprador@exemplo.com",  # E-mail válido (mesmo fictício)
                "first_name": "Nome",              # Obrigatório
                "last_name": "Sobrenome"           # Obrigatório
            },
            "description": f"Compra do {query.data}",
            "installments": 1  # Campo obrigatório para a API
        }
        
        # Envia a requisição para o Mercado Pago
        response = requests.post(
            "https://api.mercadopago.com/v1/payments",
            headers={
                "Authorization": f"Bearer {MERCADOPAGO_TOKEN}",
                "Content-Type": "application/json",  # Header essencial
                "X-Tracking-Id": "telegram-bot-pdf"  # Para rastreamento
            },
            json=payload
        )
        response.raise_for_status()  # Gera erro para respostas 4xx/5xx
        
        # Extrai o link de pagamento
        payment_data = response.json()
        payment_link = payment_data["point_of_interaction"]["transaction_data"]["ticket_url"]
        
        await query.edit_message_text(
            f"💳 **Pague com PIX aqui:**\n{payment_link}\n\n"
            "Após o pagamento, envie o **ID do pagamento** para liberar o PDF."
        )
        
    except requests.exceptions.HTTPError as e:
        # Log detalhado para diagnóstico
        logger.error(f"Erro HTTP: {e.response.status_code} - Resposta: {e.response.text}")
        await query.edit_message_text("🔒 Erro na comunicação com o gateway de pagamento.")
        
    except Exception as e:
        logger.error(f"Erro crítico: {str(e)}")
        await query.edit_message_text("❌ Erro interno. Tente novamente mais tarde.")


async def handle_payment_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica se o pagamento foi aprovado"""
    payment_id = update.message.text.strip()
    
    try:
        # Consulta o status do pagamento
        response = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {MERCADOPAGO_TOKEN}"}
        )
        response.raise_for_status()
        
        payment_status = response.json()["status"]
        
        if payment_status == "approved":
            await update.message.reply_text(f"✅ **Pagamento confirmado!** Baixe seu PDF aqui: {PDF_LINKS['pdf1']}")
        else:
            await update.message.reply_text("⚠️ Pagamento não aprovado. Verifique e tente novamente.")
            
    except Exception as e:
        logger.error(f"Erro na verificação: {str(e)}")
        await update.message.reply_text("⚠️ Erro ao verificar pagamento. Contate o suporte.")

# =================================================================
# Configuração do Bot
# =================================================================

def main():
    # Inicializa o bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Registra os handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment_id))
    
    # Inicia o bot em modo polling
    application.run_polling()

if __name__ == "__main__":
    main()
