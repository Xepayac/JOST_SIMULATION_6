
import os
import json
import click
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask.cli import with_appcontext

from .models import db, Player, Casino, BettingStrategy
from .celery_worker import celery
from .config import Config

# --- Database Initialization Command ---
def init_db():
    db.create_all()
    # Add a default player if one does not exist
    if not Player.query.filter_by(name='Default Player').first():
        default_player = Player(name='Default Player', bankroll=10000, is_default=True)
        db.session.add(default_player)

    # Add a default casino if one does not exist
    if not Casino.query.filter_by(name='Default Casino').first():
        default_casino = Casino(
            name='Default Casino',
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
            dealer_checks_for_blackjack=True,
            is_default=True
        )
        db.session.add(default_casino)

    # Add a default betting strategy if one does not exist
    if not BettingStrategy.query.filter_by(name='Default Strategy').first():
        default_betting_strategy = BettingStrategy(
            name='Default Strategy',
            min_bet=10,
            bet_ramp=json.dumps({1: 1, 2: 2, 3: 3, 4: 4, 5: 5}),
            is_default=True
        )
        db.session.add(default_betting_strategy)

    db.session.commit()


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

# --- Application Factory ---
def create_app(config_class=Config):
    app = Flask(__name__)

    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    app.config.from_object(config_class)

    # --- Initialize Extensions ---
    db.init_app(app)
    # Update celery config
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND']
    )

    # --- Register Blueprints ---
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # --- Register Commands ---
    app.cli.add_command(init_db_command)

    # --- Configure Logging ---
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Blackjack Simulator startup')

    return app
