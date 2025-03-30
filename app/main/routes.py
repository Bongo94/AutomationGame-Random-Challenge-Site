# app/main/routes.py
from flask import Blueprint, render_template, current_app, request, jsonify, flash
from werkzeug.datastructures import MultiDict
from datetime import datetime

from ..models import Template, Category, Value
from .. import db
from ..utils.generator import ChallengeGenerator, ChallengeGeneratorError

main = Blueprint('main', __name__)


# --- Вспомогательная функция для сборки кастомного конфига ---
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
        apply_all = form_data.get(f'apply_all_{category_name}') == 'true' # <-- Получаем значение чекбокса "для всех"

        category_config = {}

        try:
            count = int(count_str) if count_str.isdigit() and int(count_str) > 0 else 1
            category_config['rule'] = rule
            category_config['count'] = count
            category_config['apply_all'] = apply_all # <-- Добавляем флаг в конфиг

            # Собираем опции для конкретных правил
            if rule == 'fixed':
                # Сначала проверяем select, потом text input
                fixed_value = form_data.get(f'fixed_value_select_{category_name}') or \
                              form_data.get(f'fixed_value_{category_name}')
                if not fixed_value:
                    raise ValueError("Не указано значение для правила 'fixed'.")
                category_config['value'] = fixed_value
            elif rule == 'random_from_list':
                allowed_values = form_data.getlist(f'allowed_values_{category_name}')
                if not allowed_values:
                    raise ValueError("Не выбраны значения для правила 'random_from_list'.")
                category_config['allowed_values'] = allowed_values
            elif rule == 'range':
                min_val = form_data.get(f'range_min_{category_name}')
                max_val = form_data.get(f'range_max_{category_name}')
                step_val = form_data.get(f'range_step_{category_name}', '1')
                if not min_val or not max_val: # Простая проверка на пустые строки
                    raise ValueError("Не указаны Мин/Макс для правила 'range'.")
                # Доп. проверки на число лучше делать в генераторе
                category_config['min'] = min_val
                category_config['max'] = max_val
                category_config['step'] = step_val
            # random_from_category не требует доп. параметров

            custom_config[category_name] = category_config

        except ValueError as e:
             msg = f"Ошибка в настройках категории '{category_name}': {e}"
             errors.append(msg)
             current_app.logger.warning(msg)
        except Exception as e:
             msg = f"Неожиданная ошибка при обработке настроек '{category_name}': {e}"
             errors.append(msg)
             current_app.logger.error(msg, exc_info=True)

    if errors and not custom_config:
         return None, errors
    return custom_config, errors


@main.route('/')
def index():
    """Главная страница."""
    try:
        templates = Template.query.order_by(Template.name).all()
        # Eager load values to avoid N+1 queries in the macro
        all_categories = Category.query.options(db.joinedload(Category.values)).order_by(Category.name).all()
    except Exception as e:
        current_app.logger.error(f"Database error fetching data for index: {e}")
        templates = []
        all_categories = []
        flash('Ошибка загрузки данных из базы данных.', 'error')

    return render_template('index.html',
                           templates=templates,
                           all_categories=all_categories,
                           result=None,
                           selected_template_id='custom', # Default to custom? Or None?
                           form_data=MultiDict(), # Use empty MultiDict for initial render
                           now=datetime.utcnow)


