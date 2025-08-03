// AI CODE :) i don't know js
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
    let generationConfig = {};
    let currentResults = [];

    // --- EVENT LISTENERS ---
    if (generationForm) {
        generationForm.addEventListener('submit', handleGenerate);
    }
    if (templateSelect) {
        templateSelect.addEventListener('change', toggleCustomSettings);
        toggleCustomSettings();
    }
    if (customSettingsDiv) {
        setupCustomSettingsInteractions();
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
                displayErrors(data.errors || ['An unknown error occurred.']);
            } else {
                generationConfig = data.config;
                currentResults = data.results;
                renderResults(data.results, data.is_custom);
            }
        } catch (error) {
            console.error('Generation fetch error:', error);
            displayErrors(['Network error. Could not contact the server.']);
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
                    <h2 class="mb-0">Generation Results:</h2>
                    <div>
                        ${isCustom ? '<button id="save-as-template-btn" class="btn btn-success btn-sm me-2"><i class="bi bi-save"></i> Save as Template</button>' : ''}
                        <button id="toggle-all-descriptions" class="btn btn-info btn-sm me-2"><i class="bi bi-eye-slash"></i> Show Descriptions</button>
                        <button id="copy-all-btn" class="btn btn-secondary btn-sm"><i class="bi bi-clipboard"></i> Copy All</button>
                    </div>
                </div>
                <div class="row g-4" id="results-area"></div>
            </div>`;

        resultsPlaceholder.innerHTML = resultsHtml;
        const resultsArea = document.getElementById('results-area');

        resultsData.forEach((playerResult, playerIndex) => {
            const cardClone = playerCardTemplate.content.cloneNode(true);
            const playerCard = cardClone.querySelector('.player-card');

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

                if (generationConfig[categoryName] && !generationConfig[categoryName].apply_all) {
                    rerollButton.classList.remove('d-none');
                    rerollButton.dataset.categoryName = categoryName;
                    rerollButton.dataset.playerIndex = playerIndex;
                }

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
            alert('Error: Data for reroll is missing.');
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
                throw new Error(data.error || 'Server error during reroll.');
            }
            updateCategoryUI(playerIndex, categoryName, data.new_values);
            currentResults[playerIndex][categoryName] = data.new_values;
        } catch (error) {
            console.error('Reroll failed:', error);
            alert(`Error: ${error.message}`);
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
            alert('Error: Data for reroll is missing.');
            return;
        }

        button.disabled = true;
        const originalIcon = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        try {
            const response = await fetch('/reroll_category', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({
                    category_name: categoryName,
                    rules: categoryRules
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Server error during reroll.');
            }

            if (data.new_values && data.new_values.length > 0) {
                const newValuesForAll = data.new_values;

                for (let i = 0; i < currentResults.length; i++) {
                    updateCategoryUI(i, categoryName, newValuesForAll);
                    currentResults[i][categoryName] = newValuesForAll;
                }
            }
        } catch (error) {
            console.error('Reroll all failed:', error);
            alert(`Error: ${error.message}`);
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
            alert('Generate a challenge first!');
            return;
        }

        const categoryRules = getCurrentCategoryRules(categoryName);
        if (!categoryRules) {
            alert('Error: Could not get category rules.');
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
                throw new Error(data.error || 'Server error during reroll.');
            }
            // By default, update player 1
            updateCategoryUI(0, categoryName, data.new_values);
            currentResults[0][categoryName] = data.new_values;
        } catch (error) {
            console.error('Settings reroll single failed:', error);
            alert(`Error: ${error.message}`);
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
            alert('Generate a challenge first!');
            return;
        }

        const categoryRules = getCurrentCategoryRules(categoryName);
        if (!categoryRules) {
            alert('Error: Could not get category rules.');
            return;
        }

        button.disabled = true;
        const originalIcon = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        try {
            const response = await fetch('/reroll_category', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({
                    category_name: categoryName,
                    rules: categoryRules
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Server error during reroll.');
            }

            if (data.new_values && data.new_values.length > 0) {
                const newValuesForAll = data.new_values;

                for (let i = 0; i < currentResults.length; i++) {
                    updateCategoryUI(i, categoryName, newValuesForAll);
                    currentResults[i][categoryName] = newValuesForAll;
                }
            }
        } catch (error) {
            console.error('Settings reroll all failed:', error);
            alert(`Error: ${error.message}`);
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
        const formElement = document.querySelector(`.custom-category-block input[value="${categoryName}"]`).closest('.custom-category-block');

        const ruleSelect = formElement.querySelector(`select[name="rule_${categoryName}"]`);
        if (!ruleSelect) return null;

        const countInput = formElement.querySelector(`input[name="count_${categoryName}"]`);
        const applyAllCheckbox = formElement.querySelector(`input[name="apply_all_${categoryName}"]`);

        const rules = {
            rule: ruleSelect.value,
            count: countInput ? parseInt(countInput.value, 10) || 1 : 1,
            apply_all: applyAllCheckbox ? applyAllCheckbox.checked : true
        };

        if (rules.rule === 'fixed') {
            const fixedInput = formElement.querySelector(`input[name^="fixed_value_"]:not([style*="display: none"])`) ||
                               formElement.querySelector(`select[name^="fixed_value_"]:not([style*="display: none"])`);
            if (fixedInput) {
                rules.value = fixedInput.value;
            }
        } else if (rules.rule === 'random_from_list') {
            const allowedInputs = formElement.querySelectorAll(`input[name="allowed_values_${categoryName}"]:checked`);
            rules.allowed_values = Array.from(allowedInputs).map(input => input.value);
        } else if (rules.rule === 'range') {
            const minInput = formElement.querySelector(`input[name="range_min_${categoryName}"]`);
            const maxInput = formElement.querySelector(`input[name="range_max_${categoryName}"]`);
            const stepInput = formElement.querySelector(`input[name="range_step_${categoryName}"]`);
            if (minInput) rules.min = minInput.value;
            if (maxInput) rules.max = maxInput.value;
            if (stepInput) rules.step = stepInput.value;
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
            nameInput.nextElementSibling.textContent = 'Template name cannot be empty.';
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
                nameInput.nextElementSibling.textContent = data.error || 'Server error.';
                throw new Error(data.error);
            }

            const newOption = new Option(data.new_template.name, data.new_template.id, false, true);
            templateSelect.add(newOption);
            templateSelect.dispatchEvent(new Event('change'));

            saveTemplateModal.hide();
            saveTemplateForm.reset();
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
        buttonText.textContent = isLoading ? 'Generating...' : 'Generate Challenge!';
        buttonIcon.classList.toggle('d-none', isLoading);
    }

    function displayErrors(errors) {
        let errorHtml = '<div class="alert alert-danger alert-dismissible fade show" role="alert">';
        errorHtml += '<strong>Problems occurred during generation:</strong><ul class="mb-0">';
        errors.forEach(err => { errorHtml += `<li>${err}</li>`; });
        errorHtml += '</ul><button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>';

        // Insert after the form, not inside it
        resultsPlaceholder.insertAdjacentHTML('beforebegin', errorHtml);
    }

    function clearResultsAndErrors() {
        resultsPlaceholder.innerHTML = '';
        const existingAlert = document.querySelector('.alert-danger');
        if (existingAlert) {
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

        ulElement.classList.add('new-item-highlight');
        setTimeout(() => { ulElement.classList.remove('new-item-highlight'); }, 2000);
    }

    function toggleAllDescriptions(button) {
        const isVisible = button.classList.toggle('expanded');
        const descriptions = resultsPlaceholder.querySelectorAll('.toggleable-description');

        button.innerHTML = isVisible
            ? '<i class="bi bi-eye"></i> Hide Descriptions'
            : '<i class="bi bi-eye-slash"></i> Show Descriptions';

        descriptions.forEach(span => span.style.display = isVisible ? 'inline' : 'none');
    }

    function copyResultToClipboard(containerId) {
        const resultsContainer = document.getElementById(containerId);
        if (!resultsContainer) return;

        let textToCopy = "Generated Challenge:\n";
        resultsContainer.querySelectorAll('.player-card').forEach((card, index) => {
            textToCopy += `\n--- Player ${index + 1} ---\n`;
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
            copyButton.innerHTML = '<i class="bi bi-check-lg"></i> Copied!';
            setTimeout(() => { copyButton.innerHTML = originalText; }, 2000);
        }, (err) => {
            alert('Failed to copy.');
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
                 updateRuleOptions(block);
            }
        });
    }

    function updateRuleOptions(categoryBlock) {
        const ruleSelect = categoryBlock.querySelector('.rule-select');
        const selectedRule = ruleSelect.value;
        const categoryId = ruleSelect.id.split('_').pop();
        const ruleOptionsDiv = categoryBlock.querySelector('.rule-options-' + categoryId);

        ruleOptionsDiv.querySelectorAll('.option-fixed, .option-random_from_list, .option-range').forEach(div => div.style.display = 'none');
        categoryBlock.querySelectorAll('.rule-count-field').forEach(field => field.style.display = (selectedRule === 'fixed' || selectedRule === 'range') ? 'none' : 'inline-block');
        const targetOptionDiv = ruleOptionsDiv.querySelector('.option-' + selectedRule);
        if (targetOptionDiv) {
            targetOptionDiv.style.display = 'block';
            if (selectedRule === 'fixed') {
                const textInput = targetOptionDiv.querySelector('.fixed-input-text');
                const selectInput = targetOptionDiv.querySelector('.fixed-input-select');
                const categoryName = ruleSelect.name.replace('rule_', '');
                if (selectInput.options.length > 1) {
                    textInput.style.display = 'none'; textInput.name = '';
                    selectInput.style.display = 'block'; selectInput.name = `fixed_value_${categoryName}`;
                } else {
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