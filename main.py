import os
import requests
from flask import Flask, request
from pydub import AudioSegment
import speech_recognition as sr
from dotenv import load_dotenv
import os


load_dotenv()

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")



app = Flask(__name__)


# ----------------------------------------------------

@app.route("/")
def home():
    return "¡Bot Transcriptor Activo!"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # 1. VERIFICACIÓN DE META (NO TOCAR)
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Error de validación", 403

    # 2. PROCESAR MENSAJES
    if request.method == "POST":
        try:
            data = request.json
            # Verificamos si la estructura del JSON es la de un mensaje
            if "entry" in data and "changes" in data["entry"][0] and "value" in data["entry"][0]["changes"][0]:
                cambios = data["entry"][0]["changes"][0]["value"]
                
                if "messages" in cambios:
                    mensaje = cambios["messages"][0]
                    telefono = mensaje["from"]
                    tipo_mensaje = mensaje["type"]

                    # --- SI ES TEXTO ---
                    if tipo_mensaje == "text":
                        texto = mensaje["text"]["body"]
                        print(f"📩 Texto recibido de {telefono}: {texto}")
                        enviar_whatsapp(telefono, f"Dijiste: {texto}")

                    # --- SI ES AUDIO (TRANSCRIPCIÓN) ---
                    elif tipo_mensaje == "audio":
                        print("🎤 Audio recibido. Procesando...")
                        audio_id = mensaje["audio"]["id"]
                        
                        # 1. Descargar el archivo OGG de WhatsApp
                        ruta_ogg = descargar_audio(audio_id)
                        
                        if ruta_ogg:
                            # 2. Convertir a WAV (necesario para la librería de transcripción)
                            ruta_wav = ruta_ogg.replace(".ogg", ".wav")
                            convertir_ogg_a_wav(ruta_ogg, ruta_wav)
                            
                            # 3. Transcribir el audio a texto
                            texto_transcrito = transcribir_audio(ruta_wav)
                            
                            # 4. Enviar resultado al usuario
                            enviar_whatsapp(telefono, f"📝 Transcripción: {texto_transcrito}")
                            
                            # 5. Limpiar archivos temporales para no llenar el disco
                            try:
                                os.remove(ruta_ogg)
                                os.remove(ruta_wav)
                            except:
                                pass
                        else:
                            enviar_whatsapp(telefono, "Error: No pude descargar el audio.")

        except Exception as e:
            print(f"❌ Ocurrió un error en el webhook: {e}")

        return "Evento recibido", 200

# --- FUNCIONES AUXILIARES ---

def enviar_whatsapp(telefono, texto):
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto}
    }
    try:
        requests.post(url, json=data, headers=headers)
    except Exception as e:
        print(f"Error enviando mensaje: {e}")

def descargar_audio(media_id):
    try:
        # Paso A: Obtener la URL real del archivo
        url_info = f"https://graph.facebook.com/v22.0/{media_id}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        info = requests.get(url_info, headers=headers).json()
        
        if "url" in info:
            url_descarga = info["url"]
            # Paso B: Descargar el binario
            response = requests.get(url_descarga, headers=headers)
            nombre = f"temp_{media_id}.ogg"
            with open(nombre, "wb") as f:
                f.write(response.content)
            return nombre
    except Exception as e:
        print(f"Error en descarga: {e}")
    return None

def convertir_ogg_a_wav(ogg_path, wav_path):
    # Usa pydub y ffmpeg para convertir el formato
    try:
        audio = AudioSegment.from_ogg(ogg_path)
        audio.export(wav_path, format="wav")
    except Exception as e:
        print(f"Error en conversión de audio (¿Está instalado FFmpeg?): {e}")

def transcribir_audio(wav_path):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            # Usamos el motor gratuito de Google
            texto = recognizer.recognize_google(audio_data, language="es-ES")
            return texto
    except sr.UnknownValueError:
        return "No pude entender lo que se dijo en el audio."
    except sr.RequestError:
        return "Error de conexión con el servicio de reconocimiento de voz."
    except Exception as e:
        return f"Error procesando el audio: {e}"

if __name__ == "__main__":
    app.run(debug=True, port=5000)