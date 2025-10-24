document.addEventListener('DOMContentLoaded', function() {

    const form = document.getElementById('simulation-form');
    const loadingDiv = document.getElementById('loading');
    const progressBar = document.getElementById('simulation-progress-bar');
    const messagesDiv = document.getElementById('messages');
    const resultsOutput = document.getElementById('results-output');

    let pollingInterval = null; // To hold the setInterval reference

    if (form) {
        form.addEventListener('submit', function(event) {
            event.preventDefault(); // Prevent default form submission

            // --- 1. UI Setup: Clear old results and show progress bar ---
            messagesDiv.innerHTML = '';
            resultsOutput.innerHTML = '';
            progressBar.style.width = '0%'; // Reset progress bar
            progressBar.setAttribute('aria-valuenow', '0');
            loadingDiv.style.display = 'block'; 

            // --- 2. Gather Form Data ---
            const formData = new FormData(form);
            const data = {
                player_name: formData.get('player_name'),
                bankroll: parseInt(formData.get('bankroll'), 10),
                num_hands: parseInt(formData.get('num_hands'), 10),
                casino_profile: formData.get('casino_profile'),
                playing_strategy: formData.get('playing_strategy'),
                betting_strategy: formData.get('betting_strategy'),
            };

            // --- 3. Start the Simulation (Asynchronous) ---
            fetch('/api/simulation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })
            .then(response => response.json())
            .then(data => {
                if (data.task_id) {
                    // --- 4. Start Polling for Progress ---
                    startPolling(data.task_id);
                } else {
                    throw new Error(data.message || 'Failed to start simulation task.');
                }
            })
            .catch(error => {
                displayError(error.message);
            });
        });
    }

    function startPolling(taskId) {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }

        pollingInterval = setInterval(() => {
            fetch(`/api/simulation/progress/${taskId}`)
                .then(response => response.json())
                .then(progressData => {
                    if (progressData.status === 'running' || progressData.status === 'complete') {
                        // Update the progress bar
                        const progress = progressData.progress || 0;
                        progressBar.style.width = `${progress}%`;
                        progressBar.setAttribute('aria-valuenow', progress);
                        progressBar.textContent = `${progress}%`; // Optional: show text on bar

                        if (progressData.status === 'complete') {
                            // --- 5. Task is Done: Stop polling and get results ---
                            clearInterval(pollingInterval);
                            pollingInterval = null;
                            fetchResults(taskId);
                        }
                    } else if (progressData.status === 'error') {
                        // --- Handle errors reported by the backend ---
                        clearInterval(pollingInterval);
                        pollingInterval = null;
                        displayError(progressData.error || 'An unknown error occurred during simulation.');
                    } else if (progressData.status === 'unknown') {
                        // Still waiting for the task to be picked up, do nothing.
                    }
                })
                .catch(error => {
                    // Handle network errors during polling
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    displayError('Error checking simulation status: ' + error.message);
                });
        }, 3000); // Poll every 3 seconds
    }

    function fetchResults(taskId) {
        fetch(`/api/simulation/results/${taskId}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { 
                        throw new Error(err.details || err.message || `Server responded with status ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(results => {
                // --- 6. Display Final Results ---
                loadingDiv.style.display = 'none';
                messagesDiv.innerHTML = '<p class="success">Simulation completed successfully!</p>';
                renderResults(results);
            })
            .catch(error => {
                displayError(error.message);
            });
    }
    
    function displayError(errorMessage) {
        loadingDiv.style.display = 'none';
        messagesDiv.innerHTML = `<p class="error"><strong>Error:</strong> ${errorMessage}</p>`;
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }

    function renderResults(results) {
        let html = '<h3>Overall Summary</h3>';
        html += `<ul>`;
        html += `<li><strong>Hands Played:</strong> ${results.total_hands_played}</li>`;
        html += `<li><strong>Duration (seconds):</strong> ${results.simulation_duration_seconds.toFixed(4)}</li>`;
        html += `</ul>`;

        html += '<h3>Player Statistics</h3>';
        html += '<table id="results-table">';
        html += `
            <thead>
                <tr>
                    <th>Player</th>
                    <th>Final Bankroll</th>
                    <th>Net Gain/Loss</th>
                    <th>Hands Played</th>
                    <th>Avg. Bet</th>
                    <th>House Edge (%)</th>
                </tr>
            </thead>
        `;
        html += '<tbody>';

        for (const [playerName, stats] of Object.entries(results.players)) {
            html += `
                <tr>
                    <td>${playerName}</td>
                    <td>${stats["Final Bankroll"].toFixed(2)}</td>
                    <td>${stats["Net Gain/Loss"].toFixed(2)}</td>
                    <td>${stats["Hands Played"]}</td>
                    <td>${stats["Average Bet"].toFixed(2)}</td>
                    <td>${stats["House Edge (%)"].toFixed(4)}</td>
                </tr>
            `;
        }

        html += '</tbody></table>';
        resultsOutput.innerHTML = html;
    }

});
