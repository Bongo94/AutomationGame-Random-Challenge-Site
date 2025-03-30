# app/utils/generator.py
import random
import json
from ..models import Category, Value, Template
from .. import db

class ChallengeGeneratorError(Exception):
    """Пользовательское исключение для ошибок генерации."""
    pass

class ChallengeGenerator:
    """Класс для генерации параметров челленджа для одного или нескольких игроков."""

    def __init__(self, template_id=None, custom_config=None):
        """
        Инициализация генератора.
        Принимает либо ID шаблона, либо словарь с кастомной конфигурацией.
        """
        self.config = {}
        # self.result = {} # <--- Удаляем, результат теперь будет возвращаться из generate
        self.errors = []

        if template_id and template_id != 'custom':
            self._load_template(template_id)
        elif custom_config:
            # Валидация кастомного конфига должна быть тут или в _build_custom_config_from_form
            self.config = custom_config
        else:
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
                 raise ValueError("Конфигурация шаблона не является словарем.")
        except ValueError as e:
             self.errors.append(f"Ошибка загрузки шаблона ID {template_id}: Некорректный ID или формат конфигурации. {e}")
             raise ChallengeGeneratorError(f"Ошибка загрузки шаблона ID {template_id}: {e}")
        except Exception as e:
            self.errors.append(f"Неожиданная ошибка при загрузке шаблона ID {template_id}: {e}")
            raise ChallengeGeneratorError(f"Неожиданная ошибка при загрузке шаблона ID {template_id}: {e}")

    def generate(self, num_players=1): # <--- Добавляем параметр num_players
        """
        Основной метод генерации челленджа на основе self.config для указанного числа игроков.
        Возвращает список словарей, где каждый словарь - результат для одного игрока.
        """
        if not self.config or self.errors:
            return None # Если была ошибка при инициализации или нет конфига

        if not isinstance(num_players, int) or num_players < 1:
            self.errors.append("Некорректное количество игроков.")
            num_players = 1 # По умолчанию 1 игрок

        # Инициализируем результат как список пустых словарей для каждого игрока
        player_results = [{} for _ in range(num_players)]
        self.errors = [] # Сбрасываем ошибки перед генерацией

        # Проходим по каждой категории, указанной в конфигурации шаблона
        for category_name, rules in self.config.items():
            if not isinstance(rules, dict):
                self.errors.append(f"Некорректные правила для категории '{category_name}'.")
                continue # Пропускаем эту категорию

            rule_type = rules.get('rule', 'random_from_category')
            count = rules.get('count', 1)
            apply_all = rules.get('apply_all', False) # <-- Получаем флаг "для всех"

            try:
                # Получаем объект категории из БД
                category = Category.query.filter_by(name=category_name).first()
                if not category:
                    self.errors.append(f"Категория '{category_name}' не найдена в базе данных.")
                    continue

                generated_value_for_all = None
                if apply_all:
                    # Генерируем ОДИН раз, если "для всех"
                    generated_value_for_all = self._generate_single_value_set(category, rules, rule_type, count)
                    if generated_value_for_all is None: # Если произошла ошибка при генерации
                         continue # Ошибка уже добавлена в self.errors

                # Распределяем значения по игрокам
                for i in range(num_players):
                    if apply_all:
                        # Используем заранее сгенерированное значение
                        player_results[i][category_name] = generated_value_for_all
                    else:
                        # Генерируем индивидуальное значение для каждого игрока
                        individual_value = self._generate_single_value_set(category, rules, rule_type, count)
                        if individual_value is not None:
                             player_results[i][category_name] = individual_value
                        # Если individual_value is None, ошибка уже добавлена, пропускаем для этого игрока

            except ValueError as e:
                 msg = f"Ошибка значения в правилах для '{category_name}': {e}"
                 # Не ясно, к какому игроку отнести ошибку - добавляем в общие
                 if msg not in self.errors: self.errors.append(msg)
            except Exception as e:
                msg = f"Ошибка при генерации для категории '{category_name}': {e}"
                if msg not in self.errors: self.errors.append(msg)

        if self.errors:
             print(f"Ошибки генерации: {self.errors}") # Логируем ошибки
             # Решаем, возвращать ли частичный результат или None
             # Вернем частичный результат, чтобы пользователь видел, что получилось
             # return None

        return player_results

    def _generate_single_value_set(self, category, rules, rule_type, count):
        """
        Вспомогательный метод для генерации одного набора значений (списка)
        для одной категории по заданным правилам.
        Возвращает список значений или None в случае ошибки.
        """
        try:
            if rule_type == 'fixed':
                value = rules.get('value')
                if value is None:
                    raise ValueError("Для правила 'fixed' должно быть указано 'value'.")
                return [value] # Результат всегда список
            elif rule_type == 'random_from_category':
                return self._get_random_from_category(category, count)
            elif rule_type == 'random_from_list':
                allowed_values = rules.get('allowed_values')
                if not isinstance(allowed_values, list):
                    raise ValueError("Для правила 'random_from_list' должен быть указан список 'allowed_values'.")
                return self._get_random_from_list(allowed_values, count)
            elif rule_type == 'range':
                min_val = rules.get('min')
                max_val = rules.get('max')
                step = rules.get('step', 1)
                if min_val is None or max_val is None:
                    raise ValueError("Для правила 'range' должны быть указаны 'min' и 'max'.")
                return [self._get_random_from_range(min_val, max_val, step)] # Результат - список с одним значением
            elif rule_type == 'filter_and_random': # Проверяем, если был добавлен
                allowed_values = rules.get('allowed_values')
                if not isinstance(allowed_values, list):
                    raise ValueError("Для правила 'filter_and_random' должен быть указан список 'allowed_values'.")
                return self._get_filtered_random(category, allowed_values, count)
            else:
                raise ValueError(f"Неизвестный тип правила '{rule_type}'.")
        except ValueError as e:
            # Добавляем ошибку и возвращаем None, чтобы внешний цикл мог её обработать
            msg = f"Категория '{category.name}': {e}"
            if msg not in self.errors: self.errors.append(msg)
            return None
        except Exception as e:
            msg = f"Неожиданная ошибка при генерации значения для '{category.name}': {e}"
            if msg not in self.errors: self.errors.append(msg)
            return None

    # --- Вспомогательные методы для разных правил генерации (_get_random_... и т.д.) остаются без изменений ---
    # Они генерируют ОДИН набор значений (список)

    def _get_random_from_category(self, category, count):
        """Выбирает count случайных значений из всех значений категории."""
        all_values = [v.value_str for v in category.values]
        if not all_values:
            raise ValueError(f"Нет доступных значений для категории '{category.name}'.")
        actual_count = min(count, len(all_values))
        if actual_count < count:
            warn_msg = f"Для категории '{category.name}' запрошено {count} значений, но доступно только {len(all_values)}. Выбрано {actual_count}."
            if warn_msg not in self.errors: self.errors.append(warn_msg) # Используем как предупреждение
        if actual_count == 0: # Если значений 0, но категория есть
             raise ValueError(f"Нет доступных значений для категории '{category.name}' после применения ограничений.")
        return random.sample(all_values, actual_count)

    def _get_random_from_list(self, allowed_values, count):
        """Выбирает count случайных значений из заданного списка."""
        if not allowed_values:
            raise ValueError("Список разрешенных значений пуст.")
        actual_count = min(count, len(allowed_values))
        if actual_count < count:
             warn_msg = f"Запрошено {count} значений из списка, но доступно только {len(allowed_values)}. Выбрано {actual_count}."
             if warn_msg not in self.errors: self.errors.append(warn_msg)
        if actual_count == 0:
             raise ValueError("Список разрешенных значений пуст или не содержит подходящих вариантов.")
        return random.sample(allowed_values, actual_count)

    def _get_random_from_range(self, min_val, max_val, step):
        """Генерирует случайное число в диапазоне с шагом."""
        try:
            min_val = int(min_val)
            max_val = int(max_val)
            step = int(step)
            if step <= 0: raise ValueError("Шаг должен быть положительным числом.")
            if min_val > max_val: raise ValueError("Мин значение не может быть больше Макс.")
            possible_values = list(range(min_val, max_val + 1, step))
            if not possible_values: raise ValueError("В указанном диапазоне с шагом нет доступных значений.")
            return random.choice(possible_values)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Некорректные параметры для диапазона (min={min_val}, max={max_val}, step={step}): {e}")

    def _get_filtered_random(self, category, allowed_values_str, count):
        """Выбирает случайные значения из категории, но только те, что есть в списке allowed_values_str."""
        allowed_db_values = [v for v in category.values if v.value_str in allowed_values_str]
        allowed_values = [v.value_str for v in allowed_db_values]

        if not allowed_values:
            raise ValueError(f"В категории '{category.name}' нет значений, соответствующих фильтру: {allowed_values_str}.")

        actual_count = min(count, len(allowed_values))
        if actual_count < count:
            warn_msg = f"Для категории '{category.name}' после фильтрации доступно {len(allowed_values)} значений (запрошено {count}). Выбрано {actual_count}."
            if warn_msg not in self.errors: self.errors.append(warn_msg)
        if actual_count == 0:
            raise ValueError(f"В категории '{category.name}' после фильтрации не осталось значений.")
        return random.sample(allowed_values, actual_count)