
# AI Content Curator Bot

Telegram-бот для автоматизации создания контента из фотографий с помощью искусственного интеллекта.

## Возможности

- Анализ фотографий с помощью Google Gemini.
- Создание нескольких вариантов коллажей.
- Автоматическая компоновка фотографий с помощью Pillow.
- Генерация подписей и хештегов.
- Рекомендации по музыке для публикаций.
- Выбор готового варианта прямо в Telegram.

## Технологии

- Python 3.11+
- Aiogram
- Google Gemini API
- Pillow
- Pydantic Settings

## Установка

Клонируйте репозиторий:

```bash
git clone https://github.com/ranswel/ai-content-curator-bot.git
cd ai-content-curator-bot
```

Создайте виртуальное окружение:

```bash
py -3.11 -m venv .venv
```

Активируйте его в Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

## Настройка

Создайте файл `.env` в корне проекта на основе `.env.example`.

Заполните его своими ключами:

```env
TELEGRAM_BOT_TOKEN=your_telegram_token
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
MAX_PHOTOS_PER_SESSION=10
MAX_IMAGE_BYTES=8388608
MUSIC_PROVIDER=none
```

Не публикуйте `.env` и не передавайте свои API-ключи другим людям.

## Запуск

Из корневой папки проекта выполните:

```bash
python -m app.main
```

После запуска откройте своего Telegram-бота и отправьте фотографии.

## Статус проекта

Проект находится в активной разработке.

В планах:
- Улучшение дизайна коллажей.
- Подключение музыкальных сервисов.
- Сохранение истории генераций.
- Расширение возможностей AI-ассистента.

