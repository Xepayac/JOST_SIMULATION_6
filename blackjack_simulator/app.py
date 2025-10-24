
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from blackjack_simulator.jost_engine import run_jost_simulation

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'simulations.db')
app.config['SECRET_KEY'] = 'a_secret_key'
db = SQLAlchemy(app)

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
            'dealer_checks_for_blackjack': self.dealer_checks_for_blackjack, 
            'is_default': self.is_default
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

def load_default_players():
    players_dir = os.path.join(basedir, '..', 'JOST_ENGINE_5', 'src', 'jost_engine', 'data', 'defaults', 'players')
    if not os.path.exists(players_dir):
        return
    
    players_to_exclude = ["Insurance Tester", "Surrender Tester"]

    for player_name in players_to_exclude:
        existing_player = Player.query.filter_by(name=player_name).first()
        if existing_player:
            db.session.delete(existing_player)

    for filename in os.listdir(players_dir):
        if filename.endswith('.json'):
            with open(os.path.join(players_dir, filename)) as f:
                try:
                    player_data = json.load(f)
                    if not player_data or player_data.get('name') in players_to_exclude:
                        continue

                    existing_player = Player.query.filter_by(name=player_data['name']).first()
                    if not existing_player:
                        new_player = Player(name=player_data['name'], bankroll=player_data['bankroll'], is_default=True)
                        db.session.add(new_player)
                    else:
                        existing_player.bankroll = player_data['bankroll']
                        existing_player.is_default = True
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Warning: Could not process JSON from {filename}: {e}")

    db.session.commit()

def load_default_casinos():
    casinos_dir = os.path.join(basedir, '..', 'JOST_ENGINE_5', 'src', 'jost_engine', 'data', 'defaults', 'casinos')
    if not os.path.exists(casinos_dir):
        return

    for filename in os.listdir(casinos_dir):
        if filename.endswith('.json'):
            with open(os.path.join(casinos_dir, filename)) as f:
                try:
                    casino_data = json.load(f)
                    if not casino_data:
                        continue

                    existing_casino = Casino.query.filter_by(name=casino_data['name']).first()
                    if not existing_casino:
                        new_casino = Casino(**casino_data, is_default=True)
                        db.session.add(new_casino)
                    else:
                        for key, value in casino_data.items():
                            setattr(existing_casino, key, value)
                        existing_casino.is_default = True
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Warning: Could not process JSON from {filename}: {e}")

    db.session.commit()

def load_default_betting_strategies():
    betting_strategies_dir = os.path.join(basedir, 'data', 'betting_strategies')
    if not os.path.exists(betting_strategies_dir):
        return

    for filename in os.listdir(betting_strategies_dir):
        if filename.endswith('.json'):
            with open(os.path.join(betting_strategies_dir, filename)) as f:
                try:
                    strategy_data = json.load(f)
                    if not strategy_data:
                        continue

                    existing_strategy = BettingStrategy.query.filter_by(name=strategy_data['name']).first()
                    if not existing_strategy:
                        new_strategy = BettingStrategy(
                            name=strategy_data['name'], 
                            min_bet=strategy_data['min_bet'], 
                            bet_ramp=json.dumps(strategy_data['bet_ramp']), 
                            is_default=True
                        )
                        db.session.add(new_strategy)
                    else:
                        existing_strategy.min_bet = strategy_data['min_bet']
                        existing_strategy.bet_ramp = json.dumps(strategy_data['bet_ramp'])
                        existing_strategy.is_default = True
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Warning: Could not process JSON from {filename}: {e}")

    db.session.commit()


@app.route('/')
def index():
    latest_simulation = Simulation.query.order_by(Simulation.timestamp.desc()).first()
    if latest_simulation:
        return redirect(url_for('run_simulation_page', simulation_id=latest_simulation.id))
    return redirect(url_for('new_simulation'))

@app.route('/new_simulation', methods=['GET', 'POST'])
def new_simulation():
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for('new_simulation'))
        new_simulation = Simulation(title=title)
        db.session.add(new_simulation)
        db.session.commit()
        return redirect(url_for('run_simulation_page', simulation_id=new_simulation.id))
    return render_template('new_simulation.html')

@app.route('/simulations')
def simulations():
    sort_by = request.args.get('sort_by', 'timestamp')
    order = request.args.get('order', 'desc')
    order_by_clause = Simulation.title.asc() if order == 'asc' else Simulation.title.desc() if sort_by == 'name' else Simulation.timestamp.asc() if order == 'asc' else Simulation.timestamp.desc()
    simulations = Simulation.query.order_by(order_by_clause).all()
    return render_template('simulations.html', simulations=simulations)

@app.route('/simulation/<int:simulation_id>/run', methods=['GET', 'POST'])
def run_simulation_page(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for('run_simulation_page', simulation_id=simulation.id))
        simulation.title = title
        db.session.commit()
        flash('Simulation saved successfully!', 'success')
        return redirect(url_for('run_simulation_page', simulation_id=simulation.id))
    return render_template('run_simulation.html', simulation=simulation)

