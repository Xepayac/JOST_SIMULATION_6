# Simulation Dashboard TODO List

This document outlines the steps to transform the note-taking application into a full-featured simulation management dashboard.

## 1. Project Restructuring and Renaming
- [ ] Rename the `note_taker` directory to `simulation_dashboard` to better reflect the project's purpose.
- [ ] Update any import paths and references within the project that are affected by the name change.

## 2. Database Model Overhaul
- [ ] Define a new `Simulation` model in `app.py`. This model should store:
    - An auto-incrementing ID.
    - A timestamp for when the simulation was run.
    - The results of the simulation (potentially as a JSON string or a path to a results file).
    - A user-friendly name or title for the simulation.
- [ ] Modify the existing `Note` model to include a foreign key relationship to the `Simulation` model. This will link each note to a specific simulation.

## 3. Backend API Development
- [ ] **Simulation Endpoints:**
    - [ ] Create a `POST /api/simulations` endpoint to run a new simulation. This will trigger the simulation engine and save the results to the database.
    - [ ] Create a `GET /api/simulations` endpoint to retrieve a list of all saved simulations.
    - [ ] Create a `GET /api/simulations/<id>` endpoint to retrieve the detailed results of a single simulation.
- [ ] **Note Endpoints (Adjusted):**
    - [ ] Modify the `POST /api/notes` endpoint to `POST /api/simulations/<simulation_id>/notes` to associate a new note with a specific simulation.
    - [ ] Create a `GET /api/simulations/<simulation_id>/notes` endpoint to retrieve all notes for a particular simulation.

## 4. Frontend UI/UX Implementation
- [ ] **Main Page (`index.html`):**
    - [ ] Redesign the main page to be the "Simulation Studio" where users can configure and run new simulations.
- [ ] **Simulations List Page (`/simulations`):**
    - [ ] Create a new page that displays a list of all previously run and saved simulations.
    - [ ] Each item in the list should link to its corresponding detail page.
- [ ] **Simulation Detail Page (`/simulations/<id>`):**
    - [ ] Create a dynamic page to display the results of a specific simulation.
    - [ ] Integrate the note-taking functionality on this page, allowing users to view and add notes related to the displayed simulation.

## 5. Simulation Engine Integration
- [ ] Import and adapt the `JOST_ENGINE_5` code so it can be called from our Flask application.
- [ ] Create a function that the `POST /api/simulations` endpoint can call to run the simulation and return the results.

## 6. Testing
- [ ] Update the existing `pytest` suite to reflect the new data models and API endpoints.
- [ ] Write new tests for running simulations and associating notes with them.
