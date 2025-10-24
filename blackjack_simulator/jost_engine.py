import sys
sys.path.append('/home/user/jostsimulation6/JOST_ENGINE_5/src')

from jost_engine import main

class JostEngine:
    def run_simulation(self, simulation_config):
        # This is a placeholder for the actual simulation logic.
        # We will replace this with a call to the new engine.
        print(f'Running simulation with config: {simulation_config}')
        return {'result': 'success'}

def run_jost_simulation(simulation_config):
    engine = JostEngine()
    return engine.run_simulation(simulation_config)
