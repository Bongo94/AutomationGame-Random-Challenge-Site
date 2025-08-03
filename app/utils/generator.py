import random
import json
from ..models import Category, Value, Template
from .. import db

class ChallengeGeneratorError(Exception):
    """Пользовательское исключение для ошибок генерации."""
    pass

class ChallengeGenerator:
    """Класс для генерации параметров челленджа для одного или нескольких игроков."""

    # --- (Existing __init__, _load_template, generate, _get_... methods remain the same) ---
    def __init__(self, template_id=None, custom_config=None):
        """
        Инициализация генератора.
        Принимает либо ID шаблона, либо словарь с кастомной конфигурацией.
        """
        self.config = {}
        # self.result = {}
        self.errors = []

        if template_id and template_id != 'custom':
            self._load_template(template_id)
        elif custom_config:
            if not isinstance(custom_config, dict):
                 self.errors.append("Предоставленная кастомная конфигурация не является словарем.")
            else:
                self.config = custom_config
        else:
            pass


    def _load_template(self, template_id):
        """Загружает конфигурацию из шаблона по ID."""
        try:
            template = Template.query.get(int(template_id))
            if not template:
                self.errors.append(f"Шаблон с ID {template_id} не найден.")
                return
            self.config = template.config
            if not isinstance(self.config, dict):
                 self.errors.append(f"Конфигурация шаблона {template_id} не является словарем.")
                 self.config = {}
        except ValueError as e:
             self.errors.append(f"Ошибка загрузки шаблона ID {template_id}: Некорректный ID. {e}")
        except Exception as e:
            self.errors.append(f"Неожиданная ошибка при загрузке шаблона ID {template_id}: {e}")

    def generate(self, num_players=1):
        """
        Основной метод генерации челленджа на основе self.config для указанного числа игроков.
        Возвращает список словарей, где каждый словарь - результат для одного игрока,
        и саму использованную конфигурацию.
        """
        effective_config = self.config.copy()

        if not effective_config and not self.errors:
             self.errors.append("Конфигурация для генерации пуста.")

        if self.errors:
             if any("не найден" in str(e) or "не является словарем" in str(e) for e in self.errors):
                 return None, effective_config

        if not isinstance(num_players, int) or num_players < 1:
            self.errors.append("Некорректное количество игроков.")
            num_players = 1

        player_results = [{} for _ in range(num_players)]

        if effective_config:
            for category_name, rules in effective_config.items():
                if not isinstance(rules, dict):
                    if f"Некорректные правила для категории '{category_name}'." not in self.errors:
                        self.errors.append(f"Некорректные правила для категории '{category_name}'.")
                    continue

                rule_type = rules.get('rule', 'random_from_category')
                count = rules.get('count', 1)
                apply_all = rules.get('apply_all', False)

                try:
                    category = Category.query.filter_by(name=category_name).first()
                    if not category:
                        if f"Категория '{category_name}' не найдена в базе данных." not in self.errors:
                            self.errors.append(f"Категория '{category_name}' не найдена в базе данных.")
                        continue

                    generated_value_for_all = None
                    if apply_all:
                        category_errors_before = set(self.errors)
                        generated_value_for_all = self._generate_single_value_set(category, rules, rule_type, count)
                        category_errors_after = set(self.errors)
                        if generated_value_for_all is None and category_errors_after != category_errors_before:
                            continue

                    for i in range(num_players):
                        if apply_all:
                            if generated_value_for_all is not None:
                                player_results[i][category_name] = generated_value_for_all
                        else:
                            category_errors_before = set(self.errors)
                            individual_value = self._generate_single_value_set(category, rules, rule_type, count)
                            category_errors_after = set(self.errors)
                            if individual_value is not None and category_errors_after == category_errors_before:
                                player_results[i][category_name] = individual_value

                except ValueError as e:
                     msg = f"Ошибка значения в правилах для '{category_name}': {e}"
                     if msg not in self.errors: self.errors.append(msg)
                except Exception as e:
                    msg = f"Ошибка при генерации для категории '{category_name}': {e}"
                    if msg not in self.errors: self.errors.append(msg)


        if not any(p for p in player_results) and not self.errors:
             self.errors.append("Не удалось сгенерировать ни одного значения по заданным правилам.")

        # Return results AND the config used
        return player_results if any(p for p in player_results) else None, effective_config


    def _generate_single_value_set(self, category, rules, rule_type, count):
        """
        Генерирует набор значений для ОДНОЙ категории.
        Возвращает список словарей [{'value': ..., 'description': ...}] или None при ошибке.
        Appends errors to self.errors.
        """
        original_errors = set(self.errors)
        result = None
        try:
            if rule_type == 'fixed':
                fixed_value_core = rules.get('value')
                if fixed_value_core is None:
                    raise ValueError("Для правила 'fixed' должно быть указано 'value'.")
                value_obj = Value.query.filter_by(category_id=category.id, value_core=fixed_value_core).first()
                description = value_obj.description if value_obj else None
                result = [{'value': fixed_value_core, 'description': description}]
            elif rule_type == 'random_from_category':
                result = self._get_random_from_category(category, count)
            elif rule_type == 'random_from_list':
                allowed_values_core = rules.get('allowed_values')
                if not isinstance(allowed_values_core, list):
                    raise ValueError("Для правила 'random_from_list' должен быть указан список 'allowed_values'.")
                result = self._get_random_from_list(category, allowed_values_core, count)
            elif rule_type == 'range':
                min_val = rules.get('min')
                max_val = rules.get('max')
                step = rules.get('step', 1)
                if min_val is None or max_val is None:
                    raise ValueError("Для правила 'range' должны быть указаны 'min' и 'max'.")
                range_value = self._get_random_from_range(min_val, max_val, step)
                result = [{'value': str(range_value), 'description': None}]
            else:
                raise ValueError(f"Неизвестный тип правила '{rule_type}'.")

        except ValueError as e:
            msg = f"Категория '{category.name}': {e}"
            if msg not in self.errors: self.errors.append(msg)
            return None
        except Exception as e:
            msg = f"Неожиданная ошибка при генерации значения для '{category.name}': {e}"
            if msg not in self.errors: self.errors.append(msg)
            return None

        if set(self.errors) != original_errors:
            return None

        return result


    def _get_random_from_category(self, category, count):
        """Выбирает count случайных объектов Value из категории и форматирует результат."""
        all_value_objects = list(category.values)
        if not all_value_objects:
            raise ValueError(f"Нет доступных значений для категории '{category.name}'.")

        actual_count = min(count, len(all_value_objects))
        if actual_count < count:
            warn_msg = f"Для категории '{category.name}' запрошено {count}, доступно {len(all_value_objects)}. Выбрано {actual_count}."
            if warn_msg not in self.errors: self.errors.append(warn_msg)
        if actual_count == 0:
             raise ValueError(f"Нет доступных значений для категории '{category.name}' после применения ограничений.")


        selected_objects = random.sample(all_value_objects, actual_count)
        return [{'value': v.value_core, 'description': v.description} for v in selected_objects]

    def _get_random_from_list(self, category, allowed_values_core, count):
        """Выбирает count случайных объектов Value из заданного списка value_core."""
        if not allowed_values_core:
            raise ValueError("Список разрешенных значений (allowed_values) пуст.")

        possible_value_objects = [v for v in category.values if v.value_core in allowed_values_core]

        if not possible_value_objects:
            raise ValueError(
                f"В категории '{category.name}' нет значений, соответствующих списку: {allowed_values_core}.")

        actual_count = min(count, len(possible_value_objects))
        if actual_count < count:
            warn_msg = f"Запрошено {count} из списка для '{category.name}', доступно {len(possible_value_objects)}. Выбрано {actual_count}."
            if warn_msg not in self.errors: self.errors.append(warn_msg)
        if actual_count == 0:
            raise ValueError("Список разрешенных значений не содержит подходящих вариантов в этой категории.")

        selected_objects = random.sample(possible_value_objects, actual_count)
        return [{'value': v.value_core, 'description': v.description} for v in selected_objects]

    def _get_random_from_range(self, min_val, max_val, step):
        """Генерирует случайное число в диапазоне с шагом."""
        try:
            min_v = int(min_val)
            max_v = int(max_val)
            step_v = int(step) if step else 1
            if step_v <= 0: raise ValueError("Шаг должен быть положительным числом.")
            if min_v > max_v: raise ValueError("Мин значение не может быть больше Макс.")
            possible_values = list(range(min_v, max_v + 1, step_v))
            if not possible_values:
                raise ValueError(f"В диапазоне [{min_v}, {max_v}] с шагом {step_v} нет доступных целых значений.")
            return random.choice(possible_values)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Некорректные параметры для диапазона (min={min_val}, max={max_val}, step={step}): {e}")

    # --- NEW METHOD FOR REROLL ---
    def reroll_category(self, category, rules, num_values=None):
        """
        Генерирует значения для ОДНОЙ категории по заданным правилам.
        Не использует self.config. Возвращает список значений или None при ошибке.
        Ошибки записывает в self.errors.
        """
        self.errors = []

        if not isinstance(category, Category):
             self.errors.append("Некорректный объект категории для перегенерации.")
             return None
        if not isinstance(rules, dict):
             self.errors.append(f"Некорректные правила для перегенерации категории '{category.name}'.")
             return None

        rule_type = rules.get('rule', 'random_from_category')
        count = rules.get('count', 1)

        if num_values is not None:
            count = num_values

        result = self._generate_single_value_set(category, rules, rule_type, count)

        return result
