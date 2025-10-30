
import os
import sys
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, Response, abort

from .models import db, Player, Casino, BettingStrategy, PlayingStrategy, Simulation, Result
from .celery_worker import celery

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if db.session.query(Simulation).count() > 0:
        latest_simulation = db.session.query(Simulation).order_by(Simulation.timestamp.desc()).first()
        return redirect(url_for('main.run_simulation_page', simulation_id=latest_simulation.id))
    return redirect(url_for('main.new_simulation'))

@main.route('/simulations')
def simulations():
    all_simulations = db.session.query(Simulation).order_by(Simulation.timestamp.desc()).all()
    return render_template('simulations.html', simulations=all_simulations)

@main.route('/simulation/new', methods=['GET', 'POST'])
def new_simulation():
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for('main.new_simulation'))
        
        default_player = db.session.query(Player).filter_by(is_default=True).first()
        default_casino = db.session.query(Casino).filter_by(is_default=True).first()
        default_playing_strategy = db.session.query(PlayingStrategy).filter_by(is_default=True).first()
        default_betting_strategy = db.session.query(BettingStrategy).filter_by(is_default=True).first()

        new_sim = Simulation(
            title=title,
            player=default_player,
            casino=default_casino,
            playing_strategy=default_playing_strategy,
            betting_strategy=default_betting_strategy,
            iterations=1000000
        )
        db.session.add(new_sim)
        db.session.commit()
        flash(f"Simulation '{title}' created.", 'success')
        return redirect(url_for('main.run_simulation_page', simulation_id=new_sim.id))
    
    return render_template('new_simulation.html')

@main.route('/simulation/<int:simulation_id>/delete', methods=['POST'])
def delete_simulation(simulation_id):
    simulation = db.session.get(Simulation, simulation_id)
    if not simulation:
        abort(404)
    db.session.delete(simulation)
    db.session.commit()
    flash('Simulation and its results have been deleted.', 'success')
    return redirect(url_for('main.simulations'))

@main.route('/simulation/<int:simulation_id>/run', methods=['GET'])
def run_simulation_page(simulation_id):
    simulation = db.session.get(Simulation, simulation_id)
    if not simulation:
        abort(404)
    return render_template('run_simulation.html',
                           simulation=simulation,
                           players=db.session.query(Player).order_by(Player.name).all(),
                           casinos=db.session.query(Casino).order_by(Casino.name).all(),
                           playing_strategies=db.session.query(PlayingStrategy).order_by(PlayingStrategy.name).all(),
                           betting_strategies=db.session.query(BettingStrategy).order_by(BettingStrategy.name).all())

@main.route('/simulation/<int:simulation_id>/run_action', methods=['POST'])
def run_simulation_action(simulation_id):
    current_app.logger.info(f'Processing simulation {simulation_id}...')
    sim = db.session.get(Simulation, simulation_id)
    if not sim:
        abort(404)

    sim.player_id = request.form.get('player_id')
    sim.casino_id = request.form.get('casino_id')
    sim.playing_strategy_id = request.form.get('playing_strategy_id')
    sim.betting_strategy_id = request.form.get('betting_strategy_id')
    sim.iterations = int(request.form.get('iterations', 100))
    sim.notes = request.form.get('notes')
    
    db.session.commit()

    player = db.session.get(Player, sim.player_id)
    casino = db.session.get(Casino, sim.casino_id)
    playing_strategy = db.session.get(PlayingStrategy, sim.playing_strategy_id)
    betting_strategy = db.session.get(BettingStrategy, sim.betting_strategy_id)

    if not all([player, casino, playing_strategy, betting_strategy]):
        flash('Player, Casino, Playing Strategy, and Betting Strategy must all be selected.', 'error')
        return redirect(url_for('main.run_simulation_page', simulation_id=sim.id))

    player_data = player.to_dict()
    casino_data = casino.to_dict()
    strategy_data = playing_strategy.to_dict()
    betting_strategy_data = betting_strategy.to_dict()

    simulation_config = {
        "player": player_data,
        "casino": casino_data,
        "playing_strategy_name": playing_strategy.name,
        "strategy": strategy_data,
        "betting_strategy": betting_strategy_data,
        "iterations": sim.iterations,
        "true_count_threshold": int(request.form.get('true_count_threshold', 1)),
        "log_hands": request.form.get('log_hands') == 'true'
    }
    
    simulation_config_json = json.dumps(simulation_config)

    try:
        task = celery.send_task('jost_simulation_task', args=[simulation_config_json])
        sim.task_id = task.id
        db.session.commit()
        current_app.logger.info(f'Task {task.id} sent to Celery for simulation {sim.id}')
    except Exception as e:
        current_app.logger.error(f'Error sending task to Celery: {e}')
        flash('Error starting simulation. Please check the logs.', 'error')
        return redirect(url_for('main.run_simulation_page', simulation_id=sim.id))
    
    flash('Simulation started! You will be redirected to the results page when it is complete.', 'success')
    return redirect(url_for('main.simulation_status', simulation_id=sim.id))

