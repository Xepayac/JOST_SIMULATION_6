
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# --- Database Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'simulations.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Models ---
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    bankroll = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'bankroll': self.bankroll
        }

class PlayingStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    strategy_type = db.Column(db.String(50), nullable=False)  # e.g., 'default', 'custom'
    rules = db.Column(db.Text, nullable=True)  # For custom strategies

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'strategy_type': self.strategy_type,
            'rules': self.rules
        }

class BettingStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    strategy_type = db.Column(db.String(50), nullable=False)
    rules = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'strategy_type': self.strategy_type,
            'rules': self.rules
        }

class Casino(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    deck_count = db.Column(db.Integer, nullable=False)
    dealer_hits_on_soft_17 = db.Column(db.Boolean, nullable=False)
    double_after_split_allowed = db.Column(db.Boolean, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'deck_count': self.deck_count,
            'dealer_hits_on_soft_17': self.dealer_hits_on_soft_17,
            'double_after_split_allowed': self.double_after_split_allowed
        }

class Simulation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default=f"Simulation {datetime.utcnow()}")
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    results = db.Column(db.Text, nullable=True)
    notes = db.relationship('Note', backref='simulation', lazy=True, cascade="all, delete-orphan")
    
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    player = db.relationship('Player', backref='simulations')
    
    playing_strategy_id = db.Column(db.Integer, db.ForeignKey('playing_strategy.id'), nullable=True)
    playing_strategy = db.relationship('PlayingStrategy', backref='simulations')
    
    betting_strategy_id = db.Column(db.Integer, db.ForeignKey('betting_strategy.id'), nullable=True)
    betting_strategy = db.relationship('BettingStrategy', backref='simulations')
    
    casino_id = db.Column(db.Integer, db.ForeignKey('casino.id'), nullable=True)
    casino = db.relationship('Casino', backref='simulations')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'timestamp': self.timestamp.isoformat(),
            'results': self.results
        }

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    simulation_id = db.Column(db.Integer, db.ForeignKey('simulation.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'simulation_id': self.simulation_id
        }

# --- HTML Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simulations')
def simulations_page():
    return render_template('simulations.html')

@app.route('/simulations/<int:simulation_id>')
def simulation_page(simulation_id):
    return render_template('simulation.html', simulation_id=simulation_id)

@app.route('/player_setup')
def player_setup_page():
    return render_template('player_setup.html')

@app.route('/playing_strategy_setup')
def playing_strategy_setup_page():
    return render_template('playing_strategy_setup.html')

@app.route('/betting_strategy_setup')
def betting_strategy_setup_page():
    return render_template('betting_strategy_setup.html')

@app.route('/casino_setup')
def casino_setup_page():
    return render_template('casino_setup.html')

@app.route('/simulation_setup')
def simulation_setup_page():
    return render_template('simulation_setup.html')

# --- API Routes ---

# Player routes
@app.route('/api/players', methods=['POST'])
def create_player():
    data = request.get_json()
    if not data or not all(k in data for k in ('name', 'bankroll')):
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    new_player = Player(name=data['name'], bankroll=data['bankroll'])
    db.session.add(new_player)
    db.session.commit()
    return jsonify(new_player.to_dict()), 201

@app.route('/api/players', methods=['GET'])
def get_players():
    players = Player.query.all()
    return jsonify([player.to_dict() for player in players])

@app.route('/api/players/<int:player_id>', methods=['GET'])
def get_player(player_id):
    player = db.session.get(Player, player_id)
    if player:
        return jsonify(player.to_dict())
    return jsonify({'status': 'error', 'message': 'Player not found'}), 404

@app.route('/api/players/<int:player_id>', methods=['PUT'])
def update_player(player_id):
    player = db.session.get(Player, player_id)
    if not player:
        return jsonify({'status': 'error', 'message': 'Player not found'}), 404
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    player.name = data.get('name', player.name)
    player.bankroll = data.get('bankroll', player.bankroll)
    db.session.commit()
    return jsonify(player.to_dict())

@app.route('/api/players/<int:player_id>', methods=['DELETE'])
def delete_player(player_id):
    player = db.session.get(Player, player_id)
    if not player:
        return jsonify({'status': 'error', 'message': 'Player not found'}), 404
    db.session.delete(player)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Player deleted'})

# PlayingStrategy routes
@app.route('/api/playing_strategies', methods=['POST'])
def create_playing_strategy():
    data = request.get_json()
    if not data or not all(k in data for k in ('name', 'strategy_type')):
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    new_strategy = PlayingStrategy(
        name=data['name'],
        strategy_type=data['strategy_type'],
        rules=data.get('rules')
    )
    db.session.add(new_strategy)
    db.session.commit()
    return jsonify(new_strategy.to_dict()), 201

@app.route('/api/playing_strategies', methods=['GET'])
def get_playing_strategies():
    strategies = PlayingStrategy.query.all()
    return jsonify([s.to_dict() for s in strategies])

@app.route('/api/playing_strategies/<int:strategy_id>', methods=['GET'])
def get_playing_strategy(strategy_id):
    strategy = db.session.get(PlayingStrategy, strategy_id)
    if strategy:
        return jsonify(strategy.to_dict())
    return jsonify({'status': 'error', 'message': 'Playing strategy not found'}), 404

@app.route('/api/playing_strategies/<int:strategy_id>', methods=['PUT'])
def update_playing_strategy(strategy_id):
    strategy = db.session.get(PlayingStrategy, strategy_id)
    if not strategy:
        return jsonify({'status': 'error', 'message': 'Playing strategy not found'}), 404
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    strategy.name = data.get('name', strategy.name)
    strategy.strategy_type = data.get('strategy_type', strategy.strategy_type)
    strategy.rules = data.get('rules', strategy.rules)
    db.session.commit()
    return jsonify(strategy.to_dict())

@app.route('/api/playing_strategies/<int:strategy_id>', methods=['DELETE'])
def delete_playing_strategy(strategy_id):
    strategy = db.session.get(PlayingStrategy, strategy_id)
    if not strategy:
        return jsonify({'status': 'error', 'message': 'Playing strategy not found'}), 404
    db.session.delete(strategy)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Playing strategy deleted'})


# BettingStrategy routes
@app.route('/api/betting_strategies', methods=['POST'])
def create_betting_strategy():
    data = request.get_json()
    if not data or not all(k in data for k in ('name', 'strategy_type')):
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    new_strategy = BettingStrategy(
        name=data['name'],
        strategy_type=data['strategy_type'],
        rules=data.get('rules')
    )
    db.session.add(new_strategy)
    db.session.commit()
    return jsonify(new_strategy.to_dict()), 201

@app.route('/api/betting_strategies', methods=['GET'])
def get_betting_strategies():
    strategies = BettingStrategy.query.all()
    return jsonify([s.to_dict() for s in strategies])

@app.route('/api/betting_strategies/<int:strategy_id>', methods=['GET'])
def get_betting_strategy(strategy_id):
    strategy = db.session.get(BettingStrategy, strategy_id)
    if strategy:
        return jsonify(strategy.to_dict())
    return jsonify({'status': 'error', 'message': 'Betting strategy not found'}), 404

@app.route('/api/betting_strategies/<int:strategy_id>', methods=['PUT'])
def update_betting_strategy(strategy_id):
    strategy = db.session.get(BettingStrategy, strategy_id)
    if not strategy:
        return jsonify({'status': 'error', 'message': 'Betting strategy not found'}), 404
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    strategy.name = data.get('name', strategy.name)
    strategy.strategy_type = data.get('strategy_type', strategy.strategy_type)
    strategy.rules = data.get('rules', strategy.rules)
    db.session.commit()
    return jsonify(strategy.to_dict())

@app.route('/api/betting_strategies/<int:strategy_id>', methods=['DELETE'])
def delete_betting_strategy(strategy_id):
    strategy = db.session.get(BettingStrategy, strategy_id)
    if not strategy:
        return jsonify({'status': 'error', 'message': 'Betting strategy not found'}), 404
    db.session.delete(strategy)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Betting strategy deleted'})


# Casino routes
@app.route('/api/casinos', methods=['POST'])
def create_casino():
    data = request.get_json()
    if not data or not all(k in data for k in ('name', 'deck_count', 'dealer_hits_on_soft_17', 'double_after_split_allowed')):
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    new_casino = Casino(
        name=data['name'],
        deck_count=data['deck_count'],
        dealer_hits_on_soft_17=data['dealer_hits_on_soft_17'],
        double_after_split_allowed=data['double_after_split_allowed']
    )
    db.session.add(new_casino)
    db.session.commit()
    return jsonify(new_casino.to_dict()), 201

@app.route('/api/casinos', methods=['GET'])
def get_casinos():
    casinos = Casino.query.all()
    return jsonify([c.to_dict() for c in casinos])

@app.route('/api/casinos/<int:casino_id>', methods=['GET'])
def get_casino(casino_id):
    casino = db.session.get(Casino, casino_id)
    if casino:
        return jsonify(casino.to_dict())
    return jsonify({'status': 'error', 'message': 'Casino not found'}), 404

@app.route('/api/casinos/<int:casino_id>', methods=['PUT'])
def update_casino(casino_id):
    casino = db.session.get(Casino, casino_id)
    if not casino:
        return jsonify({'status': 'error', 'message': 'Casino not found'}), 404
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    casino.name = data.get('name', casino.name)
    casino.deck_count = data.get('deck_count', casino.deck_count)
    casino.dealer_hits_on_soft_17 = data.get('dealer_hits_on_soft_17', casino.dealer_hits_on_soft_17)
    casino.double_after_split_allowed = data.get('double_after_split_allowed', casino.double_after_split_allowed)
    db.session.commit()
    return jsonify(casino.to_dict())

@app.route('/api/casinos/<int:casino_id>', methods=['DELETE'])
def delete_casino(casino_id):
    casino = db.session.get(Casino, casino_id)
    if not casino:
        return jsonify({'status': 'error', 'message': 'Casino not found'}), 404
    db.session.delete(casino)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Casino deleted'})

@app.route('/api/simulations', methods=['POST'])
def create_simulation():
    data = request.get_json() or {}
    player_id = data.get('player_id') if data.get('player_id') != 0 else None
    playing_strategy_id = data.get('playing_strategy_id') if data.get('playing_strategy_id') != 0 else None
    betting_strategy_id = data.get('betting_strategy_id') if data.get('betting_strategy_id') != 0 else None
    casino_id = data.get('casino_id') if data.get('casino_id') != 0 else None

    new_simulation = Simulation(
        name=data.get('name', f"Simulation {datetime.utcnow()}"),
        player_id=player_id,
        playing_strategy_id=playing_strategy_id,
        betting_strategy_id=betting_strategy_id,
        casino_id=casino_id
    )
    db.session.add(new_simulation)
    db.session.commit()
    return jsonify(new_simulation.to_dict()), 201

@app.route('/api/simulations', methods=['GET'])
def get_simulations():
    simulations = Simulation.query.order_by(Simulation.timestamp.desc()).all()
    return jsonify([sim.to_.dict() for sim in simulations])

@app.route('/api/simulations/<int:simulation_id>', methods=['GET'])
def get_simulation(simulation_id):
    simulation = db.session.get(Simulation, simulation_id)
    if simulation:
        return jsonify(simulation.to_dict())
    return jsonify({'status': 'error', 'message': 'Simulation not found'}), 404

@app.route('/api/simulations/<int:simulation_id>/notes', methods=['POST'])
def create_note_for_simulation(simulation_id):
    simulation = db.session.get(Simulation, simulation_id)
    if not simulation:
        return jsonify({'status': 'error', 'message': 'Simulation not found'}), 404
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400

    new_note = Note(content=data['content'], simulation_id=simulation.id)
    db.session.add(new_note)
    db.session.commit()
    return jsonify(new_note.to_dict()), 201

@app.route('/api/simulations/<int:simulation_id>/notes', methods=['GET'])
def get_notes_for_simulation(simulation_id):
    simulation = db.session.get(Simulation, simulation_id)
    if not simulation:
        return jsonify({'status': 'error', 'message': 'Simulation not found'}), 404
    
    notes = Note.query.filter_by(simulation_id=simulation_id).order_by(Note.timestamp.desc()).all()
    return jsonify([note.to_dict() for note in notes])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5002, debug=True)
