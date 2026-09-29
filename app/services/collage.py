from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


CANVAS = (1080, 1350)
MARGIN = 54
GAP = 24


@dataclass(frozen=True)
class CollageVariant:
    number: int
    title: str
    image: bytes


def _open(data: bytes) -> Image.Image:
    return ImageOps.exif_transpose(
        Image.open(BytesIO(data))
    ).convert("RGB")


def _export(image: Image.Image) -> bytes:
    output = BytesIO()

    image.convert("RGB").save(
        output,
        "JPEG",
        quality=94,
        optimize=True,
    )

    return output.getvalue()

def _font(size: int, bold: bool = False):
    candidates = []

    if bold:
        candidates.extend(
            [
                r"C:\Windows\Fonts\arialbd.ttf",
                r"C:\Windows\Fonts\segoeuib.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                r"C:\Windows\Fonts\arial.ttf",
                r"C:\Windows\Fonts\segoeui.ttf",
            ]
        )

    candidates.append("arial.ttf")

    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass

    return ImageFont.load_default()


def _rounded_mask(
    size: tuple[int, int],
    radius: int,
) -> Image.Image:
    mask = Image.new(
        "L",
        size,
        0,
    )

    draw = ImageDraw.Draw(mask)

    draw.rounded_rectangle(
        (0, 0, size[0], size[1]),
        radius=radius,
        fill=255,
    )

    return mask


def _place_rounded(
    canvas: Image.Image,
    image: Image.Image,
    box: tuple[int, int, int, int],
    radius: int = 28,
    shadow: bool = False,
    angle: float = 0,
) -> None:
    x, y, width, height = box

    fitted = ImageOps.fit(
        image,
        (width, height),
        method=Image.Resampling.LANCZOS,
    )

    if angle:
        fitted = fitted.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=True,
        )

    mask = _rounded_mask(
        fitted.size,
        radius,
    )

    if shadow:
        shadow_layer = Image.new(
            "RGBA",
            canvas.size,
            (0, 0, 0, 0),
        )

        shadow_mask = Image.new(
            "L",
            fitted.size,
            0,
        )

        shadow_draw = ImageDraw.Draw(
            shadow_mask
        )

        shadow_draw.rounded_rectangle(
            (
                0,
                0,
                fitted.width,
                fitted.height,
            ),
            radius=radius,
            fill=90,
        )

        shadow_piece = Image.new(
            "RGBA",
            fitted.size,
            (0, 0, 0, 110),
        )

        shadow_piece.putalpha(
            shadow_mask
        )

        shadow_layer.alpha_composite(
            shadow_piece,
            (
                x + 12,
                y + 16,
            ),
        )

        shadow_layer = shadow_layer.filter(
            ImageFilter.GaussianBlur(12)
        )

        canvas.alpha_composite(
            shadow_layer
        )

    piece = Image.new(
        "RGBA",
        fitted.size,
        (255, 255, 255, 0),
    )

    piece.paste(
        fitted,
        (0, 0),
        mask,
    )

    if angle:
        rotated = Image.new(
            "RGBA",
            canvas.size,
            (0, 0, 0, 0),
        )

        rotated.alpha_composite(
            piece,
            (
                x,
                y,
            ),
        )

        canvas.alpha_composite(
            rotated
        )
    else:
        canvas.alpha_composite(
            piece,
            (
                x,
                y,
            ),
        )


def _draw_text(
    canvas: Image.Image,
    text: str,
    xy: tuple[int, int],
    size: int,
    bold: bool = False,
    fill=(20, 20, 20, 255),
) -> None:
    draw = ImageDraw.Draw(canvas)

    draw.text(
        xy,
        text,
        font=_font(size, bold),
        fill=fill,
    )


