from app import db
from flask_login import UserMixin
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def get_reset_token(self, expires_in=3600):
        """Genera un token para restablecer la contraseña que expira en 1 hora por defecto"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiration = datetime.utcnow() + timedelta(seconds=expires_in)
        db.session.commit()
        return self.reset_token
        
    def verify_reset_token(self, token):
        """Verifica si el token es válido y no ha expirado"""
        if self.reset_token != token:
            return False
        if self.reset_token_expiration is None or self.reset_token_expiration < datetime.utcnow():
            return False
        return True
        
    def clear_reset_token(self):
        """Limpia el token después de usarlo"""
        self.reset_token = None
        self.reset_token_expiration = None
        db.session.commit()

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    instagram_username = db.Column(db.String(100), nullable=False)
    instagram_password = db.Column(db.String(100), nullable=False)
    google_credentials = db.Column(db.Text)
    folder_id = db.Column(db.String(100))
    gemini_api_key = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationship with publication history
    publications = db.relationship('PublicationHistory', backref='account', lazy=True)
    
    # Gemini prompt settings
    gemini_prompt = db.Column(db.Text, default="Describe la imagen que te envío con un texto continuo ideal para un pie de foto en Instagram. Identifica la especie del ave y proporciona detalles sobre su aspecto, hábitat y distribución, manteniendo un tono natural, atractivo y animado. Incluye emojis y hashtags adecuados para resaltar la belleza de la naturaleza y la fotografía de aves. Con enfoque en la fotografía. Responde únicamente con el texto solicitado, sin añadir introducciones ni comentarios adicionales.")
    
    # Schedule settings
    morning_post = db.Column(db.Boolean, default=True)
    morning_time = db.Column(db.String(5), default="08:00")
    afternoon_post = db.Column(db.Boolean, default=True)
    afternoon_time = db.Column(db.String(5), default="15:00")
    evening_post = db.Column(db.Boolean, default=True)
    evening_time = db.Column(db.String(5), default="22:00")

class PublicationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20))
    details = db.Column(db.Text)
    image_name = db.Column(db.String(255), nullable=True)
