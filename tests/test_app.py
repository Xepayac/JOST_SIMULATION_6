import json
from unittest.mock import patch, mock_open
from flask import url_for
import pytest

# Test for the main index page, which should redirect
def test_home_page(client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET)
    THEN check the response is a valid redirect to the new simulation page.
    """
    response = client.get(url_for('main.index'))
    assert response.status_code == 302
    assert response.location == url_for('main.new_simulation', _external=False)

# Test that all the main navigation routes load successfully.
def test_main_routes_load_successfully(client):
    """
    Tests that all main navigation routes load with a 200 OK status.
    This ensures all primary pages are accessible.
    """
    routenames = [
        'main.new_simulation',
        'main.simulations',
        'main.results_list',
    ]
    for route_name in routenames:
        response = client.get(url_for(route_name))
        assert response.status_code == 200, f"Route {route_name} failed to load."

# Test for the result details page with a successful load
def test_result_details_page_success(client):
    """
    Tests that the result details page loads correctly with mocked data.
    This verifies that a completed simulation's results are displayed correctly.
    """
    from blackjack_simulator.models import Simulation, Result
    from blackjack_simulator.app import db
    new_sim = Simulation(title="Test Sim")
    db.session.add(new_sim)
    db.session.commit()
    new_result = Result(
        simulation_id=new_sim.id,
        player_name="Test Player",
        casino_name="Test Casino",
        starting_bankroll=1000,
        iterations=100,
        outcomes=json.dumps({
            'final_bankroll': 1200.0,
            'net_gain_loss': 200.0,
            'total_wagered': 5000.0,
            'player_edge': 0.04,
            'player_win_rate': 0.5
        })
    )
    db.session.add(new_result)
    db.session.commit()

    response = client.get(url_for('main.result_page', result_id=new_result.id))
    assert response.status_code == 200
    assert b"Results for" in response.data

# Test for the result details page when the result file is not found
def test_result_details_page_not_found(client):
    """
    Tests that the result details page returns a 404 error if the
    simulation result file does not exist.
    """
    response = client.get(url_for('main.result_page', result_id=999))
    assert response.status_code == 404
