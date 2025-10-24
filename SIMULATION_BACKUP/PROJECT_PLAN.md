
# Project Plan: Blackjack Simulation Dashboard

## 1. Overview

This document outlines the plan for creating a local, web-based dashboard to design, run, and analyze complex blackjack simulations. The application will provide a powerful graphical user interface (GUI) to interact with the `JOST_ENGINE_5` simulation package, removing the need for manual JSON file editing and providing a rich environment for strategy experimentation.

The application will run entirely on the user's local machine and will be accessed via a web browser.

## 2. End-State Architecture

The project will consist of three main components that work together:

*   **Core Engine (`JOST_ENGINE_5`):** The existing Python package that contains all the core blackjack logic and simulation capabilities. We will treat this as a dependency and use it to perform the heavy lifting.
*   **Backend Server (Flask):** A lightweight Python web server that will run locally on the user's machine. Its responsibilities are:
    *   To serve the frontend web pages.
    *   To provide an API for the frontend to communicate with.
    *   To translate user inputs from the UI into the JSON configuration files required by the `JOST_ENGINE_5`.
    *   To launch and manage the simulation processes using the engine.
    *   To process the simulation results and send them back to the frontend.
*   **Frontend (HTML/CSS/JS):** A user-friendly web interface that runs in the browser. It will be the user's primary point of interaction and will feature three main sections:
    1.  **Strategy Studio:** A dedicated area for designing and saving custom playing and betting strategies.
    2.  **Simulation Runner:** A control panel for configuring and launching new simulation runs.
    3.  **Results Dashboard:** A visualization area to display and compare the outcomes of different simulations.

## 3. Core Features

### 3.1. The Strategy Studio

This is the creative hub of the application. The UI will provide a guided, form-based experience for building two types of strategies:

*   **Playing Strategy Builder:**
    *   A grid-based UI representing the classic basic strategy chart (Player Hand vs. Dealer Up-Card).
    *   Each cell in the grid will have a dropdown menu to select the action (Hit, Stand, Double, Split, Surrender).
    *   Users can name their strategy and save it. The backend will convert this into the appropriate JSON format for the engine.
*   **Betting Strategy Builder:**
    *   An interface to define rules for bet sizing.
    *   This will allow for complex, count-based strategies (e.g., "If true count is +2, bet 2 units; if +5, bet 5 units").
    *   Users can define bet spreads, name their betting strategy, and save it as a reusable profile.

### 3.2. The Simulation Runner

This section will be the control panel for launching simulations.

*   **Configuration Form:** Users will be able to:
    *   Select the casino rules (e.g., number of decks, dealer hits on soft 17).
    *   Add one or more players to the simulation.
    *   For each player, assign a pre-saved playing strategy and a betting strategy from the Strategy Studio.
    *   Define the number of rounds to simulate.
*   **Launch Button:** A "Run Simulation" button will send this configuration to the backend server. The server will then prepare the necessary files and execute the simulation using `JOST_ENGINE_5`.

### 3.3. The Results Dashboard

After a simulation is complete, the results will be presented in a clear and interactive format.

*   **Data Tables:** A detailed table will show key performance indicators for each player in the simulation (e.g., Total Profit/Loss, ROI, Win Rate, Blackjack Rate).
*   **Comparison View:** The dashboard will save a history of simulation runs, allowing users to select and compare the results of different strategy combinations side-by-side.
*   **Graphical Visualization (Stretch Goal):** We can add charts to visualize player bankroll over time or to compare the performance of different strategies graphically.

## 4. User Workflow

The end-to-end user experience will be as follows:

1.  **Start the Application:** The user runs a single command (`python run_dashboard.py`) in their terminal.
2.  **Open in Browser:** The user opens their web browser and navigates to the local address provided (`http://127.0.0.1:5000`).
3.  **Design Strategies:** The user navigates to the "Strategy Studio" to create and save a new playing strategy and a new betting strategy.
4.  **Configure Simulation:** The user goes to the "Simulation Runner," sets up a game with one or more players, and assigns their newly created strategies to them.
5.  **Run Simulation:** The user clicks "Run Simulation." The backend runs the simulation, which may take a few moments depending on the number of rounds.
6.  **Analyze Results:** The user is automatically taken to the "Results Dashboard" to see a full breakdown of how their strategies performed. They can then tweak their strategies and run another comparison.

