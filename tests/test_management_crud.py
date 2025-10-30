import json
from flask import url_for
from blackjack_simulator.models import Player, Casino, BettingStrategy, PlayingStrategy

def test_create_player(client):
    """
    GIVEN a test client
    WHEN a new player is created via the form (POST)
    THEN check that the new player appears in the player list
    """
    response = client.get(url_for('management.create_player'))
    assert response.status_code == 200

    response = client.post(url_for('management.create_player'), data={
        'name': 'Test Player',
        'bankroll': 5000
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Player created successfully!" in response.data
    assert b"Test Player" in response.data

def test_edit_player(client):
    """
    GIVEN a test client
    WHEN an existing player is edited
    THEN check that the updated information appears in the list
    """
    client.post(url_for('management.create_player'), data={'name': 'PlayerToEdit', 'bankroll': 100}, follow_redirects=True)
    player = Player.query.filter_by(name='PlayerToEdit').first()
    assert player is not None

    response = client.post(url_for('management.edit_player', player_id=player.id), data={
        'name': 'Updated Player',
        'bankroll': 999
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Player updated successfully!" in response.data
    assert b"Updated Player" in response.data
    assert b"999" in response.data
    assert b"PlayerToEdit" not in response.data

def test_delete_player(client):
    """
    GIVEN a test client
    WHEN an existing player is deleted
    THEN check that the player is removed from the list
    """
    client.post(url_for('management.create_player'), data={'name': 'PlayerToDelete', 'bankroll': 100}, follow_redirects=True)
    player = Player.query.filter_by(name='PlayerToDelete').first()
    assert player is not None
    
    response = client.get(url_for('management.list_players'))
    assert b"PlayerToDelete" in response.data
    
    response = client.post(url_for('management.delete_player', player_id=player.id), follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Player deleted successfully!" in response.data
    assert b"PlayerToDelete" not in response.data

def test_default_player_protection(client):
    """
    GIVEN a test client
    WHEN an attempt is made to edit or delete the default player
    THEN check that the action is blocked and a message is flashed
    """
    response = client.get(url_for('management.edit_player', player_id=1), follow_redirects=True)
    assert response.status_code == 200
    assert b"The default player profile cannot be edited." in response.data

    response = client.post(url_for('management.delete_player', player_id=1), follow_redirects=True)
    assert response.status_code == 200
    assert b"The default player profile cannot be deleted." in response.data
    
    assert b"Master Player" in response.data

def test_create_casino(client):
    """
    GIVEN a test client
    WHEN a new casino is created via the form (POST)
    THEN check that the new casino appears in the casino list
    """
    response = client.get(url_for('management.create_casino'))
    assert response.status_code == 200

    response = client.post(url_for('management.create_casino'), data={
        'name': 'Test Casino',
        'deck_count': 6,
        'dealer_stands_on_soft_17': True,
        'blackjack_payout': 1.5,
        'allow_late_surrender': False,
        'allow_early_surrender': False,
        'allow_resplit_to_hands': 4,
        'allow_double_after_split': True,
        'allow_double_on_any_two': True,
        'reshuffle_penetration': 0.75,
        'offer_insurance': True,
        'dealer_checks_for_blackjack': True
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Casino created successfully!" in response.data
    assert b"Test Casino" in response.data

def test_edit_casino(client):
    """
    GIVEN a test client
    WHEN an existing casino is edited
    THEN check that the updated information appears in the list
    """
    client.post(url_for('management.create_casino'), data={
        'name': 'CasinoToEdit',
        'deck_count': 4,
        'dealer_stands_on_soft_17': True,
        'blackjack_payout': 1.5,
        'allow_late_surrender': True,
        'allow_early_surrender': False,
        'allow_resplit_to_hands': 2,
        'allow_double_after_split': False,
        'allow_double_on_any_two': False,
        'reshuffle_penetration': 0.5,
        'offer_insurance': False,
        'dealer_checks_for_blackjack': True
    }, follow_redirects=True)
    casino = Casino.query.filter_by(name='CasinoToEdit').first()
    assert casino is not None

    response = client.post(url_for('management.edit_casino', casino_id=casino.id), data={
        'name': 'Updated Casino',
        'deck_count': 8,
        'dealer_stands_on_soft_17': False,
        'blackjack_payout': 1.2,
        'allow_late_surrender': False,
        'allow_early_surrender': True,
        'allow_resplit_to_hands': 3,
        'allow_double_after_split': True,
        'allow_double_on_any_two': True,
        'reshuffle_penetration': 0.9,
        'offer_insurance': True,
        'dealer_checks_for_blackjack': False
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Casino updated successfully!" in response.data
    assert b"Updated Casino" in response.data
    assert b"8" in response.data
    assert b"CasinoToEdit" not in response.data

def test_delete_casino(client):
    """
    GIVEN a test client
    WHEN an existing casino is deleted
    THEN check that the casino is removed from the list
    """
    client.post(url_for('management.create_casino'), data={
        'name': 'CasinoToDelete',
        'deck_count': 6,
        'dealer_stands_on_soft_17': True,
        'blackjack_payout': 1.5,
        'allow_late_surrender': False,
        'allow_early_surrender': False,
        'allow_resplit_to_hands': 4,
        'allow_double_after_split': True,
        'allow_double_on_any_two': True,
        'reshuffle_penetration': 0.75,
        'offer_insurance': True,
        'dealer_checks_for_blackjack': True
    }, follow_redirects=True)
    casino = Casino.query.filter_by(name='CasinoToDelete').first()
    assert casino is not None

    response = client.get(url_for('management.list_casinos'))
    assert b"CasinoToDelete" in response.data
    
    response = client.post(url_for('management.delete_casino', casino_id=casino.id), follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Casino deleted successfully!" in response.data
    assert b"CasinoToDelete" not in response.data

def test_default_casino_protection(client):
    """
    GIVEN a test client
    WHEN an attempt is made to edit or delete the default casino
    THEN check that the action is blocked and a message is flashed
    """
    response = client.get(url_for('management.edit_casino', casino_id=1), follow_redirects=True)
    assert response.status_code == 200
    assert b"The default casino profile cannot be edited." in response.data

    response = client.post(url_for('management.delete_casino', casino_id=1), follow_redirects=True)
    assert response.status_code == 200
    assert b"The default casino profile cannot be deleted." in response.data
    
    assert b"Master Casino" in response.data

def test_create_betting_strategy(client):
    """
    GIVEN a test client
    WHEN a new betting strategy is created
    THEN check that it appears in the list
    """
    response = client.get(url_for('management.create_betting_strategy'))
    assert response.status_code == 200

    response = client.post(url_for('management.create_betting_strategy'), data={
        'name': 'Test Betting Strategy',
        'min_bet': 10,
        'bet_ramp': '{"1": 1, "2": 2}'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Betting strategy created successfully!" in response.data
    assert b"Test Betting Strategy" in response.data

def test_edit_betting_strategy(client):
    """
    GIVEN a test client
    WHEN a betting strategy is edited
    THEN check that the updated info appears in the list
    """
    client.post(url_for('management.create_betting_strategy'), data={'name': 'BettingToEdit', 'min_bet': 5, 'bet_ramp': '{"1": 1}'}, follow_redirects=True)
    strategy = BettingStrategy.query.filter_by(name='BettingToEdit').first()
    assert strategy is not None

    response = client.post(url_for('management.edit_betting_strategy', strategy_id=strategy.id), data={
        'name': 'Updated Betting Strategy',
        'min_bet': 20,
        'bet_ramp': '{"1": 10, "2": 20}'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Betting strategy updated successfully!" in response.data
    assert b"Updated Betting Strategy" in response.data
    assert b"BettingToEdit" not in response.data

def test_delete_betting_strategy(client):
    """
    GIVEN a test client
    WHEN a betting strategy is deleted
    THEN check that it is removed from the list
    """
    client.post(url_for('management.create_betting_strategy'), data={'name': 'BettingToDelete', 'min_bet': 5, 'bet_ramp': '{"1": 1}'}, follow_redirects=True)
    strategy = BettingStrategy.query.filter_by(name='BettingToDelete').first()
    assert strategy is not None

    response = client.get(url_for('management.list_betting_strategies'))
    assert b"BettingToDelete" in response.data

    response = client.post(url_for('management.delete_betting_strategy', strategy_id=strategy.id), follow_redirects=True)

    assert response.status_code == 200
    assert b"Betting strategy deleted successfully!" in response.data
    assert b"BettingToDelete" not in response.data

def test_default_betting_strategy_protection(client):
    """
    GIVEN a test client
    WHEN an attempt is made to edit or delete the default betting strategy
    THEN check that the action is blocked
    """
    response = client.get(url_for('management.edit_betting_strategy', strategy_id=1), follow_redirects=True)
    assert response.status_code == 200
    assert b"The default betting strategy cannot be edited." in response.data

    response = client.post(url_for('management.delete_betting_strategy', strategy_id=1), follow_redirects=True)
    assert response.status_code == 200
    assert b"The default betting strategy cannot be deleted." in response.data

    assert b"Master Betting Strategy" in response.data

def test_create_playing_strategy(client):
    response = client.get(url_for('management.create_playing_strategy'))
    assert response.status_code == 200
    
    master_strategy = json.loads(PlayingStrategy.query.get(1).hard_total_actions)

    post_data = {
        'name': 'Test Playing Strategy',
        'description': 'A test strategy'
    }
    for player_total, dealer_cards in master_strategy.items():
        for dealer_card, action in dealer_cards.items():
            post_data[f'hard_{player_total}_{dealer_card}'] = action

    response = client.post(url_for('management.create_playing_strategy'), data=post_data, follow_redirects=True)

    assert response.status_code == 200
    assert b"Playing strategy created successfully!" in response.data
    assert b"Test Playing Strategy" in response.data

def test_edit_playing_strategy(client):
    client.get(url_for('management.create_playing_strategy'))
    master_strategy = json.loads(PlayingStrategy.query.get(1).hard_total_actions)

    post_data = {
        'name': 'PlayingToEdit',
        'description': 'A test strategy'
    }
    for player_total, dealer_cards in master_strategy.items():
        for dealer_card, action in dealer_cards.items():
            post_data[f'hard_{player_total}_{dealer_card}'] = action
    client.post(url_for('management.create_playing_strategy'), data=post_data, follow_redirects=True)

    strategy = PlayingStrategy.query.filter_by(name='PlayingToEdit').first()
    assert strategy is not None

    edit_data = {
        'name': 'Updated Playing Strategy',
        'description': 'An updated strategy'
    }
    for player_total, dealer_cards in master_strategy.items():
        for dealer_card, action in dealer_cards.items():
            edit_data[f'hard_{player_total}_{dealer_card}'] = 'S' # Change all actions to Stand

    response = client.post(url_for('management.edit_playing_strategy', strategy_id=strategy.id), data=edit_data, follow_redirects=True)

    assert response.status_code == 200
    assert b"Playing strategy updated successfully!" in response.data
    assert b"Updated Playing Strategy" in response.data
    assert b"PlayingToEdit" not in response.data

def test_delete_playing_strategy(client):
    client.get(url_for('management.create_playing_strategy'))
    master_strategy = json.loads(PlayingStrategy.query.get(1).hard_total_actions)

    post_data = {
        'name': 'PlayingToDelete',
        'description': 'A test strategy'
    }
    for player_total, dealer_cards in master_strategy.items():
        for dealer_card, action in dealer_cards.items():
            post_data[f'hard_{player_total}_{dealer_card}'] = action
    client.post(url_for('management.create_playing_strategy'), data=post_data, follow_redirects=True)

    strategy = PlayingStrategy.query.filter_by(name='PlayingToDelete').first()
    assert strategy is not None

    response = client.get(url_for('management.list_playing_strategies'))
    assert b"PlayingToDelete" in response.data

    response = client.post(url_for('management.delete_playing_strategy', strategy_id=strategy.id), follow_redirects=True)

    assert response.status_code == 200
    assert b"Playing strategy deleted successfully!" in response.data
    assert b"PlayingToDelete" not in response.data

def test_default_playing_strategy_protection(client):
    response = client.get(url_for('management.edit_playing_strategy', strategy_id=1), follow_redirects=True)
    assert response.status_code == 200
    assert b"The default playing strategy cannot be edited." in response.data

    response = client.post(url_for('management.delete_playing_strategy', strategy_id=1), follow_redirects=True)
    assert response.status_code == 200
    assert b"The default playing strategy cannot be deleted." in response.data

    assert b"master_playing_strategy" in response.data
