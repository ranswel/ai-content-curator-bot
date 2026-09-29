import asyncio
import json
import re
from dataclasses import dataclass

from google import genai
from google.genai import types


FORMAT_LABELS = {
    "post": "пост",
    "stories": "сторис",
    "reels": "reels",
}


@dataclass(frozen=True)
class ContentIdea:
    visual_story: str
    content_format: str
    composition_options: list[dict]
    editing_notes: list[str]
    caption_variants: list[str]
    hashtag_sets: list[list[str]]
    music_options: list[dict]


SYSTEM_PROMPT = """
Ты — креативный директор и арт-директор социальных сетей.

Тебе передаётся набор фотографий пользователя.
Нумерация фотографий начинается с 1.

Твоя задача — самостоятельно придумать 3 РАЗНЫХ готовых концепции
контента. Пользователь не должен сам решать, какую фотографию куда ставить.

Верни ТОЛЬКО валидный JSON на русском языке.

JSON должен содержать ровно эти ключи:

{
  "visual_story": "...",
  "content_format": "post",
  "composition_options": [
    {
      "title": "...",
      "layout_type": "grid",
      "photo_order": [1, 2, 3],
      "hero_photo": 1,
      "background_style": "warm",
      "text_position": "bottom_left",
      "crop_style": "natural",
      "photo_scale": "balanced",
      "layout": ["...", "...", "..."]
    },
    {
      "title": "...",
      "layout_type": "hero",
      "photo_order": [2, 1, 3],
      "hero_photo": 2,
      "background_style": "dark",
      "text_position": "bottom_left",
      "crop_style": "cinematic",
      "photo_scale": "hero",
      "layout": ["...", "...", "..."]
    },
    {
      "title": "...",
      "layout_type": "editorial",
      "photo_order": [3, 1, 2],
      "hero_photo": 3,
      "background_style": "light",
      "text_position": "none",
      "crop_style": "natural",
      "photo_scale": "balanced",
      "layout": ["...", "...", "..."]
    }
  ],
Правила:

1. composition_options содержит РОВНО 3 объекта.

2. Каждый объект должен иметь:
   - title
   - layout_type
   - photo_order
   - hero_photo
   - background_style
   - text_position
   - crop_style
   - photo_scale
   - layout
Используй только следующие значения:

layout_type:
- grid
- hero
- editorial

background_style:
- light
- warm
- dark
- neutral

text_position:
- none
- top_left
- top_right
- bottom_left
- bottom_right

crop_style:
- natural
- cinematic
- portrait
- square

photo_scale:
- balanced
- hero
- compact

Не добавляй текст на изображение без необходимости.
Если фотографии сами по себе достаточно выразительные,
предпочитай text_position = "none".

Не используй декоративные элементы только ради заполнения
пустого пространства.

Пустое пространство допустимо только тогда,
когда оно является частью осознанной композиции.

Главная цель — результат, который пользователь реально
захочет опубликовать в социальной сети.

3. photo_order содержит только существующие номера фотографий.
   Не придумывай фотографии.

4. hero_photo должен быть одним из номеров в photo_order.

5. Используй разные композиции:
   - grid — аккуратная сетка;
   - hero — одно главное фото и дополнительные;
   - editorial — журнальная/асимметричная композиция.

6. Если фотографий мало, адаптируй композицию.
   Для одной фотографии не придумывай дополнительные фотографии.

7. Выбирай фотографии осмысленно:
   - лучшее фото делай главным;
   - похожие кадры не ставь рядом без причины;
   - учитывай ориентацию фотографии;
   - учитывай цвета;
   - учитывай визуальный сюжет.

8. Не просто описывай композицию словами.
   photo_order и hero_photo должны содержать конкретные решения,
   которые сможет выполнить программа.

9. layout содержит 3-6 коротких инструкций.

10. editing_notes содержит 2-4 рекомендации.

11. caption_variants содержит РОВНО 3 подписи,
    каждая максимум 250 символов.

12. hashtag_sets содержит РОВНО 3 набора,
    в каждом 8-15 хештегов.

13. music_options содержит РОВНО 3 варианта.
    В каждом ровно 3 предложения вида:
    "Artist — Track".

14. Не придумывай людей, места, бренды или события,
    если их нельзя определить по фотографиям или brief.

15. content_format должен быть одним из:
    post, stories, reels.
"""


