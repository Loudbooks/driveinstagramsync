import os
import logging
import base64
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import threading
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Configure SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///instagram.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Setup login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor inicia sesión para acceder a esta página."
login_manager.login_message_category = "warning"

# Import models after db initialization to avoid circular imports
from models import User, Account, PublicationHistory
from forms import LoginForm, AdminForm, AccountForm, RequestResetForm, ResetPasswordForm
from email_utils import send_reset_email
import instagram_publisher

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    accounts = Account.query.all()
    account_stats = []
    
    for account in accounts:
        # Get success and error counts for each account
        success_count = PublicationHistory.query.filter_by(account_id=account.id, status='success').count()
        error_count = PublicationHistory.query.filter_by(account_id=account.id, status='error').count()
        total_count = success_count + error_count
        
        # Get latest publication
        latest = PublicationHistory.query.filter_by(account_id=account.id).order_by(PublicationHistory.timestamp.desc()).first()
        
        account_stats.append({
            'id': account.id,
            'name': account.name,
            'instagram_username': account.instagram_username,
            'success_count': success_count,
            'error_count': error_count,
            'total_count': total_count,
            'latest': latest.timestamp if latest else None
        })
    
    return render_template('index.html', account_stats=account_stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if we need to create an admin user
    if User.query.count() == 0:
        form = AdminForm()
        if form.validate_on_submit():
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Cuenta de administrador creada correctamente. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        return render_template('login.html', form=form, first_time=True)
    
    # Normal login flow
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('login.html', form=form, first_time=False)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    accounts = Account.query.all()
    
    # Get total statistics
    total_posts = PublicationHistory.query.count()
    success_posts = PublicationHistory.query.filter_by(status='success').count()
    error_posts = PublicationHistory.query.filter_by(status='error').count()
    
    # Get recent publications
    recent_publications = PublicationHistory.query.order_by(PublicationHistory.timestamp.desc()).limit(5).all()
    
    # Get monthly stats
    # This is simplified, could be improved with SQLAlchemy func
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_posts = PublicationHistory.query.filter(
        (db.extract('month', PublicationHistory.timestamp) == current_month) & 
        (db.extract('year', PublicationHistory.timestamp) == current_year)
    ).count()
    
    return render_template('dashboard.html', 
                           accounts=accounts,
                           total_posts=total_posts,
                           success_posts=success_posts,
                           error_posts=error_posts,
                           recent_publications=recent_publications,
                           monthly_posts=monthly_posts)

@app.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    accounts = Account.query.all()
    account_count = len(accounts)
    can_add_more = account_count < 4
    return render_template('config.html', accounts=accounts, can_add_more=can_add_more, account_count=account_count)

@app.route('/account/new', methods=['GET', 'POST'])
@login_required
def new_account():
    # Verificar si ya existen 4 cuentas
    account_count = Account.query.count()
    if account_count >= 4:
        flash('El sistema está limitado a un máximo de 4 cuentas de Instagram.', 'warning')
        return redirect(url_for('config'))
        
    form = AccountForm()
    
    if form.validate_on_submit():
        account = Account(
            name=form.name.data,
            instagram_username=form.instagram_username.data,
            instagram_password=form.instagram_password.data,
            folder_id=form.folder_id.data,
            gemini_api_key=form.gemini_api_key.data,
            google_credentials=form.google_credentials.data,
            gemini_prompt=form.gemini_prompt.data,
            morning_post=form.morning_post.data,
            morning_time=form.morning_time.data,
            afternoon_post=form.afternoon_post.data,
            afternoon_time=form.afternoon_time.data,
            evening_post=form.evening_post.data,
            evening_time=form.evening_time.data
        )
        
        db.session.add(account)
        db.session.commit()
        
        # Mostrar un mensaje especial cuando se alcance el límite
        new_count = Account.query.count()
        if new_count >= 4:
            flash('Cuenta creada correctamente. Has alcanzado el límite de 4 cuentas.', 'info')
        else:
            flash(f'Cuenta creada correctamente. Puedes crear {4 - new_count} cuentas más.', 'success')
            
        return redirect(url_for('config'))
    
    return render_template('config.html', form=form, edit_mode=False)

@app.route('/account/edit/<int:account_id>', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    account = Account.query.get_or_404(account_id)
    form = AccountForm(obj=account)
    
    if form.validate_on_submit():
        account.name = form.name.data
        account.instagram_username = form.instagram_username.data
        account.instagram_password = form.instagram_password.data
        account.folder_id = form.folder_id.data
        account.gemini_api_key = form.gemini_api_key.data
        account.gemini_prompt = form.gemini_prompt.data
        
        # Handle Google credentials (don't overwrite if not provided)
        if form.google_credentials.data and form.google_credentials.data.strip():
            account.google_credentials = form.google_credentials.data
            
        # Update schedule settings
        account.morning_post = form.morning_post.data
        account.morning_time = form.morning_time.data
        account.afternoon_post = form.afternoon_post.data
        account.afternoon_time = form.afternoon_time.data
        account.evening_post = form.evening_post.data
        account.evening_time = form.evening_time.data
        
        account.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Cuenta actualizada correctamente', 'success')
        return redirect(url_for('config'))
    
    return render_template('config.html', form=form, edit_mode=True, account=account)

@app.route('/account/delete/<int:account_id>', methods=['POST'])
@login_required
def delete_account(account_id):
    account = Account.query.get_or_404(account_id)
    
    # Delete related publication history
    PublicationHistory.query.filter_by(account_id=account.id).delete()
    
    # Delete account
    db.session.delete(account)
    db.session.commit()
    
    flash('Cuenta eliminada correctamente', 'success')
    return redirect(url_for('config'))

@app.route('/run/<int:account_id>', methods=['POST'])
@login_required
def run_script(account_id):
    account = Account.query.get_or_404(account_id)
    
    try:
        logging.info(f"Ejecutando script para la cuenta: {account.name}")
        
        # Clean up and validate Google credentials
        google_creds = account.google_credentials.strip()
        padding = 4 - (len(google_creds) % 4) if len(google_creds) % 4 else 0
        google_creds += "=" * padding
        
        # Create temporary credentials file
        temp_creds_path = os.path.join(os.getcwd(), f"temp_credentials_{account.id}.json")
        logging.info(f"Creando archivo temporal de credenciales en: {temp_creds_path}")
        
        try:
            # Decode and write Google credentials
            decoded_creds = base64.b64decode(google_creds)
            
            with open(temp_creds_path, "wb") as f:
                f.write(decoded_creds)
                
            # Run the script with account info
            result = instagram_publisher.publish_for_account(
                account_id=account.id,
                instagram_username=account.instagram_username,
                instagram_password=account.instagram_password,
                folder_id=account.folder_id,
                gemini_api_key=account.gemini_api_key,
                credentials_path=temp_creds_path
            )
            
            logging.info(f"Resultado del script: {result}")
            
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
@login_required
def history():
    account_id = request.args.get('account_id', type=int)
    
    if account_id:
        account = Account.query.get_or_404(account_id)
        publications = PublicationHistory.query.filter_by(account_id=account_id).order_by(PublicationHistory.timestamp.desc()).all()
        return render_template('history.html', publications=publications, account=account, accounts=Account.query.all())
    else:
        # Show all publications
        publications = PublicationHistory.query.order_by(PublicationHistory.timestamp.desc()).all()
        return render_template('history.html', publications=publications, account=None, accounts=Account.query.all())

def run_publication_for_account(account_id):
    """Run the publication script for a specific account within an app context"""
    with app.app_context():
        account = Account.query.get(account_id)
        if not account:
            logging.error(f"Account with ID {account_id} not found")
            return
        
        logging.info(f"Running scheduled publication for account: {account.name}")
        
        try:
            # Clean up and validate Google credentials
            google_creds = account.google_credentials.strip()
            padding = 4 - (len(google_creds) % 4) if len(google_creds) % 4 else 0
            google_creds += "=" * padding
            
            # Create temporary credentials file
            temp_creds_path = os.path.join(os.getcwd(), f"temp_credentials_{account.id}.json")
            
            # Decode and write Google credentials
            decoded_creds = base64.b64decode(google_creds)
            
            with open(temp_creds_path, "wb") as f:
                f.write(decoded_creds)
                
            # Run the script with account info
            result = instagram_publisher.publish_for_account(
                account_id=account.id,
                instagram_username=account.instagram_username,
                instagram_password=account.instagram_password,
                folder_id=account.folder_id,
                gemini_api_key=account.gemini_api_key,
                credentials_path=temp_creds_path
            )
            
            logging.info(f"Scheduled publication result: {result}")
            
        except Exception as e:
            logging.error(f"Error during scheduled publication: {str(e)}", exc_info=True)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_creds_path):
                os.remove(temp_creds_path)

def schedule_tasks():
    """Schedule publication tasks for all accounts"""
    with app.app_context():
        accounts = Account.query.all()
        
        # Clear existing jobs
        schedule.clear()
        
        for account in accounts:
            # Morning post
            if account.morning_post and account.morning_time:
                schedule.every().day.at(account.morning_time).do(
                    run_publication_for_account, account_id=account.id
                ).tag(f"account_{account.id}")
                
            # Afternoon post
            if account.afternoon_post and account.afternoon_time:
                schedule.every().day.at(account.afternoon_time).do(
                    run_publication_for_account, account_id=account.id
                ).tag(f"account_{account.id}")
                
            # Evening post
            if account.evening_post and account.evening_time:
                schedule.every().day.at(account.evening_time).do(
                    run_publication_for_account, account_id=account.id
                ).tag(f"account_{account.id}")
        
        logging.info(f"Scheduled tasks for {len(accounts)} accounts")
        
        # Run the scheduler loop
        while True:
            with app.app_context():
                schedule.run_pending()
            time.sleep(60)  # Check every minute

def start_scheduler():
    """Start the scheduler in a separate thread"""
    scheduler_thread = threading.Thread(target=schedule_tasks, daemon=True)
    scheduler_thread.start()
    logging.info("Scheduler started in background thread")

# Rutas para el restablecimiento de contraseña
@app.route('/reset_request', methods=['GET', 'POST'])
def reset_request():
    # Si el usuario ya está autenticado, redirigir al dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_token()
            send_reset_email(user, token, app)
            flash('Se ha enviado un correo electrónico con instrucciones para restablecer tu contraseña.', 'info')
            return redirect(url_for('login'))
        else:
            flash('No se encontró ninguna cuenta con ese correo electrónico.', 'warning')
    
    return render_template('reset_request.html', form=form)

@app.route('/reset_password/<string:token>/<int:user_id>', methods=['GET', 'POST'])
def reset_password(token, user_id):
    # Si el usuario ya está autenticado, redirigir al dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    user = User.query.get_or_404(user_id)
    
    if not user.verify_reset_token(token):
        flash('El token es inválido o ha expirado.', 'warning')
        return redirect(url_for('reset_request'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.clear_reset_token()
        db.session.commit()
        flash('Tu contraseña ha sido actualizada. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_password.html', form=form)

# Initialize the database and handle migrations
with app.app_context():
    try:
        # Verificar si necesitamos añadir la columna gemini_prompt
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('account')] if inspector.has_table('account') else []
        needs_gemini_prompt = 'gemini_prompt' not in columns and inspector.has_table('account')
        
        # Crear tablas base
        db.create_all()
        logging.info("Base de datos inicializada correctamente")
        
        # Migración manual para añadir columna gemini_prompt si es necesario
        if needs_gemini_prompt:
            try:
                # Migración manual para SQLite (añadir columna)
                with db.engine.connect() as conn:
                    conn.execute(db.text(
                        "ALTER TABLE account ADD COLUMN gemini_prompt TEXT DEFAULT "
                        "'Describe la imagen que te envío con un texto continuo ideal para un pie de foto en Instagram. Identifica la especie del ave y proporciona detalles sobre su aspecto, hábitat y distribución, manteniendo un tono natural, atractivo y animado. Incluye emojis y hashtags adecuados para resaltar la belleza de la naturaleza y la fotografía de aves. Con enfoque en la fotografía. Responde únicamente con el texto solicitado, sin añadir introducciones ni comentarios adicionales.'"
                    ))
                    conn.commit()
                
                logging.info("Migración completada: columna gemini_prompt añadida correctamente")
            except Exception as migration_error:
                logging.error(f"Error en migración: {str(migration_error)}")
                
    except Exception as e:
        logging.error(f"Error al inicializar la base de datos: {str(e)}")

# Iniciar el planificador en un hilo separado
start_scheduler()
