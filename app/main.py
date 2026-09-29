import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import get_settings
from app.keyboards import main_keyboard, variant_keyboard
from app.services.analyzer import GeminiImageAnalyzer
from app.services.collage import generate_collages
from app.services.music import make_music_links
from app.storage import InMemorySessionStore, Photo


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()
store = InMemorySessionStore()

settings = None
analyzer = None


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def music_data(idea, number: int) -> tuple[str, str, str | None, str | None]:
    """
    Достаёт название, исполнителя и ссылки на музыку
    из ответа Gemini.

    Gemini может вернуть music_options в немного разных форматах,
    поэтому здесь специально есть нормализация.
    """

    try:
        music = idea.music_options[number - 1]
    except (IndexError, TypeError, AttributeError):
        music = {}

    # Иногда Gemini возвращает список вместо объекта.
    if isinstance(music, list):
        if music:
            first = music[0]

            if isinstance(first, dict):
                music = first
            else:
                music = {
                    "suggestions": music,
                }
        else:
            music = {}

    if not isinstance(music, dict):
        music = {}

    # Возможные варианты названий полей.
    title = (
        music.get("title")
        or music.get("track")
        or music.get("song")
        or ""
    )

    artist = (
        music.get("artist")
        or music.get("performer")
        or ""
    )

    # Иногда Gemini может вернуть "Название — Исполнитель"
    # только в suggestions.
    suggestions = music.get("suggestions", [])

    if isinstance(suggestions, str):
        suggestions = [suggestions]

    if not isinstance(suggestions, list):
        suggestions = []

    suggestions = [
        str(item).strip()
        for item in suggestions
        if item
    ]

    # Если title/artist не были отдельными полями,
    # используем первую рекомендацию.
    if not title and suggestions:
        first = suggestions[0]

        # Пытаемся разделить:
        # "Artist — Track"
        # "Track — Artist"
        if " — " in first:
            parts = [x.strip() for x in first.split(" — ", 1)]

            if len(parts) == 2:
                title = parts[0]
                artist = parts[1]
            else:
                title = first

        elif " - " in first:
            parts = [x.strip() for x in first.split(" - ", 1)]

            if len(parts) == 2:
                title = parts[0]
                artist = parts[1]
            else:
                title = first

        else:
            title = first

    title = str(title).strip()
    artist = str(artist).strip()

    if not title:
        title = "Подходящий трек"

    if not artist:
        artist = ""

    # Если Gemini уже дал search_query — используем её.
    search_query = music.get("search_query")

    if not isinstance(search_query, str) or not search_query.strip():
        search_query = f"{title} {artist}".strip()

    links = make_music_links(title, artist)

    youtube_url = links.get("youtube")
    youtube_music_url = links.get("youtube_music")

    return (
        title,
        artist,
        youtube_music_url,
        youtube_url,
    )


def music_keyboard(
    youtube_music_url: str | None,
    youtube_url: str | None,
) -> InlineKeyboardMarkup:
    """
    Кнопки для прослушивания рекомендованного трека.
    """

    buttons = []

    if youtube_music_url:
        buttons.append(
            InlineKeyboardButton(
                text="🎵 YouTube Music",
                url=youtube_music_url,
            )
        )

    if youtube_url:
        buttons.append(
            InlineKeyboardButton(
                text="▶️ YouTube",
                url=youtube_url,
            )
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[buttons] if buttons else []
    )


def hashtags_text(idea, number: int) -> str:
    try:
        hashtags = idea.hashtag_sets[number - 1]
    except (IndexError, TypeError, AttributeError):
        hashtags = []

    if isinstance(hashtags, str):
        return hashtags

    if not isinstance(hashtags, list):
        return ""

    return " ".join(
        str(tag).strip()
        for tag in hashtags
        if tag
    )


def caption_text(idea, number: int) -> str:
    try:
        captions = idea.caption_variants
    except AttributeError:
        return ""

    if not isinstance(captions, list):
        return str(captions)

    try:
        caption = captions[number - 1]
    except IndexError:
        caption = captions[0] if captions else ""

    return str(caption).strip()


# ============================================================
# СКАЧИВАНИЕ ФОТО
# ============================================================

