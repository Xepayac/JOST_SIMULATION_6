import sys
import os

# Ensure the project root is on the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from blackjack_dashboard.run_engine import run_simulation_from_web

print("--- Starting Minimal Engine Test ---")
print("This test calls the simulation engine directly, bypassing the Flask web server.")

# Hardcoded parameters for a basic simulation run
player_name = "Direct-Test Player"
bankroll = 10000
num_hands = 50
casino_profile = "default_casino" # A known default casino profile
playing_strategy_profile = "conservative" # The strategy we've been trying to use
betting_strategy_profile = "flat_bet" # A simple, known-good betting strategy

print(f"\nParameters:")
print(f"  Player: {player_name}")
print(f"  Bankroll: {bankroll}")
print(f"  Hands: {num_hands}")
print(f"  Casino: {casino_profile}")
print(f"  Playing Strategy: {playing_strategy_profile}")
print(f"  Betting Strategy: {betting_strategy_profile}\n")

try:
    # Directly invoke the function that the web server is supposed to call
    run_simulation_from_web(
        player_name=player_name,
        bankroll=bankroll,
        num_hands=num_hands,
        casino_profile=casino_profile,
        playing_strategy_profile=playing_strategy_profile,
        betting_strategy_profile=betting_strategy_profile
    )
    print("\n--- MINIMAL ENGINE TEST SUCCEEDED ---")
    print("The script ran without crashing. A new results file should be in the 'blackjack_dashboard/simulation_results' directory.")

except Exception as e:
    print(f"\n--- MINIMAL ENGINE TEST FAILED ---")
    print(f"The engine failed with the following error: {e}")
    import traceback
    traceback.print_exc()
