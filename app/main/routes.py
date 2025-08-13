from collections import OrderedDict
from datetime import datetime

from flask import Blueprint, render_template, current_app, request, jsonify, flash

from .. import db
from ..models import Template, Category
from ..utils.generator import ChallengeGenerator

main = Blueprint('main', __name__)


def _build_custom_config_from_form(form_data):
    """Builds a configuration dictionary from the form data."""
    custom_config = {}
    errors = []
    included_categories = form_data.getlist('include_category')

    if not included_categories:
        errors.append("At least one category must be selected for custom generation.")
        return None, errors

    for category_name in included_categories:
        apply_all = form_data.get(f'apply_all_{category_name}') == 'true'

        rule = form_data.get(f'rule_{category_name}')
        count_str = form_data.get(f'count_{category_name}', '1')

        category_config = {}
        try:
            count = 1
            if rule not in ['fixed', 'range']:
                if not count_str.isdigit() or int(count_str) < 1:
                    raise ValueError("Count must be a positive number.")
                count = int(count_str)

            category_config['rule'] = rule
            if rule not in ['fixed', 'range']:
                category_config['count'] = count
            category_config['apply_all'] = apply_all

            if rule == 'fixed':
                fixed_value_core = form_data.get(f'fixed_value_select_{category_name}')
                if not fixed_value_core:
                    fixed_value_core = form_data.get(f'fixed_value_{category_name}')
                if not fixed_value_core:
                    raise ValueError("A value must be specified for the 'fixed' rule.")
                category_config['value'] = fixed_value_core
            elif rule == 'random_from_list':
                allowed_values_core = form_data.getlist(f'allowed_values_{category_name}')
                if not allowed_values_core:
                    raise ValueError("No values were selected for the 'random_from_list' rule.")
                category_config['allowed_values'] = allowed_values_core
            elif rule == 'range':
                min_val = form_data.get(f'range_min_{category_name}')
                max_val = form_data.get(f'range_max_{category_name}')
                step_val = form_data.get(f'range_step_{category_name}', '1')
                if min_val is None or min_val == '' or max_val is None or max_val == '':
                    raise ValueError("Min/Max must be specified for the 'range' rule.")
                try:
                    int(min_val)
                    int(max_val)
                    if step_val: int(step_val)
                except ValueError:
                    raise ValueError("Min/Max/Step for the range must be numbers.")
                category_config['min'] = min_val
                category_config['max'] = max_val
                category_config['step'] = step_val if step_val else '1'

            custom_config[category_name] = category_config
        except ValueError as e:
            errors.append(f"Error in category '{category_name}': {e}")

    if not custom_config and not errors:
        errors.append("Failed to build the configuration.")

    return custom_config, errors


@main.route('/')
def index():
    """Main page route."""
    templates = []
    grouped_categories = OrderedDict()
    group_order = [
        "Body & Exterior", "Engine & Drivetrain", "Chassis & Suspension",
        "Interior & Features", "Restrictions & Meta", "Other"
    ]

    try:
        templates = Template.query.order_by(Template.name).all()
        all_categories_from_db = Category.query.options(
            db.joinedload(Category.values)
        ).order_by(Category.display_group, Category.name).all()

        for group_name in group_order:
            grouped_categories[group_name] = []
        for category in all_categories_from_db:
            group_name = category.display_group if category.display_group else "Other"
            if group_name not in grouped_categories:
                grouped_categories[group_name] = []
            grouped_categories[group_name].append(category)

    except Exception as e:
        current_app.logger.error(f"Database error fetching data for index: {e}")
        flash('Error loading data from the database.', 'error')

    return render_template('index.html',
                           templates=templates,
                           grouped_categories=grouped_categories,
                           now=datetime.utcnow)


@main.route('/generate', methods=['POST'])
def generate_challenge():
    """AJAX endpoint for generation. Returns JSON."""
    generation_errors = []
    selected_template_id = request.form.get('template_id')
    form_data = request.form
    final_config_used = {}

    try:
        num_players = int(request.form.get('num_players', '1'))
        if not (1 <= num_players <= 10):
            num_players = max(1, min(num_players, 10))
    except (ValueError, TypeError):
        num_players = 1

    try:
        if selected_template_id == 'custom':
            custom_config, parsing_errors = _build_custom_config_from_form(form_data)
            generation_errors.extend(parsing_errors)
            if custom_config:
                final_config_used = custom_config
        elif selected_template_id:
            template = Template.query.get(int(selected_template_id))
            if template and isinstance(template.config, dict):
                final_config_used = template.config
            else:
                generation_errors.append(f"Template ID {selected_template_id} not found or is corrupted.")
        else:
            generation_errors.append("No template selected.")

        if final_config_used and not generation_errors:
            generator = ChallengeGenerator(custom_config=final_config_used)
            generation_errors.extend(g for g in generator.errors if g not in generation_errors)

            if not generator.errors:
                result_data, _ = generator.generate(num_players=num_players)
                generation_errors.extend(g for g in generator.errors if g not in generation_errors)

                if result_data:
                    return jsonify(
                        success=True,
                        results=result_data,
                        config=final_config_used,
                        is_custom=(selected_template_id == 'custom')
                    )
    except Exception as e:
        current_app.logger.error(f"Unexpected error during /generate: {e}", exc_info=True)
        generation_errors.append("Internal server error during generation.")

    unique_errors = list(OrderedDict.fromkeys(e for e in generation_errors if e))
    return jsonify(success=False, errors=unique_errors), 400


@main.route("/reroll_category", methods=["POST"])
def reroll_category():
    """Handles AJAX request to reroll a single category or a category for all players."""
    data = request.get_json()
    if not data or "category_name" not in data or "rules" not in data:
        return jsonify(success=False, error="Invalid request data."), 400

    category_name, rules = data.get("category_name"), data.get("rules")
    reroll_type = data.get("reroll_type", "single")

    try:
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            return jsonify(success=False, error=f"Category '{category_name}' not found."), 404

        generator = ChallengeGenerator()

        new_values = generator.reroll_category(category, rules)

        if new_values is None:
            error_message = "; ".join(generator.errors) or f"Failed to reroll '{category_name}'."
            return jsonify(success=False, error=error_message), 500

        return jsonify(success=True, new_values=new_values)
    except Exception as e:
        current_app.logger.error(f"Error during reroll for '{category_name}': {e}", exc_info=True)
        return jsonify(success=False, error="Internal server error."), 500


@main.route('/about')
def about():
    """About page route."""
    return render_template('about.html', now=datetime.utcnow)


@main.route('/save_template', methods=['POST'])
def save_template():
    """AJAX endpoint for saving a custom configuration as a template."""
    data = request.get_json()
    if not data or not data.get('name') or not data.get('config'):
        return jsonify(success=False, error="Template name or configuration is missing."), 400

    name = data['name'].strip()
    description = data.get('description', '').strip()
    config = data['config']

    if not name:
        return jsonify(success=False, error="Template name cannot be empty."), 400

    if Template.query.filter_by(name=name).first():
        return jsonify(success=False, error=f"A template with the name '{name}' already exists."), 409

    try:
        new_template = Template(name=name, description=description)
        new_template.config = config
        db.session.add(new_template)
        db.session.commit()

        return jsonify(success=True, new_template={'id': new_template.id, 'name': new_template.name})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving template '{name}': {e}", exc_info=True)
        return jsonify(success=False, error="Error saving to the database."), 500