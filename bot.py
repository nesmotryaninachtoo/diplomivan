import asyncio
import os
from datetime import date

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv

from db import init_db, seed_demo_data
from services import LANG_TEXT, free_text_reply, get_contacts, get_faq, get_schedule, log_stat

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN", "")


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Русский", callback_data="lang:ru")],
            [InlineKeyboardButton(text="Беларуская", callback_data="lang:be")],
        ]
    )


def main_menu(lang: str) -> InlineKeyboardMarkup:
    labels = {
        "ru": ["Расписание", "Контакты", "FAQ", "Платные услуги", "Обратная связь"],
        "be": ["Расклад", "Кантакты", "FAQ", "Платныя паслугі", "Зваротная сувязь"],
    }
    values = ["schedule", "contacts", "faq", "paid", "feedback"]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=labels[lang][i], callback_data=f"menu:{values[i]}")]
            for i in range(len(values))
        ]
    )


class UserState(StatesGroup):
    language = State()


dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.set_state(UserState.language)
    await message.answer(LANG_TEXT["ru"]["welcome"], reply_markup=lang_keyboard())
    log_stat("telegram", str(message.from_user.id), "/start", "start")


@dp.callback_query(F.data.startswith("lang:"))
async def language_set(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split(":", maxsplit=1)[1]
    await state.update_data(lang=lang)
    await callback.message.answer(LANG_TEXT[lang]["menu"], reply_markup=main_menu(lang))
    await callback.answer()
    log_stat("telegram", str(callback.from_user.id), lang, "language")


@dp.callback_query(F.data.startswith("menu:"))
async def menu_handler(callback: CallbackQuery, state: FSMContext):
    item = callback.data.split(":", maxsplit=1)[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")

    if item == "schedule":
        answer = get_schedule(lang, "", date.today().isoformat())
    elif item == "contacts":
        answer = get_contacts(lang)
    elif item == "faq":
        answer = get_faq(lang)
    elif item == "paid":
        answer = LANG_TEXT[lang]["paid"]
    else:
        answer = LANG_TEXT[lang]["feedback"]

    await callback.message.answer(answer, reply_markup=main_menu(lang))
    await callback.answer()
    log_stat("telegram", str(callback.from_user.id), item, f"menu_{item}")


@dp.message()
async def text_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = message.text or ""
    answer = free_text_reply(lang, text)
    await message.answer(answer, reply_markup=main_menu(lang))
    log_stat("telegram", str(message.from_user.id), text, "free_text")


async def main():
    init_db()
    seed_demo_data()
    if not TOKEN:
        raise RuntimeError("Set TELEGRAM_TOKEN in environment")
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
