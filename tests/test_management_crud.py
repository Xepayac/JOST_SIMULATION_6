from flask import url_for
from blackjack_simulator.models import Player

def test_create_player(client):
    """
    GIVEN a test client
    WHEN a new player is created via the form (POST)
    THEN check that the new player appears in the player list
    """
    # GET the create page to make sure it loads
    response = client.get(url_for('management.create_player'))
    assert response.status_code == 200

    # POST to create a new player
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
    # First, create a player to edit
    client.post(url_for('management.create_player'), data={'name': 'PlayerToEdit', 'bankroll': 100})

    # Player should have id=2 (since default is 1)
    response = client.post(url_for('management.edit_player', player_id=2), data={
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
    # Create a player to delete
    client.post(url_for('management.create_player'), data={'name': 'PlayerToDelete', 'bankroll': 100})
    
    # Check it was created
    response = client.get(url_for('management.list_players'))
    assert b"PlayerToDelete" in response.data
    
    # Delete the player (id=2)
    response = client.post(url_for('management.delete_player', player_id=2), follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Player deleted successfully!" in response.data
    assert b"PlayerToDelete" not in response.data

def test_default_player_protection(client):
    """
    GIVEN a test client
    WHEN an attempt is made to edit or delete the default player
    THEN check that the action is blocked and a message is flashed
    """
    # Attempt to edit default player (id=1)
    response = client.get(url_for('management.edit_player', player_id=1), follow_redirects=True)
    assert response.status_code == 200
    assert b"The default player profile cannot be edited." in response.data

    # Attempt to delete default player (id=1)
    response = client.post(url_for('management.delete_player', player_id=1), follow_redirects=True)
    assert response.status_code == 200
    assert b"The default player profile cannot be deleted." in response.data
    
    # Verify the default player still exists
    assert b"Master Player" in response.data
