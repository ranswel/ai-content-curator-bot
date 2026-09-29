from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✨ Создать идею"), KeyboardButton(text="🗑 Очистить подборку")]],
        resize_keyboard=True,
    )


def variant_keyboard(number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"Выбрать вариант {number}", callback_data=f"choose:{number}"),
    ]])
