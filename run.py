import os
import click
from flask.cli import with_appcontext
from app import create_app, db
from seeding import populate_initial_data as populate_db_function

config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)

@app.cli.command("seed-db")
@with_appcontext
def seed_db_command():
    """Заполняет базу данных начальными данными из JSON."""
    click.echo("Запуск заполнения базы данных начальными данными...")
    try:
        populate_db_function()
        click.echo(click.style("Начальные данные успешно добавлены.", fg="green"))
    except Exception as e:
        db.session.rollback()
        click.echo(click.style(f"Ошибка при заполнении данных: {e}", fg="red"), err=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0')