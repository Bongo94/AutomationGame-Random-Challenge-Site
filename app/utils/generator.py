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

    # --- (Existing __init__, _load_template, generate, _get_... methods remain the same) ---
    def __init__(self, template_id=None, custom_config=None):
        """
        Инициализация генератора.
        Принимает либо ID шаблона, либо словарь с кастомной конфигурацией.
        """
        self.config = {}
        # self.result = {} # Result is returned from generate
        self.errors = [] # Errors accumulated during generation

        if template_id and template_id != 'custom':
            self._load_template(template_id)
        elif custom_config:
            # Basic validation (more specific validation happens during generation)
            if not isinstance(custom_config, dict):
                 self.errors.append("Предоставленная кастомная конфигурация не является словарем.")
                 # Don't raise here, let generate handle the empty config if it happens
            else:
                self.config = custom_config
        else:
            # If neither is provided, it's an invalid state unless called specifically for reroll
            pass # Allow initialization without config for reroll purposes


    def _load_template(self, template_id):
        """Загружает конфигурацию из шаблона по ID."""
        try:
            template = Template.query.get(int(template_id))
            if not template:
                self.errors.append(f"Шаблон с ID {template_id} не найден.")
                # Don't raise here, allow generate() to handle it
                return
            self.config = template.config # Используем property для получения dict
            if not isinstance(self.config, dict):
                 self.errors.append(f"Конфигурация шаблона {template_id} не является словарем.")
                 self.config = {} # Reset config on error
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
        # --- Store the effective config ---
        effective_config = self.config.copy() # Copy the config used for this generation run
        # ---

        if not effective_config and not self.errors:
             # If config is empty and no loading errors occurred (e.g., custom config was empty)
             self.errors.append("Конфигурация для генерации пуста.")

        if self.errors:
            # Return errors early if initialization failed severely
            # Check specifically for "not found" or "not a dict" type errors from _load_template
             if any("не найден" in str(e) or "не является словарем" in str(e) for e in self.errors):
                 # Return the config (even if empty) so the form can be re-rendered
                 return None, effective_config

        if not isinstance(num_players, int) or num_players < 1:
            self.errors.append("Некорректное количество игроков.")
            num_players = 1

        player_results = [{} for _ in range(num_players)]
        # Don't reset self.errors here, keep initialization errors

        # Proceed with generation only if we have a config
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
                        # Reset errors specific to this category generation attempt
                        category_errors_before = set(self.errors)
                        generated_value_for_all = self._generate_single_value_set(category, rules, rule_type, count)
                        category_errors_after = set(self.errors)
                        # Only proceed if no *new* errors occurred for this category
                        if generated_value_for_all is None and category_errors_after != category_errors_before:
                            continue # Skip applying if generation failed

                    for i in range(num_players):
                        if apply_all:
                            if generated_value_for_all is not None: # Check if generation succeeded
                                player_results[i][category_name] = generated_value_for_all
                        else:
                             # Reset errors specific to this category generation attempt
                            category_errors_before = set(self.errors)
                            individual_value = self._generate_single_value_set(category, rules, rule_type, count)
                            category_errors_after = set(self.errors)
                            # Add value only if generation succeeded without new errors
                            if individual_value is not None and category_errors_after == category_errors_before:
                                player_results[i][category_name] = individual_value

                except ValueError as e:
                     msg = f"Ошибка значения в правилах для '{category_name}': {e}"
                     if msg not in self.errors: self.errors.append(msg)
                except Exception as e:
                    msg = f"Ошибка при генерации для категории '{category_name}': {e}"
                    if msg not in self.errors: self.errors.append(msg)

        # Clean up results: remove players with no generated data if needed (optional)
        # player_results = [p for p in player_results if p]

        if not any(p for p in player_results) and not self.errors:
             # If results are empty, but no errors were explicitly recorded, add a generic one
             self.errors.append("Не удалось сгенерировать ни одного значения по заданным правилам.")

        # Return results AND the config used
        return player_results if any(p for p in player_results) else None, effective_config


    def _generate_single_value_set(self, category, rules, rule_type, count):
        """
        Генерирует набор значений для ОДНОЙ категории.
        Возвращает список словарей [{'value': ..., 'description': ...}] или None при ошибке.
        Appends errors to self.errors.
        """
        original_errors = set(self.errors) # Track errors added by this specific call
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
                 # Ensure range_value is not None (handled inside _get_random_from_range by raising error)
                result = [{'value': str(range_value), 'description': None}]
            else:
                raise ValueError(f"Неизвестный тип правила '{rule_type}'.")

        except ValueError as e:
            msg = f"Категория '{category.name}': {e}"
            if msg not in self.errors: self.errors.append(msg)
            return None # Error occurred
        except Exception as e:
            msg = f"Неожиданная ошибка при генерации значения для '{category.name}': {e}"
            if msg not in self.errors: self.errors.append(msg)
            return None # Error occurred

        # Check if any errors were added during this call specifically
        if set(self.errors) != original_errors:
            return None

        return result


    def _get_random_from_category(self, category, count):
        """Выбирает count случайных объектов Value из категории и форматирует результат."""
        all_value_objects = list(category.values)
        if not all_value_objects:
            # Raise error, caught by _generate_single_value_set
            raise ValueError(f"Нет доступных значений для категории '{category.name}'.")

        actual_count = min(count, len(all_value_objects))
        if actual_count < count:
            warn_msg = f"Для категории '{category.name}' запрошено {count}, доступно {len(all_value_objects)}. Выбрано {actual_count}."
            if warn_msg not in self.errors: self.errors.append(warn_msg) # Append warning, but proceed
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
            if warn_msg not in self.errors: self.errors.append(warn_msg) # Append warning, but proceed
        if actual_count == 0:
            raise ValueError("Список разрешенных значений не содержит подходящих вариантов в этой категории.")

        selected_objects = random.sample(possible_value_objects, actual_count)
        return [{'value': v.value_core, 'description': v.description} for v in selected_objects]

    def _get_random_from_range(self, min_val, max_val, step):
        """Генерирует случайное число в диапазоне с шагом."""
        try:
            min_v = int(min_val)
            max_v = int(max_val)
            step_v = int(step) if step else 1 # Default step to 1 if None or empty
            if step_v <= 0: raise ValueError("Шаг должен быть положительным числом.")
            # Allow min == max
            if min_v > max_v: raise ValueError("Мин значение не может быть больше Макс.")
            # Generate possible values carefully
            possible_values = list(range(min_v, max_v + 1, step_v))
            if not possible_values:
                # This can happen if e.g. min=10, max=10, step=2
                # Or min=5, max=10, step=6
                # Should we allow the min value in this case? Or error? Let's error.
                raise ValueError(f"В диапазоне [{min_v}, {max_v}] с шагом {step_v} нет доступных целых значений.")
            return random.choice(possible_values)
        except (TypeError, ValueError) as e:
            # Reraise with more context, caught by _generate_single_value_set
            raise ValueError(f"Некорректные параметры для диапазона (min={min_val}, max={max_val}, step={step}): {e}")

    # --- NEW METHOD FOR REROLL ---
    def reroll_category(self, category, rules, num_values=None):
        """
        Генерирует значения для ОДНОЙ категории по заданным правилам.
        Не использует self.config. Возвращает список значений или None при ошибке.
        Ошибки записывает в self.errors.
        """
        self.errors = [] # Clear errors for this specific reroll attempt

        if not isinstance(category, Category):
             self.errors.append("Некорректный объект категории для перегенерации.")
             return None
        if not isinstance(rules, dict):
             self.errors.append(f"Некорректные правила для перегенерации категории '{category.name}'.")
             return None

        rule_type = rules.get('rule', 'random_from_category')
        # Count is needed by helpers, default to 1 if not present (e.g., for fixed/range)
        count = rules.get('count', 1)

        # If num_values is provided, override the count from rules for this generation
        if num_values is not None:
            count = num_values

        # Use the main helper method. It handles all rule types and errors.
        result = self._generate_single_value_set(category, rules, rule_type, count)

        # _generate_single_value_set returns None on error and adds to self.errors
        return result
    # --- END NEW METHOD ---