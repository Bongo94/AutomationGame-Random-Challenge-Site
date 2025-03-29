# app/main/routes.py
from flask import Blueprint, render_template, current_app, request, jsonify, flash  # Добавили request и jsonify
from werkzeug.datastructures import MultiDict

from ..models import Template, Category, Value # Убедись, что Category и Value импортированы
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
        # Можно вернуть пустой конфиг и ошибку, или поднять исключение
        return None, errors

    for category_name in included_categories:
        rule = form_data.get(f'rule_{category_name}')
        count_str = form_data.get(f'count_{category_name}', '1')
        category_config = {}

        try:
            count = int(count_str) if count_str.isdigit() else 1
            category_config['rule'] = rule
            category_config['count'] = count # Генератор сам разберется, нужен ли count

            # Собираем опции для конкретных правил
            if rule == 'fixed':
                fixed_value = form_data.get(f'fixed_value_{category_name}') or \
                              form_data.get(f'fixed_value_select_{category_name}')
                if not fixed_value: # Проще проверка на Falsy значение
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
                # Простая проверка на пустые строки
                if not min_val or not max_val:
                    raise ValueError("Не указаны Мин/Макс для правила 'range'.")
                # Доп. проверки на число лучше делать в генераторе или здесь
                category_config['min'] = min_val
                category_config['max'] = max_val
                category_config['step'] = step_val
            # random_from_category не требует доп. параметров

            custom_config[category_name] = category_config

        except ValueError as e:
             msg = f"Ошибка в настройках категории '{category_name}': {e}"
             errors.append(msg)
             current_app.logger.warning(msg)
        except Exception as e: # Ловим более общие ошибки парсинга
             msg = f"Неожиданная ошибка при обработке настроек '{category_name}': {e}"
             errors.append(msg)
             current_app.logger.error(msg, exc_info=True)

    # Если были ошибки на этапе сборки конфига, но конфиг не пустой,
    # можем решить, возвращать ли частичный конфиг или None
    if errors and not custom_config: # Если ошибки были и конфиг собрать не удалось
         return None, errors
    # Если конфиг пустой, но ошибок не было (т.к. не выбрали категорий) - уже обработано выше
    # Возвращаем собранный конфиг (даже если частичный) и список ошибок
    return custom_config, errors


@main.route('/')
def index():
    """Главная страница."""
    try:
        templates = Template.query.order_by(Template.name).all()
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
                           selected_template_id=None,
                           # --- Change this line ---
                           form_data=MultiDict()) # Pass an empty MultiDict instead of {}
                           # --- End Change ---

# --- Маршрут для генерации ---
@main.route('/generate', methods=['POST'])
def generate_challenge():
    result_data = None
    generation_errors = []
    selected_template_id = request.form.get('template_id')
    form_data = request.form # Сохраним для передачи в шаблон
    current_app.logger.debug(f"Получен POST запрос на /generate. template_id: {selected_template_id}")

    generator = None
    custom_config = None

    try:
        if selected_template_id == 'custom':
            current_app.logger.debug("Режим 'custom'. Сбор конфигурации из формы.")
            custom_config, parsing_errors = _build_custom_config_from_form(form_data)
            generation_errors.extend(parsing_errors) # Добавляем ошибки парсинга

            if custom_config: # Если конфиг успешно собран (хотя бы частично)
                current_app.logger.debug(f"Собран custom_config: {custom_config}")
                generator = ChallengeGenerator(custom_config=custom_config)
            # Если custom_config is None, значит были критичные ошибки парсинга или не выбраны категории
            elif not generation_errors: # Если конфига нет, но и ошибок не было (странно, но может быть)
                flash("Не удалось собрать кастомную конфигурацию.", "warning")

        elif selected_template_id:
            current_app.logger.debug(f"Инициализация генератора для шаблона ID: {selected_template_id}")
            generator = ChallengeGenerator(template_id=selected_template_id)
            # Ошибки инициализации (e.g., шаблон не найден) будут в generator.errors или в исключении
        else:
            flash("Необходимо выбрать шаблон или настроить кастомный челлендж.", "warning")

        # --- Вызов генератора (если он был создан) ---
        if generator:
             current_app.logger.debug("Вызов generator.generate()")
             generated_result = generator.generate()
             generation_errors.extend(generator.errors) # Добавляем ошибки ИЗ генератора

             current_app.logger.debug(f"generator.generate() вернул: {generated_result}")
             current_app.logger.debug(f"Ошибки (парсинг + генерация): {generation_errors}")

             if generated_result is not None:
                 result_data = generated_result
             # Если результат None, ошибки уже должны быть в generation_errors
             elif not generation_errors: # На всякий случай, если генератор вернул None без ошибок
                 generation_errors.append("Генерация не дала результата по неизвестной причине.")
                 current_app.logger.warning(f"Генерация ({selected_template_id}) вернула None без явных ошибок.")

    except ChallengeGeneratorError as e:
        # Ошибки, возникшие при *инициализации* генератора (например, не найден шаблон)
        current_app.logger.error(f"Ошибка инициализации ChallengeGenerator: {e}")
        generation_errors.append(f"Ошибка генератора: {e}")
    except Exception as e:
        current_app.logger.error(f"Неожиданная ошибка во время /generate: {e}", exc_info=True)
        generation_errors.append("Внутренняя ошибка сервера.") # Пользователю не показываем детали

    # Отображение ошибок пользователю
    if generation_errors:
        flash("При генерации возникли проблемы:", "error")
        for error in generation_errors:
            # Можно сделать более user-friendly сообщения
            flash(f"- {error}", "warning")

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
                           result=result_data,
                           selected_template_id=selected_template_id,
                           form_data=form_data) # Передаем исходные данные формы обратно