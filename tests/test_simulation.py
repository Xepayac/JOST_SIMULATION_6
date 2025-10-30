import pytest
from flask import url_for
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def setup_default_data(app):
    from blackjack_simulator.app import db
    from blackjack_simulator.models import Player, Casino, PlayingStrategy, BettingStrategy
    with app.app_context():
        # Clear any existing data
        db.drop_all()
        db.create_all()
        player = Player(name='default_player', bankroll=1000, is_default=True)
        casino = Casino(name='default_casino', is_default=True, deck_count=6, dealer_stands_on_soft_17=True, blackjack_payout=1.5, allow_late_surrender=True, allow_early_surrender=False, allow_resplit_to_hands=4, allow_double_after_split=True, allow_double_on_any_two=True, reshuffle_penetration=0.5, offer_insurance=True, dealer_checks_for_blackjack=True)
        playing_strategy = PlayingStrategy(name='basic_strategy', is_default=True, hard_total_actions='{}', soft_total_actions='{}', pair_splitting_actions='{}')
        betting_strategy = BettingStrategy(name='flat_bet', is_default=True, min_bet=10, bet_ramp='{}')
        db.session.add_all([player, casino, playing_strategy, betting_strategy])
        db.session.commit()

def test_run_simulation_get(client):
    """Tests that the new simulation page loads correctly."""
    response = client.get(url_for('main.new_simulation'))
    assert response.status_code == 200
    assert b'New Simulation' in response.data

def test_run_simulation_post(client, mock_celery_task):
    """
    Tests that submitting the simulation form triggers the Celery task
    and redirects to the status page.
    """
    from blackjack_simulator.models import Simulation, Player, Casino, PlayingStrategy, BettingStrategy
    from blackjack_simulator.app import db
    
    # The simulation is created on the setup page, so we need to get it
    new_sim = Simulation(title="Test Sim Post")
    db.session.add(new_sim)
    db.session.commit()

    form_data = {
        'player_id': Player.query.filter_by(name='default_player').first().id,
        'casino_id': Casino.query.filter_by(name='default_casino').first().id,
        'playing_strategy_id': PlayingStrategy.query.filter_by(name='basic_strategy').first().id,
        'betting_strategy_id': BettingStrategy.query.filter_by(name='flat_bet').first().id,
        'iterations': 100
    }
    response = client.post(url_for('main.run_simulation_action', simulation_id=new_sim.id), data=form_data, follow_redirects=False)

    mock_celery_task.assert_called_once()
    assert response.status_code == 302
    assert response.location == url_for('main.simulation_status', simulation_id=new_sim.id, _external=False)

def test_simulation_status_pending(client, monkeypatch):
    """
    Tests the simulation status page when the task is still pending.
    """
    from blackjack_simulator.models import Simulation
    from blackjack_simulator.app import db
    new_sim = Simulation(title="Test Sim Pending")
    db.session.add(new_sim)
    db.session.commit()

    mock_result = MagicMock()
    mock_result.state = 'PENDING'
    mock_result.info = {}
    monkeypatch.setattr('blackjack_simulator.celery_worker.celery.AsyncResult', lambda id: mock_result)
    response = client.get(url_for('main.simulation_status', simulation_id=new_sim.id))
    assert response.status_code == 200
    assert b"Simulation in Progress..." in response.data

def test_simulation_status_success(client, monkeypatch):
    """
    Tests the simulation status page when the task has succeeded.
    """
    from blackjack_simulator.models import Simulation, Player, Casino, PlayingStrategy, BettingStrategy
    from blackjack_simulator.app import db
    
    player = Player.query.first()
    casino = Casino.query.first()
    playing_strategy = PlayingStrategy.query.first()
    betting_strategy = BettingStrategy.query.first()

    new_sim = Simulation(
        title="Test Sim Success", 
        task_id="test_task_id",
        player_id=player.id,
        casino_id=casino.id,
        playing_strategy_id=playing_strategy.id,
        betting_strategy_id=betting_strategy.id,
        player=player,
        casino=casino,
        playing_strategy=playing_strategy,
        betting_strategy=betting_strategy
    )
    db.session.add(new_sim)
    db.session.commit()

    mock_result = MagicMock()
    mock_result.state = 'SUCCESS'
    mock_result.get.return_value = {
        "default_player": {
            "final_bankroll": 1200.0,
            "total_wagered": 5000.0,
            "player_edge": 0.04,
            "player_win_rate": 0.5,
            "net_gain_loss": 200.0,
            "hand_history": []
        }
    }
    monkeypatch.setattr('blackjack_simulator.routes.celery.AsyncResult', lambda id: mock_result)

    response = client.get(url_for('main.task_status', task_id=new_sim.task_id))
    assert response.status_code == 200
    json_response = response.get_json()
    assert json_response['state'] == 'SUCCESS'
    assert 'result_url' in json_response
