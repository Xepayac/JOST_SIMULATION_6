from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import db, Player, Casino, PlayingStrategy, BettingStrategy
from .forms import PlayerForm, CasinoForm, BettingStrategyForm
import json

management_bp = Blueprint('management', __name__, url_prefix='/management', template_folder='templates')

@management_bp.route('/')
def index():
    return render_template("management_index.html")

# Player Routes
@management_bp.route('/players')
def list_players():
    players = Player.query.all()
    return render_template("list_players.html", players=players)

@management_bp.route('/players/create', methods=['GET', 'POST'])
def create_player():
    form = PlayerForm()
    if form.validate_on_submit():
        new_player = Player(name=form.name.data, bankroll=form.bankroll.data)
        db.session.add(new_player)
        db.session.commit()
        flash('Player created successfully!', 'success')
        return redirect(url_for('management.list_players'))
    return render_template('create_player.html', form=form)

@management_bp.route('/players/edit/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    if player.is_default:
        flash('The default player profile cannot be edited.', 'warning')
        return redirect(url_for('management.list_players'))
    form = PlayerForm(obj=player)
    if form.validate_on_submit():
        player.name = form.name.data
        player.bankroll = form.bankroll.data
        db.session.commit()
        flash('Player updated successfully!', 'success')
        return redirect(url_for('management.list_players'))
    return render_template('edit_player.html', form=form, player=player)

@management_bp.route('/players/delete/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    if player.is_default:
        flash('The default player profile cannot be deleted.', 'danger')
        return redirect(url_for('management.list_players'))
    db.session.delete(player)
    db.session.commit()
    flash('Player deleted successfully!', 'success')
    return redirect(url_for('management.list_players'))

# Casino Routes
@management_bp.route('/casinos')
def list_casinos():
    casinos = Casino.query.all()
    return render_template("list_casinos.html", casinos=casinos)

@management_bp.route('/casinos/create', methods=['GET', 'POST'])
def create_casino():
    form = CasinoForm()
    if form.validate_on_submit():
        new_casino = Casino()
        form.populate_obj(new_casino)
        db.session.add(new_casino)
        db.session.commit()
        flash('Casino created successfully!', 'success')
        return redirect(url_for('management.list_casinos'))
    return render_template('create_casino.html', form=form)

@management_bp.route('/casinos/edit/<int:casino_id>', methods=['GET', 'POST'])
def edit_casino(casino_id):
    casino = Casino.query.get_or_404(casino_id)
    if casino.is_default:
        flash('The default casino profile cannot be edited.', 'warning')
        return redirect(url_for('management.list_casinos'))
    form = CasinoForm(obj=casino)
    if form.validate_on_submit():
        form.populate_obj(casino)
        db.session.commit()
        flash('Casino updated successfully!', 'success')
        return redirect(url_for('management.list_casinos'))
    return render_template('edit_casino.html', form=form, casino=casino)

@management_bp.route('/casinos/delete/<int:casino_id>', methods=['POST'])
def delete_casino(casino_id):
    casino = Casino.query.get_or_404(casino_id)
    if casino.is_default:
        flash('The default casino profile cannot be deleted.', 'danger')
        return redirect(url_for('management.list_casinos'))
    db.session.delete(casino)
    db.session.commit()
    flash('Casino deleted successfully!', 'success')
    return redirect(url_for('management.list_casinos'))

# Betting Strategy Routes
@management_bp.route('/betting_strategies')
def list_betting_strategies():
    strategies = BettingStrategy.query.all()
    return render_template("list_betting_strategies.html", strategies=strategies)

@management_bp.route('/betting_strategies/create', methods=['GET', 'POST'])
def create_betting_strategy():
    form = BettingStrategyForm()
    if form.validate_on_submit():
        new_strategy = BettingStrategy()
        form.populate_obj(new_strategy)
        db.session.add(new_strategy)
        db.session.commit()
        flash('Betting strategy created successfully!', 'success')
        return redirect(url_for('management.list_betting_strategies'))
    return render_template('create_betting_strategy.html', form=form)

@management_bp.route('/betting_strategies/edit/<int:strategy_id>', methods=['GET', 'POST'])
def edit_betting_strategy(strategy_id):
    strategy = BettingStrategy.query.get_or_404(strategy_id)
    if strategy.is_default:
        flash('The default betting strategy cannot be edited.', 'warning')
        return redirect(url_for('management.list_betting_strategies'))
    form = BettingStrategyForm(obj=strategy)
    if form.validate_on_submit():
        form.populate_obj(strategy)
        db.session.commit()
        flash('Betting strategy updated successfully!', 'success')
        return redirect(url_for('management.list_betting_strategies'))
    return render_template('edit_betting_strategy.html', form=form, strategy=strategy)

@management_bp.route('/betting_strategies/delete/<int:strategy_id>', methods=['POST'])
def delete_betting_strategy(strategy_id):
    strategy = BettingStrategy.query.get_or_404(strategy_id)
    if strategy.is_default:
        flash('The default betting strategy cannot be deleted.', 'danger')
        return redirect(url_for('management.list_betting_strategies'))
    db.session.delete(strategy)
    db.session.commit()
    flash('Betting strategy deleted successfully!', 'success')
    return redirect(url_for('management.list_betting_strategies'))

# Playing Strategy Routes
@management_bp.route('/playing_strategies')
def list_playing_strategies():
    strategies = PlayingStrategy.query.order_by(PlayingStrategy.is_default.desc(), PlayingStrategy.name).all()
    return render_template("list_playing_strategies.html", strategies=strategies)

@management_bp.route('/playing_strategies/create', methods=['GET', 'POST'])
def create_playing_strategy():
    default_strategy = PlayingStrategy.query.filter_by(is_default=True).first()
    
    if request.method == 'POST':
        hard_totals = {}
        soft_totals = {}
        pairs = {}

        for key, value in request.form.items():
            if key.startswith('hard_'):
                _, player_total, dealer_card = key.split('_')
                if player_total not in hard_totals:
                    hard_totals[player_total] = {}
                hard_totals[player_total][dealer_card] = value
            elif key.startswith('soft_'):
                _, player_total, dealer_card = key.split('_')
                if player_total not in soft_totals:
                    soft_totals[player_total] = {}
                soft_totals[player_total][dealer_card] = value
            elif key.startswith('pair_'):
                _, player_pair, dealer_card = key.split('_')
                if player_pair not in pairs:
                    pairs[player_pair] = {}
                pairs[player_pair][dealer_card] = value
        
        new_strategy = PlayingStrategy(
            name=request.form.get('name'),
            description=request.form.get('description'),
            hard_total_actions=json.dumps(hard_totals),
            soft_total_actions=json.dumps(soft_totals),
            pair_splitting_actions=json.dumps(pairs),
            is_default=False
        )
        db.session.add(new_strategy)
        db.session.commit()
        flash('Playing strategy created successfully!', 'success')
        return redirect(url_for('management.list_playing_strategies'))
    
    strategy_data = {
        "name": "",
        "description": default_strategy.description,
        "hard_totals": json.loads(default_strategy.hard_total_actions),
        "soft_totals": json.loads(default_strategy.soft_total_actions),
        "pairs": json.loads(default_strategy.pair_splitting_actions)
    }
    actions = ['H', 'S', 'D', 'P', 'U']
    dealer_cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'A']
    
    return render_template('create_playing_strategy.html', 
                           strategy=strategy_data, 
                           actions=actions, 
                           dealer_cards=dealer_cards)


@management_bp.route('/playing_strategies/edit/<int:strategy_id>', methods=['GET', 'POST'])
def edit_playing_strategy(strategy_id):
    strategy = PlayingStrategy.query.get_or_404(strategy_id)
    if strategy.is_default:
        flash('The default playing strategy cannot be edited. Please create a new one.', 'warning')
        return redirect(url_for('management.list_playing_strategies'))
        
    if request.method == 'POST':
        hard_totals = {}
        soft_totals = {}
        pairs = {}

        for key, value in request.form.items():
            if key.startswith('hard_'):
                _, player_total, dealer_card = key.split('_')
                if player_total not in hard_totals:
                    hard_totals[player_total] = {}
                hard_totals[player_total][dealer_card] = value
            elif key.startswith('soft_'):
                _, player_total, dealer_card = key.split('_')
                if player_total not in soft_totals:
                    soft_totals[player_total] = {}
                soft_totals[player_total][dealer_card] = value
            elif key.startswith('pair_'):
                _, player_pair, dealer_card = key.split('_')
                if player_pair not in pairs:
                    pairs[player_pair] = {}
                pairs[player_pair][dealer_card] = value
        
        strategy.name = request.form.get('name')
        strategy.description = request.form.get('description')
        strategy.hard_total_actions = json.dumps(hard_totals)
        strategy.soft_total_actions = json.dumps(soft_totals)
        strategy.pair_splitting_actions = json.dumps(pairs)
        db.session.commit()
        flash('Playing strategy updated successfully!', 'success')
        return redirect(url_for('management.list_playing_strategies'))
    
    strategy_data = {
        "name": strategy.name,
        "description": strategy.description,
        "hard_totals": json.loads(strategy.hard_total_actions),
        "soft_totals": json.loads(strategy.soft_total_actions),
        "pairs": json.loads(strategy.pair_splitting_actions)
    }
    actions = ['H', 'S', 'D', 'P', 'U']
    dealer_cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'A']
    
    return render_template('edit_playing_strategy.html', 
                           strategy=strategy_data, 
                           actions=actions, 
                           dealer_cards=dealer_cards, 
                           strategy_id=strategy_id)


@management_bp.route('/playing_strategies/delete/<int:strategy_id>', methods=['POST'])
def delete_playing_strategy(strategy_id):
    strategy = PlayingStrategy.query.get_or_404(strategy_id)
    if strategy.is_default:
        flash('The default playing strategy cannot be deleted.', 'danger')
        return redirect(url_for('management.list_playing_strategies'))
    db.session.delete(strategy)
    db.session.commit()
    flash('Playing strategy deleted successfully!', 'success')
    return redirect(url_for('management.list_playing_strategies'))
