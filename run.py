import os
import click
from flask.cli import with_appcontext
from flask_migrate import upgrade
from app import create_app, db
from seeding import populate_initial_data as populate_db_function

config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)


@app.cli.command("seed-db")
@with_appcontext
def seed_db_command():
    """Seeds the database with initial data from JSON."""
    click.echo("Seeding the database with initial data...")
    try:
        populate_db_function()
        click.echo(click.style("Initial data added successfully.", fg="green"))
    except Exception as e:
        db.session.rollback()
        click.echo(click.style(f"Error while seeding data: {e}", fg="red"), err=True)


# Новая, автоматизированная команда
@app.cli.command("init-app")
@with_appcontext
def init_app_command():
    """Initializes the application: creates/updates DB schema and seeds it."""
    click.echo("Initializing the application...")

    click.echo("Applying database migrations...")
    try:
        upgrade()
        click.echo(click.style("Migrations applied successfully.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error applying migrations: {e}", fg="red"), err=True)
        return

    click.echo("Seeding the database with initial data...")
    try:
        populate_db_function()
        click.echo(click.style("Initial data seeded successfully.", fg="green"))
    except Exception as e:
        db.session.rollback()
        click.echo(click.style(f"Error while seeding data: {e}", fg="red"), err=True)

    click.echo(click.style("Application initialized successfully!", fg="cyan"))


if __name__ == '__main__':
    app.run(host='0.0.0.0')