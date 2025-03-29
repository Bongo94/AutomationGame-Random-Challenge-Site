# seeding.py (Адаптированная версия)
import os
import json
from app import db # <--- Импортируем db из app
from app.models import Category, Value, Template
from config import datadir

# Функция должна работать с уже инициализированным 'db' в контексте приложения
def populate_initial_data():
    """Заполняет базу данных начальными значениями из JSON."""
    json_path = os.path.join(datadir, "ready_data.json")

    print("Проверка и заполнение базы данных начальными данными...")
    # Проверка на существование данных (можно оставить)
    if Category.query.first():
        print("База данных уже содержит данные категорий. Пропуск заполнения.")
        return

    print(f"Чтение данных из {json_path}...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f).get("automation", {})
            if not data:
                print("Ошибка: Секция 'automation' в JSON не найдена или пуста.")
                return
    except FileNotFoundError:
        print(f"Ошибка: Файл {json_path} не найден.")
        return
    except json.JSONDecodeError:
        print(f"Ошибка: Не удалось декодировать JSON из файла {json_path}.")
        return
    except Exception as e:
        print(f"Неожиданная ошибка при чтении файла: {e}")
        return

    # --- Заполнение Категорий и Значений ---
    print("Добавление категорий и значений...")
    try:
        # ... (остальной код добавления категорий, значений, шаблонов как был) ...
        # ... используем db.session.add(), db.session.flush(), db.session.commit() ...

        # В конце успешного добавления
        db.session.commit()
        print("База данных успешно заполнена начальными данными.")

    except Exception as e:
        db.session.rollback() # Важно откатить изменения при ошибке
        print(f"Ошибка при добавлении данных: {e}")

# Удали или закомментируй блок if __name__ == '__main__':
# if __name__ == '__main__':
#    config_name = os.getenv('FLASK_CONFIG') or 'default'
#    app = create_app(config_name)
#    with app.app_context():
#        print("Создание таблиц базы данных...")
#        try:
#            db.create_all()
#            print("Таблицы успешно созданы или уже существуют.")
#            populate_initial_data()
#        except Exception as e:
#            print(f"Ошибка при создании таблиц: {e}")