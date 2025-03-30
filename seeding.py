# seeding.py
import os
import json
from app import db
from app.models import Category, Value
from config import datadir

# --- NEW: Определяем группы для категорий ---
CATEGORY_GROUP_MAP = {
    # Кузов и Экстерьер
    "Тип кузова (длинна базы)": "Кузов и Экстерьер",
    "Материалы кузова": "Кузов и Экстерьер",
    "Стиль дизайна": "Кузов и Экстерьер",
    "Осовенные фишки": "Кузов и Экстерьер", # Название странное, но по смыслу тут
    # Двигатель и Трансмиссия
    "Тип двигателя": "Двигатель и Трансмиссия",
    "Тип впуска двигателя": "Двигатель и Трансмиссия",
    "Количество л.с": "Двигатель и Трансмиссия",
    "Привод": "Двигатель и Трансмиссия",
    # Шасси и Подвеска
    "Тип шасси": "Шасси и Подвеска",
    # Интерьер и Особенности
    "Интерьер": "Интерьер и Особенности",
    "Мультимедиа": "Интерьер и Особенности",
    # Ограничения и Мета
    "Классификация": "Ограничения и Мета",
    "Год выпуска": "Ограничения и Мета",
    "Качество": "Ограничения и Мета",
    "Бюджет": "Ограничения и Мета",
    "Специальное условие": "Ограничения и Мета",
}
DEFAULT_GROUP = "Прочее"
# --- END NEW ---

def populate_initial_data():
    """
    Заполняет или обновляет базу данных значениями категорий из JSON,
    включая группу отображения для категорий.
    """
    json_path = os.path.join(datadir, "ready_data.json")

    print(f"Чтение данных для сидинга/обновления из {json_path}...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            automation_data = data.get("automation", {})
            if not automation_data:
                print("Предупреждение: Секция 'automation' в JSON не найдена или пуста.")
                # return
    except FileNotFoundError:
        print(f"Ошибка: Файл {json_path} не найден.")
        return
    except json.JSONDecodeError:
        print(f"Ошибка: Не удалось декодировать JSON из файла {json_path}.")
        return
    except Exception as e:
        print(f"Неожиданная ошибка при чтении файла: {e}")
        return

    print("Проверка и добавление категорий и значений...")
    try:
        for category_name, values_list in automation_data.items():
            if not isinstance(values_list, list):
                print(f"Предупреждение: Ожидался список значений для категории '{category_name}', пропуск.")
                continue

            # --- MODIFIED: Получаем или создаем категорию и назначаем группу ---
            category = Category.query.filter_by(name=category_name).first()
            display_group = CATEGORY_GROUP_MAP.get(category_name, DEFAULT_GROUP) # Получаем группу из карты

            if not category:
                category = Category(name=category_name, display_group=display_group)
                db.session.add(category)
                db.session.flush() # Flush to get category ID immediately
                print(f"  Добавлена новая категория: {category_name} (Группа: {display_group})")
            elif category.display_group != display_group: # Обновляем группу, если она изменилась или была пустой
                print(f"  Обновлена группа для категории '{category_name}' на '{display_group}'")
                category.display_group = display_group
            # --- END MODIFIED ---

            # Получаем текущие ОСНОВНЫЕ значения ИЗ БАЗЫ для этой категории
            existing_value_cores = {val.value_core for val in category.values}

            for value_item in values_list:
                value_str = str(value_item) # Полная строка из JSON
                parts = value_str.split(':', 1)
                value_core = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else None

                if value_core not in existing_value_cores:
                    new_value = Value(value_core=value_core, description=description, category=category)
                    db.session.add(new_value)
                    existing_value_cores.add(value_core) # Добавляем основное значение в set
                    # Убираем лог добавления значения, чтобы вывод был чище
                    # print(f"    Добавлено значение '{value_core}' в категорию '{category_name}'")
                # else: # Логика обновления описания существующего значения (если нужно)
                #     existing_value = next((v for v in category.values if v.value_core == value_core), None)
                #     if existing_value and existing_value.description != description:
                #         print(f"    Обновлено описание для '{value_core}' в '{category_name}'")
                #         existing_value.description = description


        db.session.commit()
        print("База данных успешно обновлена/заполнена данными категорий и их групп.")

    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при добавлении/обновлении данных: {e}")
        import traceback
        traceback.print_exc()