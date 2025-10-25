
import sys
import os
import argparse
import json
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from frontend.blackjack_simulator.celery_worker import run_jost_simulation_task, celery

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/simulations.db'
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379/0',
    CELERY_RESULT_BACKEND='redis://localhost:6379/0'
)
app.config['SECRET_KEY'] = 'a_secret_key'
db = SQLAlchemy(app)

# --- Database Models ---

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    bankroll = db.Column(db.Integer, nullable=False, default=1000)
    is_default = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'bankroll': self.bankroll, 'is_default': self.is_default}

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
        return {
            'id': self.id,
            'name': self.name, 
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

class BettingStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    min_bet = db.Column(db.Integer, nullable=False)
    bet_ramp = db.Column(db.Text, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'min_bet': self.min_bet,
            'bet_ramp': json.loads(self.bet_ramp),
            'is_default': self.is_default
        }

class Simulation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    strategy = db.Column(db.String(100), nullable=True)
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

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    simulation_id = db.Column(db.Integer, db.ForeignKey('simulation.id'), nullable=False)
    simulation = db.relationship('Simulation', backref='results')
    player_name = db.Column(db.String(100), nullable=False)
    casino_name = db.Column(db.String(100), nullable=False)
    strategy = db.Column(db.String(100), nullable=True)
    betting_strategy_name = db.Column(db.String(100), nullable=True)
    starting_bankroll = db.Column(db.Integer, nullable=False)
    iterations = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    outcomes = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- Data Loading ---

def load_default_data():
    # Load Players
    player_file = os.path.join(basedir, '..', '..', 'backend', 'src', 'jost_engine', 'data', 'defaults', 'players', 'basic_strategy_player.json')
    with open(player_file, 'r') as f:
        player_data = json.load(f)
    if not Player.query.filter_by(name=player_data['name']).first():
        new_player = Player(
            name=player_data['name'],
            bankroll=player_data['bankroll'],
            is_default=True
        )
        db.session.add(new_player)

    # Load Casinos
    casino_file = os.path.join(basedir, '..', '..', 'backend', 'src', 'jost_engine', 'data', 'defaults', 'casinos', 'default_casino.json')
    with open(casino_file, 'r') as f:
        casino_data = json.load(f)
    if not Casino.query.filter_by(name=casino_data['name']).first():
        new_casino = Casino(
            name=casino_data['name'],
            deck_count=casino_data['deck_count'],
            dealer_stands_on_soft_17=casino_data['dealer_stands_on_soft_17'],
            blackjack_payout=casino_data['blackjack_payout'],
            allow_late_surrender=casino_data['allow_late_surrender'],
            allow_early_surrender=casino_data['allow_early_surrender'],
            allow_resplit_to_hands=casino_data['allow_resplit_to_hands'],
            allow_double_after_split=casino_data['allow_double_after_split'],
            allow_double_on_any_two=casino_data['allow_double_on_any_two'],
            reshuffle_penetration=casino_data['reshuffle_penetration'],
            offer_insurance=casino_data['offer_insurance'],
            dealer_checks_for_blackjack=casino_data['dealer_checks_for_blackjack'],
            is_default=True
        )
        db.session.add(new_casino)

    # Load Betting Strategies
    betting_strategy_file = os.path.join(basedir, '..', '..', 'backend', 'src', 'jost_engine', 'data', 'betting_strategies', 'flat_bet.json')
    with open(betting_strategy_file, 'r') as f:
        betting_strategy_data = json.load(f)
    if not BettingStrategy.query.filter_by(name=betting_strategy_data['name']).first():
        new_betting_strategy = BettingStrategy(
            name=betting_strategy_data['name'],
            min_bet=betting_strategy_data['min_bet'],
            bet_ramp=json.dumps(betting_strategy_data['bet_ramp']),
            is_default=True
        )
        db.session.add(new_betting_strategy)

    db.session.commit()

# --- Routes ---

@app.route('/')
def index():
    latest_simulation = Simulation.query.order_by(Simulation.timestamp.desc()).first()
    if latest_simulation:
        return redirect(url_for('run_simulation_page', simulation_id=latest_simulation.id))
    return redirect(url_for('simulations'))

@app.route('/simulations')
def simulations():
    simulations = Simulation.query.order_by(Simulation.timestamp.desc()).all()
    return render_template('simulations.html', simulations=simulations)

@app.route('/simulation/new', methods=['GET', 'POST'])
def new_simulation():
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for('simulations'))
        
        new_sim = Simulation(title=title)
        db.session.add(new_sim)
        db.session.commit()
        flash('Simulation created.', 'success')
        return redirect(url_for('run_simulation_page', simulation_id=new_sim.id))
    return render_template('new_simulation.html')

