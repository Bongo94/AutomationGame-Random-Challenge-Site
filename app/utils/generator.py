import random
import json
from ..models import Category, Value, Template
from .. import db

class ChallengeGeneratorError(Exception):
    """Custom exception for generation errors."""
    pass

class ChallengeGenerator:
    """Class to generate challenge parameters for one or more players."""

    def __init__(self, template_id=None, custom_config=None):
        """
        Initializes the generator.
        Accepts either a template ID or a custom configuration dictionary.
        """
        self.config = {}
        self.errors = []

        if template_id and template_id != 'custom':
            self._load_template(template_id)
        elif custom_config:
            if not isinstance(custom_config, dict):
                 self.errors.append("The provided custom configuration is not a dictionary.")
            else:
                self.config = custom_config
        else:
            pass

    def _load_template(self, template_id):
        """Loads a configuration from a template by its ID."""
        try:
            template = Template.query.get(int(template_id))
            if not template:
                self.errors.append(f"Template with ID {template_id} not found.")
                return
            self.config = template.config
            if not isinstance(self.config, dict):
                 self.errors.append(f"The configuration for template {template_id} is not a dictionary.")
                 self.config = {}
        except ValueError as e:
             self.errors.append(f"Error loading template ID {template_id}: Invalid ID. {e}")
        except Exception as e:
            self.errors.append(f"Unexpected error while loading template ID {template_id}: {e}")

    def generate(self, num_players=1):
        """
        Main method to generate a challenge based on self.config for a specified number of players.
        Returns a list of dictionaries, where each dictionary is the result for one player,
        and the configuration used.
        """
        effective_config = self.config.copy()

        if not effective_config and not self.errors:
             self.errors.append("The configuration for generation is empty.")

        if self.errors:
             if any("not found" in str(e) or "not a dictionary" in str(e) for e in self.errors):
                 return None, effective_config

        if not isinstance(num_players, int) or num_players < 1:
            self.errors.append("Invalid number of players.")
            num_players = 1

        player_results = [{} for _ in range(num_players)]

        if effective_config:
            for category_name, rules in effective_config.items():
                if not isinstance(rules, dict):
                    if f"Invalid rules for category '{category_name}'." not in self.errors:
                        self.errors.append(f"Invalid rules for category '{category_name}'.")
                    continue

                rule_type = rules.get('rule', 'random_from_category')
                count = rules.get('count', 1)
                apply_all = rules.get('apply_all', False)

                try:
                    category = Category.query.filter_by(name=category_name).first()
                    if not category:
                        if f"Category '{category_name}' not found in the database." not in self.errors:
                            self.errors.append(f"Category '{category_name}' not found in the database.")
                        continue

                    generated_value_for_all = None
                    if apply_all:
                        category_errors_before = set(self.errors)
                        generated_value_for_all = self._generate_single_value_set(category, rules, rule_type, count)
                        category_errors_after = set(self.errors)
                        if generated_value_for_all is None and category_errors_after != category_errors_before:
                            continue

                    for i in range(num_players):
                        if apply_all:
                            if generated_value_for_all is not None:
                                player_results[i][category_name] = generated_value_for_all
                        else:
                            category_errors_before = set(self.errors)
                            individual_value = self._generate_single_value_set(category, rules, rule_type, count)
                            category_errors_after = set(self.errors)
                            if individual_value is not None and category_errors_after == category_errors_before:
                                player_results[i][category_name] = individual_value

                except ValueError as e:
                     msg = f"Value error in rules for '{category_name}': {e}"
                     if msg not in self.errors: self.errors.append(msg)
                except Exception as e:
                    msg = f"Error generating for category '{category_name}': {e}"
                    if msg not in self.errors: self.errors.append(msg)

        if not any(p for p in player_results) and not self.errors:
             self.errors.append("Failed to generate any values with the given rules.")

        return player_results if any(p for p in player_results) else None, effective_config


    def _generate_single_value_set(self, category, rules, rule_type, count):
        """
        Generates a set of values for a SINGLE category.
        Returns a list of dictionaries [{'value': ..., 'description': ...}] or None on error.
        Appends errors to self.errors.
        """
        original_errors = set(self.errors)
        result = None
        try:
            if rule_type == 'fixed':
                fixed_value_core = rules.get('value')
                if fixed_value_core is None:
                    raise ValueError("The 'fixed' rule must have a 'value' specified.")
                value_obj = Value.query.filter_by(category_id=category.id, value_core=fixed_value_core).first()
                description = value_obj.description if value_obj else None
                result = [{'value': fixed_value_core, 'description': description}]
            elif rule_type == 'random_from_category':
                result = self._get_random_from_category(category, count)
            elif rule_type == 'random_from_list':
                allowed_values_core = rules.get('allowed_values')
                if not isinstance(allowed_values_core, list):
                    raise ValueError("The 'random_from_list' rule must have a list of 'allowed_values' specified.")
                result = self._get_random_from_list(category, allowed_values_core, count)
            elif rule_type == 'range':
                min_val = rules.get('min')
                max_val = rules.get('max')
                step = rules.get('step', 1)
                if min_val is None or max_val is None:
                    raise ValueError("The 'range' rule must have 'min' and 'max' specified.")
                range_value = self._get_random_from_range(min_val, max_val, step)
                result = [{'value': str(range_value), 'description': None}]
            else:
                raise ValueError(f"Unknown rule type '{rule_type}'.")

        except ValueError as e:
            msg = f"Category '{category.name}': {e}"
            if msg not in self.errors: self.errors.append(msg)
            return None
        except Exception as e:
            msg = f"Unexpected error while generating a value for '{category.name}': {e}"
            if msg not in self.errors: self.errors.append(msg)
            return None

        if set(self.errors) != original_errors:
            return None

        return result

    def _get_random_from_category(self, category, count):
        """Selects 'count' random Value objects from a category and formats the result."""
        all_value_objects = list(category.values)
        if not all_value_objects:
            raise ValueError(f"No available values for category '{category.name}'.")

        actual_count = min(count, len(all_value_objects))
        if actual_count < count:
            warn_msg = f"Requested {count} for category '{category.name}', but only {len(all_value_objects)} available. Selected {actual_count}."
            if warn_msg not in self.errors: self.errors.append(warn_msg)
        if actual_count == 0:
             raise ValueError(f"No available values for category '{category.name}' after applying constraints.")

        selected_objects = random.sample(all_value_objects, actual_count)
        return [{'value': v.value_core, 'description': v.description} for v in selected_objects]

    def _get_random_from_list(self, category, allowed_values_core, count):
        """Selects 'count' random Value objects from a given list of value_core strings."""
        if not allowed_values_core:
            raise ValueError("The list of allowed values is empty.")

        possible_value_objects = [v for v in category.values if v.value_core in allowed_values_core]

        if not possible_value_objects:
            raise ValueError(f"No values in category '{category.name}' match the provided list: {allowed_values_core}.")

        actual_count = min(count, len(possible_value_objects))
        if actual_count < count:
            warn_msg = f"Requested {count} from list for '{category.name}', but only {len(possible_value_objects)} available. Selected {actual_count}."
            if warn_msg not in self.errors: self.errors.append(warn_msg)
        if actual_count == 0:
            raise ValueError("The list of allowed values contains no matching options in this category.")

        selected_objects = random.sample(possible_value_objects, actual_count)
        return [{'value': v.value_core, 'description': v.description} for v in selected_objects]

    def _get_random_from_range(self, min_val, max_val, step):
        """Generates a random number within a range with a given step."""
        try:
            min_v = int(min_val)
            max_v = int(max_val)
            step_v = int(step) if step else 1
            if step_v <= 0: raise ValueError("Step must be a positive number.")
            if min_v > max_v: raise ValueError("Min value cannot be greater than Max value.")
            possible_values = list(range(min_v, max_v + 1, step_v))
            if not possible_values:
                raise ValueError(f"No available integer values in range [{min_v}, {max_v}] with step {step_v}.")
            return random.choice(possible_values)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid parameters for range (min={min_val}, max={max_val}, step={step}): {e}")

    def reroll_category(self, category, rules, num_values=None):
        """
        Generates values for a SINGLE category based on given rules.
        Does not use self.config. Returns a list of values or None on error.
        Errors are written to self.errors.
        """
        self.errors = []

        if not isinstance(category, Category):
             self.errors.append("Invalid category object for reroll.")
             return None
        if not isinstance(rules, dict):
             self.errors.append(f"Invalid rules for rerolling category '{category.name}'.")
             return None

        rule_type = rules.get('rule', 'random_from_category')
        count = rules.get('count', 1)

        if num_values is not None:
            count = num_values

        result = self._generate_single_value_set(category, rules, rule_type, count)

        return result