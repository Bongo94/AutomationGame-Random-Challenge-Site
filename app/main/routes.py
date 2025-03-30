# app/main/routes.py
from collections import OrderedDict
import json # Import json

from flask import Blueprint, render_template, current_app, request, jsonify, flash
from werkzeug.datastructures import MultiDict
from datetime import datetime

from ..models import Template, Category, Value
from .. import db
from ..utils.generator import ChallengeGenerator, ChallengeGeneratorError

main = Blueprint('main', __name__)

# --- (_build_custom_config_from_form remains the same) ---
def _build_custom_config_from_form(form_data):
    """Собирает словарь конфигурации из данных формы."""
    custom_config = {}
    errors = []
    included_categories = form_data.getlist('include_category')

    if not included_categories:
        errors.append("Для кастомной генерации нужно выбрать хотя бы одну категорию.")
        return None, errors

    for category_name in included_categories:
        rule = form_data.get(f'rule_{category_name}')
        count_str = form_data.get(f'count_{category_name}', '1')

        # --- INVERTED LOGIC ---
        # Читаем состояние нового чекбокса 'individual_{category_name}'
        is_individual_checked = form_data.get(f'individual_{category_name}') == 'true'

        # Флаг 'apply_all' для генератора должен быть ОБРАТНЫМ состоянию чекбокса 'individual'.
        # Если individual ОТМЕЧЕН (True) => apply_all = False (генерировать разные)
        # Если individual НЕ отмечен (False) => apply_all = True (генерировать одинаковые)
        apply_all_for_generator = not is_individual_checked
        # --- END INVERTED LOGIC ---

        category_config = {}

        try:
            count = 1
            if rule not in ['fixed', 'range']:
                 if not count_str.isdigit() or int(count_str) < 1:
                     raise ValueError("Количество должно быть положительным числом.")
                 count = int(count_str)

            category_config['rule'] = rule
            if rule not in ['fixed', 'range']:
                 category_config['count'] = count
            # Сохраняем инвертированное значение в конфигурацию
            category_config['apply_all'] = apply_all_for_generator

            # Сбор опций для правил (без изменений здесь)
            if rule == 'fixed':
                fixed_value_core = form_data.get(f'fixed_value_select_{category_name}')
                if not fixed_value_core:
                    fixed_value_core = form_data.get(f'fixed_value_{category_name}')
                if not fixed_value_core:
                    raise ValueError("Не указано значение для правила 'fixed'.")
                category_config['value'] = fixed_value_core # Используем value_core
            elif rule == 'random_from_list':
                allowed_values_core = form_data.getlist(f'allowed_values_{category_name}')
                if not allowed_values_core:
                    raise ValueError("Не выбраны значения для правила 'random_from_list'.")
                category_config['allowed_values'] = allowed_values_core # Используем value_core
            elif rule == 'range':
                min_val = form_data.get(f'range_min_{category_name}')
                max_val = form_data.get(f'range_max_{category_name}')
                step_val = form_data.get(f'range_step_{category_name}', '1')
                if min_val is None or min_val == '' or max_val is None or max_val == '':
                    raise ValueError("Не указаны Мин/Макс для правила 'range'.")
                try:
                    int(min_val)
                    int(max_val)
                    if step_val: int(step_val)
                except ValueError:
                    raise ValueError("Мин/Макс/Шаг для диапазона должны быть числами.")
                category_config['min'] = min_val
                category_config['max'] = max_val
                category_config['step'] = step_val if step_val else '1'

            custom_config[category_name] = category_config

        except ValueError as e:
             msg = f"Ошибка в настройках категории '{category_name}': {e}"
             errors.append(msg)
             current_app.logger.warning(msg)
        except Exception as e:
             msg = f"Неожиданная ошибка при обработке настроек '{category_name}': {e}"
             errors.append(msg)
             current_app.logger.error(msg, exc_info=True)

    if not custom_config and not errors and included_categories:
        errors.append("Не удалось собрать конфигурацию для выбранных категорий.")

    if errors and not custom_config:
        return None, errors
    return custom_config, errors

