from app import app, db, start_scheduler
import os
import logging
from dotenv import load_dotenv

load_dotenv()

scheduler_running = False

def start_scheduler_once():
    """Inicia el scheduler solo si no está en ejecución."""
    global scheduler_running
    
    if not scheduler_running:
        logging.warning("🚨 Se está ejecutando start_scheduler()")
        scheduler_running = True
        start_scheduler()  # Inicia el scheduler
    else:
        logging.info("El scheduler ya está en ejecución.")

def start_scheduler():
    """Lógica del scheduler (simulada)."""
    logging.info("Iniciando el scheduler...")
    # Aquí va el código de ejecución del scheduler
    # Simulamos un proceso largo
    import time
    time.sleep(10)  # Simula un trabajo largo
    global scheduler_running
    scheduler_running = False  # Reseteamos cuando termine el proceso

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Arrancando servidor Flask...")
    
    with app.app_context():
        # Create all database tables
        db.create_all()
        # Start the scheduler in background
        # Usar una función dedicada para evitar duplicación
        start_scheduler_once()
    
    # Run Flask application
    app.run(host=os.getenv('HOST', '0.0.0.0'), port=int(os.getenv('PORT', 5000)), debug=False)
