# app/utils/generator.py
import random
import json
from ..models import Category, Value, Template
from .. import db

class ChallengeGeneratorError(Exception):
    """Пользовательское исключение для ошибок генерации."""
    pass

class ChallengeGenerator:
    """Класс для генерации параметров челленджа."""

    def __init__(self, template_id=None, custom_config=None):
        """
        Инициализация генератора.
        Принимает либо ID шаблона, либо словарь с кастомной конфигурацией.
        """
        self.config = {}
        self.result = {}
        self.errors = []

        if template_id and template_id != 'custom':
            self._load_template(template_id)
        elif custom_config:
            self.config = custom_config # TODO: Добавить валидацию кастомного конфига
        else:
            # Возможно, стоит загрузить шаблон "по умолчанию" или вызвать ошибку
            self.errors.append("Не указан шаблон или кастомная конфигурация.")
            raise ChallengeGeneratorError("Необходимо указать шаблон или кастомную конфигурацию.")

    def _load_template(self, template_id):
        """Загружает конфигурацию из шаблона по ID."""
        try:
            template = Template.query.get(int(template_id))
            if not template:
                self.errors.append(f"Шаблон с ID {template_id} не найден.")
                raise ChallengeGeneratorError(f"Шаблон с ID {template_id} не найден.")
            self.config = template.config # Используем property для получения dict
            if not isinstance(self.config, dict):
                 # Доп. проверка, если config_json был некорректным
                 raise ValueError("Конфигурация шаблона не является словарем.")
        except ValueError as e:
             self.errors.append(f"Ошибка загрузки шаблона ID {template_id}: Некорректный ID или формат конфигурации. {e}")
             raise ChallengeGeneratorError(f"Ошибка загрузки шаблона ID {template_id}: {e}")
        except Exception as e:
            self.errors.append(f"Неожиданная ошибка при загрузке шаблона ID {template_id}: {e}")
            raise ChallengeGeneratorError(f"Неожиданная ошибка при загрузке шаблона ID {template_id}: {e}")


    def generate(self):
        """Основной метод генерации челленджа на основе self.config."""
        if not self.config or self.errors:
            # Если была ошибка при инициализации или нет конфига
            return None

        self.result = {} # Сбрасываем предыдущий результат

        # Проходим по каждой категории, указанной в конфигурации шаблона
        for category_name, rules in self.config.items():
            if not isinstance(rules, dict):
                self.errors.append(f"Некорректные правила для категории '{category_name}'.")
                continue # Пропускаем эту категорию

            rule_type = rules.get('rule', 'random_from_category') # Правило по умолчанию
            count = rules.get('count', 1) # Количество значений по умолчанию

            try:
                # Получаем объект категории из БД
                category = Category.query.filter_by(name=category_name).first()
                if not category:
                    self.errors.append(f"Категория '{category_name}' не найдена в базе данных.")
                    continue

                # Выбираем метод генерации в зависимости от правила
                if rule_type == 'fixed':
                    value = rules.get('value')
                    if value is None:
                         raise ValueError("Для правила 'fixed' должно быть указано 'value'.")
                    # Для фиксированного значения count игнорируется, берем одно значение
                    self.result[category_name] = [value] # Результат всегда список
                elif rule_type == 'random_from_category':
                    self.result[category_name] = self._get_random_from_category(category, count)
                elif rule_type == 'random_from_list':
                    allowed_values = rules.get('allowed_values')
                    if not isinstance(allowed_values, list):
                         raise ValueError("Для правила 'random_from_list' должен быть указан список 'allowed_values'.")
                    self.result[category_name] = self._get_random_from_list(allowed_values, count)
                elif rule_type == 'range':
                     min_val = rules.get('min')
                     max_val = rules.get('max')
                     step = rules.get('step', 1) # Шаг по умолчанию 1
                     if min_val is None or max_val is None:
                         raise ValueError("Для правила 'range' должны быть указаны 'min' и 'max'.")
                     # Для диапазона count игнорируется, берем одно значение
                     self.result[category_name] = [self._get_random_from_range(min_val, max_val, step)]
                # Добавить другие правила по мере необходимости (filter_and_random, с весами и т.д.)
                elif rule_type == 'filter_and_random':
                     allowed_values = rules.get('allowed_values')
                     if not isinstance(allowed_values, list):
                         raise ValueError("Для правила 'filter_and_random' должен быть указан список 'allowed_values'.")
                     self.result[category_name] = self._get_filtered_random(category, allowed_values, count)
                else:
                    self.errors.append(f"Неизвестный тип правила '{rule_type}' для категории '{category_name}'.")

            except ValueError as e:
                 self.errors.append(f"Ошибка значения в правилах для '{category_name}': {e}")
            except Exception as e:
                self.errors.append(f"Ошибка при генерации для категории '{category_name}': {e}")
                # Можно решить, продолжать ли генерацию для других категорий или остановиться

        if self.errors:
             # Можно вернуть частичный результат и ошибки, или None
             print(f"Ошибки генерации: {self.errors}") # Логируем ошибки
             return None # Или self.result, если хотим показать частичный результат

        return self.result

    # --- Вспомогательные методы для разных правил генерации ---

    def _get_random_from_category(self, category, count):
        """Выбирает count случайных значений из всех значений категории."""
        # Получаем все значения как строки
        # Используем .with_entities(Value.value_str) для оптимизации - получаем только строки
        all_values = [v.value_str for v in category.values]
        if not all_values:
            raise ValueError(f"Нет доступных значений для категории '{category.name}'.")

        # Убедимся, что count не больше доступного количества уникальных значений
        actual_count = min(count, len(all_values))
        if actual_count < count:
            self.errors.append(f"Для категории '{category.name}' запрошено {count} значений, но доступно только {len(all_values)}. Выбрано {actual_count}.")

        return random.sample(all_values, actual_count) # sample выбирает без повторений

    def _get_random_from_list(self, allowed_values, count):
        """Выбирает count случайных значений из заданного списка."""
        if not allowed_values:
            raise ValueError("Список разрешенных значений пуст.")

        actual_count = min(count, len(allowed_values))
        if actual_count < count:
             self.errors.append(f"Запрошено {count} значений из списка, но доступно только {len(allowed_values)}. Выбрано {actual_count}.")

        return random.sample(allowed_values, actual_count)

    def _get_random_from_range(self, min_val, max_val, step):
        """Генерирует случайное число в диапазоне с шагом."""
        try:
            min_val = int(min_val)
            max_val = int(max_val)
            step = int(step)
            if step <= 0:
                raise ValueError("Шаг должен быть положительным числом.")
            if min_val > max_val:
                raise ValueError("Минимальное значение не может быть больше максимального.")
            # Генерируем все возможные значения в диапазоне
            possible_values = list(range(min_val, max_val + 1, step))
            if not possible_values:
                raise ValueError("В указанном диапазоне с шагом нет доступных значений.")
            return random.choice(possible_values)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Некорректные параметры для диапазона (min={min_val}, max={max_val}, step={step}): {e}")

    def _get_filtered_random(self, category, allowed_values_str, count):
        """Выбирает случайные значения из категории, но только те, что есть в списке allowed_values_str."""
        # Получаем ID значений, соответствующих строкам из allowed_values_str в данной категории
        allowed_db_values = [v for v in category.values if v.value_str in allowed_values_str]
        allowed_values = [v.value_str for v in allowed_db_values]

        if not allowed_values:
            raise ValueError(f"В категории '{category.name}' нет значений, соответствующих фильтру: {allowed_values_str}.")

        actual_count = min(count, len(allowed_values))
        if actual_count < count:
            self.errors.append(f"Для категории '{category.name}' после фильтрации доступно {len(allowed_values)} значений (запрошено {count}). Выбрано {actual_count}.")

        return random.sample(allowed_values, actual_count)