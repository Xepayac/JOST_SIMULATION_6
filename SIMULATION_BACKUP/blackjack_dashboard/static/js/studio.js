document.addEventListener('DOMContentLoaded', function() {

    // --- DOM Elements ---
    const playingStrategyBuilder = document.getElementById('playing-strategy-builder');
    const bettingStrategyBuilder = document.getElementById('betting-strategy-builder');
    const savePlayingStrategyBtn = document.getElementById('save-playing-strategy');
    const saveBettingStrategyBtn = document.getElementById('save-betting-strategy');
    const strategyLibrarySelect = document.getElementById('strategy-library-select');
    const loadStrategyBtn = document.getElementById('load-strategy-btn');
    const deleteStrategyBtn = document.getElementById('delete-strategy-btn');
    const saveFeedback = document.getElementById('save-feedback');
    const libraryFeedback = document.getElementById('library-feedback');

    // --- Constants ---
    const HAND_SECTIONS = {
        "Hard Totals": ['5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20'],
        "Soft Totals": ['A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9'],
        "Pairs": ['22', '33', '44', '55', '66', '77', '88', '99', 'TT', 'AA']
    };
    const PLAYER_HANDS = Object.values(HAND_SECTIONS).flat();
    const DEALER_UP_CARDS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'A'];
    const ACTIONS = ['H', 'S', 'D', 'P', 'Sr']; // Hit, Stand, Double, Split, Surrender
    const DEFAULT_STRATEGY = 's17_basic_strategy.json';

    /**
     * Applies the correct CSS class to the parent TD element for color-coding.
     * @param {HTMLElement} cell - The parent TD element.
     * @param {string} action - The action value (e.g., 'H', 'S').
     */
    function setCellColor(cell, action) {
        cell.classList.remove('action-H', 'action-S', 'action-D', 'action-P', 'action-R');
        let actionClass = '';
        switch (action) {
            case 'H':  actionClass = 'action-H'; break;
            case 'S':  actionClass = 'action-S'; break;
            case 'D':  actionClass = 'action-D'; break;
            case 'P':  actionClass = 'action-P'; break;
            case 'Sr': actionClass = 'action-R'; break;
        }
        if (actionClass) {
            cell.classList.add(actionClass);
        }
    }

    // --- 1. Generate UI Elements ---

    function generatePlayingGrid() {
        let table = '<table id="strategy-grid" class="table table-bordered text-center table-sm small">';
        table += '<thead class="table-dark"><tr><th>Hand</th>';
        DEALER_UP_CARDS.forEach(upCard => { table += `<th>${upCard}</th>`; });
        table += '</tr></thead><tbody>';
        const sections = Object.values(HAND_SECTIONS);
        sections.forEach((hands, index) => {
            hands.forEach(playerHand => {
                table += `<tr><td><strong>${playerHand}</strong></td>`;
                DEALER_UP_CARDS.forEach(dealerCard => {
                    const selectId = `cell-${playerHand}-${dealerCard}`;
                    table += `<td><select id="${selectId}" class="form-select form-select-sm action-select">`;
                    ACTIONS.forEach(action => { table += `<option value="${action}">${action}</option>`; });
                    table += '</select></td>';
                });
                table += '</tr>';
            });
            if (index < sections.length - 1) {
                const colspan = DEALER_UP_CARDS.length + 1;
                table += `<tr><td colspan="${colspan}" class="p-0"><hr class="my-1"></td></tr>`;
            }
        });
        table += '</tbody></table>';
        playingStrategyBuilder.innerHTML = table;
        document.querySelectorAll('.action-select').forEach(selectElement => {
            const parentCell = selectElement.parentElement;
            setCellColor(parentCell, selectElement.value);
            selectElement.addEventListener('change', (event) => {
                setCellColor(parentCell, event.target.value);
            });
        });
    }

    function generateBettingForm() {
        let form = '<div id="betting-rules-container">';
        form += '<p>If True Count is <input type="text" class="form-control-sm" placeholder=">="> <input type="number" class="form-control-sm rule-value" placeholder="e.g., 2">, then Bet <input type="number" class="form-control-sm bet-value" placeholder="e.g., 5"> units.</p>';
        form += '</div>';
        form += '<button id="add-betting-rule" class="btn btn-secondary btn-sm mt-2">Add Rule</button>';
        bettingStrategyBuilder.innerHTML = form;

        document.getElementById('add-betting-rule').addEventListener('click', () => {
            const container = document.getElementById('betting-rules-container');
            const newRule = document.createElement('p');
            newRule.innerHTML = 'If True Count is <input type="text" class="form-control-sm" placeholder=">="> <input type="number" class="form-control-sm rule-value" placeholder="e.g., 2">, then Bet <input type="number" class="form-control-sm bet-value" placeholder="e.g., 5"> units. <button class="btn btn-danger btn-sm remove-rule">X</button>';
            container.appendChild(newRule);
        });

        bettingStrategyBuilder.addEventListener('click', function(event) {
            if (event.target.classList.contains('remove-rule')) {
                event.target.parentElement.remove();
            }
        });
    }

    // --- 2. API Calls & Data Handling ---

    function populateStrategyLibrary() {
        fetch('/api/strategies/playing')
            .then(response => response.json())
            .then(strategies => {
                strategyLibrarySelect.innerHTML = ''; // Clear existing options
                strategies.forEach(strategy => {
                    const option = document.createElement('option');
                    option.value = strategy.name;
                    option.textContent = strategy.name.replace('.json', '').replace(/_/g, ' ');
                    option.dataset.isCustom = strategy.is_custom;
                    if (strategy.name === DEFAULT_STRATEGY) {
                        option.selected = true;
                    }
                    strategyLibrarySelect.appendChild(option);
                });
                // After populating, ensure the delete button's state is correct
                updateDeleteButtonState();
                // Load the default strategy
                loadAndPopulateStrategy(DEFAULT_STRATEGY);
            })
            .catch(error => {
                libraryFeedback.textContent = `Error: ${error.message}`;
                libraryFeedback.className = 'mt-2 text-danger';
            });
    }

    function loadAndPopulateStrategy(filename) {
        fetch(`/api/strategies/playing/${filename}`)
            .then(response => {
                if (!response.ok) throw new Error(`Failed to load strategy: ${response.statusText}`);
                return response.json();
            })
            .then(strategyData => {
                populatePlayingGridWithData(strategyData);
                const suggestedName = filename.replace('.json', '') + '_v2';
                document.getElementById('playing-strategy-name').value = suggestedName;
                libraryFeedback.textContent = `Successfully loaded '${filename.replace('.json','').replace(/_/g, ' ')}'.`;
                libraryFeedback.className = 'mt-2 text-success';
            })
            .catch(error => {
                libraryFeedback.textContent = `Error loading strategy: ${error.message}`;
                libraryFeedback.className = 'mt-2 text-danger';
            });
    }

    function populatePlayingGridWithData(strategyData) {
        for (const playerHand in strategyData) {
            if (Object.hasOwnProperty.call(strategyData, playerHand)) {
                for (const dealerCard in strategyData[playerHand]) {
                    if (Object.hasOwnProperty.call(strategyData[playerHand], dealerCard)) {
                        const action = strategyData[playerHand][dealerCard];
                        const selectId = `cell-${playerHand}-${dealerCard}`;
                        const selectElement = document.getElementById(selectId);
                        if (selectElement) {
                            selectElement.value = action;
                            setCellColor(selectElement.parentElement, action);
                        }
                    }
                }
            }
        }
    }
    
    function updateDeleteButtonState(){
        const selectedOption = strategyLibrarySelect.options[strategyLibrarySelect.selectedIndex];
        // The `isCustom` is a string 'true' or 'false', so we compare to 'true'
        if (selectedOption && selectedOption.dataset.isCustom === 'true') {
            deleteStrategyBtn.disabled = false;
            deleteStrategyBtn.classList.remove('btn-secondary');
            deleteStrategyBtn.classList.add('btn-danger');
        } else {
            deleteStrategyBtn.disabled = true;
            deleteStrategyBtn.classList.remove('btn-danger');
            deleteStrategyBtn.classList.add('btn-secondary');
        }
    }

    // --- 3. Event Listeners ---

    strategyLibrarySelect.addEventListener('change', updateDeleteButtonState);

    loadStrategyBtn.addEventListener('click', () => {
        const selectedStrategy = strategyLibrarySelect.value;
        loadAndPopulateStrategy(selectedStrategy);
    });

    deleteStrategyBtn.addEventListener('click', function() {
        const selectedStrategy = strategyLibrarySelect.value;
        if (!selectedStrategy || strategyLibrarySelect.options[strategyLibrarySelect.selectedIndex].dataset.isCustom !== 'true') {
            libraryFeedback.textContent = 'Please select a custom strategy to delete.';
            libraryFeedback.className = 'mt-2 text-warning';
            return;
        }

        if (!confirm(`Are you sure you want to delete the strategy: ${selectedStrategy}? This action cannot be undone.`)) {
            return;
        }

        fetch(`/api/strategies/playing/${selectedStrategy}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                libraryFeedback.textContent = data.message;
                libraryFeedback.className = 'mt-2 text-success';
                populateStrategyLibrary(); // Refresh the list
            } else {
                libraryFeedback.textContent = `Error: ${data.message}`;
                libraryFeedback.className = 'mt-2 text-danger';
            }
        })
        .catch(error => {
            libraryFeedback.textContent = `An unexpected error occurred: ${error.message}`;
            libraryFeedback.className = 'mt-2 text-danger';
        });
    });

    savePlayingStrategyBtn.addEventListener('click', function() {
        const strategyName = document.getElementById('playing-strategy-name').value.trim();
        if (!strategyName) {
            saveFeedback.textContent = 'Please enter a name for the playing strategy.';
            saveFeedback.className = 'mt-2 text-danger';
            return;
        }

        const strategyData = {};
        PLAYER_HANDS.forEach(playerHand => {
            strategyData[playerHand] = {};
            DEALER_UP_CARDS.forEach(dealerCard => {
                const selectId = `cell-${playerHand}-${dealerCard}`;
                strategyData[playerHand][dealerCard] = document.getElementById(selectId).value;
            });
        });

        const payload = { name: strategyName, strategy: strategyData };

        fetch('/api/strategies/playing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            if(data.status === 'success'){
                saveFeedback.textContent = data.message;
                saveFeedback.className = 'mt-2 text-success';
                populateStrategyLibrary();
            } else {
                saveFeedback.textContent = `Error: ${data.message}`;
                saveFeedback.className = 'mt-2 text-danger';
            }
        }).catch(error => {
            saveFeedback.textContent = `An unexpected error occurred: ${error.message}`;
            saveFeedback.className = 'mt-2 text-danger';
        });
    });
    
    saveBettingStrategyBtn.addEventListener('click', function() {
        const strategyName = document.getElementById('betting-strategy-name').value.trim();
        if (!strategyName) {
            alert('Please enter a name for the betting strategy.');
            return;
        }
        const strategyData = { "name": strategyName, "description": "A custom betting strategy.", "rules": [] };
        const ruleElements = document.querySelectorAll('#betting-rules-container p');
        ruleElements.forEach(rule => {
            const condition = rule.querySelector('input[type="text"]').value;
            const value = rule.querySelector('.rule-value').value;
            const bet = rule.querySelector('.bet-value').value;
            if(value && bet){
                 strategyData.rules.push({ "condition": `true_count ${condition} ${value}`, "action": "bet", "value": parseInt(bet, 10) });
            }
        });
         const payload = { name: strategyName, strategy: strategyData };
        fetch('/api/strategies/betting', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            if(data.status === 'success'){
                alert(data.message);
                document.getElementById('betting-strategy-name').value = '';
            } else {
                alert(`Error: ${data.message}`)
            }
        }).catch(error => {
            console.error('Error saving betting strategy:', error);
            alert('An error occurred while saving the betting strategy.');
        });
    });

    // --- Initializations ---
    generatePlayingGrid();
    generateBettingForm();
    populateStrategyLibrary();

});