def _clean_editorial(
    images: list[Image.Image],
    order: list[int],
) -> tuple[Image.Image, str]:
    canvas = Image.new(
        "RGBA",
        CANVAS,
        (244, 241, 236, 255),
    )

    valid = [
        index
        for index in order
        if 1 <= index <= len(images)
    ]

    if not valid:
        valid = list(
            range(1, len(images) + 1)
        )

    # Главная фотография
    hero = valid[0]

    _place_rounded(
        canvas,
        images[hero - 1],
        (
            MARGIN,
            145,
            CANVAS[0] - MARGIN * 2,
            700,
        ),
        radius=34,
    )

    # Маленькие фотографии снизу
    secondary = [
        index
        for index in valid
        if index != hero
    ]

    if secondary:
        y = 875

        available = (
            CANVAS[0]
            - MARGIN * 2
            - GAP * (min(len(secondary), 3) - 1)
        )

        count = min(
            len(secondary),
            3,
        )

        width = available // count

        for position, index in enumerate(
            secondary[:3]
        ):
            _place_rounded(
                canvas,
                images[index - 1],
                (
                    MARGIN
                    + position * (width + GAP),
                    y,
                    width,
                    310,
                ),
                radius=28,
            )

    _draw_text(
        canvas,
        "MOMENTS",
        (MARGIN, 54),
        34,
        bold=True,
    )

    _draw_text(
        canvas,
        "visual diary",
        (
            MARGIN + 220,
            62,
        ),
        20,
        fill=(100, 96, 90, 255),
    )

    return canvas, "Clean Editorial"


def _cinematic(
    images: list[Image.Image],
    order: list[int],
    hero_photo: int,
) -> tuple[Image.Image, str]:
    canvas = Image.new(
        "RGBA",
        CANVAS,
        (18, 18, 18, 255),
    )

    valid = [
        index
        for index in order
        if 1 <= index <= len(images)
    ]

    if not valid:
        valid = list(
            range(1, len(images) + 1)
        )

    if hero_photo not in valid:
        hero_photo = valid[0]

    # Большой фон
    background = ImageOps.fit(
        images[hero_photo - 1],
        CANVAS,
        method=Image.Resampling.LANCZOS,
    )

    # Затемняем изображение
    dark = Image.new(
        "RGBA",
        CANVAS,
        (0, 0, 0, 95),
    )

    background = background.convert(
        "RGBA"
    )

    background.alpha_composite(dark)

    canvas.alpha_composite(
        background
    )

    # Градиент снизу
    gradient = Image.new(
        "RGBA",
        CANVAS,
        (0, 0, 0, 0),
    )

    gradient_draw = ImageDraw.Draw(
        gradient
    )

    for y in range(650, CANVAS[1]):
        alpha = int(
            210
            * (
                (y - 650)
                / (CANVAS[1] - 650)
            )
        )

        gradient_draw.line(
            (0, y, CANVAS[0], y),
            fill=(0, 0, 0, alpha),
        )

    canvas.alpha_composite(
        gradient
    )

    # Дополнительные фотографии
    secondary = [
        index
        for index in valid
        if index != hero_photo
    ]

    card_w = 250
    card_h = 310

    for position, index in enumerate(
        secondary[:3]
    ):
        x = (
            CANVAS[0]
            - MARGIN
            - card_w
        )

        y = (
            MARGIN
            + position * (
                card_h + 20
            )
        )

        _place_rounded(
            canvas,
            images[index - 1],
            (
                x,
                y,
                card_w,
                card_h,
            ),
            radius=24,
            shadow=True,
        )

    _draw_text(
        canvas,
        "AFTER",
        (
            MARGIN,
            CANVAS[1] - 190,
        ),
        64,
        bold=True,
        fill=(255, 255, 255, 255),
    )

    _draw_text(
        canvas,
        "THE MOMENT",
        (
            MARGIN,
            CANVAS[1] - 115,
        ),
        64,
        bold=True,
        fill=(255, 255, 255, 255),
    )

    return canvas, "Cinematic"


