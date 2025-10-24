$(document).ready(function() {
    // Initialize DataTable
    var table = $('#historyTable').DataTable({
        "processing": true,
        "serverSide": false, 
        "ajax": {
            "url": "/api/history",
            "type": "GET",
            "dataSrc": ""
        },
        "columns": [
            { "data": "id", "width": "15%" },
            { "data": "date" },
            { "data": "player_name" },
            { "data": "playing_strategy" },
            { "data": "betting_strategy" },
            { "data": "initial_bankroll" },
            { "data": "rounds_played" },
            { "data": "final_bankroll" },
            { "data": "net_gain_loss" },
            { "data": "outcome" },
            {
                "data": null,
                "defaultContent": '<button class="btn btn-primary btn-sm view-btn" data-bs-toggle="modal" data-bs-target="#resultsModal">View</button> <button class="btn btn-danger btn-sm delete-btn">Delete</button>',
                "orderable": false
            }
        ],
        "order": [[1, 'desc']] // Order by date descending
    });

    // Handle view button click
    $('#historyTable tbody').on('click', '.view-btn', function () {
        var data = table.row($(this).parents('tr')).data();
        var simulationId = data.id;

        $('#resultsModalLabel').text('Results for Simulation ' + simulationId);
        $('#resultsJson').text('Loading...');

        $.ajax({
            url: '/api/history/' + simulationId,
            type: 'GET',
            success: function(response) {
                $('#resultsJson').text(JSON.stringify(response, null, 2));
                // If using a syntax highlighter like Prism, you might need to re-highlight
                // Prism.highlightAll();
            },
            error: function(xhr, status, error) {
                $('#resultsJson').text('Error loading results: ' + xhr.responseText);
            }
        });
    });

    // Handle delete button click
    $('#historyTable tbody').on('click', '.delete-btn', function () {
        var data = table.row($(this).parents('tr')).data();
        var simulationId = data.id;

        if (confirm('Are you sure you want to delete simulation ' + simulationId + '?')) {
            $.ajax({
                url: '/api/history/' + simulationId,
                type: 'DELETE',
                success: function(result) {
                    table.ajax.reload(); // Reload table data
                },
                error: function(xhr, status, error) {
                    alert('Error deleting simulation: ' + xhr.responseText);
                }
            });
        }
    });

    // Handle delete all button click
    $('#delete-all-btn').on('click', function() {
        if (confirm('Are you sure you want to delete all simulation history? This action cannot be undone.')) {
            $.ajax({
                url: '/api/history',
                type: 'DELETE',
                success: function(result) {
                    table.ajax.reload();
                },
                error: function(xhr, status, error) {
                    alert('Error deleting all simulations: ' + xhr.responseText);
                }
            });
        }
    });
});
