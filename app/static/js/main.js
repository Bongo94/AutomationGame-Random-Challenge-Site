// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    const templateSelect = document.getElementById('template_select');
    const customSettingsDiv = document.getElementById('custom_settings');
    const resultsContainer = document.getElementById('results-container'); // Get results container
    const resultsArea = document.getElementById('results-area'); // Get specific area with cards
    const toggleAllButton = document.getElementById('toggle-all-descriptions');


    // --- Template Select Logic (no changes needed) ---
    function toggleCustomSettings() {
        if (templateSelect && customSettingsDiv) {
            customSettingsDiv.style.display = templateSelect.value === 'custom' ? 'block' : 'none';
        }
    }
    if (templateSelect) {
        templateSelect.addEventListener('change', toggleCustomSettings);
        toggleCustomSettings();
    }

    // --- Custom Settings Rule Logic (no changes needed) ---
    function updateRuleOptions(categoryBlock) {
         // ... (keep existing logic)
        const ruleSelect = categoryBlock.querySelector('.rule-select');
        if (!ruleSelect) return;

        const selectedRule = ruleSelect.value;
        const categoryId = ruleSelect.id.split('_').pop();
        const ruleOptionsDiv = categoryBlock.querySelector('.rule-options-' + categoryId);
        if (!ruleOptionsDiv) return;

        ruleOptionsDiv.querySelectorAll('.option-fixed, .option-random_from_list, .option-range').forEach(div => {
            div.style.display = 'none';
        });

        const countFields = categoryBlock.querySelectorAll('.rule-count-field');
        countFields.forEach(field => {
            field.style.display = (selectedRule === 'fixed' || selectedRule === 'range') ? 'none' : 'inline-block';
        });

        const targetOptionDiv = ruleOptionsDiv.querySelector('.option-' + selectedRule);
        if (targetOptionDiv) {
            targetOptionDiv.style.display = 'block';
             if (selectedRule === 'fixed') {
                const textInput = targetOptionDiv.querySelector('.fixed-input-text');
                const selectInput = targetOptionDiv.querySelector('.fixed-input-select');
                if (textInput && selectInput) {
                    const categoryValuesExist = selectInput.options.length > 1;
                    const categoryName = ruleSelect.name.replace('rule_', '');
                    if (categoryValuesExist) {
                        textInput.style.display = 'none';
                        selectInput.style.display = 'block';
                        textInput.name = ''; // Clear name
                        selectInput.name = `fixed_value_${categoryName}`;
                    } else {
                        textInput.style.display = 'block';
                        selectInput.style.display = 'none';
                        textInput.name = `fixed_value_${categoryName}`;
                        selectInput.name = ''; // Clear name
                    }
                }
            }
        }
    }
    if (customSettingsDiv) {
        customSettingsDiv.querySelectorAll('.custom-category-block').forEach(block => {
            const includeCheckbox = block.querySelector('input[name="include_category"]');
            const rulesDiv = block.querySelector('.custom-rules');
            const ruleSelect = block.querySelector('.rule-select');

            if (includeCheckbox && rulesDiv) {
                rulesDiv.style.display = includeCheckbox.checked ? 'block' : 'none';
                includeCheckbox.addEventListener('change', function() {
                    rulesDiv.style.display = this.checked ? 'block' : 'none';
                    if (this.checked) {
                        updateRuleOptions(block);
                    }
                });
            }
            if (ruleSelect) {
                 ruleSelect.addEventListener('change', function() {
                    updateRuleOptions(block);
                });
            }
            if (includeCheckbox && includeCheckbox.checked) {
                updateRuleOptions(block);
            }
        });
    }

    // --- Description Toggle Logic (no changes needed) ---
    let descriptionsVisible = false; // Keep track of state
    function handleToggleDescriptionsClick() {
        if (!resultsArea) return;
        const descriptions = resultsArea.querySelectorAll('.toggleable-description');
        if (descriptions.length === 0) return;

        descriptionsVisible = !descriptionsVisible; // Toggle state

        if (descriptionsVisible) {
            console.log("Action: Showing descriptions...");
            descriptions.forEach(span => span.style.display = 'inline');
            toggleAllButton.innerHTML = '<i class="bi bi-eye"></i> Скрыть описания';
            toggleAllButton.classList.add('expanded'); // Add class for state tracking if needed elsewhere
        } else {
            console.log("Action: Hiding descriptions...");
            descriptions.forEach(span => span.style.display = 'none');
            toggleAllButton.innerHTML = '<i class="bi bi-eye-slash"></i> Показать описания';
            toggleAllButton.classList.remove('expanded');
        }
        console.log("--- Handler finished ---");
    }

    if (toggleAllButton && resultsArea) {
        // Use named function for easy add/remove if needed, but direct is fine
        toggleAllButton.addEventListener('click', handleToggleDescriptionsClick);
         // Set initial button text based on initial state (hidden)
        toggleAllButton.innerHTML = '<i class="bi bi-eye-slash"></i> Показать описания';
    } else {
        if (!toggleAllButton) console.warn("Кнопка 'toggle-all-descriptions' не найдена.");
        if (!resultsArea) console.warn("Область 'results-area' не найдена.");
    }


    // --- NEW: Reroll Button Logic ---
    function handleRerollClick(button) {
        const categoryName = button.dataset.categoryName;
        const playerIndex = button.dataset.playerIndex; // This is 0-based index

        if (!resultsContainer) {
             console.error("Results container not found for reroll.");
             alert("Ошибка: Не найден контейнер результатов.");
             return;
        }
        const configString = resultsContainer.dataset.generationConfig;

        if (!categoryName || !playerIndex || !configString) {
            console.error("Missing data attributes on reroll button or config container.");
            alert("Ошибка: Отсутствуют данные для перегенерации.");
            return;
        }

        let originalConfig;
        try {
            originalConfig = JSON.parse(configString);
        } catch (e) {
            console.error("Failed to parse generation config JSON:", e);
            alert("Ошибка: Не удалось прочитать конфигурацию генерации.");
            return;
        }

        const categoryRules = originalConfig[categoryName];

        if (!categoryRules) {
            console.error(`Rules for category '${categoryName}' not found in config.`);
            alert(`Ошибка: Правила для категории '${categoryName}' не найдены.`);
            return;
        }

        // Disable button and show spinner (optional)
        button.disabled = true;
        const originalIcon = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

        console.log(`Rerolling category '${categoryName}' for player ${playerIndex} with rules:`, categoryRules);

        fetch('/reroll_category', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
                // Add CSRF token header if using Flask-WTF CSRF protection
            },
            body: JSON.stringify({
                category_name: categoryName,
                rules: categoryRules
                // player_index is not needed by backend, but useful for debugging maybe
            })
        })
        .then(response => {
            if (!response.ok) {
                 // Try to get error message from JSON response body
                 return response.json().then(errData => {
                     throw new Error(errData.error || `Server error: ${response.status}`);
                 }).catch(() => {
                      // If response body is not JSON or empty
                      throw new Error(`Server error: ${response.status} ${response.statusText}`);
                 });
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.new_values) {
                console.log("Reroll successful:", data.new_values);
                // Update the UI
                updateCategoryUI(playerIndex, categoryName, data.new_values);
            } else {
                 // Handle backend success=false with error message
                throw new Error(data.error || "Перегенерация не удалась.");
            }
        })
        .catch(error => {
            console.error('Reroll failed:', error);
            alert(`Ошибка при перегенерации: ${error.message}`);
        })
        .finally(() => {
            // Re-enable button and restore icon
            button.disabled = false;
            button.innerHTML = originalIcon;
        });
    }

    function updateCategoryUI(playerIndex, categoryName, newValues) {
        if (!resultsArea) return;
        // Find the specific player card using data attribute
        const playerCard = resultsArea.querySelector(`.player-card[data-player-index="${playerIndex}"]`);
        if (!playerCard) {
            console.error(`Player card with index ${playerIndex} not found.`);
            return;
        }
        // Find the specific category block within the player card
        const categoryBlock = playerCard.querySelector(`.result-category[data-category="${categoryName}"]`);
        if (!categoryBlock) {
            console.error(`Category block '${categoryName}' not found for player ${playerIndex}.`);
            return;
        }
        // Find the UL element to update
        const ulElement = categoryBlock.querySelector('.category-values-list');
        if (!ulElement) {
             console.error(`Values list UL not found for category '${categoryName}' player ${playerIndex}.`);
            return;
        }

        // Clear existing values
        ulElement.innerHTML = '';

        // Check the global description visibility state
        const descriptionsCurrentlyVisible = toggleAllButton && toggleAllButton.classList.contains('expanded');

        // Add new values
        newValues.forEach(item => {
            const li = document.createElement('li');
            li.classList.add('result-item');

            const valueSpan = document.createElement('span');
            valueSpan.textContent = item.value;
            li.appendChild(valueSpan);

            if (item.description) {
                const descSpan = document.createElement('span');
                descSpan.classList.add('value-description', 'text-muted', 'fst-italic', 'ms-1', 'toggleable-description');
                descSpan.textContent = ` - ${item.description}`;
                // Set initial display based on global toggle state
                descSpan.style.display = descriptionsCurrentlyVisible ? 'inline' : 'none';
                li.appendChild(descSpan);
            }
            ulElement.appendChild(li);
        });
    }

    // Attach event listener using delegation
    if (resultsArea) {
        resultsArea.addEventListener('click', function(event) {
            // Find the closest reroll button to the clicked element
            const button = event.target.closest('.reroll-button');
            if (button) {
                 event.preventDefault(); // Prevent any default button action
                 handleRerollClick(button);
            }
        });
    }
     // --- END REROLL Button Logic ---


}); // End DOMContentLoaded


