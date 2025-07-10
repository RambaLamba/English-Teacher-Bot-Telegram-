import psycopg2
import logging
from contextlib import contextmanager
from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Общий набор слов (10 слов: цвета, местоимения, базовые слова)
DEFAULT_WORDS = [
    ("Красный", "Red"),
    ("Синий", "Blue"),
    ("Зеленый", "Green"),
    ("Я", "I"),
    ("Ты", "You"),
    ("Он", "He"),
    ("Она", "She"),
    ("Дом", "House"),
    ("Книга", "Book"),
    ("Вода", "Water")
]


@contextmanager
def db_connection():
    """Автоматическое управление соединением с БД"""
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        yield conn
        conn.commit()
    except Exception as e:
        logging.error(f"Ошибка БД: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


@contextmanager
def db_cursor():
    """Автоматическое управление курсором"""
    with db_connection() as conn:
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()


def init_database():
    """Инициализация базы данных"""
    try:
        with db_cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS words (
                    word_id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    russian TEXT NOT NULL,
                    english TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS words_unique 
                ON words (user_id, russian, english)
            """)

            cur.execute("""
                INSERT INTO users (user_id, username) 
                VALUES (0, 'system') 
                ON CONFLICT (user_id) DO NOTHING
            """)

            # Общие слова
            for rus, eng in DEFAULT_WORDS:
                cur.execute("""
                    INSERT INTO words (user_id, russian, english)
                    VALUES (0, %s, %s)
                    ON CONFLICT (user_id, russian, english) DO NOTHING
                """, (rus, eng))

        logging.info("База данных успешно инициализирована")
    except Exception as e:
        logging.error(f"Ошибка инициализации БД: {e}")
        raise


def save_word(user_id, russian, english):
    """Сохраняет слово в словарь пользователя"""
    try:
        with db_cursor() as cur:
            # Добавляет пользователя если его нет
            cur.execute(
                "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
                (user_id,)
            )
            # Добавляет слово
            cur.execute(
                """
                INSERT INTO words (user_id, russian, english) 
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, russian, english) DO NOTHING
                """,
                (user_id, russian, english)
            )
            return cur.rowcount > 0
    except Exception as e:
        logging.error(f"Ошибка сохранения слова: {e}")
        return False


def get_random_word(user_id):
    """Получает случайное слово для пользователя"""
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT word_id, russian, english 
                FROM words 
                WHERE user_id IN (%s, 0)
                ORDER BY RANDOM() 
                LIMIT 1
            """, (user_id,))
            return cur.fetchone() or (None, None, None)
    except Exception as e:
        logging.error(f"Ошибка получения слова: {e}")
        return None, None, None


def get_other_words(user_id, exclude, limit=3):
    """Получает варианты для ответов"""
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT english FROM words
                WHERE user_id IN (%s, 0) 
                AND english != %s
                ORDER BY RANDOM() 
                LIMIT %s
            """, (user_id, exclude, limit))
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logging.error(f"Ошибка получения вариантов: {e}")
        return []


def delete_word(user_id, word_id):
    """Удаляет слово пользователя"""
    try:
        with db_cursor() as cur:
            cur.execute("""
                DELETE FROM words 
                WHERE user_id = %s AND word_id = %s AND user_id != 0
            """, (user_id, word_id))
            return cur.rowcount > 0
    except Exception as e:
        logging.error(f"Ошибка удаления слова: {e}")
        return False


def get_user_words(user_id):
    """Получает все слова пользователя"""
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT word_id, russian, english 
                FROM words 
                WHERE user_id = %s AND user_id != 0
                ORDER BY added_at DESC
            """, (user_id,))
            return cur.fetchall()
    except Exception as e:
        logging.error(f"Ошибка получения слов пользователя: {e}")
        return []
