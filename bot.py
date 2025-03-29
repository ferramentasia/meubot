import os
import logging
import requests
import asyncio
import hmac
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from quart import Quart, request, jsonify

# ========================================================
# CONFIGURAÇÕES (OBRIGATÓRIO NO RAILWAY)
# ========================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Verifique o nome exato no Railway!
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
DOMINIO = os.getenv("RAILWAY_STATIC_URL")  # Automático no Railway
PORT = int(os.getenv("PORT", 8080))  # Porta dinâmica do Railway

# Links reais dos seus PDFs (SUBSTITUA!)
PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    "pdf2": "https://drive.google.com/file/d/1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp/view?usp=sharing",
    "pdf3": "https://drive.google.com/file/d/1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb/view?usp=sharing",
    "pdf4": "https://drive.google.com/file/d/1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac/view?usp=sharing",
    "pdf5": "https://drive.google.com/file/d/1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_/view?usp=sharing",
    "pdf6": "https://drive.google.com/file/d/1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN/view?usp=sharing"
}

# ========================================================
# INICIALIZAÇÃO DO SISTEMA
# ========================================================
app = Quart(__name__)
bot_application = Application.builder().token(TELEGRAM_TOKEN).build()

# ========================================================
# ROTAS PRINCIPAIS (QUART ASYNC)
# ========================================================
@app.route("/")
async def home():
    return "✅ Bot operacional! Envie /start no Telegram."

@app.route("/telegram_webhook", methods=["POST"])
async def telegram_webhook():
    try:
        data = await request.get_json()
        update = Update.de_json(data, bot_application.bot)
        await bot_application.process_update(update)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"ERRO WEBHOOK: {str(e)}", exc_info=True)
        return jsonify({"status": "error"}), 500

@app.route("/mercadopago_webhook", methods=["POST"])
async def mercadopago_webhook():
    try:
        # Validação HMAC
        signature = request.headers.get("X-Signature")
        payload = await request.get_data()
        hash_obj = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256)
        
        if not hmac.compare_digest(signature, f"sha256={hash_obj.hexdigest()}"):
            logger.error("Assinatura HMAC inválida!")
            return jsonify({"status": "error"}), 403

        # Processamento do pagamento
        payment_id = (await request.get_json()).get("data", {}).get("id")
        response = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {MERCADOPAGO_TOKEN}"}
        )
        payment_data = response.json()

        if payment_data.get("status") == "approved":
            external_ref = payment_data.get("external_reference", "")
            if ":" in external_ref:
                user_id, pdf_id = external_ref.split(":")
                if pdf_link := PDF_LINKS.get(pdf_id):
                    await bot_application.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ *Pagamento Aprovado!*\n\n📥 Acesse seu PDF: {pdf_link}",
                        parse_mode="MarkdownV2",
                        disable_web_page_preview=True
                    )

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"ERRO MERCADO PAGO: {str(e)}", exc_info=True)
        return jsonify({"status": "error"}), 500

# ========================================================
# HANDLERS DO BOT (COM LOGS DETALHADOS)
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Novo usuário: {update.effective_user.id}")
    await update.message.reply_text(
        "👋 *Bem-vindo à Loja de PDFs!*\n\nUse /menu para ver nossos produtos.",
        parse_mode="MarkdownV2"
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Planilha Orçamento", callback_data="pdf1")],
        [InlineKeyboardButton("🛒 Guia Compras", callback_data="pdf2")],
        [InlineKeyboardButton("💡 Economia Energia", callback_data="pdf3")],
        [InlineKeyboardButton("🍲 Receitas Econômicas", callback_data="pdf4")],
        [InlineKeyboardButton("🚀 Sair das Dívidas", callback_data="pdf5")],
        [InlineKeyboardButton("🎯 Metas Financeiras", callback_data="pdf6")]
    ]
    
    await update.message.reply_text(
        "📚 *Nossos PDFs Disponíveis:*\nValor: R\$9,90 • Pagamento via PIX",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2"
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    pdf_id = query.data
    logger.info(f"Pedido de PDF: {pdf_id} por {user_id}")

    try:
        # Cria pagamento no Mercado Pago
        response = requests.post(
            "https://api.mercadopago.com/v1/payments",
            headers={"Authorization": f"Bearer {MERCADOPAGO_TOKEN}"},
            json={
                "transaction_amount": 1.00,
                "payment_method_id": "pix",
                "payer": {"email": "comprador@exemplo.com"},
                "description": f"PDF {pdf_id}",
                "external_reference": f"{user_id}:{pdf_id}",
                "notification_url": f"{DOMINIO}/mercadopago_webhook"
            }
        )
        response.raise_for_status()
        payment_data = response.json()
        payment_link = payment_data["point_of_interaction"]["transaction_data"]["ticket_url"]
        
        await query.edit_message_text(
            f"🔗 [Clique aqui para pagar via PIX]({payment_link})\n\n"
            "Após a confirmação do pagamento, enviaremos o PDF automaticamente!",
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Falha no pagamento: {str(e)}")
        await query.edit_message_text("❌ Erro ao processar pagamento. Tente novamente mais tarde.")

# ========================================================
# INICIALIZAÇÃO FINAL (CONFIGURAÇÃO RAILWAY)
# ========================================================
async def main():
    # Registra handlers
    bot_application.add_handler(CommandHandler("start", start))
    bot_application.add_handler(CommandHandler("menu", menu))
    bot_application.add_handler(CallbackQueryHandler(handle_button))

    # Configura webhook
    await bot_application.initialize()
    await bot_application.start()
    await bot_application.bot.set_webhook(
        url=f"{DOMINIO}/telegram_webhook",
        secret_token=WEBHOOK_SECRET
    )

    # Inicia servidor
    await app.run_task(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    asyncio.run(main())