// --- Copy Function (no changes needed) ---
function copyResultToClipboard(containerId) {
    const resultsContainer = document.getElementById(containerId);
    if (!resultsContainer) {
        console.warn("Result container not found for copying.");
        return;
    }

    let textToCopy = "Сгенерированный Челлендж:\n";
    // Find player cards using the class added earlier
    const playerCards = resultsContainer.querySelectorAll('.player-card');

    playerCards.forEach((card, index) => {
        textToCopy += `\n--- Игрок ${index + 1} ---\n`;
        // Find category blocks within the card
        const categoryBlocks = card.querySelectorAll('.result-category');

        if (categoryBlocks.length > 0) {
             categoryBlocks.forEach(catBlock => {
                 const categoryTitleElement = catBlock.querySelector('strong');
                 const categoryTitle = categoryTitleElement ? categoryTitleElement.innerText.replace(':', '').trim() : 'Категория';
                 textToCopy += `${categoryTitle}:\n`;

                 const itemsList = catBlock.querySelectorAll('.result-item');
                 itemsList.forEach(item => {
                     const valueSpan = item.querySelector('span:not(.value-description)');
                     const descriptionSpan = item.querySelector('.value-description');

                     const valueCore = valueSpan ? valueSpan.innerText.trim() : '';
                     const description = descriptionSpan ? descriptionSpan.innerText.replace('-','').trim() : '';

                     textToCopy += `  - ${valueCore}`;
                     if (description) {
                         textToCopy += `: ${description}`;
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