import os
import json
from app import db
from app.models import Category, Value
from config import datadir

CATEGORY_GROUP_MAP = {
    "Body Type (Wheelbase)": "Body & Exterior",
    "Body Materials": "Body & Exterior",
    "Special Features": "Body & Exterior",
    "Engine Type": "Engine & Drivetrain",
    "Engine Intake Type": "Engine & Drivetrain",
    "Horsepower": "Engine & Drivetrain",
    "Drivetrain": "Engine & Drivetrain",
    "Chassis Type": "Chassis & Suspension",
    "Interior": "Interior & Features",
    "Infotainment": "Interior & Features",
    "Classification": "Restrictions & Meta",
    "Model Year": "Restrictions & Meta",
    "Quality": "Restrictions & Meta",
    "Budget": "Restrictions & Meta",
    "Special Condition": "Restrictions & Meta",
}
DEFAULT_GROUP = "Other"

def populate_initial_data():
    """
    Populates or updates the database with category values from the JSON file,
    including the display group for categories.
    """
    json_path = os.path.join(datadir, "ready_data.json")

    print(f"Reading data for seeding/updating from {json_path}...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            automation_data = data.get("automation", {})
            if not automation_data:
                print("Warning: 'automation' section in JSON not found or is empty.")
                # return
    except FileNotFoundError:
        print(f"Error: File {json_path} not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from file {json_path}.")
        return
    except Exception as e:
        print(f"Unexpected error while reading file: {e}")
        return

    print("Checking and adding categories and values...")
    try:
        for category_name, values_list in automation_data.items():
            if not isinstance(values_list, list):
                print(f"Warning: Expected a list of values for category '{category_name}', skipping.")
                continue

            category = Category.query.filter_by(name=category_name).first()
            display_group = CATEGORY_GROUP_MAP.get(category_name, DEFAULT_GROUP)

            if not category:
                category = Category(name=category_name, display_group=display_group)
                db.session.add(category)
                db.session.flush()
                print(f"  Added new category: {category_name} (Group: {display_group})")
            elif category.display_group != display_group:
                print(f"  Updated group for category '{category_name}' to '{display_group}'")
                category.display_group = display_group

            existing_value_cores = {val.value_core for val in category.values}

            for value_item in values_list:
                value_str = str(value_item)
                parts = value_str.split(':', 1)
                value_core = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else None

                if value_core not in existing_value_cores:
                    new_value = Value(value_core=value_core, description=description, category=category)
                    db.session.add(new_value)
                    existing_value_cores.add(value_core)

        db.session.commit()
        print("Database has been successfully updated/populated with category and group data.")

    except Exception as e:
        db.session.rollback()
        print(f"Error while adding/updating data: {e}")
        import traceback
        traceback.print_exc()