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

    const toggleAllButton = document.getElementById('toggle-all-descriptions');
    const resultsArea = document.getElementById('results-area');
    let clickCounter = 0;

    // --- Создаем именованную функцию для обработчика ---
    function handleToggleDescriptionsClick(event) {
        clickCounter++;
        console.log(`--- Toggle Button Click Handler Run #${clickCounter} ---`);

        // event.stopPropagation(); // Можно раскомментировать для теста, если предыдущее не помогло

        // Проверяем класс expanded НА МОМЕНТ ВХОДА в функцию
        const isCurrentlyExpanded = toggleAllButton.classList.contains('expanded');
        const descriptions = resultsArea.querySelectorAll('.toggleable-description');

        console.log(`   State on entry: expanded=${isCurrentlyExpanded}`);

        if (descriptions.length === 0) {
            console.warn("Не найдено элементов с классом 'toggleable-description'.");
            return;
        }

        // Действие зависит ТОЛЬКО от состояния на входе
        if (isCurrentlyExpanded) {
            console.log("   Action: Hiding descriptions...");
            descriptions.forEach(span => span.style.display = 'none');
            toggleAllButton.innerHTML = '<i class="bi bi-eye-slash"></i> Показать описания';
            toggleAllButton.classList.remove('expanded');
        } else {
            console.log("   Action: Showing descriptions...");
            descriptions.forEach(span => span.style.display = 'inline');
            toggleAllButton.innerHTML = '<i class="bi bi-eye"></i> Скрыть описания';
            toggleAllButton.classList.add('expanded');
        }
        console.log("--- Handler finished ---");
    }

    if (toggleAllButton && resultsArea) {
        console.log("Setting up toggle button listener...");

        // --- Удаляем ЛЮБОЙ предыдущий обработчик (на всякий случай) ---
        // Создаем клон кнопки без обработчиков
        const newButton = toggleAllButton.cloneNode(true);
        toggleAllButton.parentNode.replaceChild(newButton, toggleAllButton);

        // Добавляем обработчик к НОВОЙ кнопке
        newButton.addEventListener('click', handleToggleDescriptionsClick);

    } else {
        if (!toggleAllButton) console.error("Кнопка с ID 'toggle-all-descriptions' не найдена!");
        if (!resultsArea) console.error("Область с ID 'results-area' не найдена!");
    }

}); // End DOMContentLoaded


// --- UPDATED: Copy function ---
function copyResultToClipboard(containerId) { // Added containerId parameter
    const resultsContainer = document.getElementById(containerId); // Use the ID
    if (!resultsContainer) {
        console.warn("Result container not found for copying.");
        return;
    }

    let textToCopy = "Сгенерированный Челлендж:\n";
    const playerColumns = resultsContainer.querySelectorAll('.card'); // Get each player card

    playerColumns.forEach((card, index) => {
        textToCopy += `\n--- Игрок ${index + 1} ---\n`;
        const categoryBlocks = card.querySelectorAll('.result-category'); // Get categories

        if (categoryBlocks.length > 0) {
             categoryBlocks.forEach(catBlock => {
                 const categoryTitleElement = catBlock.querySelector('strong');
                 const categoryTitle = categoryTitleElement ? categoryTitleElement.innerText.replace(':', '').trim() : 'Категория';
                 textToCopy += `${categoryTitle}:\n`;

                 const itemsList = catBlock.querySelectorAll('.result-item');
                 itemsList.forEach(item => {
                     const valueSpan = item.querySelector('span:not(.value-description)'); // Get the main value span
                     const descriptionSpan = item.querySelector('.value-description'); // Get the description span

                     const valueCore = valueSpan ? valueSpan.innerText.trim() : '';
                     const description = descriptionSpan ? descriptionSpan.innerText.replace('-','').trim() : ''; // Clean up description

                     textToCopy += `  - ${valueCore}`; // Indent items
                     if (description) {
                         textToCopy += `: ${description}`; // Add description back with colon
                     }
                     textToCopy += '\n';
                 });
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