def _moodboard(
    images: list[Image.Image],
    order: list[int],
    hero_photo: int,
) -> tuple[Image.Image, str]:
    """
    Асимметричный editorial layout.
    Плотная композиция без больших пустых областей.
    """

    canvas = Image.new(
        "RGBA",
        CANVAS,
        (238, 235, 229, 255),
    )

    valid = [
        index
        for index in order
        if 1 <= index <= len(images)
    ]

    if not valid:
        valid = list(
            range(1, len(images) + 1)
        )

    if hero_photo not in valid:
        hero_photo = valid[0]

    # -------------------------
    # 1. Главное изображение
    # -------------------------

    hero_width = 625
    hero_height = 790

    _place_rounded(
        canvas,
        images[hero_photo - 1],
        (
            MARGIN,
            110,
            hero_width,
            hero_height,
        ),
        radius=24,
        shadow=True,
    )

    # -------------------------
    # 2. Второстепенные фото
    # -------------------------

    secondary = [
        index
        for index in valid
        if index != hero_photo
    ]

    right_x = (
        MARGIN
        + hero_width
        + GAP
    )

    right_width = (
        CANVAS[0]
        - MARGIN
        - right_x
    )

    # Два вертикальных акцента справа
    for position, index in enumerate(
        secondary[:2]
    ):
        _place_rounded(
            canvas,
            images[index - 1],
            (
                right_x,
                110 + position * (
                    380 + GAP
                ),
                right_width,
                380,
            ),
            radius=24,
            shadow=True,
        )

    # -------------------------
    # 3. Нижняя полоса
    # -------------------------

    bottom = secondary[2:]

    if bottom:
        bottom_y = 930

        count = min(
            len(bottom),
            3,
        )

        available_width = (
            CANVAS[0]
            - MARGIN * 2
            - GAP * (count - 1)
        )

        cell_width = (
            available_width // count
        )

        cell_height = 300

        for position, index in enumerate(
            bottom[:3]
        ):
            _place_rounded(
                canvas,
                images[index - 1],
                (
                    MARGIN
                    + position * (
                        cell_width + GAP
                    ),
                    bottom_y,
                    cell_width,
                    cell_height,
                ),
                radius=22,
                shadow=False,
            )

    # -------------------------
    # 4. Минималистичная подпись
    # -------------------------

    _draw_text(
        canvas,
        "VISUAL STORY",
        (
            MARGIN,
            54,
        ),
        24,
        bold=True,
        fill=(55, 52, 48, 255),
    )

    _draw_text(
        canvas,
        "03",
        (
            CANVAS[0] - MARGIN - 40,
            54,
        ),
        22,
        bold=True,
        fill=(110, 105, 98, 255),
    )

    return canvas, "Editorial Story"

def _make_variant(
    images: list[Image.Image],
    number: int,
    plan: dict,
) -> CollageVariant:
    layout_type = plan.get(
        "layout_type",
        "grid",
    )

    order = plan.get(
        "photo_order",
        list(
            range(
                1,
                len(images) + 1,
            )
        ),
    )

    hero_photo = plan.get(
        "hero_photo",
        order[0] if order else 1,
    )

    if layout_type == "hero":
        canvas, default_title = _cinematic(
            images,
            order,
            hero_photo,
        )

    elif layout_type == "editorial":
        canvas, default_title = _moodboard(
            images,
            order,
            hero_photo,
        )

    else:
        canvas, default_title = _clean_editorial(
            images,
            order,
        )

    title = plan.get(
        "title",
        default_title,
    )

    return CollageVariant(
        number=number,
        title=title,
        image=_export(canvas),
    )


def generate_collages(
    source_images: list[bytes],
    composition_options: list[dict] | None = None,
) -> list[CollageVariant]:
    images = [
        _open(data)
        for data in source_images
    ]

    if not images:
        raise ValueError(
            "At least one image is required"
        )

    all_photos = list(
        range(
            1,
            len(images) + 1,
        )
    )

    if composition_options:
        plans = composition_options[:3]
    else:
        plans = [
            {
                "title": "Clean Editorial",
                "layout_type": "grid",
                "photo_order": all_photos,
                "hero_photo": all_photos[0],
            },
            {
                "title": "Cinematic",
                "layout_type": "hero",
                "photo_order": all_photos,
                "hero_photo": all_photos[0],
            },
            {
                "title": "Moodboard",
                "layout_type": "editorial",
                "photo_order": all_photos,
                "hero_photo": all_photos[0],
            },
        ]

    while len(plans) < 3:
        plans.append(plans[-1])

    return [
        _make_variant(
            images,
            number,
            plans[number - 1],
        )
        for number in range(1, 4)
    ]