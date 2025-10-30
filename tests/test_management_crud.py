import pytest
from unittest.mock import patch, mock_open
from flask import url_for

from blackjack_simulator.models import db, Casino

@pytest.fixture
def mock_file_io(monkeypatch):
    """Fixture to mock file I/O operations for management commands."""
    m_open = mock_open()
    m_exists = patch('os.path.exists', return_value=False)
    m_remove = patch('os.remove')
    
    monkeypatch.setattr('builtins.open', m_open)
    monkeypatch.setattr('os.path.exists', m_exists)
    monkeypatch.setattr('os.remove', m_remove)
    
    return m_open, m_exists, m_remove

class TestCasinoCRUD:

    def test_create_casino(self, client, mock_file_io):
        mock_file, mock_exists, _ = mock_file_io
        mock_exists.return_value = False
        
        form_data = {
            'name': 'test_casino',
            'deck_count': 6,
            'dealer_stands_on_soft_17': True,
            'blackjack_payout': 1.5,
            'allow_late_surrender': True,
            'allow_early_surrender': False,
            'allow_resplit_to_hands': 4,
            'allow_double_after_split': True,
            'allow_double_on_any_two': True,
            'reshuffle_penetration': 0.5,
            'offer_insurance': True,
            'dealer_checks_for_blackjack': True
        }
        response = client.post(url_for('management.create_casino'), data=form_data, follow_redirects=True)
        assert response.status_code == 200

    def test_delete_casino(self, client, mock_file_io):
        _, mock_exists, mock_remove = mock_file_io
        mock_exists.return_value = True
        
        new_casino = Casino(
            name="test_casino_to_delete", 
            deck_count=6, 
            dealer_stands_on_soft_17=True, 
            blackjack_payout=1.5, 
            allow_late_surrender=True, 
            allow_early_surrender=False, 
            allow_resplit_to_hands=4, 
            allow_double_after_split=True, 
            allow_double_on_any_two=True, 
            reshuffle_penetration=0.5, 
            offer_insurance=True, 
            dealer_checks_for_blackjack=True
        )
        db.session.add(new_casino)
        db.session.commit()

        response = client.post(url_for('management.delete_casino', casino_id=new_casino.id), follow_redirects=True)
        assert response.status_code == 200
