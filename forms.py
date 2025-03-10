from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SubmitField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')

class AdminForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Confirmar Contraseña', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Crear Cuenta')

class AccountForm(FlaskForm):
    name = StringField('Nombre de la Cuenta', validators=[DataRequired()])
    instagram_username = StringField('Usuario de Instagram', validators=[DataRequired()])
    instagram_password = StringField('Contraseña de Instagram', validators=[DataRequired()])
    google_credentials = TextAreaField('Credenciales de Google (Base64)', validators=[Optional()])
    folder_id = StringField('ID de Carpeta de Google Drive', validators=[DataRequired()])
    gemini_api_key = StringField('Clave API de Gemini', validators=[DataRequired()])
    
    # Gemini Prompt settings
    gemini_prompt = TextAreaField('Prompt para Gemini (generación de descripciones)', validators=[Optional()], 
                              default="Describe la imagen que te envío con un texto continuo ideal para un pie de foto en Instagram. Identifica la especie del ave y proporciona detalles sobre su aspecto, hábitat y distribución, manteniendo un tono natural, atractivo y animado. Incluye emojis y hashtags adecuados para resaltar la belleza de la naturaleza y la fotografía de aves. Con enfoque en la fotografía. Responde únicamente con el texto solicitado, sin añadir introducciones ni comentarios adicionales.")
    
    # Schedule settings
    morning_post = BooleanField('Publicar en la mañana', default=True)
    morning_time = StringField('Hora (mañana)', default="08:00", validators=[Optional()])
    
    afternoon_post = BooleanField('Publicar en la tarde', default=True)
    afternoon_time = StringField('Hora (tarde)', default="15:00", validators=[Optional()])
    
    evening_post = BooleanField('Publicar en la noche', default=True)
    evening_time = StringField('Hora (noche)', default="22:00", validators=[Optional()])
    
    submit = SubmitField('Guardar')
    
class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Solicitar Restablecimiento')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('No existe una cuenta con ese correo electrónico.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nueva Contraseña', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Confirmar Contraseña', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Restablecer Contraseña')
