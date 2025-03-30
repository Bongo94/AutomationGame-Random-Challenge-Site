# seeding.py
import os
import json
from app import db
from app.models import Category, Value # Убедись, что Template импортирован, если нужно
from config import datadir

def populate_initial_data():
    """
    Заполняет или обновляет базу данных значениями категорий из JSON.
    Добавляет новые категории и новые значения (с разделением на value_core и description).
    Не удаляет существующие записи.
    """
    json_path = os.path.join(datadir, "ready_data.json")

    print(f"Чтение данных для сидинга/обновления из {json_path}...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            automation_data = data.get("automation", {})
            if not automation_data:
                print("Предупреждение: Секция 'automation' в JSON не найдена или пуста.")
                # return # Раскомментировать, если без 'automation' продолжать не нужно

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

            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.flush() # Flush to get category ID immediately
                print(f"  Добавлена новая категория: {category_name}")

            # Получаем текущие ОСНОВНЫЕ значения ИЗ БАЗЫ для этой категории
            existing_value_cores = {val.value_core for val in category.values}

            for value_item in values_list:
                value_str = str(value_item) # Полная строка из JSON

                # --- ИЗМЕНЕНИЕ: Разделяем строку ---
                parts = value_str.split(':', 1) # Разделяем по первому ':'
                value_core = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else None # Описание, если есть
                # --- КОНЕЦ ИЗМЕНЕНИЯ ---

                # Проверяем, существует ли уже такое ОСНОВНОЕ значение В ЭТОЙ КАТЕГОРИИ
                if value_core not in existing_value_cores:
                    # --- ИЗМЕНЕНИЕ: Создаем Value с новыми полями ---
                    new_value = Value(value_core=value_core, description=description, category=category)
                    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
                    db.session.add(new_value)
                    existing_value_cores.add(value_core) # Добавляем основное значение в set
                    print(f"    Добавлено значение '{value_core}' в категорию '{category_name}'")
                # else: # Логика обновления описания существующего значения (если нужно)
                #     existing_value = next((v for v in category.values if v.value_core == value_core), None)
                #     if existing_value and existing_value.description != description:
                #         print(f"    Обновлено описание для '{value_core}' в '{category_name}'")
                #         existing_value.description = description


        db.session.commit()
        print("База данных успешно обновлена/заполнена данными категорий.")

    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при добавлении/обновлении данных: {e}")
        import traceback
        traceback.print_exc() # <-- Для детальной отладки ошибки

# Запуск сидинга через `flask seed-db` (из run.py)