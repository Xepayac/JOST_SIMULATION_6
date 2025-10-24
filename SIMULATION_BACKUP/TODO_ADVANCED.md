
# TODO List: Advanced Blackjack Simulation Dashboard

This document provides a detailed, phase-by-phase checklist for building the local web-based Blackjack Simulation Dashboard.

---

### Phase 1: Project Setup & Backend Foundation

**Goal:** Create a basic, runnable Flask server that will act as the backbone for our application.

- [ ] **1.1. Create Project Structure:**
    - [ ] Create the main project directory: `blackjack_dashboard`.
    - [ ] Inside `blackjack_dashboard`, create the following structure:
        ```
        /blackjack_dashboard
        |-- app.py             # Main Flask application
        |-- requirements.txt   # Python dependencies
        |-- /static
        |   |-- /css           # For CSS stylesheets
        |   `-- /js            # For JavaScript files
        `-- /templates
            `-- layout.html    # Base HTML template
        ```

- [ ] **1.2. Set Up Dependencies:**
    - [ ] Create `requirements.txt` with the following content:
        ```
        Flask
        # Path to the local engine, to be installed in editable mode
        -e ../JOST_ENGINE_5
        ```
    - [ ] In your terminal, create and activate a virtual environment and run `pip install -r requirements.txt`.

- [ ] **1.3. Create Basic Flask App (`app.py`):**
    - [ ] Initialize a new Flask application.
    - [ ] Create a main route (`/`) that renders a simple `index.html` template.
    - [ ] Create placeholder API endpoints that return dummy JSON data:
        - `POST /api/simulation` (for running a simulation)
        - `GET /api/strategies/playing` (for listing strategies)
        - `POST /api/strategies/playing` (for saving a new strategy)

- [ ] **1.4. Create Base Template (`layout.html`):**
    - [ ] Create a basic HTML5 structure.
    - [ ] Include links to a main CSS file (e.g., `static/css/main.css`) and a main JS file (e.g., `static/js/app.js`).
    - [ ] Define a main content block that other templates can extend.

---

### Phase 2: Engine Integration & Simulation Runner UI

**Goal:** Wire up the backend to run a simulation using `JOST_ENGINE_5` and create a basic UI to trigger it.

- [ ] **2.1. Develop Simulation Service Module:**
    - [ ] Create a new Python module (e.g., `simulation_service.py`).
    - [ ] Write a function that programmatically creates the necessary `config.json` file from Python dictionaries.
    - [ ] Write a function that uses Python's `subprocess` module to call the `jost_engine` command-line tool with the generated config.
    - [ ] Write a function to parse the `simulation_results.json` output and return it as a Python dictionary.

- [ ] **2.2. Implement Simulation API Endpoint:**
    - [ ] In `app.py`, replace the placeholder `/api/simulation` endpoint.
    - [ ] The endpoint should receive simulation parameters (players, strategies, rounds) as a JSON payload.
    - [ ] It should use the `simulation_service` to run the simulation.
    - [ ] It should return the processed results as a JSON response.

- [ ] **2.3. Build Simulation Runner Frontend (`index.html`):**
    - [ ] Create an HTML form that allows users to set basic simulation parameters (e.g., number of rounds, number of decks).
    - [ ] Add a "Run Simulation" button.

- [ ] **2.4. Add Frontend JavaScript Logic (`app.js`):**
    - [ ] Add an event listener to the "Run Simulation" button.
    - [ ] On click, gather the form data.
    - [ ] Use the `fetch` API to send a POST request to your `/api/simulation` endpoint.
    - [ ] On response, dynamically create an HTML table to display the returned simulation results.

---

### Phase 3: Strategy Studio (Playing & Betting)

**Goal:** Build the UI and backend logic for creating, saving, and using custom strategies.

- [ ] **3.1. Playing Strategy Builder UI:**
    - [ ] Create a new template (`playing_strategy.html`).
    - [ ] Design a grid UI (table or CSS grid) representing Player Hand vs. Dealer Up-Card.
    - [ ] Populate each cell with a dropdown (`<select>`) of possible actions (Hit, Stand, etc.).
    - [ ] Add an input for the strategy name and a "Save Strategy" button.

- [ ] **3.2. Implement Save Playing Strategy API:**
    - [ ] In `app.py`, implement the `POST /api/strategies/playing` endpoint.
    - [ ] It should receive the grid data and strategy name from the frontend.
    - [ ] It will contain a function to convert this data into the JSON format required by `JOST_ENGINE_5`.
    - [ ] Save the generated JSON to a file in a designated directory (e.g., `JOST_ENGINE_5/src/jost_engine/data/custom/playing/`).

- [ ] **3.3. Betting Strategy Builder UI:**
    - [ ] Create a new template (`betting_strategy.html`).
    - [ ] Design a form that allows users to define a series of rules (e.g., "IF True Count >= X, THEN Bet Y units").
    - [ ] Use JavaScript to allow the user to dynamically add or remove rules.
    - [ ] Add an input for the strategy name and a "Save Strategy" button.

- [ ] **3.4. Implement Save Betting Strategy API:**
    - [ ] Create and implement a `POST /api/strategies/betting` endpoint.
    - [ ] Convert the received rules into the engine's required JSON format.
    - [ ] Save the file to `JOST_ENGINE_5/src/jost_engine/data/custom/betting/`.

- [ ] **3.5. Integrate Custom Strategies:**
    - [ ] Modify the Simulation Runner UI form (`index.html`).
    - [ ] Add dropdowns for each player to select a Playing Strategy and a Betting Strategy.
    - [ ] These dropdowns should be dynamically populated by making calls to `GET` endpoints (e.g., `/api/strategies/playing`) that list the available saved JSON files.

---

### Phase 4: Results History & Visualization

**Goal:** Persist simulation results and provide a way to view and compare historical runs.

- [ ] **4.1. Set Up Database:**
    - [ ] Add `Flask-SQLAlchemy` to `requirements.txt`.
    - [ ] Configure `SQLAlchemy` in `app.py` to use a simple SQLite database file.
    - [ ] Define database models for `SimulationRun` (with parameters) and `PlayerResult` (with resulting stats).

- [ ] **4.2. Persist Results:**
    - [ ] Modify the `/api/simulation` endpoint.
    - [ ] After a simulation successfully completes, save the run parameters and all player results to the SQLite database.

- [ ] **4.3. Build History Dashboard:**
    - [ ] Create a new page (`history.html`) and a new API endpoint (`/api/history`).
    - [ ] The API should query the database and return a list of all past simulation runs.
    - [ ] The frontend should display these runs in a table, showing key parameters and a link to view details.

- [ ] **4.4. (Stretch Goal) Add Charting:**
    - [ ] Integrate a JavaScript charting library like `Chart.js`.
    - [ ] Add a feature to view a line chart of a player's bankroll over the course of a simulation.

---

### Phase 5: Polish & Finalization

**Goal:** Refine the application for a better user experience.

- [ ] **5.1. Add User Feedback:**
    - [ ] Show loading indicators (spinners) on the UI while a simulation is running.
    - [ ] Display success or error messages (e.g., "Strategy Saved!" or "Simulation Failed").

- [ ] **5.2. Styling and CSS:**
    - [ ] Write CSS to create a clean, modern, and intuitive layout.
    - [ ] Ensure the application is easy to navigate and understand.

- [ ] **5.3. Documentation:**
    - [ ] Create a `README.md` for the `blackjack_dashboard` project itself, explaining how to install dependencies and run the local server.
