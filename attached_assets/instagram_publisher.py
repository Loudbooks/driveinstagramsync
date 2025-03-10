import os
import base64
import sys
from instagrapi import Client
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv
import google.generativeai as genai
from oauth2client.service_account import ServiceAccountCredentials




# Copy the necessary functions from mainpublish.py
def authenticate_google_drive():
    print("autenticamos en google ok")
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        scopes=['https://www.googleapis.com/auth/drive'])
    
    return build('drive', 'v3', credentials=credentials)


def get_new_images(service):
    query = f"'{os.environ['FOLDER_ID']}' in parents and mimeType='image/jpeg'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    images = results.get('files', [])
    new_images = [img for img in images if "_enviada" not in img['name']]
    return new_images


def download_image(service, file_id, file_name):
    request = service.files().get_media(fileId=file_id)
    file_path = f'./{file_name}'
    with open(file_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
    return file_path


def get_gemini_image_description(image_path):
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    with open(image_path, "rb") as image_file:
        image_data = image_file.read()

    prompt = "Describe la imagen que te envío con un texto continuo ideal para un pie de foto en Instagram. Identifica la especie del ave y proporciona detalles sobre su aspecto, hábitat y distribución, manteniendo un tono natural, atractivo y animado. Incluye emojis y hashtags adecuados para resaltar la belleza de la naturaleza y la fotografía de aves. Con enfoque en la fotografía. Responde únicamente con el texto solicitado, sin añadir introducciones ni comentarios adicionales."
    try:
        response = model.generate_content(
            [prompt, {
                "mime_type": "image/jpeg",
                "data": image_data
            }])
        return response.text
    except Exception as e:
        return f"Error al obtener la descripción: {str(e)}"


def rename_file(service, file_id, new_name):
    file_metadata = {'name': new_name}
    service.files().update(fileId=file_id, body=file_metadata).execute()


def generate_message(image_description, tags):
    if image_description == ' No se ha encontrado nada ':
        return tags
    return f"{image_description}\n\n{tags}"

# Publicar en Instagram usando instagrapi
def post_to_instagram(image_path, caption):
    cl = Client()
    cl.login(os.environ.get("INSTAGRAM_USERNAME"), os.environ.get("INSTAGRAM_PASSWORD"))  # Login con instagrapi
    cl.photo_upload(image_path, caption)  # Subir foto con descripción


def main():


  



    results = []
    try:

        print("Ejecutando la tarea programada...")
        service = authenticate_google_drive()
        
        images = get_new_images(service)

        print("obtenermos imagenes ok")

        if not images:
            return {
                "status": "success",
                "message": "No hay imágenes nuevas para procesar"
            }

        for image in images:
            file_id = image['id']
            file_name = image['name']

            results.append(f"Procesando: {file_name}")
            image_path = download_image(service, file_id, file_name)

            image_description = get_gemini_image_description(image_path)
            results.append(f"Descripción: {image_description}")

            tags = ''
            final_message = generate_message(image_description, tags)

            # La siguiente línea está comentada para evitar publicaciones en Instagram por ahora
            post_to_instagram(image_path, final_message)

            # Rename file to mark as processed
            name_without_extension, extension = os.path.splitext(file_name)
            new_name = f"{name_without_extension}_enviada{extension}"
            rename_file(service, file_id, new_name)

            os.remove(image_path)
            results.append("Imagen procesada correctamente")

        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    


