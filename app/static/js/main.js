const templateSelect = document.getElementById('template_select');
        const customSettingsDiv = document.getElementById('custom_settings');

        function toggleCustomSettings() {
            if (templateSelect.value === 'custom') {
                customSettingsDiv.style.display = 'block';
            } else {
                customSettingsDiv.style.display = 'none';
            }
        }

        function updateRuleOptions(categoryBlock) {
            const ruleSelect = categoryBlock.querySelector('select[name^="rule_"]');
            const selectedRule = ruleSelect.value;
            const ruleOptionsDiv = categoryBlock.querySelector('.rule-options-' + ruleSelect.id.split('_').pop());

            // Скрываем все доп. опции
             ruleOptionsDiv.querySelectorAll('.option-fixed, .option-random_from_list, .option-range').forEach(div => {
                div.style.display = 'none';
            });

            // Скрываем поле "Кол-во" для fixed и range
            const countFields = categoryBlock.querySelectorAll('.rule-count-field'); // Находим и label, и input
             countFields.forEach(field => {
                field.style.display = (selectedRule === 'fixed' || selectedRule === 'range') ? 'none' : 'block'; // Используем block вместо inline-block для колонок сетки
             });

            // Показываем нужные опции
            const targetOptionDiv = ruleOptionsDiv.querySelector('.option-' + selectedRule);
             if (targetOptionDiv) {
                 targetOptionDiv.style.display = 'block';

                // Особая логика для выбора input/select в 'fixed'
                 if (selectedRule === 'fixed') {
                    const textInput = targetOptionDiv.querySelector('.fixed-input-text');
                    const selectInput = targetOptionDiv.querySelector('.fixed-input-select');
                    const categoryValuesExist = selectInput && selectInput.options.length > 1; // Проверяем, есть ли опции кроме "-- Выберите --"

                    if (categoryValuesExist) {
                        textInput.style.display = 'none';
                        selectInput.style.display = 'block'; // Используем block
                        textInput.name = '';
                        selectInput.name = `fixed_value_${ruleSelect.name.split('_')[1]}`;
                    } else {
                        textInput.style.display = 'block'; // Используем block
                        selectInput.style.display = 'none';
                        textInput.name = `fixed_value_${ruleSelect.name.split('_')[1]}`;
                        selectInput.name = '';
                    }
                 }
             }
        }

        // Инициализация и обработчики (без изменений в логике, но JS должен работать с новой структурой)
        if(templateSelect) {
            templateSelect.addEventListener('change', toggleCustomSettings);
        }

        if(customSettingsDiv) {
            customSettingsDiv.querySelectorAll('select[name^="rule_"]').forEach(select => {
                select.addEventListener('change', function() {
                    const categoryBlock = this.closest('.custom-category-block');
                    updateRuleOptions(categoryBlock);
                });
            });

            customSettingsDiv.querySelectorAll('.form-check-input[name="include_category"]').forEach(checkbox => {
                 checkbox.addEventListener('change', function() {
                     const rulesDiv = this.closest('.custom-category-block').querySelector('.custom-rules');
                     rulesDiv.style.display = this.checked ? 'block' : 'none';
                     if(this.checked) {
                         updateRuleOptions(this.closest('.custom-category-block'));
                     }
                 });
                 // Инициализация видимости блока правил при загрузке (JS теперь в конце, DOM готов)
                // const rulesDiv = checkbox.closest('.custom-category-block').querySelector('.custom-rules');
                // rulesDiv.style.display = checkbox.checked ? 'block' : 'none';
                // if(checkbox.checked) {
                //      updateRuleOptions(checkbox.closest('.custom-category-block'));
                // }
            });
        }

        document.addEventListener('DOMContentLoaded', function() {
            if (templateSelect) { // Проверка на случай, если элемента нет
                toggleCustomSettings(); // Инициализация видимости кастомного блока
            }

            if(customSettingsDiv) { // Проверка на случай, если элемента нет
                customSettingsDiv.querySelectorAll('.custom-category-block').forEach(block => {
                    const checkbox = block.querySelector('.form-check-input[name="include_category"]');
                    if (checkbox) { // Доп. проверка
                         const rulesDiv = block.querySelector('.custom-rules');
                         if (rulesDiv) {
                             rulesDiv.style.display = checkbox.checked ? 'block' : 'none';
                             if(checkbox.checked) {
                                 updateRuleOptions(block);
                             }
                         }
                    }
                });
            }
        });

        function copyResultToClipboard() {
            // ... (функция копирования без изменений) ...
            const resultArea = document.querySelector('.challenge-result');
            if (!resultArea) return;
            let textToCopy = "Сгенерированный Челлендж:\n---\n";
            const resultItems = resultArea.querySelectorAll('.result-item');
            resultItems.forEach(item => {
                const key = item.querySelector('strong').innerText;
                const value = item.querySelector('span').innerText;
                textToCopy += `${key} ${value}\n`;
            });
            textToCopy += "---\nСгенерировано: " + new Date().toLocaleString('ru-RU');

            navigator.clipboard.writeText(textToCopy.trim()).then(function() {
                alert('Результат скопирован в буфер обмена!');
            }, function(err) {
                alert('Не удалось скопировать результат. Попробуйте вручную.');
                console.error('Ошибка копирования: ', err);
            });
        }