async def download_images(message: Message) -> list[bytes]:
    images = []

    session = store.get(message.from_user.id)

    for photo in session.photos:
        remote = await message.bot.get_file(photo.file_id)

        downloaded = await message.bot.download_file(
            remote.file_path
        )

        images.append(downloaded.read())

    return images


# ============================================================
# START
# ============================================================

@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    store.reset(message.from_user.id)

    await message.answer(
        "Привет! 👋\n\n"
        "Я AI-ассистент для создания контента.\n\n"
        "📸 Отправь мне несколько фотографий.\n"
        "Я сам:\n"
        "• проанализирую фотографии;\n"
        "• придумаю визуальную концепцию;\n"
        "• создам 3 варианта коллажа;\n"
        "• подберу музыку;\n"
        "• напишу подпись;\n"
        "• подберу хештеги.\n\n"
        "Тебе останется выбрать лучший вариант.",
        reply_markup=main_keyboard(),
    )


# ============================================================
# СОЗДАТЬ ИДЕЮ
# ============================================================

@router.message(F.text == "✨ Создать идею")
async def create_button_handler(message: Message) -> None:
    session = store.get(message.from_user.id)

    if not session.photos:
        await message.answer(
            "📸 Сначала отправь мне фотографии.\n\n"
            "Можно отправить несколько фотографий подряд."
        )
        return

    await create_variants(message)


# ============================================================
# ФОТО
# ============================================================

@router.message(F.photo)
async def photo_handler(message: Message) -> None:
    user_id = message.from_user.id

    photo = message.photo[-1]

    try:
        count = store.add_photo(
            user_id,
            Photo(
                file_id=photo.file_id,
                file_size=photo.file_size,
            ),
            settings.max_photos_per_session,
        )

    except ValueError as exc:
        if str(exc) == "photo_limit":
            await message.answer(
                f"Можно использовать максимум "
                f"{settings.max_photos_per_session} фотографий."
            )
            return

        raise

    await message.answer(
        f"📸 Фото добавлено: {count}/"
        f"{settings.max_photos_per_session}\n\n"
        "Можешь отправить ещё фотографии.\n"
        "Когда закончишь — нажми «✨ Создать идею»."
    )


# ============================================================
# ТЕКСТОВЫЙ BRIEF
# ============================================================

@router.message(F.text)
async def text_handler(message: Message) -> None:
    text = (message.text or "").strip()

    if not text:
        return

    # Команды и кнопки не считаем brief.
    if text.startswith("/"):
        return

    if text in {
        "✨ Создать идею",
        "🗑 Очистить подборку",
    }:
        return

    session = store.get(message.from_user.id)

    if not session.photos:
        await message.answer(
            "📸 Сначала отправь фотографии."
        )
        return

    store.set_brief(message.from_user.id, text)

    await message.answer(
        "📝 Записал пожелание.\n\n"
        "Теперь нажми «✨ Создать идею»."
    )


# ============================================================
# СОЗДАНИЕ ВАРИАНТОВ
# ============================================================

