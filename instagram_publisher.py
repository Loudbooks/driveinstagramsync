import logging
import os
from googleapiclient.http import MediaIoBaseDownload
import google.generativeai as genai
from datetime import datetime
from instagrapi import Client
from models import PublicationHistory, Account
from app import db, app #Modified line to include app
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

def authenticate_google_drive(credentials_path):
    """Authenticate with Google Drive API"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        logging.error(f"Error authenticating with Google Drive: {str(e)}")
        raise e

def get_new_images(service, folder_id):
    """Get new images from Google Drive folder.
    
    # Incluir todos los tipos de imágenes comunes
    """
    query = f"'{folder_id}' in parents and (mimeType contains 'image/')"

    logging.info(f"Buscando imágenes en carpeta: {folder_id}")

    try:
        results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        all_images = results.get('files', [])

        logging.info(f"Total de archivos en la carpeta: {len(all_images)}")

        for img in all_images:
            logging.info(f"Archivo encontrado: {img['name']} - Tipo: {img.get('mimeType', 'desconocido')}")

        # Filtrar solo las imágenes que no han sido procesadas
        new_images = [img for img in all_images if "_enviada" not in img['name']]

        logging.info(f"Imágenes sin procesar encontradas: {len(new_images)}")

        return new_images
    except Exception as e:
        logging.error(f"Error al buscar imágenes: {str(e)}")
        return []

def download_image(service, file_id, file_name):
    """Download an image from Google Drive"""
    request = service.files().get_media(fileId=file_id)
    file_path = f'./{file_name}'

    with open(file_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    return file_path

def get_gemini_image_description(image_path, api_key, custom_prompt=None):
    """Generate image description using Gemini AI"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    with open(image_path, "rb") as image_file:
        image_data = image_file.read()

    # Usar prompt personalizado si está disponible, sino usar uno predeterminado
    default_prompt = "Describe la imagen que te envío con un texto continuo ideal para un pie de foto en Instagram. Identifica la especie del ave y proporciona detalles sobre su aspecto, hábitat y distribución, manteniendo un tono natural, atractivo y animado. Incluye emojis y hashtags adecuados para resaltar la belleza de la naturaleza y la fotografía de aves. Con enfoque en la fotografía. Responde únicamente con el texto solicitado, sin añadir introducciones ni comentarios adicionales."
    prompt = custom_prompt if custom_prompt else default_prompt

    try:
        response = model.generate_content(
            [prompt, {
                "mime_type": "image/jpeg",
                "data": image_data
            }]
        )
        return response.text
    except Exception as e:
        logging.error(f"Error generating image description: {str(e)}")
        return f"Error al obtener la descripción: {str(e)}"

def rename_file(service, file_id, new_name):
    """Rename a file in Google Drive to mark as processed"""
    try:
        file_metadata = {'name': new_name}
        service.files().update(fileId=file_id, body=file_metadata).execute()
        logging.info(f"Archivo renombrado exitosamente a {new_name}")
    except Exception as e:
        logging.error(f"Error al renombrar archivo: {str(e)}")
        # Continuar con la ejecución aunque falle el renombrado
        # La imagen ya se publicó en Instagram, así que esto es secundario

def post_to_instagram(image_path, caption, username, password):
    """Publica una imagen en Instagram usando instagrapi con persistencia de sesión"""
    try:
        sessions_dir = './instagram_sessions'
        os.makedirs(sessions_dir, exist_ok=True)

        session_file = f"{sessions_dir}/{username}_session.json"
        cl = Client()
        # Configurar manualmente el "device"
        cl.set_device({
            "app_version": "123.0.0.21.114",
            "android_version": 29,
            "android_release": "10",
            "dpi": "420dpi",
            "resolution": "1080x1920",
            "manufacturer": "Xiaomi",
            "model": "Mi 9T",
            "device": "davinci"
        })
        login_success = False
        login_message = "No se pudo iniciar sesión"

        def try_login():
            nonlocal login_success, login_message
            try:
                cl.login(username, password)
                login_success = True
                logging.info(f"Login exitoso para {username}")
                cl.dump_settings(session_file)
                # Persistencia extendida (si fuera necesario para el cliente)
                with open(session_file, 'r+') as f:
                    settings = json.load(f)
                    f.seek(0)
                    json.dump(settings, f)
                    f.truncate()
            except Exception as le:
                logging.error(f"Error en login para {username}: {str(le)}")
                login_message = f"Error en login: {str(le)}"

        # Intentar cargar configuración y sesión
        if os.path.exists(session_file):
            try:
                cl.load_settings(session_file)
                logging.info(f"Sesión cargada para {username}")
                cl.get_timeline_feed()  # Verifica si la sesión aún es válida
                login_success = True
                logging.info(f"Sesión válida para {username}")
            except Exception as ve:
                logging.warning(f"Sesión inválida, intentando login completo: {str(ve)}")
                try_login()
        else:
            try_login()

        if login_success:
            try:
                media = cl.photo_upload(image_path, caption)
                return True, f"Publicado con éxito. ID de media: {media.id}"
            except Exception as e:
                logging.error(f"Primer intento fallido: {str(e)}")
                if "login_required" in str(e):
                    logging.warning("Sesión inválida al publicar, intentando nuevo login y reintento...")
                    try_login()
                    if login_success:
                        try:
                            media = cl.photo_upload(image_path, caption)
                            return True, f"Publicado tras reintento. ID de media: {media.id}"
                        except Exception as e2:
                            logging.error(f"Reintento fallido: {str(e2)}")
                            return False, f"Error tras reintento: {str(e2)}"
                return False, f"Error al publicar la foto: {str(e)}"
        else: 
            return False, f"No se pudo autenticar con Instagram. {login_message}"

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Instagram posting error: {error_msg}")

        if "challenge_required" in error_msg or "Unexpected token '<'" in error_msg:
            return False, "La cuenta de Instagram requiere verificación manual. Inicia sesión en un navegador y completa los desafíos de seguridad."

        return False, f"Error posting to Instagram: {error_msg}"

