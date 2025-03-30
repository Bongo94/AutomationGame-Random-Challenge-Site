// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    const templateSelect = document.getElementById('template_select');
    const customSettingsDiv = document.getElementById('custom_settings');

    function toggleCustomSettings() {
        if (templateSelect && customSettingsDiv) {
            customSettingsDiv.style.display = templateSelect.value === 'custom' ? 'block' : 'none';
        }
    }

    function updateRuleOptions(categoryBlock) {
        const ruleSelect = categoryBlock.querySelector('.rule-select'); // Using class selector
        if (!ruleSelect) return; // Exit if rule select not found

        const selectedRule = ruleSelect.value;
        // Construct the class name for the options div dynamically
        const categoryId = ruleSelect.id.split('_').pop(); // Get category ID
        const ruleOptionsDiv = categoryBlock.querySelector('.rule-options-' + categoryId);
        if (!ruleOptionsDiv) return; // Exit if options div not found

        // Hide all optional rule blocks first
        ruleOptionsDiv.querySelectorAll('.option-fixed, .option-random_from_list, .option-range').forEach(div => {
            div.style.display = 'none';
        });

        // Show/hide the "Count" field based on the rule
        const countFields = categoryBlock.querySelectorAll('.rule-count-field');
        countFields.forEach(field => {
            field.style.display = (selectedRule === 'fixed' || selectedRule === 'range') ? 'none' : 'inline-block'; // Or 'block' if layout needs it
        });

        // Show the specific options block for the selected rule
        const targetOptionDiv = ruleOptionsDiv.querySelector('.option-' + selectedRule);
        if (targetOptionDiv) {
            targetOptionDiv.style.display = 'block';

            // Special handling for 'fixed' rule: choose between text input and select dropdown
            if (selectedRule === 'fixed') {
                const textInput = targetOptionDiv.querySelector('.fixed-input-text');
                const selectInput = targetOptionDiv.querySelector('.fixed-input-select');

                if (textInput && selectInput) { // Ensure both elements exist
                    const categoryValuesExist = selectInput.options.length > 1; // Check if select has actual options

                    const categoryName = ruleSelect.name.replace('rule_', ''); // Get category name from rule select name

                    if (categoryValuesExist) {
                        textInput.style.display = 'none';
                        selectInput.style.display = 'block';
                        textInput.name = ''; // Disable text input by removing name
                        selectInput.name = `fixed_value_${categoryName}`; // Enable select input
                    } else {
                        textInput.style.display = 'block';
                        selectInput.style.display = 'none';
                        textInput.name = `fixed_value_${categoryName}`; // Enable text input
                        selectInput.name = ''; // Disable select input by removing name
                    }
                }
            }
        }
    }

    // --- Initialize and Event Listeners ---

    // Template selector change
    if (templateSelect) {
        templateSelect.addEventListener('change', toggleCustomSettings);
        toggleCustomSettings(); // Initial check on page load
    }

    // Custom settings visibility and rule initialization
    if (customSettingsDiv) {
        customSettingsDiv.querySelectorAll('.custom-category-block').forEach(block => {
            const includeCheckbox = block.querySelector('input[name="include_category"]');
            const rulesDiv = block.querySelector('.custom-rules');
            const ruleSelect = block.querySelector('.rule-select');

            // Toggle rules visibility based on main category checkbox
            if (includeCheckbox && rulesDiv) {
                rulesDiv.style.display = includeCheckbox.checked ? 'block' : 'none'; // Initial state
                includeCheckbox.addEventListener('change', function() {
                    rulesDiv.style.display = this.checked ? 'block' : 'none';
                    if (this.checked) {
                        updateRuleOptions(block); // Update options if revealed
                    }
                });
            }

            // Update rule options when rule type changes
            if (ruleSelect) {
                 ruleSelect.addEventListener('change', function() {
                    updateRuleOptions(block);
                });
            }

            // Initial rule options state if category is checked
            if (includeCheckbox && includeCheckbox.checked) {
                updateRuleOptions(block);
            }
        });
    }

}); // End DOMContentLoaded


function copyResultToClipboard() {
    const resultsContainer = document.querySelector('.challenge-results-container');
    if (!resultsContainer) {
        console.warn("Result container not found for copying.");
        return;
    }

    let textToCopy = "Сгенерированный Челлендж:\n";
    const playerColumns = resultsContainer.querySelectorAll('.card'); // Get each player card

    playerColumns.forEach((card, index) => {
        textToCopy += `\n--- Игрок ${index + 1} ---\n`;
        const resultItems = card.querySelectorAll('.result-item');
        if (resultItems.length > 0) {
             resultItems.forEach(item => {
                const keyElement = item.querySelector('strong');
                const valueElement = item.querySelector('span');
                if (keyElement && valueElement) {
                     const key = keyElement.innerText.replace(':', '').trim();
                     const value = valueElement.innerText.trim();
                     textToCopy += `${key}: ${value}\n`;
                }
             });
        } else {
            textToCopy += "(Нет данных)\n";
        }

    });

    textToCopy += "\n---\nСгенерировано: " + new Date().toLocaleString('ru-RU');

    navigator.clipboard.writeText(textToCopy.trim()).then(function() {
        alert('Результаты скопированы в буфер обмена!');
    }, function(err) {
        alert('Не удалось скопировать результаты. Попробуйте вручную.');
        console.error('Ошибка копирования: ', err);
    });
}