from flask import Flask, request, jsonify
from flask_cors import CORS
import syncedlyrics
from yt_dlp import YoutubeDL
import re

app = Flask(__name__)
# CORS permite que tu App (React Native) hable con este Server sin bloqueos de seguridad
CORS(app)

def limpiar_titulo(titulo):
    """
    Limpia 'basura' del título de YouTube para buscar mejor la letra.
    Ej: "Linkin Park - Numb (Official Video) [4K]" -> "Linkin Park - Numb"
    """
    # Quitamos lo que esté entre paréntesis () o corchetes []
    titulo = re.sub(r'\[.*?\]', '', titulo)
    titulo = re.sub(r'\(.*?\)', '', titulo)
    # Quitamos espacios extra y palabras comunes que estorban
    titulo = titulo.replace("Official Video", "").replace("Lyrics", "").strip()
    return titulo

def parsear_lrc_a_json(lrc_texto):
    """
    Transforma el texto plano LRC en una lista de objetos JSON.
    Entrada: "[00:12.50] Hola mundo"
    Salida:  {"time": 12.5, "text": "Hola mundo"}
    """
    lineas_json = []
    # Regex para encontrar patrones de tiempo [mm:ss.xx]
    patron = r'\[(\d+):(\d+\.\d+)\](.*)'
    
    for linea in lrc_texto.split('\n'):
        match = re.match(patron, linea)
        if match:
            minutos = int(match.group(1))
            segundos = float(match.group(2))
            texto = match.group(3).strip()
            
            # Convertimos todo a segundos totales (float) para facilitar la app
            tiempo_total = (minutos * 60) + segundos
            
            if texto: # Solo guardamos si hay texto (evitamos líneas vacías)
                lineas_json.append({
                    "time": tiempo_total,
                    "text": texto
                })
    return lineas_json

@app.route('/buscar-letra', methods=['GET'])
def buscar_letra():
    # 1. Recibir la URL desde la App
    url_youtube = request.args.get('url')
    
    if not url_youtube:
        return jsonify({"error": "Por favor envía un parámetro 'url'"}), 400

    print(f"--- Nueva petición recibida para: {url_youtube} ---")

    try:
        # 2. Obtener el título real del video usando yt-dlp
        # Usamos 'extract_flat' para que sea rápido y no intente descargar video
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url_youtube, download=False)
            titulo_original = info.get('title', 'Desconocido')
            video_id = info.get('id')
            
        titulo_limpio = limpiar_titulo(titulo_original)
        print(f"Buscando letra para: '{titulo_limpio}'")

        # 3. Buscar la letra sincronizada (LRC)
        # syncedlyrics busca en Musixmatch, Deezer, etc.
        lrc_resultado = syncedlyrics.search(titulo_limpio)
        
        if not lrc_resultado:
            print("No se encontró letra sincronizada.")
            return jsonify({
                "found": False,
                "video_id": video_id,
                "title": titulo_original
            })

        # 4. Procesar la letra para enviarla
        letra_procesada = parsear_lrc_a_json(lrc_resultado) 
        
        print("¡Letra encontrada y procesada!")
        
        return jsonify({
            "found": True,
            "video_id": video_id,
            "title": titulo_original,
            "lyrics": letra_procesada
        })

    except Exception as e:
        print(f"Error en el servidor: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ejecutamos el servidor en modo debug para ver errores en consola
    # host='0.0.0.0' permite que tu celular (en la misma red WiFi) pueda acceder a tu PC
    app.run(debug=True, host='0.0.0.0', port=5000)