# app/main/routes.py
from flask import Blueprint, render_template, current_app, request, flash # Добавили flash
from .models import Template, Category, Value # Добавили Category, Value
from . import db
from .utils.generator import ChallengeGenerator, ChallengeGeneratorError # Импортируем генератор

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Главная страница."""
    try:
        templates = Template.query.order_by(Template.name).all()
    except Exception as e:
        current_app.logger.error(f"Database error fetching templates: {e}")
        templates = []
        flash('Ошибка загрузки шаблонов из базы данных.', 'error')
    return render_template('index.html', templates=templates, result=None, selected_template_id=None)

@main.route('/generate', methods=['POST'])
def generate_challenge():
    """Обрабатывает запрос на генерацию челленджа."""
    result_data = None
    generation_errors = []
    selected_template_id = request.form.get('template_id')

    try:
        if selected_template_id == 'custom':
            # --- Логика для КАСТОМНОГО челленджа (пока заглушка) ---
            flash("Генерация кастомных челленджей пока не реализована.", "warning")
            # TODO: Собрать custom_config из данных формы (когда будут поля)
            custom_config = {} # Placeholder
            # generator = ChallengeGenerator(custom_config=custom_config) # Когда будет готово
            # result_data = generator.generate()
            # generation_errors = generator.errors
        elif selected_template_id:
            # --- Логика для генерации по ШАБЛОНУ ---
            generator = ChallengeGenerator(template_id=selected_template_id)
            result_data = generator.generate() # Вызываем генерацию
            generation_errors = generator.errors # Получаем ошибки, если были
            if result_data is None and not generation_errors:
                 # Если generate вернул None без явных ошибок (например, из-за ошибки в __init__)
                 generation_errors.append("Не удалось выполнить генерацию. Проверьте конфигурацию шаблона.")

        else:
            flash("Необходимо выбрать шаблон или настроить кастомный челлендж.", "warning")

    except ChallengeGeneratorError as e:
        # Ошибки, возникшие при инициализации генератора (e.g., шаблон не найден)
        flash(f"Ошибка инициализации генератора: {e}", "error")
        generation_errors.append(str(e))
    except Exception as e:
        # Другие неожиданные ошибки
        current_app.logger.error(f"Unexpected error during challenge generation: {e}", exc_info=True)
        flash("Произошла непредвиденная ошибка при генерации.", "error")
        generation_errors.append("Внутренняя ошибка сервера.")

    # Обработка ошибок генерации для пользователя
    if generation_errors:
        for error in generation_errors:
            flash(f"Ошибка генерации: {error}", "warning") # Показываем каждую ошибку

    # Получаем список шаблонов снова для отображения в форме
    try:
        templates = Template.query.order_by(Template.name).all()
    except Exception as e:
        current_app.logger.error(f"Database error fetching templates: {e}")
        templates = []
        flash('Ошибка загрузки шаблонов из базы данных.', 'error')

    # Передаем результат и выбранный ID обратно в шаблон
    return render_template('index.html',
                           templates=templates,
                           result=result_data,
                           selected_template_id=selected_template_id)