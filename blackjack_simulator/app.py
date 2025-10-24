
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from blackjack_simulator.simulation import run_simulation

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

class Simulation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    iterations = db.Column(db.Integer, nullable=False, default=100)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    player = db.relationship('Player', backref='simulations')

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    simulation_id = db.Column(db.Integer, db.ForeignKey('simulation.id'), nullable=False)
    simulation = db.relationship('Simulation', backref='results')
    player_name = db.Column(db.String(100), nullable=False)
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
        return redirect(url_for('edit_simulation', simulation_id=new_simulation.id))
    return render_template('new_simulation.html')

@app.route('/simulations')
def simulations():
    sort_by = request.args.get('sort_by', 'timestamp')
    order = request.args.get('order', 'desc')
    order_by_clause = Simulation.title.asc() if order == 'asc' else Simulation.title.desc() if sort_by == 'name' else Simulation.timestamp.asc() if order == 'asc' else Simulation.timestamp.desc()
    simulations = Simulation.query.order_by(order_by_clause).all()
    return render_template('simulations.html', simulations=simulations)

@app.route('/simulation/<int:simulation_id>/edit', methods=['GET', 'POST'])
def edit_simulation(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    if request.method == 'POST':
        title = request.form.get('title')

        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for('edit_simulation', simulation_id=simulation.id))

        simulation.title = title
        db.session.commit()
        flash('Simulation saved successfully!', 'success')
        return redirect(url_for('edit_simulation', simulation_id=simulation.id))
    return render_template('edit_simulation.html', simulation=simulation)

@app.route('/simulation/<int:simulation_id>/run', methods=['GET'])
def run_simulation_page(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    return render_template('run_simulation.html', simulation=simulation)

@app.route('/simulation/<int:simulation_id>/run_action', methods=['POST'])
def run_simulation_action(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    if not simulation.player:
        flash('Please choose a player before running the simulation.', 'error')
        return redirect(url_for('edit_simulation', simulation_id=simulation.id))
    
    iterations = request.form.get('iterations')
    if not iterations or not iterations.isdigit():
        flash('Iterations must be a valid number.', 'error')
        return redirect(url_for('run_simulation_page', simulation_id=simulation.id))

    simulation.iterations = int(iterations)
    simulation.notes = request.form.get('notes')
    db.session.commit()
    
    outcomes = run_simulation(simulation.player.bankroll, simulation.iterations)
    
    new_result = Result(
        simulation_id=simulation.id,
        player_name=simulation.player.name,
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
                return redirect(url_for('edit_simulation', simulation_id=simulation.id))

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Blackjack Simulator')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the web server on.')
    args = parser.parse_args()

    with app.app_context():
        db.create_all()
        load_default_players()
    app.run(debug=True, port=args.port)
