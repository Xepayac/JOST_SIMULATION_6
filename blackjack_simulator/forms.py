import json
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, BooleanField, FloatField, TextAreaField
from wtforms.validators import DataRequired, ValidationError

# Custom validator for Bet Ramp JSON field
def validate_json(form, field):
    try:
        data = json.loads(field.data)
        if not isinstance(data, dict):
            raise ValidationError('JSON must be a dictionary (object).')
        for key, value in data.items():
            if not isinstance(key, str) or not isinstance(value, (int, float)):
                raise ValidationError('JSON keys must be strings and values must be numbers.')
    except (json.JSONDecodeError, TypeError):
        raise ValidationError('Invalid JSON format. Please provide a valid JSON dictionary.')

class PlayerForm(FlaskForm):
    name = StringField('Player Name', validators=[DataRequired()])
    bankroll = IntegerField('Bankroll', validators=[DataRequired()])
    submit = SubmitField('Save')

class CasinoForm(FlaskForm):
    name = StringField('Casino Name', validators=[DataRequired()])
    deck_count = IntegerField('Deck Count', validators=[DataRequired()])
    dealer_stands_on_soft_17 = BooleanField('Dealer Stands on Soft 17')
    blackjack_payout = FloatField('Blackjack Payout', validators=[DataRequired()])
    allow_late_surrender = BooleanField('Allow Late Surrender')
    allow_early_surrender = BooleanField('Allow Early Surrender')
    allow_resplit_to_hands = IntegerField('Allow Resplit to Hands', validators=[DataRequired()])
    allow_double_after_split = BooleanField('Allow Double After Split')
    allow_double_on_any_two = BooleanField('Allow Double on Any Two')
    reshuffle_penetration = FloatField('Reshuffle Penetration (%)', validators=[DataRequired()])
    offer_insurance = BooleanField('Offer Insurance')
    dealer_checks_for_blackjack = BooleanField('Dealer Checks for Blackjack')
    submit = SubmitField('Save Casino')

class BettingStrategyForm(FlaskForm):
    name = StringField('Strategy Name', validators=[DataRequired()])
    min_bet = IntegerField('Minimum Bet', validators=[DataRequired()])
    bet_ramp = TextAreaField('Bet Ramp (JSON)', validators=[DataRequired(), validate_json])
    submit = SubmitField('Save Strategy')