@main.route('/simulation/<int:simulation_id>/status')
def simulation_status(simulation_id):
    simulation = db.session.get(Simulation, simulation_id)
    if not simulation:
        abort(404)
    return render_template('simulation_status.html', simulation=simulation)

@main.route('/task_status/<task_id>')
def task_status(task_id):
    task = celery.AsyncResult(task_id)

    if task.state == 'SUCCESS':
        current_app.logger.info(f"Task {task.id} succeeded. Processing results.")
        results_data = task.get()
        sim = db.session.query(Simulation).filter_by(task_id=task_id).first()
        if not sim:
            current_app.logger.error(f"FATAL: Simulation not found for task_id {task_id}")
            return jsonify({'state': 'ERROR', 'status': 'Simulation not found for this.'})
        
        # --- DEFINITIVE FIX: Robustly extract the single player's results ---
        if not results_data or not isinstance(results_data, dict) or not list(results_data.values()):
            current_app.logger.error(f"Invalid or empty results data for task {task.id}: {results_data}")
            flash('Error processing simulation results.', 'error')
            return jsonify({'state': 'ERROR', 'status': 'Invalid results data.'})

        player_name = list(results_data.keys())[0]
        outcomes = list(results_data.values())[0]
        hand_history = outcomes.pop('hand_history', None)

        current_app.logger.info(f"Found simulation {sim.id} for task {task.id}. Creating result.")
        new_result = Result(
            simulation_id=sim.id, 
            player_name=player_name, 
            casino_name=sim.casino.name,
            strategy=sim.playing_strategy.name,
            betting_strategy_name=sim.betting_strategy.name,
            starting_bankroll=sim.player.bankroll, 
            iterations=sim.iterations,
            notes=sim.notes, 
            outcomes=json.dumps(outcomes),
            hand_history=json.dumps(hand_history) if hand_history else None
        )
        db.session.add(new_result)
        db.session.commit()
        current_app.logger.info(f"Result {new_result.id} created for simulation {sim.id}. Redirecting.")
        return jsonify({'state': 'SUCCESS', 'result_url': url_for('main.result_page', result_id=new_result.id)})
    
    elif task.state == 'FAILURE':
        current_app.logger.error(f"Task {task.id} failed. Reason: {task.info}")
        status = str(task.info)
    else:
        status = 'In Progress'

    return jsonify({'state': task.state, 'status': status})

@main.route('/results/<int:result_id>')
def result_page(result_id):
    result = db.session.get(Result, result_id)
    if not result:
        abort(404)
    try:
        outcomes = json.loads(result.outcomes)
    except json.JSONDecodeError:
        flash('Error decoding simulation results. The data may be corrupt.', 'error')
        return redirect(url_for('main.results_list'))

    return render_template('result_details.html', 
                           result=result, 
                           outcomes=outcomes)

@main.route('/results/<int:result_id>/download_history')
def download_history(result_id):
    result = db.session.get(Result, result_id)
    if not result:
        abort(404)
    if not result.hand_history:
        flash('No hand history available for this result.', 'error')
        return redirect(url_for('main.result_page', result_id=result.id))

    return Response(
        result.hand_history,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment;filename=hand_history_{result.id}.json'}
    )

@main.route('/results')
def results_list():
    results = db.session.query(Result).order_by(Result.timestamp.desc()).all()
    return render_template('results_list.html', results=results)
