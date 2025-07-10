import random
import logging
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
from config import BOT_TOKEN
from data_base import (
    init_database, save_word, get_random_word,
    get_other_words, delete_word, get_user_words
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

init_database()

# Словарь для хранения данных
data = {}

MENU_BUTTONS = {
    'STUDY': 'Учить слова 🚀',
    'DICTIONARY': 'Мой словарь 📚',
    'ADD_WORD': 'Добавить слово ➕',
    'DELETE_WORD': 'Удалить слово 🔙',
    'MAIN_MENU': 'Главное меню ◀️',
    'SKIP': 'Пропустить ➡️',
    'CANCEL': 'Отмена ❌'
}


def clean_text(text):
    """Очищает текст от пробелов, кавычек и возможных невидимых символов"""
    if not text:
        return ""
    text = text.strip().strip("'").strip('"').encode('utf-8').decode('utf-8')
    return text


@bot.message_handler(commands=['start'])
def send_welcome(obj):
    """Отправляет приветственное сообщение и главное меню"""
    try:
        if isinstance(obj, types.Message):
            chat_id = obj.chat.id
            user_id = obj.from_user.id
        elif isinstance(obj, types.CallbackQuery):
            chat_id = obj.message.chat.id
            user_id = obj.from_user.id
        else:
            raise ValueError(f"Неподдерживаемый тип объекта: {type(obj)}")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(MENU_BUTTONS['STUDY'], MENU_BUTTONS['DICTIONARY'])
        markup.row(MENU_BUTTONS['ADD_WORD'], MENU_BUTTONS['DELETE_WORD'])

        bot.send_message(
            chat_id,
            '<b>Добро пожаловать! 🎉</b>\n\n'
            'Я помогу тебе учить английские слова! 📖\n'
            'Выбери опцию в меню ниже, чтобы начать.',
            reply_markup=markup
        )

        data.pop(chat_id, None)
        logging.info(f"Пользователь {user_id} открыл главное меню")
    except ApiTelegramException as e:
        logging.error(f"Ошибка при отправке приветственного сообщения: {e}")
        if "chat not found" in str(e).lower():
            logging.warning(f"Чат {chat_id} не найден. Возможно, бот заблокирован.")
        else:
            bot.send_message(chat_id, '⚠️ Произошла ошибка. Попробуйте снова.')
    except Exception as e:
        logging.error(f"Неизвестная ошибка в send_welcome: {e}")
        bot.send_message(chat_id, '⚠️ Произошла ошибка. Попробуйте снова.')


@bot.message_handler(func=lambda m: clean_text(m.text) == MENU_BUTTONS['ADD_WORD'])
def start_adding_word(message):
    """Начинает процесс добавления нового слова"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(MENU_BUTTONS['CANCEL'], MENU_BUTTONS['MAIN_MENU'])

    bot.send_message(
        message.chat.id,
        '📝 Введите слово в формате: <b>Русский - English</b>\n'
        'Пример: <i>Дом - House</i>',
        reply_markup=markup
    )
    data[message.chat.id] = {'mode': 'adding_word'}
    logging.info(f"Пользователь {message.from_user.id} начал добавление слова")


@bot.message_handler(func=lambda m: clean_text(m.text) in [MENU_BUTTONS['CANCEL'], MENU_BUTTONS['MAIN_MENU']])
def cancel_or_menu(message):
    """Обрабатывает отмену или возврат в главное меню"""
    data.pop(message.chat.id, None)
    send_welcome(message)


@bot.message_handler(func=lambda m: clean_text(m.text) == MENU_BUTTONS['DELETE_WORD'])
def start_deleting_word(message):
    """Показывает слова пользователя для удаления"""
    words = get_user_words(message.from_user.id)

    if not words:
        bot.send_message(message.chat.id, '📭 Ваш личный словарь пуст!')
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for word_id, russian, english in words:
        markup.add(types.InlineKeyboardButton(
            f'{russian} - {english}',
            callback_data=f'delete_{word_id}'
        ))

    markup.add(types.InlineKeyboardButton(MENU_BUTTONS['CANCEL'], callback_data='cancel_delete'))

    bot.send_message(
        message.chat.id,
        '🗑️ Выберите слово для удаления:',
        reply_markup=markup
    )
    data.pop(message.chat.id, None)
    logging.info(f"Пользователь {message.from_user.id} открыл меню удаления слов")


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def handle_delete(call):
    """Обрабатывает удаление слова"""
    try:
        chat_id = call.message.chat.id
        word_id = int(call.data.split('_')[1])
        if delete_word(call.from_user.id, word_id):
            bot.answer_callback_query(call.id, '✅ Слово удалено!')
            bot.delete_message(chat_id, call.message.message_id)
            bot.send_message(chat_id, 'Слово успешно удалено!')
        else:
            bot.answer_callback_query(call.id, '❌ Ошибка при удалении!')
            bot.send_message(chat_id, '❌ Ошибка при удалении слова.')
        send_welcome(call)
    except ApiTelegramException as e:
        logging.error(f"Ошибка при удалении слова: {e}")
        bot.answer_callback_query(call.id, '❌ Ошибка при удалении!')
        bot.send_message(call.from_user.id, '❌ Произошла ошибка. Попробуйте еще раз.')
        send_welcome(call)
    except Exception as e:
        logging.error(f"Ошибка при удалении слова: {e}")
        bot.answer_callback_query(call.id, '❌ Ошибка при удалении!')
        bot.send_message(call.from_user.id, '❌ Произошла ошибка. Попробуйте еще раз.')
        send_welcome(call)


@bot.callback_query_handler(func=lambda call: call.data == 'cancel_delete')
def cancel_delete(call):
    """Отменяет удаление слова"""
    try:
        chat_id = call.message.chat.id
        bot.delete_message(chat_id, call.message.message_id)
        bot.answer_callback_query(call.id)
        send_welcome(call)
    except ApiTelegramException as e:
        logging.error(f"Ошибка при отмене удаления: {e}")
        bot.answer_callback_query(call.id, '❌ Ошибка при отмене!')
        bot.send_message(call.from_user.id, '❌ Произошла ошибка. Попробуйте еще раз.')
        send_welcome(call)
    except Exception as e:
        logging.error(f"Ошибка при отмене удаления: {e}")
        bot.answer_callback_query(call.id, '❌ Ошибка при отмене!')
        bot.send_message(call.from_user.id, '❌ Произошла ошибка. Попробуйте еще раз.')
        send_welcome(call)


@bot.message_handler(func=lambda m: clean_text(m.text) == MENU_BUTTONS['DICTIONARY'])
def show_user_words(message):
    """Показывает все слова пользователя"""
    words = get_user_words(message.from_user.id)

    if not words:
        bot.send_message(message.chat.id, '📭 Ваш личный словарь пуст!')
        return

    response = '📚 <b>Ваши слова:</b>\n\n'
    for _, russian, english in words:
        response += f'• {russian} - {english}\n'

    bot.send_message(message.chat.id, response)
    data.pop(message.chat.id, None)  # Очищаем данные
    logging.info(f"Пользователь {message.from_user.id} просмотрел свой словарь")


@bot.message_handler(func=lambda m: clean_text(m.text) == MENU_BUTTONS['STUDY'])
def start_quiz(message):
    """Начинает квиз"""
    word = get_random_word(message.from_user.id)

    if not word or not word[0]:
        bot.send_message(
            message.chat.id,
            '📭 Ваш словарь пуст! Добавьте слова или используйте общие слова.'
        )
        return

    word_id, russian, english = word
    other_words = get_other_words(message.from_user.id, english)
    variants = [english] + other_words[:3]
    random.shuffle(variants)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    cleaned_variants = [clean_text(v) for v in variants]
    for word in cleaned_variants:
        markup.add(types.KeyboardButton(word))
    markup.row(MENU_BUTTONS['SKIP'], MENU_BUTTONS['MAIN_MENU'])

    sent_message = bot.send_message(
        message.chat.id,
        f'Как переводится слово: <b>{russian}</b>?',
        reply_markup=markup
    )

    # Сохраняет данные квиза
    data[message.chat.id] = {
        'mode': 'quiz',
        'message_id': sent_message.message_id,
        'correct': clean_text(english),
        'russian': russian,
        'variants': cleaned_variants,
        'word_id': word_id
    }

    logging.info(
        f"Пользователь {message.from_user.id} начал квиз, слово: {russian}, правильный ответ: {data[message.chat.id]['correct']}, варианты: {cleaned_variants}, raw_variants: {variants}")


@bot.message_handler(content_types=['text'])
def check_answer(message):
    """Проверяет ответ в квизе или добавление слова"""
    cleaned_text = clean_text(message.text)
    logging.info(f"Получен ответ: raw='{repr(message.text)}', cleaned='{cleaned_text}'")

    if message.chat.id not in data:
        logging.info(f"Нет активного режима для chat_id: {message.chat.id}")
        handle_other_messages(message)
        return

    mode = data[message.chat.id].get('mode')

    if mode == 'adding_word':
        process_new_word(message)
        return

    if mode == 'quiz':
        quiz = data[message.chat.id]
        correct = quiz['correct']
        russian = quiz['russian']
        variants = quiz['variants']
        message_id = quiz['message_id']

        logging.info(
            f"Проверка ответа в квизе: cleaned_text='{cleaned_text}', correct='{correct}', variants={variants}, quiz_message_id={message_id}")

        if cleaned_text in [MENU_BUTTONS['MAIN_MENU'], MENU_BUTTONS['CANCEL']]:
            data.pop(message.chat.id, None)
            send_welcome(message)
            return

        if cleaned_text == MENU_BUTTONS['SKIP']:
            bot.send_message(
                message.chat.id,
                f'⏭️ Пропущено! Правильный ответ: <b>{correct}</b>',
                reply_markup=types.ReplyKeyboardRemove()
            )
            data.pop(message.chat.id, None)
            start_quiz(message)
            return

        cleaned_text_lower = cleaned_text.lower()
        variants_lower = [v.lower() for v in variants]

        if cleaned_text_lower in variants_lower:
            if cleaned_text_lower == correct.lower():
                bot.send_message(
                    message.chat.id,
                    random.choice(['✅ Отлично!', '👍 Молодец!', '🎯 В точку!']),
                    reply_markup=types.ReplyKeyboardRemove()
                )
                data.pop(message.chat.id, None)
                start_quiz(message)
            else:
                bot.send_message(
                    message.chat.id,
                    f'❌ Неверно! Попробуйте еще раз для слова: <b>{russian}</b>'
                )
        else:
            bot.send_message(
                message.chat.id,
                f'🤔 Пожалуйста, выберите один из предложенных вариантов или используйте кнопки:\n'
                f'• {MENU_BUTTONS["SKIP"]}\n'
                f'• {MENU_BUTTONS["MAIN_MENU"]}'
            )
    else:
        logging.info(f"Неизвестный режим для chat_id: {message.chat.id}, mode: {mode}")
        handle_other_messages(message)


def process_new_word(message):
    """Обрабатывает новое слово"""
    cleaned_text = clean_text(message.text)
    logging.info(f"Обработка добавления слова: raw='{repr(message.text)}', cleaned='{cleaned_text}'")

    try:
        if '-' not in cleaned_text:
            bot.send_message(
                message.chat.id,
                '❌ Неверный формат! Используйте: <b>Русский - English</b>\n'
                'Пример: <i>Дом - House</i>'
            )
            return

        russian, english = [part.strip() for part in cleaned_text.split('-', 1)]

        if not russian or not english:
            bot.send_message(
                message.chat.id,
                '❌ Оба поля должны быть заполнены!'
            )
            return

        if save_word(message.from_user.id, russian, english):
            bot.send_message(
                message.chat.id,
                f'✅ Слово добавлено: <b>{russian} - {english}</b>',
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            bot.send_message(
                message.chat.id,
                f'⚠️ Слово <b>{russian} - {english}</b> уже есть в вашем словаре!',
                reply_markup=types.ReplyKeyboardRemove()
            )

    except Exception as e:
        logging.error(f"Ошибка при добавлении слова: {e}")
        bot.send_message(
            message.chat.id,
            '⚠️ Произошла ошибка. Попробуйте еще раз.',
            reply_markup=types.ReplyKeyboardRemove()
        )

    data.pop(message.chat.id, None)
    send_welcome(message)


@bot.message_handler(func=lambda m: True)
def handle_other_messages(message):
    """Обрабатывает неизвестные команды"""
    cleaned_text = clean_text(message.text)
    logging.warning(
        f"Неизвестное сообщение от {message.from_user.id}: raw='{repr(message.text)}', cleaned='{cleaned_text}'")

    bot.reply_to(message, f'🤔 Неизвестная команда. Используйте кнопки меню:\n'
                          f'• {MENU_BUTTONS["STUDY"]}\n'
                          f'• {MENU_BUTTONS["DICTIONARY"]}\n'
                          f'• {MENU_BUTTONS["ADD_WORD"]}\n'
                          f'• {MENU_BUTTONS["DELETE_WORD"]}')


if __name__ == '__main__':
    logging.info("Бот запущен!")
    try:
        bot.infinity_polling()
    except Exception as e:
        logging.error(f"Ошибка работы бота: {e}")