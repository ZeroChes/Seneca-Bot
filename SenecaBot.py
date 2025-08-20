import requests
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import logging
from bs4 import BeautifulSoup
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
import os

# Загружаем токены из .env
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OAUTH_TOKEN = os.getenv("OAUTH_TOKEN")

# Настройка логирования с ротацией
log_filename = 'bot.log'
log_handler = TimedRotatingFileHandler(log_filename, when='midnight', interval=1, backupCount=3)
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(log_formatter)
logger = logging.getLogger(__name__)
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Отправьте мне ссылку на статью!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    if 'http' in user_message:
        await get_sharing_url_and_text(user_message, update)
    else:
        await update.message.reply_text('Пожалуйста, отправьте ссылку.')

async def get_sharing_url_and_text(article_url: str, update: Update) -> None:
    endpoint = 'https://300.ya.ru/api/sharing-url'

    try:
        response = requests.post(
            endpoint,
            json={'article_url': article_url},
            headers={'Authorization': f'OAuth {OAUTH_TOKEN}'}
        )

        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                sharing_url = data['sharing_url']
                await update.message.reply_text(f'Ссылка на сгенерированный текст: {sharing_url}')

                # Ждем некоторое время, чтобы текст на странице был сгенерирован
                time.sleep(3)

                # Получаем HTML-контент страницы
                page_response = requests.get(sharing_url)
                if page_response.status_code == 200:
                    soup = BeautifulSoup(page_response.content, 'html.parser')

                    description_tag = soup.find('meta', attrs={'name': 'description'})

                    if description_tag and 'content' in description_tag.attrs:
                        generated_text = description_tag['content']
                        await update.message.reply_text(f'Текст:\n{generated_text}')
                    else:
                        await update.message.reply_text('Не удалось найти текст на странице.')
                else:
                    logger.info(f"Failed to get data from {sharing_url}. Status code: {page_response.status_code}")
                    await update.message.reply_text('Не удалось получить данные со страницы.')
            else:
                logger.info(f"API request failed. Data: {data}")
                await update.message.reply_text('Ошибка при запросе к API.')
        else:
            logger.info(f"API request failed. Status code: {response.status_code}")
            await update.message.reply_text('Ошибка при запросе к API.')
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        await update.message.reply_text('Произошла ошибка при обработке запроса.')

def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