async def create_variants(message: Message) -> None:
    user_id = message.from_user.id

    session = store.get(user_id)

    if not session.photos:
        await message.answer(
            "📸 У тебя пока нет фотографий."
        )
        return

    if analyzer is None:
        await message.answer(
            "❌ Анализатор ещё не запущен."
        )
        return

    progress = await message.answer(
        "🧠 Анализирую фотографии...\n\n"
        "Это может занять некоторое время."
    )

    try:
        images = await download_images(message)

        # ----------------------------------------------------
        # AI АНАЛИЗ
        # ----------------------------------------------------

        idea = await analyzer.analyze(
            images=images,
            brief=session.brief,
            content_format=session.content_format,
        )

        store.save_result(
            user_id,
            idea,
        )

        await progress.edit_text(
            "🎨 AI придумал композиции.\n"
            "Создаю визуальные варианты..."
        )

        # ----------------------------------------------------
        # ГЕНЕРАЦИЯ КОЛЛАЖЕЙ
        # ----------------------------------------------------

        collages = generate_collages(
            images,
            idea.composition_options,
        )

        store.save_collages(
            user_id,
            collages,
        )

        await progress.delete()

        # ----------------------------------------------------
        # ОТПРАВКА 3 ВАРИАНТОВ
        # ----------------------------------------------------

        for collage in collages:
            number = collage.number

            title, artist, youtube_music, youtube = music_data(
                idea,
                number,
            )

            caption = caption_text(
                idea,
                number,
            )

            hashtags = hashtags_text(
                idea,
                number,
            )

            if artist:
                music_line = f"🎵 <b>{title}</b> — {artist}"
            else:
                music_line = f"🎵 <b>{title}</b>"

            text_parts = [
                f"<b>Вариант {number}</b>",
                "",
                music_line,
            ]

            if caption:
                text_parts.extend(
                    [
                        "",
                        "✍️ <b>Подпись</b>",
                        caption,
                    ]
                )

            if hashtags:
                text_parts.extend(
                    [
                        "",
                        "🔖 <b>Хештеги</b>",
                        hashtags,
                    ]
                )

            await message.answer_photo(
                BufferedInputFile(
                    collage.image,
                    filename=f"variant_{number}.jpg",
                ),
                caption="\n".join(text_parts),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🎵 Слушать",
                                url=youtube_music
                                or youtube,
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=f"✅ Выбрать вариант {number}",
                                callback_data=f"choose:{number}",
                            )
                        ],
                    ]
                ),
            )

    except Exception:
        logger.exception("Ошибка при создании вариантов")

        try:
            await progress.edit_text(
                "❌ Не удалось создать варианты.\n\n"
                "Попробуй ещё раз."
            )
        except Exception:
            await message.answer(
                "❌ Не удалось создать варианты.\n\n"
                "Попробуй ещё раз."
            )


# ============================================================
# ВЫБОР ВАРИАНТА
# ============================================================

@router.callback_query(F.data.startswith("choose:"))
async def choose_variant(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    try:
        number = int(callback.data.split(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer(
            "Некорректный вариант.",
            show_alert=True,
        )
        return

    collage = store.collage(
        user_id,
        number,
    )

    idea = store.latest_result(
        user_id,
    )

    if collage is None or idea is None:
        await callback.answer(
            "Вариант больше недоступен.",
            show_alert=True,
        )
        return

    title, artist, youtube_music, youtube = music_data(
        idea,
        number,
    )

    caption = caption_text(
        idea,
        number,
    )

    hashtags = hashtags_text(
        idea,
        number,
    )

    if artist:
        music_line = f"🎵 <b>{title}</b> — {artist}"
    else:
        music_line = f"🎵 <b>{title}</b>"

    text_parts = [
        "✅ <b>Вариант выбран</b>",
        "",
        music_line,
    ]

    if caption:
        text_parts.extend(
            [
                "",
                "✍️ <b>Готовая подпись</b>",
                caption,
            ]
        )

    if hashtags:
        text_parts.extend(
            [
                "",
                "🔖 <b>Хештеги</b>",
                hashtags,
            ]
        )

    await callback.message.answer(
        "\n".join(text_parts),
        reply_markup=music_keyboard(
            youtube_music,
            youtube,
        ),
    )

    # Отдельно отправляем готовый коллаж как файл.
    await callback.message.answer_document(
        BufferedInputFile(
            collage.image,
            filename=f"selected_variant_{number}.jpg",
        ),
        caption="🖼️ Готовый коллаж",
    )

    await callback.answer(
        "Вариант выбран ✅"
    )


# ============================================================
# ОЧИСТКА
# ============================================================

@router.message(F.text == "🗑 Очистить подборку")
async def reset_handler(message: Message) -> None:
    store.reset(message.from_user.id)

    await message.answer(
        "🗑 Подборка очищена.\n\n"
        "Можешь начать заново — просто отправь фотографии.",
        reply_markup=main_keyboard(),
    )


# ============================================================
# MAIN
# ============================================================

async def main() -> None:
    global settings
    global analyzer

    settings = get_settings()

    analyzer = GeminiImageAnalyzer(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.gemini_model,
    )

    bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )

    dp = Dispatcher()

    dp.include_router(router)

    logger.info(
        "Bot started. Gemini model: %s",
        settings.gemini_model,
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())