@app.route('/simulation/<int:simulation_id>/run_action', methods=['POST'])
def run_simulation_action(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    if not simulation.player:
        flash('Please choose a player before running the simulation.', 'error')
        return redirect(url_for('run_simulation_page', simulation_id=simulation.id))
    if not simulation.casino:
        flash('Please choose a casino before running the simulation.', 'error')
        return redirect(url_for('run_simulation_page', simulation_id=simulation.id))
    if not simulation.strategy:
        flash('Please choose a playing strategy before running the simulation.', 'error')
        return redirect(url_for('run_simulation_page', simulation_id=simulation.id))
    if not simulation.betting_strategy:
        flash('Please choose a betting strategy before running the simulation.', 'error')
        return redirect(url_for('run_simulation_page', simulation_id=simulation.id))
    
    iterations = request.form.get('iterations')
    if not iterations or not iterations.isdigit():
        flash('Iterations must be a valid number.', 'error')
        return redirect(url_for('run_simulation_page', simulation_id=simulation.id))

    simulation.iterations = int(iterations)
    simulation.notes = request.form.get('notes')
    db.session.commit()

    simulation_config = {
        "player": simulation.player.to_dict(),
        "casino": simulation.casino.to_dict(),
        "strategy": simulation.strategy,
        "betting_strategy": simulation.betting_strategy.to_dict(),
        "iterations": simulation.iterations
    }
    
    outcomes = run_jost_simulation(simulation_config)
    
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
    
    return redirect(url_for('result_page', result_id=new_result.id))

@app.route('/results')
def results_list():
    results = Result.query.order_by(Result.timestamp.desc()).all()
    return render_template('results_list.html', results=results)

@app.route('/result/<int:result_id>')
def result_page(result_id):
    result = Result.query.get_or_404(result_id)
    outcomes = json.loads(result.outcomes)
    return render_template('result_details.html', result=result, outcomes=outcomes)

@app.route('/delete_result/<int:result_id>', methods=['POST'])
def delete_result(result_id):
    result = Result.query.get_or_404(result_id)
    db.session.delete(result)
    db.session.commit()
    flash('Result deleted successfully!', 'success')
    return redirect(url_for('results_list'))

@app.route('/delete_simulation/<int:simulation_id>', methods=['POST'])
def delete_simulation(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    db.session.delete(simulation)
    db.session.commit()
    flash('Simulation deleted successfully!', 'success')
    return redirect(url_for('simulations'))

@app.route('/players')
def players():
    simulation_id = request.args.get('simulation_id', type=int)
    players = Player.query.all()
    return render_template('players.html', players=[p.to_dict() for p in players], simulation_id=simulation_id)

@app.route('/add_player', methods=['POST'])
def add_player():
    player_name = request.form.get('player_name')
    bankroll = request.form.get('bankroll', 1000, type=int)
    simulation_id = request.form.get('simulation_id', type=int)
    is_default_player_add = request.form.get('is_default', 'false').lower() == 'true'

    if player_name:
        existing_player = Player.query.filter_by(name=player_name).first()
        if not existing_player:
            new_player = Player(name=player_name, bankroll=bankroll, is_default=is_default_player_add)
            db.session.add(new_player)
            db.session.commit()
            player_id = new_player.id
        else:
            if existing_player.is_default:
                existing_player.bankroll = bankroll
                db.session.commit()
            player_id = existing_player.id
        
        if simulation_id:
            simulation = Simulation.query.get(simulation_id)
            if simulation:
                simulation.player_id = player_id
                db.session.commit()
                return redirect(url_for('run_simulation_page', simulation_id=simulation.id))

    return redirect(url_for('players', simulation_id=simulation_id))

@app.route('/delete_player/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    if player.is_default:
        flash('Default players cannot be deleted.', 'error')
        return redirect(url_for('players'))
    if player.simulations:
        flash('Cannot delete a player with existing simulations.', 'error')
    else:
        db.session.delete(player)
        db.session.commit()
        flash(f'Player {player.name} deleted successfully!', 'success')
    return redirect(url_for('players'))

@app.route('/edit_player/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    if player.is_default:
        flash('Default players cannot be edited.', 'error')
        return redirect(url_for('players'))
    if request.method == 'POST':
        player.name = request.form['name']
        player.bankroll = request.form['bankroll']
        db.session.commit()
        return redirect(url_for('players'))
    return render_template('edit_player.html', player=player)

@app.route('/casinos')
def casinos():
    simulation_.id = request.args.get('simulation_id', type=int)
    casinos = Casino.query.all()
    return render_template('casinos.html', casinos=[c.to_dict() for c in casinos], simulation_id=simulation_id)

@app.route('/simulation/<int:simulation_id>/strategies', methods=['GET', 'POST'])
def strategies(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    if request.method == 'POST':
        strategy = request.form.get('strategy')
        simulation.strategy = strategy
        db.session.commit()
        return redirect(url_for('run_simulation_page', simulation_id=simulation.id))

    strategies_dir = os.path.join(basedir, 'data', 'strategies')
    strategy_files = [f for f in os.listdir(strategies_dir) if f.endswith('.json')]
    return render_template('strategies.html', simulation=simulation, strategies=strategy_files)

@app.route('/simulation/<int:simulation_id>/betting_strategies_selection', methods=['GET', 'POST'])
def betting_strategies_selection(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    if request.method == 'POST':
        betting_strategy_id = request.form.get('betting_strategy')
        simulation.betting_strategy_id = betting_strategy_id
        db.session.commit()
        return redirect(url_for('run_simulation_page', simulation_id=simulation.id))

    betting_strategies = BettingStrategy.query.all()
    return render_template('betting_strategies.html', simulation=simulation, betting_strategies=betting_strategies)

@app.route('/playing_strategies')
def playing_strategies():
    strategies_dir = os.path.join(basedir, 'data', 'strategies')
    strategy_files = [f for f in os.listdir(strategies_dir) if f.endswith('.json')]
    return render_template('playing_strategies.html', strategies=strategy_files)

@app.route('/betting_strategies_list')
def betting_strategies_list():
    betting_strategies = BettingStrategy.query.all()
    return render_template('betting_strategies_list.html', betting_strategies=betting_strategies)


@app.route('/add_casino', methods=['POST'])
def add_casino():
    casino_name = request.form.get('casino_name')
    simulation_id = request.form.get('simulation_id', type=int)

    if casino_name:
        existing_casino = Casino.query.filter_by(name=casino_name).first()
        if not existing_casino:
            # For simplicity, creating a new casino from this form will use default values
            # A more complete implementation would have a form for all casino properties
            new_casino = Casino(name=casino_name, deck_count=6, dealer_stands_on_soft_17=True, blackjack_payout=1.5, allow_late_surrender=True, allow_early_surrender=False, allow_resplit_to_hands=4, allow_double_after_split=True, allow_double_on_any_two=True, reshuffle_penetration=75, offer_insurance=True, dealer_checks_for_blackjack=True, is_default=False)
            db.session.add(new_casino)
            db.session.commit()
            casino_id = new_casino.id
        else:
            casino_id = existing_casino.id

        if simulation_id:
            simulation = Simulation.query.get(simulation_id)
            if simulation:
                simulation.casino_id = casino_id
                db.session.commit()
                return redirect(url_for('run_simulation_page', simulation_id=simulation.id))

    return redirect(url_for('casinos', simulation_id=simulation_id))

@app.route('/delete_casino/<int:casino_id>', methods=['POST'])
def delete_casino(casino_id):
    casino = Casino.query.get_or_404(casino_id)
    if casino.is_default:
        flash('Default casinos cannot be deleted.', 'error')
        return redirect(url_for('casinos'))
    if casino.simulations:
        flash('Cannot delete a casino with existing simulations.', 'error')
    else:
        db.session.delete(casino)
        db.session.commit()
        flash(f'Casino {casino.name} deleted successfully!', 'success')
    return redirect(url_for('casinos'))

@app.route('/edit_casino/<int:casino_id>', methods=['GET', 'POST'])
def edit_casino(casino_id):
    casino = Casino.query.get_or_404(casino_id)
    simulation_id = request.args.get('simulation_id', type=int)

    if request.method == 'POST':
        simulation_id = request.form.get('simulation_id', type=int)
        if casino.is_default:
            flash('Default casinos cannot be edited.', 'error')
        else:
            casino.name = request.form['name']
            casino.deck_count = int(request.form['deck_count'])
            casino.dealer_stands_on_soft_17 = 'dealer_stands_on_soft_17' in request.form
            casino.blackjack_payout = float(request.form['blackjack_payout'])
            casino.allow_late_surrender = 'allow_late_surrender' in request.form
            casino.allow_early_surrender = 'allow_early_surrender' in request.form
            casino.allow_resplit_to_hands = int(request.form['allow_resplit_to_hands'])
            casino.allow_double_after_split = 'allow_double_after_split' in request.form
            casino.allow_double_on_any_two = 'allow_double_on_any_two' in request.form
            casino.reshuffle_penetration = float(request.form['reshuffle_penetration'])
            casino.offer_insurance = 'offer_insurance' in request.form
            casino.dealer_checks_for_blackjack = 'dealer_checks_for_blackjack' in request.form
            db.session.commit()
            flash(f'Casino {casino.name} updated successfully!', 'success')

        if simulation_id:
            return redirect(url_for('run_simulation_page', simulation_id=simulation.id))
        return redirect(url_for('casinos'))

    return render_template('edit_casino.html', casino=casino, simulation_id=simulation_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Blackjack Simulator')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the web server on.')
    args = parser.parse_args()

    with app.app_context():
        db.create_all()
        load_default_players()
        load_default_casinos()
        load_default_betting_strategies()
    app.run(debug=True, port=args.port)
