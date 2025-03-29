# app/main/routes.py
from flask import Blueprint, render_template, current_app, request, jsonify, flash  # Добавили request и jsonify
from ..models import Template
from .. import db
from ..utils.generator import ChallengeGenerator, ChallengeGeneratorError

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Главная страница."""
    try:
        templates = Template.query.order_by(Template.name).all()
    except Exception as e:
        current_app.logger.error(f"Database error fetching templates: {e}")
        templates = []
    return render_template('index.html', templates=templates, result=None) # Добавили result=None

# --- Маршрут для генерации ---
@main.route('/generate', methods=['POST'])
def generate_challenge():
    result_data = None # Инициализируем как None
    generation_errors = []
    selected_template_id = request.form.get('template_id')
    current_app.logger.debug(f"Получен POST запрос на /generate. template_id: {selected_template_id}") # Логирование

    generator = None # Инициализируем генератор

    try:
        if selected_template_id == 'custom':
            flash("Генерация кастомных челленджей пока не реализована.", "warning")
            # TODO: Логика кастомной генерации
            # generator = ChallengeGenerator(custom_config=...) # Пример
        elif selected_template_id:
            current_app.logger.debug(f"Попытка инициализации генератора для шаблона ID: {selected_template_id}")
            generator = ChallengeGenerator(template_id=selected_template_id) # Создаем генератор
            current_app.logger.debug(f"Генератор инициализирован. Config: {generator.config}")

        else:
            flash("Необходимо выбрать шаблон или настроить кастомный челлендж.", "warning")

        # Если генератор был успешно создан (не кастомный режим или кастомный будет реализован)
        if generator:
             current_app.logger.debug("Вызов generator.generate()")
             generated_result = generator.generate() # Вызываем генерацию
             generation_errors.extend(generator.errors) # Добавляем ошибки из генератора

             current_app.logger.debug(f"generator.generate() вернул: {generated_result}")
             current_app.logger.debug(f"Ошибки генератора: {generation_errors}")

             if generated_result is not None:
                 result_data = generated_result # <--- Присваиваем результат ТОЛЬКО если он не None
             elif not generation_errors:
                 # Ситуация: результат None, но явных ошибок нет. Возможно, конфиг пустой?
                 generation_errors.append("Генерация не дала результата (возможно, пустой или некорректный конфиг шаблона).")
                 current_app.logger.warning(f"Генерация для шаблона ID {selected_template_id} вернула None без ошибок.")


    except ChallengeGeneratorError as e:
        # Ошибки инициализации генератора
        current_app.logger.error(f"Ошибка инициализации ChallengeGenerator: {e}")
        flash(f"Ошибка инициализации генератора: {e}", "error")
        generation_errors.append(str(e))
    except Exception as e:
        # Другие неожиданные ошибки
        current_app.logger.error(f"Неожиданная ошибка во время /generate: {e}", exc_info=True) # exc_info=True добавит traceback в лог
        flash("Произошла непредвиденная ошибка при генерации.", "error")
        generation_errors.append("Внутренняя ошибка сервера.")

    # Обработка ошибок для пользователя
    if generation_errors:
        flash("Обнаружены ошибки при генерации:", "error") # Общий заголовок для ошибок
        for error in generation_errors:
            flash(f"- {error}", "warning") # Выводим каждую ошибку как предупреждение для лучшей читаемости

    # Получаем список шаблонов снова
    try:
        templates = Template.query.order_by(Template.name).all()
    except Exception as e:
        current_app.logger.error(f"Database error fetching templates: {e}")
        templates = []
        flash('Ошибка загрузки шаблонов из базы данных.', 'error')

    current_app.logger.debug(f"Рендеринг index.html с result_data: {result_data}")
    # Передаем результат и выбранный ID обратно в шаблон
    return render_template('index.html',
                           templates=templates,
                           result=result_data, # Передаем result_data (может быть None)
                           selected_template_id=selected_template_id)