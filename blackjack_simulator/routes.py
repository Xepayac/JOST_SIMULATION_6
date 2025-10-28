import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from .models import db, Player, Casino, BettingStrategy, Simulation, Result
from .celery_worker import celery

main = Blueprint('main', __name__)

@main.route('/')
def index():
    latest_simulation = Simulation.query.order_by(Simulation.timestamp.desc()).first()
    return redirect(url_for('main.run_simulation_page', simulation_id=latest_simulation.id)) if latest_simulation else redirect(url_for('main.simulations'))

@main.route('/simulations')
def simulations():
    all_simulations = Simulation.query.order_by(Simulation.timestamp.desc()).all()
    return render_template('simulations.html', simulations=all_simulations)

@main.route('/simulation/new', methods=['GET', 'POST'])
def new_simulation():
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for('main.simulations'))
        new_sim = Simulation(title=title)
        db.session.add(new_sim)
        db.session.commit()
        flash('Simulation created.', 'success')
        return redirect(url_for('main.run_simulation_page', simulation_id=new_sim.id))
    return render_template('new_simulation.html')

@main.route('/simulation/<int:simulation_id>/delete', methods=['POST'])
def delete_simulation(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    db.session.delete(simulation)
    db.session.commit()
    flash('Simulation and its results have been deleted.', 'success')
    return redirect(url_for('main.simulations'))

@main.route('/simulation/<int:simulation_id>/run', methods=['GET'])
def run_simulation_page(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    basedir = os.path.abspath(os.path.dirname(__file__))
    strategies_dir = os.path.join(basedir, '..', '..', 'backend', 'src', 'jost_engine', 'data', 'strategies')
    return render_template('run_simulation.html',
                           simulation=simulation,
                           players=Player.query.all(),
                           casinos=Casino.query.all(),
                           strategies=[f for f in os.listdir(strategies_dir) if f.endswith('.json')],
                           betting_strategies=BettingStrategy.query.all())

@main.route('/simulation/<int:simulation_id>/run_action', methods=['POST'])
def run_simulation_action(simulation_id):
    sim = Simulation.query.get_or_404(simulation_id)
    sim.player_id = request.form.get('player_id')
    sim.casino_id = request.form.get('casino_id')
    strategy_filename = request.form.get('strategy')
    sim.strategy = strategy_filename
    sim.betting_strategy_id = request.form.get('betting_strategy_id')
    sim.iterations = int(request.form.get('iterations', 100))
    sim.notes = request.form.get('notes')
    true_count_threshold = int(request.form.get('true_count_threshold', 1))

    if not all([sim.player, sim.casino, sim.strategy, sim.betting_strategy]):
        flash('Player, Casino, Playing Strategy, and Betting Strategy must all be selected.', 'error')
        return redirect(url_for('main.run_simulation_page', simulation_id=sim.id))

    # Construct path to strategy file
    basedir = os.path.abspath(os.path.dirname(__file__))
    strategies_dir = os.path.join(basedir, '..', '..', 'backend', 'src', 'jost_engine', 'data', 'strategies')
    strategy_path = os.path.join(strategies_dir, strategy_filename)

    # Read and parse the strategy JSON file
    try:
        with open(strategy_path, 'r') as f:
            strategy_config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        flash(f'Error loading strategy file: {e}', 'error')
        return redirect(url_for('main.run_simulation_page', simulation_id=sim.id))

    task = celery.send_task('jost_simulation_task', args=[{
        "player": sim.player.to_dict(),
        "casino": sim.casino.to_dict(),
        "strategy": strategy_config,
        "betting_strategy": sim.betting_strategy.to_dict(),
        "iterations": sim.iterations,
        "true_count_threshold": true_count_threshold
    }])
    sim.task_id = task.id
    db.session.commit()
    flash('Simulation started! You will be redirected to the results page when it is complete.', 'success')
    return redirect(url_for('main.simulation_status', simulation_id=sim.id))

@main.route('/simulation/<int:simulation_id>/status')
def simulation_status(simulation_id):
    simulation = Simulation.query.get_or_404(simulation_id)
    return render_template('simulation_status.html', simulation=simulation)

@main.route('/task_status/<task_id>')
def task_status(task_id):
    task = celery.AsyncResult(task_id)
    if task.state == 'SUCCESS':
        outcomes = task.get()
        sim = Simulation.query.filter_by(task_id=task_id).first()
        if not sim:
            return jsonify({'state': 'ERROR', 'status': 'Simulation not found.'})
        
        new_result = Result(
            simulation_id=sim.id, player_name=sim.player.name, casino_name=sim.casino.name,
            strategy=sim.strategy, betting_strategy_name=sim.betting_strategy.name,
            starting_bankroll=sim.player.bankroll, iterations=sim.iterations,
            notes=sim.notes, outcomes=json.dumps(outcomes)
        )
        db.session.add(new_result)
        db.session.commit()
        return jsonify({'state': 'SUCCESS', 'result_url': url_for('main.result_page', result_id=new_result.id)})
    
    status = 'Pending...' if task.state == 'PENDING' else 'Running...' if task.state != 'FAILURE' else str(task.info)
    return jsonify({'state': task.state, 'status': status})

@main.route('/results/<int:result_id>')
def result_page(result_id):
    result = Result.query.get_or_404(result_id)
    current_app.logger.info(f"Attempting to load results for result_id: {result_id}")
    current_app.logger.info(f"Raw outcomes data: {result.outcomes}")
    try:
        outcomes = json.loads(result.outcomes)
        is_new_format = isinstance(outcomes, list)
    except json.JSONDecodeError as e:
        current_app.logger.error(f"JSONDecodeError for result_id {result_id}: {e}")
        current_app.logger.error(f"Malformed JSON data: {result.outcomes}")
        flash('Error decoding simulation results. The data may be corrupt.', 'error')
        # Redirect to a safe page, or render an error template
        return redirect(url_for('main.results_list'))

    return render_template('result_details.html',
                           result=result,
                           outcomes=outcomes,
                           is_new_format=is_new_format)

@main.route('/results')
def results_list():
    return render_template('results_list.html', results=Result.query.order_by(Result.timestamp.desc()).all())
