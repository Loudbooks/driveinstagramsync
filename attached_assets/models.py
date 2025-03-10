from app import db
from datetime import datetime

class Credentials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instagram_username = db.Column(db.String(100))
    instagram_password = db.Column(db.String(100))
    google_credentials = db.Column(db.Text)
    folder_id = db.Column(db.String(100))
    gemini_api_key = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PublicationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20))
    details = db.Column(db.Text)
