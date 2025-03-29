# app/main/routes.py
from flask import Blueprint, render_template, current_app, request, jsonify, flash  # Добавили request и jsonify
from ..models import Template, Category, Value # Убедись, что Category и Value импортированы
from .. import db
from ..utils.generator import ChallengeGenerator, ChallengeGeneratorError

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Главная страница."""
    try:
        templates = Template.query.order_by(Template.name).all()
        # Загружаем все категории с их значениями для кастомных настроек
        # Используем joinedload для предзагрузки значений, чтобы избежать N+1 запросов в шаблоне
        all_categories = Category.query.order_by(Category.name).all()
    except Exception as e:
        current_app.logger.error(f"Database error fetching data for index: {e}")
        templates = []
        all_categories = []
        flash('Ошибка загрузки данных из базы данных.', 'error')

    return render_template('index.html',
                           templates=templates,
                           all_categories=all_categories, # Передаем категории в шаблон
                           result=None,
                           selected_template_id=None)

# --- Маршрут для генерации ---
@main.route('/generate', methods=['POST'])
def generate_challenge():
    result_data = None
    generation_errors = []
    selected_template_id = request.form.get('template_id')
    current_app.logger.debug(f"Получен POST запрос на /generate. template_id: {selected_template_id}")

    generator = None
    custom_config_built = {} # Для хранения собранного кастомного конфига

    try:
        if selected_template_id == 'custom':
            current_app.logger.debug("Режим 'custom'. Сбор конфигурации из формы.")
            # --- Логика для КАСТОМНОГО челленджа ---
            included_categories = request.form.getlist('include_category') # Получаем список имен включенных категорий

            if not included_categories:
                flash("Для кастомной генерации нужно выбрать хотя бы одну категорию.", "warning")
            else:
                for category_name in included_categories:
                    rule = request.form.get(f'rule_{category_name}')
                    count_str = request.form.get(f'count_{category_name}', '1')
                    category_config = {}

                    try:
                        count = int(count_str) if count_str.isdigit() else 1
                        category_config['rule'] = rule
                        # Count не нужен для fixed и range, но генератор его игнорирует, так что можно оставить
                        category_config['count'] = count

                        # Собираем опции для конкретных правил
                        if rule == 'fixed':
                            # Проверяем, есть ли значение из select или из input
                            fixed_value = request.form.get(f'fixed_value_{category_name}') or \
                                          request.form.get(f'fixed_value_select_{category_name}')

                            if fixed_value is None or fixed_value == '':
                                raise ValueError("Не указано значение для правила 'fixed'.")
                            category_config['value'] = fixed_value
                        elif rule == 'random_from_list':
                            allowed_values = request.form.getlist(f'allowed_values_{category_name}')
                            if not allowed_values:
                                raise ValueError("Не выбраны значения для правила 'random_from_list'.")
                            category_config['allowed_values'] = allowed_values
                        elif rule == 'range':
                            min_val = request.form.get(f'range_min_{category_name}')
                            max_val = request.form.get(f'range_max_{category_name}')
                            step_val = request.form.get(f'range_step_{category_name}', '1')
                            if min_val is None or max_val is None or min_val == '' or max_val == '':
                                raise ValueError("Не указаны Мин/Макс для правила 'range'.")
                            # Проверка на число может быть добавлена здесь или в генераторе
                            category_config['min'] = min_val
                            category_config['max'] = max_val
                            category_config['step'] = step_val
                        # Для 'random_from_category' дополнительные параметры не нужны

                        custom_config_built[category_name] = category_config

                    except ValueError as e:
                         msg = f"Ошибка в настройках категории '{category_name}': {e}"
                         generation_errors.append(msg)
                         current_app.logger.warning(msg)
                         # Пропускаем эту категорию, но продолжаем с другими
                    except Exception as e:
                         msg = f"Неожиданная ошибка при обработке настроек '{category_name}': {e}"
                         generation_errors.append(msg)
                         current_app.logger.error(msg, exc_info=True)


                if custom_config_built and not generation_errors: # Если конфиг собран и нет ошибок сборки
                    current_app.logger.debug(f"Собран custom_config: {custom_config_built}")
                    generator = ChallengeGenerator(custom_config=custom_config_built)
                elif not custom_config_built and not generation_errors:
                     flash("Не удалось собрать конфигурацию. Проверьте настройки.", "warning")


        elif selected_template_id:
            # --- Логика для генерации по ШАБЛОНУ (без изменений) ---
            current_app.logger.debug(f"Попытка инициализации генератора для шаблона ID: {selected_template_id}")
            generator = ChallengeGenerator(template_id=selected_template_id)
            current_app.logger.debug(f"Генератор инициализирован. Config: {generator.config}")
        else:
            flash("Необходимо выбрать шаблон или настроить кастомный челлендж.", "warning")

        # --- Вызов генератора (если он был создан) ---
        if generator:
             current_app.logger.debug("Вызов generator.generate()")
             generated_result = generator.generate()
             # Добавляем ошибки ИЗ генератора к ошибкам СБОРКИ конфига
             generation_errors.extend(generator.errors)

             current_app.logger.debug(f"generator.generate() вернул: {generated_result}")
             current_app.logger.debug(f"Ошибки (сборка + генерация): {generation_errors}")

             if generated_result is not None:
                 result_data = generated_result
             elif not generation_errors:
                 generation_errors.append("Генерация не дала результата (возможно, пустой или некорректный конфиг).")
                 current_app.logger.warning(f"Генерация ({'custom' if selected_template_id == 'custom' else 'template '+selected_template_id}) вернула None без ошибок.")

    # ... (обработка исключений и flash-сообщений как раньше) ...
    except ChallengeGeneratorError as e:
        current_app.logger.error(f"Ошибка инициализации ChallengeGenerator: {e}")
        flash(f"Ошибка инициализации генератора: {e}", "error")
        generation_errors.append(str(e))
    except Exception as e:
        current_app.logger.error(f"Неожиданная ошибка во время /generate: {e}", exc_info=True)
        flash("Произошла непредвиденная ошибка при генерации.", "error")
        generation_errors.append("Внутренняя ошибка сервера.")

    if generation_errors:
        flash("Обнаружены ошибки:", "error")
        for error in generation_errors:
            flash(f"- {error}", "warning")

    # --- Получаем данные для рендеринга шаблона ---
    try:
        templates = Template.query.order_by(Template.name).all()
        # Категории нужны всегда для кастомного блока
        all_categories = Category.query.options(db.joinedload(Category.values)).order_by(Category.name).all()
    except Exception as e:
        current_app.logger.error(f"Database error fetching data for re-render: {e}")
        templates = []
        all_categories = []
        flash('Ошибка загрузки данных из базы данных при перерисовке.', 'error')

    current_app.logger.debug(f"Рендеринг index.html с result_data: {result_data}")
    # Передаем все необходимое обратно в шаблон
    return render_template('index.html',
                           templates=templates,
                           all_categories=all_categories, # Категории нужны снова
                           result=result_data,
                           selected_template_id=selected_template_id,
                           # Важно: передать введенные пользователем данные обратно, чтобы форма сохраняла состояние!
                           # Это можно сделать, передав request.form в шаблон, но безопаснее передавать только нужные части
                           form_data=request.form if request.method == 'POST' else {})