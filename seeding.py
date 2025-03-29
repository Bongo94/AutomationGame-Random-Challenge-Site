# seeding.py (Адаптированная и улучшенная версия)
import os
import json
from app import db # <--- Импортируем db из app
from app.models import Category, Value # Убедись, что Template импортирован, если нужно
from config import datadir

# Функция должна работать с уже инициализированным 'db' в контексте приложения
def populate_initial_data():
    """
    Заполняет или обновляет базу данных значениями категорий из JSON.
    Добавляет новые категории и новые значения к существующим категориям.
    Не удаляет существующие записи.
    """
    json_path = os.path.join(datadir, "ready_data.json5")

    print(f"Чтение данных для сидинга/обновления из {json_path}...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            # --- ИЗМЕНЕНИЕ: Берем весь словарь, а не только 'automation' ---
            # Это позволит легче добавлять другие секции, если нужно
            # Если структура всегда 'automation', можно оставить .get("automation", {})
            data = json.load(f)
            automation_data = data.get("automation", {}) # Получаем данные для automation
            if not automation_data:
                print("Предупреждение: Секция 'automation' в JSON не найдена или пуста.")
                # Решаем, прерывать ли или продолжать (если есть другие секции)
                # return # Раскомментировать, если без 'automation' продолжать не нужно
                # Оставим возможность добавления других секций в будущем

    except FileNotFoundError:
        print(f"Ошибка: Файл {json_path} не найден.")
        return
    except json.JSONDecodeError:
        print(f"Ошибка: Не удалось декодировать JSON из файла {json_path}.")
        return
    except Exception as e:
        print(f"Неожиданная ошибка при чтении файла: {e}")
        return

    # --- Заполнение/Обновление Категорий и Значений ---
    print("Проверка и добавление категорий и значений...")
    try:
        # --- УДАЛЕНА ПРОВЕРКА if Category.query.first(): ---
        # Теперь скрипт будет работать и на непустой базе

        # Обрабатываем секцию automation
        for category_name, values_list in automation_data.items():
            if not isinstance(values_list, list):
                print(f"Предупреждение: Ожидался список значений для категории '{category_name}', пропуск.")
                continue

            # 1. Найти или создать категорию
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
                # Используем flush, чтобы получить ID категории для связи со значениями, если она новая
                # db.session.flush() # Не обязательно, если commit в конце
                print(f"  Добавлена новая категория: {category_name}")
            # else: # Если нужно, можно добавить логику обновления описания категории и т.д.
            #    print(f"  Категория '{category_name}' уже существует.")
            #    pass

            # 2. Добавить отсутствующие значения для этой категории
            # Получаем текущие значения ИЗ БАЗЫ для этой категории, чтобы не делать много запросов в цикле
            existing_value_strs = {val.value_str for val in category.values} # Используем set для быстрой проверки

            for value_item in values_list:
                value_str = str(value_item) # Приводим к строке на всякий случай (для bool/int)

                # Проверяем, существует ли уже такое значение В ЭТОЙ КАТЕГОРИИ
                if value_str not in existing_value_strs:
                    new_value = Value(value_str=value_str, category=category)
                    db.session.add(new_value)
                    existing_value_strs.add(value_str) # Добавляем в set, чтобы не добавить дубль из JSON
                    print(f"    Добавлено значение '{value_str}' в категорию '{category_name}'")

        # --- КОНЕЦ обработки automation ---

        # Можно добавить обработку других секций из JSON здесь, если нужно

        # Фиксируем все изменения в базе данных
        db.session.commit()
        print("База данных успешно обновлена/заполнена данными категорий.")

    except Exception as e:
        db.session.rollback() # Важно откатить изменения при любой ошибке
        print(f"Ошибка при добавлении/обновлении данных: {e}")
        # Можно добавить traceback для детальной отладки
        # import traceback
        # traceback.print_exc()

# Код для запуска через flask seed-db остается в run.py
# Удали или закомментируй блок if __name__ == '__main__': если он был здесь