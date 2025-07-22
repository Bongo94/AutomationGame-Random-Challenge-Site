// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    // --- FORM ELEMENTS ---
    const generationForm = document.getElementById('generation-form');
    const templateSelect = document.getElementById('template_select');
    const customSettingsDiv = document.getElementById('custom_settings');
    const generateButton = document.getElementById('generate-button');
    const resultsPlaceholder = document.getElementById('results-placeholder');

    // --- TEMPLATE ELEMENTS ---
    const playerCardTemplate = document.getElementById('player-card-template');
    const categoryItemTemplate = document.getElementById('category-item-template');

    // --- MODAL ELEMENTS ---
    const saveTemplateModal = new bootstrap.Modal(document.getElementById('saveTemplateModal'));
    const saveTemplateForm = document.getElementById('save-template-form');
    const confirmSaveButton = document.getElementById('confirm-save-template');

    // --- STATE ---
    let generationConfig = {}; // Store config for reroll/save
    let currentResults = []; // Store current results for reroll all functionality

    // --- EVENT LISTENERS ---
    if (generationForm) {
        generationForm.addEventListener('submit', handleGenerate);
    }
    if (templateSelect) {
        templateSelect.addEventListener('change', toggleCustomSettings);
        toggleCustomSettings(); // Initial check
    }
    if (customSettingsDiv) {
        setupCustomSettingsInteractions();
        // Add event listeners for new reroll buttons in settings
        customSettingsDiv.addEventListener('click', handleSettingsRerollClick);
    }
    if (resultsPlaceholder) {
        resultsPlaceholder.addEventListener('click', handleResultsAreaClick);
    }
    if (confirmSaveButton) {
        confirmSaveButton.addEventListener('click', handleSaveTemplate);
    }


    // --- MAIN FUNCTIONS ---

    /**
     * Handles the main form submission for challenge generation.
     * @param {Event} e - The form submission event.
     */
    async function handleGenerate(e) {
        e.preventDefault();
        toggleLoading(true);
        clearResultsAndErrors();

        const formData = new FormData(generationForm);

        try {
            const response = await fetch('/generate', { method: 'POST', body: formData });
            const data = await response.json();

            if (!response.ok) {
                displayErrors(data.errors || ['Произошла неизвестная ошибка.']);
            } else {
                generationConfig = data.config; // Save config
                currentResults = data.results; // Save results
                renderResults(data.results, data.is_custom);
            }
        } catch (error) {
            console.error('Generation fetch error:', error);
            displayErrors(['Ошибка сети. Не удалось связаться с сервером.']);
        } finally {
            toggleLoading(false);
        }
    }

    /**
     * Renders the generated results into the DOM.
     * @param {Array} resultsData - Array of player results.
     * @param {boolean} isCustom - Was this a custom generation?
     */
    function renderResults(resultsData, isCustom) {
        const resultsHtml = `
            <div class="challenge-results-container border rounded p-4 bg-white shadow-sm mt-5">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h2 class="mb-0">Результаты Генерации:</h2>
                    <div>
                        ${isCustom ? '<button id="save-as-template-btn" class="btn btn-success btn-sm me-2"><i class="bi bi-save"></i> Сохранить как шаблон</button>' : ''}
                        <button id="toggle-all-descriptions" class="btn btn-info btn-sm me-2"><i class="bi bi-eye-slash"></i> Показать описания</button>
                        <button id="copy-all-btn" class="btn btn-secondary btn-sm"><i class="bi bi-clipboard"></i> Копировать все</button>
                    </div>
                </div>
                <div class="row g-4" id="results-area"></div>
            </div>`;

        resultsPlaceholder.innerHTML = resultsHtml;
        const resultsArea = document.getElementById('results-area');

        resultsData.forEach((playerResult, playerIndex) => {
            const cardClone = playerCardTemplate.content.cloneNode(true);
            const playerCard = cardClone.querySelector('.player-card');

            // Dynamic column classes
            const colCount = resultsData.length;
            let colClass = 'col-lg-3 col-md-4 col-sm-6';
            if (colCount === 1) colClass = 'col-lg-12';
            else if (colCount === 2) colClass = 'col-lg-6 col-md-6';
            else if (colCount === 3) colClass = 'col-lg-4 col-md-6';
            playerCard.classList.add(...colClass.split(' '));

            playerCard.dataset.playerIndex = playerIndex;
            playerCard.querySelector('.player-number').textContent = playerIndex + 1;

            const categoriesList = playerCard.querySelector('.categories-list');

            for (const [categoryName, itemsList] of Object.entries(playerResult)) {
                const categoryClone = categoryItemTemplate.content.cloneNode(true);
                const categoryItem = categoryClone.querySelector('.result-category');

                categoryItem.dataset.category = categoryName;
                categoryItem.querySelector('.category-name').textContent = `${categoryName}:`;

                const rerollButton = categoryItem.querySelector('.reroll-button');
                const rerollAllButton = categoryItem.querySelector('.reroll-all-button');
                
                // Show reroll buttons if rule is not shared for all players
                if (generationConfig[categoryName] && !generationConfig[categoryName].apply_all) {
                    rerollButton.classList.remove('d-none');
                    rerollButton.dataset.categoryName = categoryName;
                    rerollButton.dataset.playerIndex = playerIndex;
                }
                
                // Always show reroll all button for categories that are included
                if (generationConfig[categoryName]) {
                    rerollAllButton.classList.remove('d-none');
                    rerollAllButton.dataset.categoryName = categoryName;
                }

                const valuesUl = categoryItem.querySelector('.category-values-list');
                itemsList.forEach(item => {
                    const li = document.createElement('li');
                    li.classList.add('result-item');
                    li.innerHTML = `<span>${item.value}</span>` +
                        (item.description ? `<span class="value-description text-muted fst-italic ms-1 toggleable-description" style="display: none;"> - ${item.description}</span>` : '');
                    valuesUl.appendChild(li);
                });
                categoriesList.appendChild(categoryClone);
            }
            resultsArea.appendChild(cardClone);
        });
    }

    /**
     * Handles clicks within the dynamic results area using event delegation.
     * @param {Event} e - The click event.
     */
    function handleResultsAreaClick(e) {
        const button = e.target.closest('button');
        if (!button) return;

        if (button.id === 'toggle-all-descriptions') toggleAllDescriptions(button);
        if (button.id === 'copy-all-btn') copyResultToClipboard('results-area');
        if (button.id === 'save-as-template-btn') saveTemplateModal.show();
        if (button.classList.contains('reroll-button')) handleReroll(button);
        if (button.classList.contains('reroll-all-button')) handleRerollAll(button);
    }

    /**
     * Handles clicks within the custom settings area for reroll buttons.
     * @param {Event} e - The click event.
     */
    function handleSettingsRerollClick(e) {
        const button = e.target.closest('button');
        if (!button) return;

        if (button.classList.contains('reroll-single-btn')) {
            handleSettingsRerollSingle(button);
        } else if (button.classList.contains('reroll-all-btn')) {
            handleSettingsRerollAll(button);
        }
    }

    /**
     * Handles the reroll action for a single category and single player.
     * @param {HTMLElement} button - The reroll button that was clicked.
     */
    async function handleReroll(button) {
        const { categoryName, playerIndex } = button.dataset;
        const categoryRules = generationConfig[categoryName];
        if (!categoryName || !playerIndex || !categoryRules) {
            alert('Ошибка: Отсутствуют данные для перегенерации.');
            return;
        }

        button.disabled = true;
        const originalIcon = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        try {
            const response = await fetch('/reroll_category', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ category_name: categoryName, rules: categoryRules })
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Ошибка сервера при перегенерации.');
            }
            updateCategoryUI(playerIndex, categoryName, data.new_values);
            // Update stored results
            currentResults[playerIndex][categoryName] = data.new_values;
        } catch (error) {
            console.error('Reroll failed:', error);
            alert(`Ошибка: ${error.message}`);
        } finally {
            button.disabled = false;
            button.innerHTML = originalIcon;
        }
    }

    /**
     * Handles the reroll action for a category for all players.
     * @param {HTMLElement} button - The reroll all button that was clicked.
     */
    async function handleRerollAll(button) {
        const { categoryName } = button.dataset;
        const categoryRules = generationConfig[categoryName];
        if (!categoryName || !categoryRules) {
            alert('Ошибка: Отсутствуют данные для перегенерации.');
            return;
        }

        button.disabled = true;
        const originalIcon = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        try {
            // Request one value for all players
            const response = await fetch('/reroll_category', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ 
                    category_name: categoryName, 
                    rules: categoryRules,
                    reroll_type: 'all' // Request one value for all players
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Ошибка сервера при перегенерации.');
            }

            // Apply the same value to all players
            if (data.new_values && data.new_values.length > 0) {
                const singleValue = data.new_values;
                
                for (let i = 0; i < currentResults.length; i++) {
                    updateCategoryUI(i, categoryName, singleValue);
                    // Update stored results
                    currentResults[i][categoryName] = singleValue;
                }
            }
        } catch (error) {
            console.error('Reroll all failed:', error);
            alert(`Ошибка: ${error.message}`);
        } finally {
            button.disabled = false;
            button.innerHTML = originalIcon;
        }
    }

    /**
     * Handles reroll single from settings area.
     * @param {HTMLElement} button - The reroll single button that was clicked.
     */
    async function handleSettingsRerollSingle(button) {
        const categoryName = button.dataset.category;
        if (!categoryName || !currentResults.length) {
            alert('Сначала сгенерируйте челлендж!');
            return;
        }

        // Get current rules from form
        const categoryRules = getCurrentCategoryRules(categoryName);
        if (!categoryRules) {
            alert('Ошибка: Не удалось получить правила категории.');
            return;
        }

        // For single reroll from settings, reroll for first player only
        button.disabled = true;
        const originalIcon = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        try {
            const response = await fetch('/reroll_category', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ category_name: categoryName, rules: categoryRules })
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Ошибка сервера при перегенерации.');
            }
            updateCategoryUI(0, categoryName, data.new_values);
            // Update stored results
            currentResults[0][categoryName] = data.new_values;
        } catch (error) {
            console.error('Settings reroll single failed:', error);
            alert(`Ошибка: ${error.message}`);
        } finally {
            button.disabled = false;
            button.innerHTML = originalIcon;
        }
    }

    /**
     * Handles reroll all from settings area.
     * @param {HTMLElement} button - The reroll all button that was clicked.
     */
    async function handleSettingsRerollAll(button) {
        const categoryName = button.dataset.category;
        if (!categoryName || !currentResults.length) {
            alert('Сначала сгенерируйте челлендж!');
            return;
        }

        // Get current rules from form
        const categoryRules = getCurrentCategoryRules(categoryName);
        if (!categoryRules) {
            alert('Ошибка: Не удалось получить правила категории.');
            return;
        }

        button.disabled = true;
        const originalIcon = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        try {
            // Request one value for all players
            const response = await fetch('/reroll_category', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ 
                    category_name: categoryName, 
                    rules: categoryRules,
                    reroll_type: 'all' // Request one value for all players
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Ошибка сервера при перегенерации.');
            }

            // Apply the same value to all players
            if (data.new_values && data.new_values.length > 0) {
                const singleValue = data.new_values;
                
                for (let i = 0; i < currentResults.length; i++) {
                    updateCategoryUI(i, categoryName, singleValue);
                    // Update stored results
                    currentResults[i][categoryName] = singleValue;
                }
            }
        } catch (error) {
            console.error('Settings reroll all failed:', error);
            alert(`Ошибка: ${error.message}`);
        } finally {
            button.disabled = false;
            button.innerHTML = originalIcon;
        }
    }

    /**
     * Gets current category rules from the form.
     * @param {string} categoryName - The category name.
     * @returns {Object|null} - The category rules or null if not found.
     */
    function getCurrentCategoryRules(categoryName) {
        const includeCheckbox = document.querySelector(`input[name="include_category"][value="${categoryName}"]`);
        if (!includeCheckbox || !includeCheckbox.checked) {
            return null;
        }

        const ruleSelect = document.querySelector(`select[name="rule_${categoryName}"]`);
        const countInput = document.querySelector(`input[name="count_${categoryName}"]`);
        const applyAllCheckbox = document.querySelector(`input[name="apply_all_${categoryName}"]`);

        if (!ruleSelect) return null;

        const rules = {
            rule: ruleSelect.value,
            count: countInput ? parseInt(countInput.value) || 1 : 1,
            apply_all: applyAllCheckbox ? applyAllCheckbox.checked : true
        };

        // Add rule-specific parameters
        if (rules.rule === 'fixed') {
            const fixedInput = document.querySelector(`input[name="fixed_value_${categoryName}"]`) ||
                             document.querySelector(`select[name="fixed_value_${categoryName}"]`);
            if (fixedInput) {
                rules.fixed_value = fixedInput.value;
            }
        } else if (rules.rule === 'random_from_list') {
            const allowedInputs = document.querySelectorAll(`input[name="allowed_values_${categoryName}"]:checked`);
            rules.allowed_values = Array.from(allowedInputs).map(input => input.value);
        } else if (rules.rule === 'range') {
            const minInput = document.querySelector(`input[name="range_min_${categoryName}"]`);
            const maxInput = document.querySelector(`input[name="range_max_${categoryName}"]`);
            const stepInput = document.querySelector(`input[name="range_step_${categoryName}"]`);
            rules.range_min = minInput ? parseInt(minInput.value) : 0;
            rules.range_max = maxInput ? parseInt(maxInput.value) : 100;
            rules.range_step = stepInput ? parseInt(stepInput.value) : 1;
        }

        return rules;
    }

    /**
     * Handles saving the current custom config as a new template.
     */
    async function handleSaveTemplate() {
        const nameInput = document.getElementById('template-name');
        const descInput = document.getElementById('template-description');
        const name = nameInput.value.trim();
        const description = descInput.value.trim();

        nameInput.classList.remove('is-invalid');

        if (!name) {
            nameInput.classList.add('is-invalid');
            nameInput.nextElementSibling.textContent = 'Имя шаблона не может быть пустым.';
            return;
        }

        try {
            const response = await fetch('/save_template', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ name, description, config: generationConfig })
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                nameInput.classList.add('is-invalid');
                nameInput.nextElementSibling.textContent = data.error || 'Ошибка сервера.';
                throw new Error(data.error);
            }

            // Add new template to dropdown and select it
            const newOption = new Option(data.new_template.name, data.new_template.id, false, true);
            templateSelect.add(newOption);
            templateSelect.dispatchEvent(new Event('change'));

            saveTemplateModal.hide();
            // Optional: show a success toast/alert
        } catch (error) {
            console.error('Failed to save template:', error);
        }
    }

    // --- UI HELPER FUNCTIONS ---

    function toggleLoading(isLoading) {
        const spinner = generateButton.querySelector('.spinner-border');
        const buttonText = generateButton.querySelector('.button-text');
        const buttonIcon = generateButton.querySelector('.bi-dice-5');

        generateButton.disabled = isLoading;
        spinner.classList.toggle('d-none', !isLoading);
        buttonText.textContent = isLoading ? 'Генерация...' : 'Сгенерировать Челлендж!';
        buttonIcon.classList.toggle('d-none', isLoading);
    }

    function displayErrors(errors) {
        let errorHtml = '<div class="alert alert-danger alert-dismissible fade show" role="alert">';
        errorHtml += '<strong>При генерации возникли проблемы:</strong><ul class="mb-0">';
        errors.forEach(err => { errorHtml += `<li>${err}</li>`; });
        errorHtml += '</ul><button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>';

        // Insert after the form
        generationForm.insertAdjacentHTML('afterend', errorHtml);
    }

    function clearResultsAndErrors() {
        resultsPlaceholder.innerHTML = '';
        const existingAlert = generationForm.nextElementSibling;
        if (existingAlert && existingAlert.classList.contains('alert')) {
            existingAlert.remove();
        }
    }

    function updateCategoryUI(playerIndex, categoryName, newValues) {
        const playerCard = resultsPlaceholder.querySelector(`.player-card[data-player-index="${playerIndex}"]`);
        if (!playerCard) return;
        const categoryBlock = playerCard.querySelector(`.result-category[data-category="${categoryName}"]`);
        if (!categoryBlock) return;
        const ulElement = categoryBlock.querySelector('.category-values-list');
        if (!ulElement) return;

        ulElement.innerHTML = '';
        const descriptionsCurrentlyVisible = document.getElementById('toggle-all-descriptions')?.classList.contains('expanded');

        newValues.forEach(item => {
            const li = document.createElement('li');
            li.classList.add('result-item');
            li.innerHTML = `<span>${item.value}</span>` +
                (item.description ? `<span class="value-description text-muted fst-italic ms-1 toggleable-description" style="display: ${descriptionsCurrentlyVisible ? 'inline' : 'none'};"> - ${item.description}</span>` : '');
            ulElement.appendChild(li);
        });

        // Highlight animation
        ulElement.classList.add('new-item-highlight');
        setTimeout(() => { ulElement.classList.remove('new-item-highlight'); }, 2000);
    }

    function toggleAllDescriptions(button) {
        const isVisible = button.classList.toggle('expanded');
        const descriptions = resultsPlaceholder.querySelectorAll('.toggleable-description');

        button.innerHTML = isVisible
            ? '<i class="bi bi-eye"></i> Скрыть описания'
            : '<i class="bi bi-eye-slash"></i> Показать описания';

        descriptions.forEach(span => span.style.display = isVisible ? 'inline' : 'none');
    }

    function copyResultToClipboard(containerId) {
        const resultsContainer = document.getElementById(containerId);
        if (!resultsContainer) return;

        let textToCopy = "Сгенерированный Челлендж:\n";
        resultsContainer.querySelectorAll('.player-card').forEach((card, index) => {
            textToCopy += `\n--- Игрок ${index + 1} ---\n`;
            card.querySelectorAll('.result-category').forEach(catBlock => {
                const categoryTitle = catBlock.querySelector('.category-name').innerText.trim();
                textToCopy += `${categoryTitle}\n`;
                catBlock.querySelectorAll('.result-item').forEach(item => {
                    const valueCore = item.querySelector('span:not(.value-description)').innerText.trim();
                    const descriptionSpan = item.querySelector('.value-description');
                    const description = descriptionSpan ? descriptionSpan.innerText.replace('-','').trim() : '';
                    textToCopy += `  - ${valueCore}${description ? `: ${description}` : ''}\n`;
                });
            });
        });

        navigator.clipboard.writeText(textToCopy.trim()).then(() => {
            const copyButton = document.getElementById('copy-all-btn');
            const originalText = copyButton.innerHTML;
            copyButton.innerHTML = '<i class="bi bi-check-lg"></i> Скопировано!';
            setTimeout(() => { copyButton.innerHTML = originalText; }, 2000);
        }, (err) => {
            alert('Не удалось скопировать.');
        });
    }

    // --- SETUP LOGIC FOR CUSTOM FORM ---
    function setupCustomSettingsInteractions() {
        customSettingsDiv.querySelectorAll('.custom-category-block').forEach(block => {
            const includeCheckbox = block.querySelector('input[name="include_category"]');
            const rulesDiv = block.querySelector('.custom-rules');
            const ruleSelect = block.querySelector('.rule-select');

            if (includeCheckbox && rulesDiv) {
                rulesDiv.style.display = includeCheckbox.checked ? 'block' : 'none';
                includeCheckbox.addEventListener('change', (e) => {
                    rulesDiv.style.display = e.target.checked ? 'block' : 'none';
                });
            }
            if (ruleSelect) {
                 ruleSelect.addEventListener('change', () => updateRuleOptions(block));
                 updateRuleOptions(block); // Initial call
            }
        });
    }

    function updateRuleOptions(categoryBlock) {
        const ruleSelect = categoryBlock.querySelector('.rule-select');
        const selectedRule = ruleSelect.value;
        const categoryId = ruleSelect.id.split('_').pop();
        const ruleOptionsDiv = categoryBlock.querySelector('.rule-options-' + categoryId);

        // Hide all options first
        ruleOptionsDiv.querySelectorAll('.option-fixed, .option-random_from_list, .option-range').forEach(div => div.style.display = 'none');
        // Hide/show count field
        categoryBlock.querySelectorAll('.rule-count-field').forEach(field => field.style.display = (selectedRule === 'fixed' || selectedRule === 'range') ? 'none' : 'inline-block');
        // Show the target option
        const targetOptionDiv = ruleOptionsDiv.querySelector('.option-' + selectedRule);
        if (targetOptionDiv) {
            targetOptionDiv.style.display = 'block';
            if (selectedRule === 'fixed') { // Special logic for fixed value input/select
                const textInput = targetOptionDiv.querySelector('.fixed-input-text');
                const selectInput = targetOptionDiv.querySelector('.fixed-input-select');
                const categoryName = ruleSelect.name.replace('rule_', '');
                if (selectInput.options.length > 1) { // Values exist
                    textInput.style.display = 'none'; textInput.name = '';
                    selectInput.style.display = 'block'; selectInput.name = `fixed_value_${categoryName}`;
                } else { // No values, use text input
                    textInput.style.display = 'block'; textInput.name = `fixed_value_${categoryName}`;
                    selectInput.style.display = 'none'; selectInput.name = '';
                }
            }
        }
    }

    function toggleCustomSettings() {
        customSettingsDiv.style.display = templateSelect.value === 'custom' ? 'block' : 'none';
    }
});