
import json
import pytest
from flask import url_for
from blackjack_simulator.models import db, Simulation, Result

@pytest.fixture
def simulation(client):
    """
    Fixture to create a new simulation record and return its instance.
    This simulates the first step of a user creating a new simulation entry.
    """
    client.post(url_for('main.new_simulation'), data={'title': 'Test Simulation'}, follow_redirects=True)
    return Simulation.query.filter_by(title='Test Simulation').first()

def test_new_simulation_page(client):
    """
    GIVEN a test client
    WHEN the /simulation/new page is requested (GET)
    THEN check that the page loads correctly.
    """
    response = client.get(url_for('main.new_simulation'))
    assert response.status_code == 200
    assert b"Create a New Simulation" in response.data

def test_new_simulation_action(client):
    """
    GIVEN a test client
    WHEN a new simulation is created (POST)
    THEN check that a new Simulation object is created and the user is redirected.
    """
    response = client.post(url_for('main.new_simulation'), data={'title': 'My New Sim'}, follow_redirects=True)
    assert response.status_code == 200
    sim = Simulation.query.filter_by(title='My New Sim').first()
    assert sim is not None
    assert sim.title == 'My New Sim'

def test_run_simulation_page(client, simulation):
    """
    GIVEN a test client and an existing simulation
    WHEN the run page for that simulation is requested (GET)
    THEN check that the configuration page loads correctly.
    """
    assert simulation is not None
    response = client.get(url_for('main.run_simulation_page', simulation_id=simulation.id))
    assert response.status_code == 200
    assert bytes(simulation.title, 'utf-8') in response.data

def test_run_simulation_action(client, simulation, mocker):
    """
    GIVEN a test client and an existing simulation
    WHEN the simulation is executed (POST)
    THEN check that a Celery task is dispatched and the user is redirected.
    """
    mock_send_task = mocker.patch('blackjack_simulator.celery_worker.celery.send_task')
    mock_send_task.return_value.id = 'test-task-id'
    
    post_data = {
        'player_id': 1,
        'casino_id': 1,
        'playing_strategy_id': 1,
        'betting_strategy_id': 1,
        'iterations': 500
    }
    response = client.post(url_for('main.run_simulation_action', simulation_id=simulation.id), data=post_data)

    mock_send_task.assert_called_once()
    assert response.status_code == 302
    # The location header gives a relative path, but url_for might give an absolute path
    # depending on the context. Check that the relative path is part of the absolute URL.
    assert response.location in url_for('main.simulation_status', simulation_id=simulation.id, _external=True)

def test_result_page(client):
    """
    GIVEN a test client
    WHEN a result page is requested
    THEN check that the page loads correctly with the result details.
    """
    sim = Simulation.query.first()
    if not sim:
        client.post(url_for('main.new_simulation'), data={'title': 'Sim for Result'}, follow_redirects=True)
        sim = Simulation.query.first()

    outcomes_data = {"final_bankroll": 1100, "net_gain_loss": 100, "total_wagered": 5000, "player_edge": 0.02}
    result = Result(
        simulation_id=sim.id,
        player_name="Test Player",
        casino_name="Test Casino",
        strategy="Test Strategy",
        betting_strategy_name="Test Betting Strategy",
        starting_bankroll=1000,
        iterations=100,
        outcomes=json.dumps(outcomes_data)
    )
    db.session.add(result)
    db.session.commit()

    response = client.get(url_for('main.result_page', result_id=result.id))
    assert response.status_code == 200
    assert b"Results for" in response.data
    assert b"1100" in response.data