class GeminiImageAnalyzer:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def analyze(
        self,
        images: list[bytes],
        brief: str = "",
        content_format: str = "post",
    ) -> ContentIdea:
        contents = self._contents(images, brief, content_format)

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )

        return parse_idea(response.text)

    async def regenerate_part(
        self,
        images: list[bytes],
        brief: str,
        content_format: str,
        part: str,
        current: ContentIdea,
    ) -> ContentIdea:
        labels = {
            "composition": "composition_options",
            "caption": "caption_variants",
            "hashtags": "hashtag_sets",
            "music": "music_options",
        }

        if part not in labels:
            raise ValueError("unknown_part")

        contents = self._contents(images, brief, content_format)

        contents.append(
            types.Part.from_text(
                text=(
                    f"Create a fresh alternative only for "
                    f"{labels[part]}. "
                    "Keep every other field exactly as in this JSON:\n"
                    + json.dumps(
                        current.__dict__,
                        ensure_ascii=False,
                    )
                )
            )
        )

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.9,
            ),
        )

        return parse_idea(response.text)

    @staticmethod
    def _contents(
        images: list[bytes],
        brief: str,
        content_format: str,
    ) -> list[types.Part]:
        label = FORMAT_LABELS.get(
            content_format,
            "пост",
        )

        contents = [
            types.Part.from_text(
                text=(
                    f"User brief: "
                    f"{brief or 'No additional context.'}\n"
                    f"Requested format: {label}.\n\n"
                    f"Количество фотографий: {len(images)}.\n"
                    f"Нумерация фотографий начинается с 1."
                )
            )
        ]

        for index, image in enumerate(images, start=1):
            contents.append(
                types.Part.from_text(
                    text=f"Фотография №{index}"
                )
            )
            contents.append(
                types.Part.from_bytes(
                    data=image,
                    mime_type="image/jpeg",
                )
            )

        return contents


def parse_idea(raw: str) -> ContentIdea:
    cleaned = re.sub(
        r"^`(?:json)?\s*|\s*`$",
        "",
        raw.strip(),
        flags=re.I,
    )

    data = json.loads(cleaned)

    required = {
        "visual_story",
        "content_format",
        "composition_options",
        "editing_notes",
        "caption_variants",
        "hashtag_sets",
        "music_options",
    }

    missing = required - data.keys()

    if missing:
        raise ValueError(
            f"Missing fields: {sorted(missing)}"
        )

    if data["content_format"] not in FORMAT_LABELS:
        data["content_format"] = "post"

    if len(data["composition_options"]) != 3:
        raise ValueError(
            "Expected exactly 3 composition options"
        )

    for option in data["composition_options"]:
        required_composition_fields = [
            "photo_order",
            "hero_photo",
            "layout_type",
            "background_style",
            "text_position",
            "crop_style",
            "photo_scale",
        ]

        for field in required_composition_fields:
            if field not in option:
                raise ValueError(
                    f"Composition is missing {field}"
                )

        if option["layout_type"] not in {
            "grid",
            "hero",
            "editorial",
        }:
            raise ValueError(
                "Unknown layout_type"
            )

        if option["background_style"] not in {
            "light",
            "warm",
            "dark",
            "neutral",
        }:
            raise ValueError(
                "Unknown background_style"
            )

        if option["text_position"] not in {
            "none",
            "top_left",
            "top_right",
            "bottom_left",
            "bottom_right",
        }:
            raise ValueError(
                "Unknown text_position"
            )

        if option["crop_style"] not in {
            "natural",
            "cinematic",
            "portrait",
            "square",
        }:
            raise ValueError(
                "Unknown crop_style"
            )

        if option["photo_scale"] not in {
            "balanced",
            "hero",
            "compact",
        }:
            raise ValueError(
                "Unknown photo_scale"
            )

    if len(data["caption_variants"]) != 3:
        raise ValueError(
            "Expected exactly 3 captions"
        )

    if len(data["hashtag_sets"]) != 3:
        raise ValueError(
            "Expected exactly 3 hashtag sets"
        )

    if len(data["music_options"]) != 3:
        raise ValueError(
            "Expected exactly 3 music options"
        )

    return ContentIdea(
        **{
            key: data[key]
            for key in required
        }
    )