def publish_for_account(account_id, instagram_username, instagram_password, folder_id, gemini_api_key, credentials_path):
    """Main function to publish images for a specific account."""
    results = []

    try:
        logging.info(f"Starting publication process for account {instagram_username}")
        logging.info(f"ID de carpeta configurado: {folder_id}")

        if not folder_id or folder_id.strip() == "":
            message = "Error: No se ha configurado un ID de carpeta válido"
            logging.error(message)
            return {"status": "error", "message": message}

        # Obtener el prompt personalizado de la cuenta si existe
        custom_prompt = None
        with app.app_context(): #Using app context here
            account = Account.query.get(account_id)
            if account and account.gemini_prompt:
                custom_prompt = account.gemini_prompt
                logging.info(f"Usando prompt personalizado para la cuenta {account.name}")

        # Authenticate with Google Drive
        service = authenticate_google_drive(credentials_path)

        # Verificar que el ID de carpeta existe
        try:
            folder_info = service.files().get(fileId=folder_id, fields="name").execute()
            logging.info(f"Carpeta encontrada: {folder_info.get('name', 'Nombre desconocido')}")
        except Exception as e:
            logging.error(f"Error al verificar la carpeta {folder_id}: {str(e)}")
            if "File not found" in str(e):
                return {"status": "error", "message": f"La carpeta con ID {folder_id} no existe o no es accesible"}

        # Get new images from the folder
        images = get_new_images(service, folder_id)

        if not images:
            message = "No hay imágenes nuevas para procesar"
            logging.info(message)

            # Record the check in history even if no images were found
            history = PublicationHistory(
                account_id=account_id,
                timestamp=datetime.utcnow(),
                status='info',
                details=message
            )
            db.session.add(history)
            db.session.commit()

            return {
                "status": "success",
                "message": message
            }

        for image in images:
            file_id = image['id']
            file_name = image['name']

            results.append(f"Procesando: {file_name}")
            logging.info(f"Processing image: {file_name}")

            # Download the image
            image_path = download_image(service, file_id, file_name)

            # Generate image description
            image_description = get_gemini_image_description(image_path, gemini_api_key, custom_prompt)
            results.append(f"Descripción: {image_description}")

            # Post to Instagram
            success, message = post_to_instagram(
                image_path, 
                image_description, 
                instagram_username, 
                instagram_password
            )

            # Record in publication history
            history = PublicationHistory(
                account_id=account_id,
                timestamp=datetime.utcnow(),
                status='success' if success else 'error',
                details=message,
                image_name=file_name
            )
            db.session.add(history)
            db.session.commit()

            # Rename file to mark as processed
            name_without_extension, extension = os.path.splitext(file_name)
            new_name = f"{name_without_extension}_enviada{extension}"
            rename_file(service, file_id, new_name)

            # Clean up local file
            if os.path.exists(image_path):
                os.remove(image_path)

            results.append("Imagen procesada correctamente" if success else f"Error: {message}")

        return {"status": "success", "results": results}

    except Exception as e:
        error_message = str(e)
        logging.error(f"Error in publication process: {error_message}", exc_info=True)

        # Record error in history
        history = PublicationHistory(
            account_id=account_id,
            timestamp=datetime.utcnow(),
            status='error',
            details=error_message
        )
        db.session.add(history)
        db.session.commit()

        return {"status": "error", "message": error_message}