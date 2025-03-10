from app import app, db, start_scheduler
import os
import logging
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Arrancando servidor Flask...")
    
    with app.app_context():
        # Create all database tables
        db.create_all()
        # Start the scheduler in background
        start_scheduler()
    
    # Run Flask application
    app.run(host=os.getenv('HOST', '0.0.0.0'), port=int(os.getenv('PORT', 5000)), debug=False)
