import requests

BOT_TOKEN = "8763518242:AAHh3uOrUhSiSIe65EgQUekGY16R_k9-H_s"


def send_telegram_message(chat_id, text):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": text
    }

    requests.post(url, data=data)