import os
import logging
from flask import Flask, request
from threading import Thread
from yt_dlp import YoutubeDL, utils as ytdlp_utils
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# 🔐 Token depuis variables d’environnement
TOKEN = os.environ.get("7922618318:AAFeTFXCnfVNLj6xuWQIoIBh73IPhAhutwc", "TON_TOKEN_ICI")

# Logger
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Fonction téléchargement vidéo TikTok
def download_video(url, chat_id):
    ydl_opts = {
        "outtmpl": f"{chat_id}_%(title).50s.%(ext)s",
        "format": "mp4",
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
        "retries": 10,
        "socket_timeout": 1000,
        "concurrent_fragment_downloads": 5,
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4"
        }]
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Envoie-moi un lien TikTok pour télécharger une vidéo.")

# Handler message texte
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    url = update.message.text.strip()

    if "tiktok.com" not in url:
        await update.message.reply_text("❌ Je ne supporte actuellement que les vidéos TikTok.")
        return

    try:
        await update.message.reply_text("⏳ Téléchargement en cours...")
        filename = download_video(url, chat_id)

        if not os.path.exists(filename):
            await update.message.reply_text("❌ Fichier introuvable après téléchargement.")
            return

        size = os.path.getsize(filename)
        with open(filename, "rb") as video_file:
            if size < 50 * 1024 * 1024:
                await context.bot.send_video(chat_id=chat_id, video=video_file)
            else:
                await context.bot.send_document(chat_id=chat_id, document=video_file)

        os.remove(filename)

    except ytdlp_utils.DownloadError as e:
        logger.error(f"Erreur yt-dlp : {e}")
        await update.message.reply_text("❌ Impossible de télécharger la vidéo.")
    except Exception as e:
        logger.error(f"Erreur inattendue : {e}")
        await update.message.reply_text("❌ Une erreur est survenue pendant le téléchargement.")

# Création de l'application Telegram
application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Route webhook Flask
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, application.bot)
    await application.process_update(update)
    return "ok"

# Route simple test HTTP
@app.route("/")
def home():
    return "✅ Bot TikTok en ligne"

if __name__ == "__main__":
    # On met en place le webhook sur Telegram
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Exemple: "https://tondomaine.com/" + TOKEN
    if not WEBHOOK_URL:
        logger.error("Variable WEBHOOK_URL non définie, arrêt du bot.")
        exit(1)

    # Supprime webhook si existant (sécurité)
    application.bot.delete_webhook()
    # Définir le webhook sur Telegram
    application.bot.set_webhook(WEBHOOK_URL)

    # Lancement serveur Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
