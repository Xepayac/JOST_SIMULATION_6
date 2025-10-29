
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    bankroll = db.Column(db.Integer, nullable=False, default=1000)
    is_default = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {'name': self.name, 'bankroll': self.bankroll}

class Casino(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    deck_count = db.Column(db.Integer, nullable=False)
    dealer_stands_on_soft_17 = db.Column(db.Boolean, nullable=False)
    blackjack_payout = db.Column(db.Float, nullable=False)
    allow_late_surrender = db.Column(db.Boolean, nullable=False)
    allow_early_surrender = db.Column(db.Boolean, nullable=False)
    allow_resplit_to_hands = db.Column(db.Integer, nullable=False)
    allow_double_after_split = db.Column(db.Boolean, nullable=False)
    allow_double_on_any_two = db.Column(db.Boolean, nullable=False)
    reshuffle_penetration = db.Column(db.Float, nullable=False)
    offer_insurance = db.Column(db.Boolean, nullable=False)
    dealer_checks_for_blackjack = db.Column(db.Boolean, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        # No changes needed here, the engine expects the nested 'rules'
        return {
            'name': self.name,
            'rules': {
                'deck_count': self.deck_count,
                'dealer_stands_on_soft_17': self.dealer_stands_on_soft_17,
                'blackjack_payout': self.blackjack_payout,
                'allow_late_surrender': self.allow_late_surrender,
                'allow_early_surrender': self.allow_early_surrender,
                'allow_resplit_to_hands': self.allow_resplit_to_hands,
                'allow_double_after_split': self.allow_double_after_split,
                'allow_double_on_any_two': self.allow_double_on_any_two,
                'reshuffle_penetration': self.reshuffle_penetration,
                'offer_insurance': self.offer_insurance,
                'dealer_checks_for_blackjack': self.dealer_checks_for_blackjack
            }
        }

class BettingStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    min_bet = db.Column(db.Integer, nullable=False)
    bet_ramp = db.Column(db.Text, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        # --- CORRECTED to use 'min_bet' key ---
        return {
            'name': self.name,
            'min_bet': self.min_bet,
            'bet_ramp': json.loads(self.bet_ramp)
        }

class PlayingStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    hard_total_actions = db.Column(db.Text, nullable=False)
    soft_total_actions = db.Column(db.Text, nullable=False)
    pair_splitting_actions = db.Column(db.Text, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        # --- CORRECTED to return only the strategy dict, name is handled separately ---
        return {
            'hard': json.loads(self.hard_total_actions),
            'soft': json.loads(self.soft_total_actions),
            'pairs': json.loads(self.pair_splitting_actions)
        }

class Simulation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    
    playing_strategy_id = db.Column(db.Integer, db.ForeignKey('playing_strategy.id'), nullable=True)
    playing_strategy = db.relationship('PlayingStrategy', backref='simulations')

    betting_strategy_id = db.Column(db.Integer, db.ForeignKey('betting_strategy.id'), nullable=True)
    betting_strategy = db.relationship('BettingStrategy', backref='simulations')

    notes = db.Column(db.Text, nullable=True)
    iterations = db.Column(db.Integer, nullable=False, default=100)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    player = db.relationship('Player', backref='simulations')
    
    casino_id = db.Column(db.Integer, db.ForeignKey('casino.id'), nullable=True)
    casino = db.relationship('Casino', backref='simulations')
    
    task_id = db.Column(db.String(155), nullable=True)
    results = db.relationship('Result', backref='simulation', cascade='all, delete-orphan', lazy=True)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    simulation_id = db.Column(db.Integer, db.ForeignKey('simulation.id'), nullable=False)
    player_name = db.Column(db.String(100), nullable=False)
    casino_name = db.Column(db.String(100), nullable=False)
    
    strategy = db.Column(db.String(100), nullable=True)
    betting_strategy_name = db.Column(db.String(100), nullable=True)

    starting_bankroll = db.Column(db.Integer, nullable=False)
    iterations = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    outcomes = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # --- FEATURE: Add hand_history field ---
    hand_history = db.Column(db.Text, nullable=True)
