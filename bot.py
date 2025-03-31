import os
import logging
import requests
import hmac
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request, jsonify
from threading import Thread

# ========================================================
# CONFIGURAÇÕES (VERIFICAÇÃO RIGOROSA)
# ========================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Validação crítica das variáveis
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADOPAGO_TOKEN = os.getenv("MERCADOPAGO_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
DOMINIO = os.getenv("RAILWAY_STATIC_URL")

if not all([TELEGRAM_TOKEN, MERCADOPAGO_TOKEN, WEBHOOK_SECRET, DOMINIO]):
    missing = [var for var in ["TELEGRAM_TOKEN", "MERCADOPAGO_TOKEN", "WEBHOOK_SECRET", "RAILWAY_STATIC_URL"] if not os.getenv(var)]
    raise ValueError(f"Variáveis faltando: {', '.join(missing)}")

# Links reais dos PDFs (SUBSTITUA!)
PDF_LINKS = {
    "pdf1": "https://drive.google.com/file/d/1-PwvnRSp73SpNYTqDg5TuJc8M5957CVF/view?usp=sharing",
    "pdf2": "https://drive.google.com/file/d/1-JzKTnHRg1Pj4x1BYH6I6GtHkMPEChcp/view?usp=sharing",
    "pdf3": "https://drive.google.com/file/d/1-dwYZDUWx4VoasF5bzKITCj55Uu-s4sb/view?usp=sharing",
    "pdf4": "https://drive.google.com/file/d/1-ismWr0Qk2QJYl3TLzo7POi1lrq_1jac/view?usp=sharing",
    "pdf5": "https://drive.google.com/file/d/1-nkMMXQXAXqH8CMLu2Kj-_pLXbhDTSo_/view?usp=sharing",
    "pdf6": "https://drive.google.com/file/d/1-LBDKvaWpJUWjPguWZReHiIvwtyi6yWN/view?usp=sharing"
}

# ========================================================
# SERVIDOR WEB (FLASK COM ROTA RAIZ)
# ========================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Bot operacional! Acesse via Telegram: t.me/seu_bot"

@app.route('/mercadopago_webhook', methods=['POST'])
def mercadopago_webhook():
    try:
        # Validação HMAC reforçada
        signature = request.headers.get('X-Signature', '')
        payload = request.get_data()
        hash_obj = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256)
        
        if not hmac.compare_digest(signature, f"sha256={hash_obj.hexdigest()}"):
            logger.error("Tentativa de acesso não autorizada!")
            return jsonify({"status": "error"}), 403

        # Processamento seguro do pagamento
        payment_id = request.json.get('data', {}).get('id')
        if not payment_id:
            return jsonify({"status": "invalid data"}), 400

        response = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {MERCADOPAGO_TOKEN}"}
        )
        response.raise_for_status()
        payment_data = response.json()

        if payment_data.get('status') == 'approved':
            external_ref = payment_data.get('external_reference', '')
            if ':' in external_ref:
                user_id, pdf_id = external_ref.split(':')
                if pdf_link := PDF_LINKS.get(pdf_id):
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                        json={
                            "chat_id": user_id,
                            "text": f"✅ *Pagamento confirmado!*\n\n📥 Acesse: {pdf_link}",
                            "parse_mode": "MarkdownV2",
                            "disable_web_page_preview": True
                        }
                    )
        
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"Erro crítico no webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error"}), 500

# ========================================================
# LÓGICA DO BOT (COM URL ABSOLUTA GARANTIDA)
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Planilha Orçamento (R$9,90)", callback_data='pdf1')],
        [InlineKeyboardButton("🛒 Guia Compras (R$9,90)", callback_data='pdf2')],
        [InlineKeyboardButton("💡 Economia Energia (R$9,90)", callback_data='pdf3')],
        [InlineKeyboardButton("🍲 Receitas Econômicas (R$9,90)", callback_data='pdf4')],
        [InlineKeyboardButton("🚀 Sair das Dívidas (R$9,90)", callback_data='pdf5')],
        [InlineKeyboardButton("🎯 Metas Financeiras (R$9,90)", callback_data='pdf6')]
    ]
    await update.message.reply_text(
        "📚 *Materiais Exclusivos Disponíveis:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2"
    )

async def handle_pdf_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = query.from_user.id
        pdf_id = query.data
        
        # Geração segura da URL de notificação
        notification_url = f"{DOMINIO}/mercadopago_webhook"
        logger.info(f"Gerando pagamento para: {notification_url}")
        
        # Dados de pagamento completos
        payload = {
            "transaction_amount": 1.00,
            "payment_method_id": "pix",
            "payer": {
                "email": "comprador@exemplo.com",
                "identification": {
                    "type": "CPF",
                    "number": "12345678909"
                }
            },
            "description": f"PDF {pdf_id}",
            "external_reference": f"{user_id}:{pdf_id}",
            "notification_url": notification_url
        }
        
        # Comunicação robusta com a API
        response = requests.post(
            "https://api.mercadopago.com/v1/payments",
            headers={
                "Authorization": f"Bearer {MERCADOPAGO_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=10
        )

        # Tratamento detalhado de respostas
        if response.status_code not in [200, 201]:
            logger.error(f"Falha na API MP: {response.status_code} - {response.text}")
            await query.edit_message_text("❌ Falha no sistema de pagamentos. Tente novamente.")
            return

        payment_data = response.json()
        payment_link = payment_data['point_of_interaction']['transaction_data']['ticket_url']
        
        await query.edit_message_text(
            f"💳 *PAGAMENTO VIA PIX*\n\n"
            f"Valor: R\$1,00\n"
            f"[Clique aqui para pagar]({payment_link})\n\n"
            "Após a confirmação, seu PDF será enviado automaticamente!",
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )

    except KeyError:
        logger.error("Estrutura de resposta inválida da API")
        await query.edit_message_text("⚠️ Erro inesperado. Contate o suporte.")
    except Exception as e:
        logger.error(f"Falha crítica: {str(e)}", exc_info=True)
        await query.edit_message_text("⛔ Erro temporário. Por favor, tente novamente mais tarde.")

# ========================================================
# INICIALIZAÇÃO OTIMIZADA
# ========================================================
def run_flask():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))

def run_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_pdf_selection))
    application.run_polling()

if __name__ == "__main__":
    # Configuração para Railway (1 instância apenas)
    Thread(target=run_flask, daemon=True).start()
    run_bot()
