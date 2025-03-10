from app import app, start_scheduler  # Importamos app y la función para iniciar el scheduler
import os
import logging
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    logging.info("Arrancando servidor Flask...")

    # Iniciar el scheduler en un hilo separado
    with app.app_context():
        logging.info("Iniciando scheduler en segundo plano...")
        start_scheduler()  # Iniciar el programador de tareas en un hilo aparte

        # Ejecutar el script manualmente al iniciar
        logging.info("Ejecutando run_script manualmente al inicio...")


    # Ejecutar Flask normalmente
    app.run(host=os.getenv('HOST', '0.0.0.0'), port=int(os.getenv('PORT', 5000)), debug=False)
