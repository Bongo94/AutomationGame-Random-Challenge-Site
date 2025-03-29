# run.py
import os
import click  # Импортируем click для декораторов и вывода
from flask.cli import with_appcontext # Для получения контекста приложения
from app import create_app, db # Импортируем фабрику и db
# Импортируем модели (уже есть)
from app.models import Category, Value, Template
# --- Добавь импорт твоей функции ---
from seeding import populate_initial_data as populate_db_function

# Получаем имя конфигурации (уже есть)
config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)

# --- Определение новой CLI команды ---
@app.cli.command("seed-db") # Имя команды будет 'flask seed-db'
@with_appcontext          # Гарантирует, что код выполняется внутри контекста приложения
def seed_db_command():
    """Заполняет базу данных начальными данными из JSON."""
    click.echo("Запуск заполнения базы данных начальными данными...")
    try:
        populate_db_function() # Вызываем твою импортированную функцию
        click.echo(click.style("Начальные данные успешно добавлены.", fg="green"))
    except Exception as e:
        # Откат транзакции важен, если populate_db_function его не делает сама
        db.session.rollback()
        click.echo(click.style(f"Ошибка при заполнении данных: {e}", fg="red"), err=True)
        # Можно добавить более детальное логирование ошибки, если нужно
        # import traceback
        # traceback.print_exc()

# --- КОНЕЦ определения команды ---

# Код для запуска сервера (уже есть)
if __name__ == '__main__':
    app.run(host='0.0.0.0')