# --- (index route remains the same) ---
@main.route('/')
def index():
    """Главная страница."""
    templates = []
    grouped_categories = OrderedDict()
    group_order = [
        "Кузов и Экстерьер", "Двигатель и Трансмиссия", "Шасси и Подвеска",
        "Интерьер и Особенности", "Ограничения и Мета", "Прочее"
    ]

    try:
        templates = Template.query.order_by(Template.name).all()
        all_categories_from_db = Category.query.options(
            db.joinedload(Category.values)
        ).order_by(Category.display_group, Category.name).all()

        for group_name in group_order:
            grouped_categories[group_name] = []
        for category in all_categories_from_db:
            group_name = category.display_group if category.display_group else "Прочее"
            if group_name not in grouped_categories:
                grouped_categories[group_name] = []
            grouped_categories[group_name].append(category)

    except Exception as e:
        current_app.logger.error(f"Database error fetching data for index: {e}")
        flash('Ошибка загрузки данных из базы данных.', 'error')

    return render_template('index.html',
                           templates=templates,
                           grouped_categories=grouped_categories,
                           result=None,
                           selected_template_id='custom',
                           form_data=MultiDict(),
                           generation_config=None, # No config on initial load
                           now=datetime.utcnow)


# --- Маршрут /generate ---
@main.route('/generate', methods=['POST'])
def generate_challenge():
    result_data = None
    generation_errors = []
    selected_template_id = request.form.get('template_id')
    form_data = request.form
    final_config_used = {} # Store the config that was actually used

    num_players_str = request.form.get('num_players', '1')
    try:
        num_players = int(num_players_str)
        if not (1 <= num_players <= 10):
            flash("Количество игроков должно быть от 1 до 10.", "warning")
            num_players = max(1, min(num_players, 10))
    except ValueError:
        flash("Некорректное количество игроков. Установлено 1.", "warning")
        num_players = 1

    current_app.logger.debug(f"Получен POST запрос на /generate. template_id: {selected_template_id}, num_players: {num_players}")

    generator = None
    custom_config = None

    try:
        if selected_template_id == 'custom':
            current_app.logger.debug("Режим 'custom'. Сбор конфигурации из формы.")
            custom_config, parsing_errors = _build_custom_config_from_form(form_data)
            generation_errors.extend(parsing_errors)

            if custom_config is None and not parsing_errors:
                 flash("Для кастомной генерации нужно выбрать и настроить хотя бы одну категорию.", "warning")
                 # generation_errors.append("Категории для кастомной генерации не выбраны или не настроены.") # Redundant
            elif custom_config:
                current_app.logger.debug(f"Собран custom_config: {custom_config}")
                # Use the custom config directly, no need to instantiate generator here yet
                final_config_used = custom_config
            # else: parsing errors exist, handled below

        elif selected_template_id:
            current_app.logger.debug(f"Загрузка шаблона ID: {selected_template_id}")
            template = Template.query.get(int(selected_template_id))
            if template and isinstance(template.config, dict):
                final_config_used = template.config
            elif template: # Config is not dict
                 msg = f"Конфигурация шаблона '{template.name}' (ID: {selected_template_id}) повреждена."
                 generation_errors.append(msg)
                 flash(msg, 'error')
            else: # Template not found
                 msg = f"Шаблон с ID {selected_template_id} не найден."
                 generation_errors.append(msg)
                 flash(msg, 'error')
        else:
            flash("Необходимо выбрать шаблон или настроить кастомный челлендж.", "warning")
            generation_errors.append("Шаблон не выбран.")

        # --- Actual Generation ---
        # Proceed only if we have a config and no critical errors so far
        if final_config_used and not any("не найден" in e or "повреждена" in e for e in generation_errors):
            # Instantiate generator WITH the chosen/built config
            generator = ChallengeGenerator(custom_config=final_config_used) # Pass config directly
            # Add any init errors (should be rare now)
            generation_errors.extend(g_error for g_error in generator.errors if g_error not in generation_errors)

            if not generator.errors: # Only generate if init was ok
                 current_app.logger.debug(f"Вызов generator.generate(num_players={num_players}) с config: {final_config_used}")
                 # generate() now returns results AND the config it actually used (should be same as final_config_used)
                 generated_result, config_from_gen = generator.generate(num_players=num_players)
                 # Add generation errors
                 generation_errors.extend(g_error for g_error in generator.errors if g_error not in generation_errors)

                 current_app.logger.debug(f"generator.generate() вернул: {generated_result}")
                 current_app.logger.debug(f"Ошибки (всего): {generation_errors}")

                 if generated_result is not None:
                     result_data = generated_result
                 elif not generator.errors: # Generator returned None without explicit errors
                     generation_errors.append("Генерация не дала результата по неизвестной причине.")
                     current_app.logger.warning(f"Генерация ({selected_template_id}, {num_players} players) вернула None без явных ошибок.")

    except ValueError as e:
        # Catch potential int conversion errors for template ID if not caught earlier
        msg = f"Ошибка обработки ID шаблона: {e}"
        generation_errors.append(msg)
        flash(msg, 'error')
        current_app.logger.error(msg)
    except Exception as e:
        current_app.logger.error(f"Неожиданная ошибка во время /generate: {e}", exc_info=True)
        generation_errors.append("Внутренняя ошибка сервера при генерации.")
        flash("Произошла внутренняя ошибка сервера.", "error")

    # --- Error Display ---
    unique_errors = list(OrderedDict.fromkeys(error for error in generation_errors if error))
    if unique_errors:
        flash("При генерации возникли проблемы: " + "; ".join(unique_errors), "warning")

    # --- Re-fetch data for rendering ---
    templates = []
    grouped_categories = OrderedDict()
    group_order = [
        "Кузов и Экстерьер", "Двигатель и Трансмиссия", "Шасси и Подвеска",
        "Интерьер и Особенности", "Ограничения и Мета", "Прочее"
    ]
    try:
        templates = Template.query.order_by(Template.name).all()
        all_categories_from_db = Category.query.options(
            db.joinedload(Category.values)
        ).order_by(Category.display_group, Category.name).all()

        for group_name in group_order:
            grouped_categories[group_name] = []
        for category in all_categories_from_db:
            group_name = category.display_group if category.display_group else "Прочее"
            if group_name not in grouped_categories:
                grouped_categories[group_name] = []
            grouped_categories[group_name].append(category)

    except Exception as e:
        current_app.logger.error(f"Database error fetching data for re-render: {e}")
        flash('Ошибка загрузки данных из базы данных при перерисовке.', 'error')

    current_app.logger.debug(f"Рендеринг index.html с result_data: {result_data is not None}, config_used: {final_config_used is not None}")
    return render_template('index.html',
                           templates=templates,
                           grouped_categories=grouped_categories,
                           result=result_data,
                           selected_template_id=selected_template_id,
                           form_data=form_data,
                           # --- PASS THE CONFIG USED TO THE TEMPLATE ---
                           generation_config=final_config_used,
                           # ---
                           now=datetime.utcnow)


