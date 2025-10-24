from blackjack_dashboard.app import app, db

if __name__ == '__main__':
    # Initialize the database in the application context
    with app.app_context():
        db.create_all()

    print("\n" + "-"*50)
    print("Blackjack Simulation Dashboard is starting...")
    print("To view the application, find the 'Ports' tab in the IDE's bottom panel.")
    print("Then, click the 'Open in browser' (globe) icon for port 5000.")
    print("-"*50 + "\n")

    # Run the Flask application, listening on all available network interfaces
    # The reloader is disabled to prevent confusing double output in this environment.
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