@app.route('/simulation/<int:simulation_id>/delete', methods=['POST'])
def delete_simulation(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    
    # Delete all results for this simulation
    Result.query.filter_by(simulation_id=simulation.id).delete()
    
    db.session.delete(simulation)
    db.session.commit()
    
    flash('Simulation deleted successfully.', 'success')
    return redirect(url_for('simulations'))

@app.route('/simulation/<int:simulation_id>/run', methods=['GET'])
def run_simulation_page(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    players = Player.query.all()
    casinos = Casino.query.all()
    strategies_dir = os.path.join(basedir, '..', '..', 'backend', 'src', 'jost_engine', 'data', 'strategies')
    strategy_files = [f for f in os.listdir(strategies_dir) if f.endswith('.json')]
    betting_strategies = BettingStrategy.query.all()
    
    return render_template('run_simulation.html', 
                           simulation=simulation,
                           players=players,
                           casinos=casinos,
                           strategies=strategy_files,
                           betting_strategies=betting_strategies)

@app.route('/simulation/<int:simulation_id>/run_action', methods=['POST'])
def run_simulation_action(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    
    # --- Update simulation from form data ---
    simulation.player_id = request.form.get('player_id')
    simulation.casino_id = request.form.get('casino_id')
    simulation.strategy = request.form.get('strategy')
    simulation.betting_strategy_id = request.form.get('betting_strategy_id')
    simulation.iterations = int(request.form.get('iterations', 100))
    simulation.notes = request.form.get('notes')
    
    # --- Validation ---
    if not all([simulation.player, simulation.casino, simulation.strategy, simulation.betting_strategy]):
        flash('Player, Casino, Playing Strategy, and Betting Strategy must all be selected.', 'error')
        return redirect(url_for('run_simulation_page', simulation_id=simulation.id))

    # --- Config for JOST Engine ---
    strategy_name = simulation.strategy.replace('.json', '')

    simulation_config = {
        "player": simulation.player.to_dict(),
        "casino": simulation.casino.to_dict(),
        "strategy": {"name": strategy_name},
        "betting_strategy": simulation.betting_strategy.to_dict(),
        "iterations": simulation.iterations
    }

    # --- Run Simulation Asynchronously ---
    task = run_jost_simulation_task.delay(simulation_config)
    
    # --- Save Task ID ---
    simulation.task_id = task.id
    db.session.commit()
    
    flash('Simulation started! You will be redirected to the results page when it is complete.', 'success')
    return redirect(url_for('simulation_status', simulation_id=simulation.id))

@app.route('/simulation/<int:simulation_id>/status')
def simulation_status(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    return render_template('simulation_status.html', simulation=simulation)

@app.route('/task_status/<task_id>')
def task_status(task_id):
    task = celery.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'status': 'Running...'
        }
        if task.state == 'SUCCESS':
            outcomes = task.get()
            simulation = Simulation.query.filter_by(task_id=task_id).first()
            if not simulation:
                return jsonify({'state': 'ERROR', 'status': 'Simulation not found for this task.'})
            if isinstance(outcomes, dict) and 'error' in outcomes:
                 response = {
                    'state': 'FAILURE',
                    'status': outcomes.get('error', 'Task failed with an unknown error.')
                }
            else:
                new_result = Result(
                    simulation_id=simulation.id,
                    player_name=simulation.player.name,
                    casino_name=simulation.casino.name,
                    strategy=simulation.strategy,
                    betting_strategy_name=simulation.betting_strategy.name,
                    starting_bankroll=simulation.player.bankroll,
                    iterations=simulation.iterations,
                    notes=simulation.notes,
                    outcomes=json.dumps(outcomes)
                )
                db.session.add(new_result)
                db.session.commit()
                
                result_url = url_for('result_page', result_id=new_result.id)
                response = {
                    'state': 'SUCCESS',
                    'status': 'Complete!',
                    'result_url': result_url
                }
    else: # FAILURE
        response = {
            'state': task.state,
            'status': str(task.info),
        }
    return jsonify(response)

@app.route('/results/<int:result_id>')
def result_page(result_id):
    result = Result.query.get_or_404(result_id)
    outcomes = json.loads(result.outcomes)
    
    is_new_format = isinstance(outcomes, list)
    
    return render_template('result_details.html', result=result, outcomes=outcomes, is_new_format=is_new_format)

@app.route('/results')
def results_list():
    results = Result.query.order_by(Result.timestamp.desc()).all()
    return render_template('results_list.html', results=results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Blackjack Simulator')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the web server on.')
    args = parser.parse_args()

    with app.app_context():
        db.create_all()
        load_default_data()
    app.run(debug=True, port=args.port)
