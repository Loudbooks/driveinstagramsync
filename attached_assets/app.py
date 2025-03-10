import os
import logging
import base64
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import instagram_publisher
from datetime import datetime
import threading
import schedule
import time


# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Configure SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///instagram.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Import models after db initialization
from models import Credentials, PublicationHistory




@app.route('/')
def index():
    return render_template('index.html')

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        creds = Credentials.query.first() or Credentials()
        creds.instagram_username = request.form['instagram_username']
        creds.instagram_password = request.form['instagram_password']
        # Clean up the Google credentials string
        google_creds = request.form['google_credentials'].strip()
        # Add padding if needed
        padding = 4 - (len(google_creds) % 4) if len(google_creds) % 4 else 0
        google_creds += "=" * padding
        creds.google_credentials = google_creds
        creds.folder_id = request.form['folder_id']
        creds.gemini_api_key = request.form['gemini_api_key']

        db.session.add(creds)
        db.session.commit()
        flash('Credenciales guardadas exitosamente', 'success')
        return redirect(url_for('index'))

    creds = Credentials.query.first()
    return render_template('config.html', credentials=creds)

@app.route('/run', methods=['POST'])
def run_script():
    with app.app_context():  # 🔹 Agregar contexto de aplicación aquí
            logging.info("Ejecutando script...")
    try:
        creds = Credentials.query.first()
        if not creds:
            logging.error("No se encontraron credenciales en la base de datos")
            return jsonify({'status': 'error', 'message': 'No hay credenciales configuradas'})

        logging.info("Credenciales encontradas, configurando variables de entorno")

        # Clean up and validate Google credentials
        google_creds = creds.google_credentials.strip()
        padding = 4 - (len(google_creds) % 4) if len(google_creds) % 4 else 0
        google_creds += "=" * padding

        # Set environment variables
        os.environ['INSTAGRAM_USERNAME'] = creds.instagram_username
        os.environ['INSTAGRAM_PASSWORD'] = creds.instagram_password
        os.environ['FOLDER_ID'] = creds.folder_id
        os.environ['GEMINI_API_KEY'] = creds.gemini_api_key

        # Create temporary credentials file
        temp_creds_path = os.path.join(os.getcwd(), "temp_credentials.json")
        logging.info(f"Creando archivo temporal de credenciales en: {temp_creds_path}")

        try:
            # Decode and write Google credentials
            decoded_creds = base64.b64decode(google_creds)
            logging.info("Credenciales de Google decodificadas correctamente")

            with open(temp_creds_path, "wb") as f:
                f.write(decoded_creds)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds_path
            logging.info("Archivo de credenciales creado correctamente")

            # Run the script
            logging.info("Ejecutando script de publicación")
            result = instagram_publisher.main()
            logging.info(f"Resultado del script: {result}")

            # Log the publication
            history = PublicationHistory(
                timestamp=datetime.now(),
                status='success' if result.get('status') == 'success' else 'error',
                details=str(result.get('results', [])) if result.get('status') == 'success' else result.get('message', 'Error desconocido')
            )
            db.session.add(history)
            db.session.commit()

            return jsonify({
                'status': result.get('status', 'error'),
                'message': 'Script ejecutado correctamente' if result.get('status') == 'success' else result.get('message', 'Error desconocido'),
                'results': result.get('results', [])
            })

        finally:
            # Clean up temporary file
            if os.path.exists(temp_creds_path):
                os.remove(temp_creds_path)
                logging.info("Archivo temporal de credenciales eliminado")

    except Exception as e:
        logging.error(f"Error al ejecutar el script: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/history')
def history():
    publications = PublicationHistory.query.order_by(PublicationHistory.timestamp.desc()).all()
    return render_template('history.html', publications=publications)

with app.app_context():
    db.create_all()


# Programar la ejecución automática
def schedule_task():
    logging.info("Iniciando tarea programada...")
    
    schedule.every().day.at("08:00").do(run_script)
    schedule.every().day.at("15:00").do(run_script)
    schedule.every().day.at("22:00").do(run_script)

    while True:
        logging.info("Comprobando las tareas pendientes...")
        with app.app_context():  # 🔹 Envolver en un contexto de aplicación
            schedule.run_pending()
        logging.info("miramos la hora que es")
        time.sleep(60)  # Esperar un minuto antes de verificar de nuevo

def start_scheduler():
    thread = threading.Thread(target=schedule_task, daemon=True)
    thread.start()
    

# Iniciar el scheduler al arrancar la aplicación
if __name__ == '__main__':
    with app.app_context():
        # Iniciar el programador de tareas
        start_scheduler()
    app.run(debug=True)
