from flask import Flask, request, jsonify
from flask_cors import CORS
import syncedlyrics
import requests
import re

app = Flask(__name__)
CORS(app)

def limpiar_titulo(titulo):
    """
    Limpia el título para mejorar la búsqueda de la letra.
    """
    # Quitamos corchetes y paréntesis con regex
    titulo = re.sub(r'\[.*?\]', '', titulo)
    titulo = re.sub(r'\(.*?\)', '', titulo)
    # Quitamos palabras irrelevantes
    titulo = titulo.replace("Official Video", "").replace("Lyrics", "").replace("Official Audio", "").strip()
    return titulo

def obtener_titulo_seguro(url_youtube):
    """
    Usa la API oEmbed de YouTube. 
    Es oficial, no requiere login y no suele bloquear servidores.
    """
    try:
        oembed_url = f"https://www.youtube.com/oembed?url={url_youtube}&format=json"
        respuesta = requests.get(oembed_url)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            return datos.get('title')
        else:
            print(f"Error oEmbed: {respuesta.status_code}")
            return None
    except Exception as e:
        print(f"Error conectando a YouTube: {e}")
        return None

def parsear_lrc_a_json(lrc_texto):
    """Convierte texto LRC a JSON"""
    lineas_json = []
    patron = r'\[(\d+):(\d+\.\d+)\](.*)'
    
    for linea in lrc_texto.split('\n'):
        match = re.match(patron, linea)
        if match:
            minutos = int(match.group(1))
            segundos = float(match.group(2))
            texto = match.group(3).strip()
            tiempo_total = (minutos * 60) + segundos
            
            if texto:
                lineas_json.append({
                    "time": tiempo_total,
                    "text": texto
                })
    return lineas_json

# RUTA DE BIENVENIDA (Para que no salga error 404 al entrar directo)
@app.route('/')
def home():
    return "Servidor de Karaoke Funcionando 🎤"

# RUTA PRINCIPAL
@app.route('/buscar-letra', methods=['GET'])
def buscar_letra():
    url_youtube = request.args.get('url')
    
    if not url_youtube:
        return jsonify({"error": "Falta parametro url"}), 400

    print(f"--- Procesando: {url_youtube} ---")

    try:
        # 1. Obtener título de forma segura (Sin yt-dlp)
        titulo_original = obtener_titulo_seguro(url_youtube)
        
        if not titulo_original:
            return jsonify({"error": "No se pudo obtener el título del video (Posible bloqueo o link roto)"}), 404

        titulo_limpio = limpiar_titulo(titulo_original)
        print(f"Buscando letra para: '{titulo_limpio}'")

        # 2. Buscar letra
        lrc_resultado = syncedlyrics.search(titulo_limpio)
        
        if not lrc_resultado:
            print("No se encontró letra.")
            return jsonify({
                "found": False,
                "title": titulo_original,
                "lyrics": []
            })

        # 3. Procesar y enviar
        letra_procesada = parsear_lrc_a_json(lrc_resultado)
        
        return jsonify({
            "found": True,
            "title": titulo_original,
            "lyrics": letra_procesada
        })

    except Exception as e:
        print(f"Error interno: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
if __name__ == '__main__':
    # Ejecutamos el servidor en modo debug para ver errores en consola
    # host='0.0.0.0' permite que tu celular (en la misma red WiFi) pueda acceder a tu PC

    app.run(debug=True, host='0.0.0.0', port=5000)