# --- NEW ROUTE FOR REROLL ---
@main.route('/reroll_category', methods=['POST'])
def reroll_category():
    """Handles AJAX request to reroll a single category."""
    data = request.get_json()
    if not data:
        return jsonify(success=False, error="Invalid request data."), 400

    category_name = data.get('category_name')
    rules = data.get('rules') # Expecting the rules dict directly

    if not category_name or not rules or not isinstance(rules, dict):
        return jsonify(success=False, error="Missing category name or rules."), 400

    current_app.logger.debug(f"Reroll requested for category: {category_name} with rules: {rules}")

    try:
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            return jsonify(success=False, error=f"Category '{category_name}' not found."), 404

        # Use a temporary generator instance just to access the reroll method
        # It doesn't need template_id or config during init for this
        temp_generator = ChallengeGenerator()
        new_values = temp_generator.reroll_category(category, rules)

        # Check for errors accumulated during the reroll
        if new_values is None:
            error_message = "; ".join(temp_generator.errors) if temp_generator.errors else f"Failed to reroll '{category_name}'."
            current_app.logger.warning(f"Reroll failed for '{category_name}': {error_message}")
            return jsonify(success=False, error=error_message), 500

        current_app.logger.debug(f"Reroll successful for '{category_name}'. New values: {new_values}")
        return jsonify(success=True, new_values=new_values)

    except Exception as e:
        current_app.logger.error(f"Error during reroll for category '{category_name}': {e}", exc_info=True)
        return jsonify(success=False, error="Internal server error during reroll."), 500
# --- END NEW ROUTE ---