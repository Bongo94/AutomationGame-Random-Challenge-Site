# init_db.py
import os
import json
from app import create_app, db
from app.models import Category, Value, Template
from config import datadir # Импортируем путь к папке data

# Создаем приложение в контексте, чтобы работать с БД
# Важно использовать ту же конфигурацию, что и для приложения
config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)

def populate_initial_data():
    """Заполняет базу данных начальными значениями из JSON."""
    # Путь к JSON файлу
    json_path = os.path.join(datadir, "ready_data.json")

    print("Проверка и заполнение базы данных...")
    # Проверим, есть ли уже категории, чтобы не дублировать
    if Category.query.first():
        print("База данных уже содержит данные категорий. Пропуск заполнения.")
        # Можно добавить логику обновления или выборочного добавления, если нужно
        return

    print(f"Чтение данных из {json_path}...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f).get("automation", {}) # Берем секцию automation, или пустой dict
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
        for category_name, values_list in data.items():
            if not isinstance(values_list, list):
                print(f"Предупреждение: Ожидался список значений для категории '{category_name}', пропуск.")
                continue

            category = Category(name=category_name)
            db.session.add(category)
            # db.session.flush() # Не обязательно здесь, можно в конце

            for value_item in values_list:
                value = Value(value_str=str(value_item), category=category)
                db.session.add(value)
        # Предварительно коммитим категории и значения, чтобы получить их ID для шаблонов (если нужно)
        db.session.flush()

    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при добавлении категорий/значений: {e}")
        return

    # --- Заполнение Шаблонов ---
    print("Добавление примеров шаблонов...")
    try:
        # Шаблон "Полный Рандом"
        all_categories = Category.query.all()
        config_all_random = {}
        for cat in all_categories:
             # Простой конфиг: для каждой категории берем 1 случайное значение
            config_all_random[cat.name] = {'count': 1, 'rule': 'random_from_category'}

        template_all = Template(name="Полный Рандом",
                                description="Случайный выбор по одному значению из всех категорий.",
                                config_json=json.dumps(config_all_random, ensure_ascii=False))
        db.session.add(template_all)

        # Шаблон "Ралли 70-х" (гипотетический)
        # Убедимся, что используем актуальные имена категорий
        config_rally_70s = {
            'bodies': {'count': 1, 'rule': 'filter_and_random', 'allowed_values': ['Купе (до 2.5)', 'Хетчбэк (до 2.5)']},
            'classifications': {'count': 1, 'rule': 'fixed', 'value': 'Ралли'},
            'drive_wheels': {'count': 1, 'rule': 'random_from_list', 'allowed_values': ['AWD', 'RWD']},
            'time_ranges': {'count': 1, 'rule': 'fixed', 'value': '70-е'},
            'horsepowers': {'count': 1, 'rule': 'range', 'min': 150, 'max': 350, 'step': 10},
            'materials': {'count': 1, 'rule': 'fixed', 'value': 'Сталь'},
            'is_frame': {'count': 1, 'rule': 'fixed', 'value': 'false'}
        }
        template_rally = Template(name="Ралли 70-х",
                                  description="Ограниченный челлендж для раллийных машин 70-х.",
                                  config_json=json.dumps(config_rally_70s, ensure_ascii=False))
        db.session.add(template_rally)

        # Сохраняем все изменения в БД
        db.session.commit()
        print("База данных успешно заполнена.")

    except Exception as e:
        db.session.rollback() # Откатываем изменения в случае ошибки
        print(f"Ошибка при добавлении шаблонов или коммите: {e}")


if __name__ == '__main__':
    # Этот блок выполнится при запуске скрипта: python init_db.py
    with app.app_context():
        print("Создание таблиц базы данных...")
        try:
            db.create_all() # Создаем таблицы, если их нет
            print("Таблицы успешно созданы или уже существуют.")
            populate_initial_data() # Заполняем данными
        except Exception as e:
            print(f"Ошибка при создании таблиц: {e}")