# --- Маршрут для генерации ---
@main.route('/generate', methods=['POST'])
def generate_challenge():
    result_data = None
    generation_errors = []
    selected_template_id = request.form.get('template_id')
    form_data = request.form # Сохраним для передачи в шаблон

    # --- NEW: Получаем количество игроков ---
    num_players_str = request.form.get('num_players', '1')
    try:
        num_players = int(num_players_str)
        if not (1 <= num_players <= 10): # Ограничиваем 1-10
            flash("Количество игроков должно быть от 1 до 10.", "warning")
            num_players = 1
    except ValueError:
        flash("Некорректное количество игроков. Установлено 1.", "warning")
        num_players = 1
    # --- END NEW ---

    current_app.logger.debug(f"Получен POST запрос на /generate. template_id: {selected_template_id}, num_players: {num_players}")

    generator = None
    custom_config = None

    try:
        if selected_template_id == 'custom':
            current_app.logger.debug("Режим 'custom'. Сбор конфигурации из формы.")
            custom_config, parsing_errors = _build_custom_config_from_form(form_data)
            generation_errors.extend(parsing_errors)

            if custom_config:
                current_app.logger.debug(f"Собран custom_config: {custom_config}")
                generator = ChallengeGenerator(custom_config=custom_config)
            elif not generation_errors:
                 # Если конфиг пуст И нет ошибок парсинга - значит не выбрали категорий
                 generation_errors.append("Для кастомной генерации нужно выбрать хотя бы одну категорию.")
                 flash("Для кастомной генерации нужно выбрать хотя бы одну категорию.", "warning")

        elif selected_template_id:
            current_app.logger.debug(f"Инициализация генератора для шаблона ID: {selected_template_id}")
            generator = ChallengeGenerator(template_id=selected_template_id)
            # Ошибки инициализации (e.g., шаблон не найден) будут в generator.errors или в исключении ChallengeGeneratorError
            generation_errors.extend(generator.errors) # Собираем ошибки инициализации
        else:
            flash("Необходимо выбрать шаблон или настроить кастомный челлендж.", "warning")
            generation_errors.append("Шаблон не выбран.") # Добавляем в ошибки для логики ниже

        # --- Вызов генератора (если он был создан и нет критических ошибок инициализации) ---
        if generator and not any("Шаблон с ID" in err for err in generation_errors): # Проверяем, что шаблон найден, если не кастом
             current_app.logger.debug(f"Вызов generator.generate(num_players={num_players})")
             # Передаем количество игроков в метод generate
             generated_result = generator.generate(num_players=num_players)
             generation_errors.extend(generator.errors) # Добавляем ошибки ИЗ генератора

             current_app.logger.debug(f"generator.generate() вернул: {generated_result}")
             current_app.logger.debug(f"Ошибки (парсинг + инициализация + генерация): {generation_errors}")

             if generated_result is not None:
                 result_data = generated_result # Это уже список словарей
             # Если результат None, ошибки уже должны быть в generation_errors
             elif not generation_errors: # На всякий случай, если генератор вернул None без ошибок
                 generation_errors.append("Генерация не дала результата по неизвестной причине.")
                 current_app.logger.warning(f"Генерация ({selected_template_id}, {num_players} players) вернула None без явных ошибок.")

    except ChallengeGeneratorError as e:
        # Ошибки, возникшие при *инициализации* генератора (например, не найден шаблон или нет конфига)
        current_app.logger.error(f"Ошибка инициализации ChallengeGenerator: {e}")
        generation_errors.append(f"Ошибка генератора: {e}")
    except Exception as e:
        current_app.logger.error(f"Неожиданная ошибка во время /generate: {e}", exc_info=True)
        generation_errors.append("Внутренняя ошибка сервера.")

    # Отображение ошибок пользователю
    # Используем set для удаления дубликатов ошибок
    unique_errors = list(dict.fromkeys(error for error in generation_errors if error)) # Убираем пустые и дубликаты
    if unique_errors:
        flash("При генерации возникли проблемы:", "error")
        for error in unique_errors:
            flash(f"- {error}", "warning") # Показываем как warning, т.к. может быть частичный результат

    # --- Получаем данные для рендеринга шаблона (как было) ---
    try:
        templates = Template.query.order_by(Template.name).all()
        all_categories = Category.query.options(db.joinedload(Category.values)).order_by(Category.name).all()
    except Exception as e:
        current_app.logger.error(f"Database error fetching data for re-render: {e}")
        templates = []
        all_categories = []
        flash('Ошибка загрузки данных из базы данных при перерисовке.', 'error')

    current_app.logger.debug(f"Рендеринг index.html с result_data: {result_data}")
    return render_template('index.html',
                           templates=templates,
                           all_categories=all_categories,
                           result=result_data, # result_data теперь список
                           selected_template_id=selected_template_id,
                           form_data=form_data, # Передаем исходные данные формы обратно
                           now=datetime.utcnow)