import os
import pandas as pd
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# --- TUS CREDENCIALES (Configuradas para Producción) ---
WHATSAPP_TOKEN = 'EAANWuMDMXXABQiCWb98z3hiATEXksdRaLImoZBxEADIa3p7ydtANiPgxtIbtU81bFAxIketlSCzaZChM0hyYdRlofyFZBDIuZBB9mlSi86cJVxgjPvBKo8AeU3rjLZClaNIhoh1RtqUmeb0EmjeZCxokHi57IwZCMr4eOo7sGH6hKAX2czkqtEkuJ2k4ZAeWw8MITx8fgICZC0ZB6trZAbZCF0ZCeW8iGWICpoyPqNk2nK2mUzq7hAQEoIcw9E8CqNTOLwPTqezHZBLAjrr5G3y3QZAEVnOZCgZDZD'
PHONE_ID = '935331223004041'
VERIFY_TOKEN = 'ingenio123'

# --- CARGAR EL EXCEL ---
# Buscamos el archivo en la ruta actual
print(f"📂 Directorio actual de trabajo: {os.getcwd()}")
ARCHIVO_EXCEL = 'inventario.xlsx'

try:
    if os.path.exists(ARCHIVO_EXCEL):
        print("📂 Archivo encontrado. Cargando base de datos...")
        df = pd.read_excel(ARCHIVO_EXCEL, engine='openpyxl')
        # Limpieza de datos: Convertir todo a texto
        df = df.fillna('').astype(str)
        print(f"✅ ÉXITO: Inventario cargado con {len(df)} registros.")
    else:
        print(f"⚠️ ADVERTENCIA: No encuentro el archivo '{ARCHIVO_EXCEL}'. El bot funcionará pero no buscará datos.")
        df = pd.DataFrame()
except Exception as e:
    print(f"❌ ERROR CRÍTICO cargando Excel: {e}")
    df = pd.DataFrame()

# --- RUTAS DEL SERVIDOR ---

@app.route('/')
def home():
    # Esta ruta sirve para saber si el servidor está vivo
    return "🤖 Bot de Soporte IT - Ingenio El Ángel: ONLINE 🟢"

# 1. Verificación del Webhook (Para Meta)
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("✅ Webhook verificado correctamente.")
            return str(challenge), 200
        else:
            print("⛔ Token de verificación incorrecto.")
            return 'Forbidden', 403
    return 'Bad Request', 400

# 2. Recepción de Mensajes
@app.route('/webhook', methods=['POST'])
def webhook():
    body = request.json
    
    if body.get('object'):
        try:
            # Navegar el JSON de WhatsApp
            if (
                body.get('entry') and 
                body['entry'][0].get('changes') and 
                body['entry'][0]['changes'][0].get('value') and 
                body['entry'][0]['changes'][0]['value'].get('messages')
            ):
                message = body['entry'][0]['changes'][0]['value']['messages'][0]
                
                # Datos del remitente
                numero_remitente = message['from'] 
                texto_mensaje = message.get('text', {}).get('body', '')

                print(f"📩 Mensaje de {numero_remitente}: {texto_mensaje}")

                if texto_mensaje:
                    procesar_intencion(numero_remitente, texto_mensaje)
            else:
                pass # Ignorar estados de lectura/envío
                
        except Exception as e:
            print(f"⚠️ Error procesando mensaje: {e}")
            
        return 'EVENT_RECEIVED', 200
    else:
        return 'Not Found', 404

# --- LÓGICA DEL BOT ---

def procesar_intencion(numero, texto):
    texto_limpio = texto.lower().strip()
    
    # Saludos
    if texto_limpio in ['hola', 'buenos dias', 'buenas', 'ayuda', 'menu', 'inicio']:
        bienvenida = (
            "👋 *Soporte IT - Ingenio El Ángel*\n\n"
            "Sistema de Inventario en Línea.\n"
            "Escribe *buscar [dato]* para consultar.\n\n"
            "Ejemplos:\n"
            "🔍 _buscar 5CD944_\n"
            "👤 _buscar emerson_\n"
            "💻 _buscar laptop_"
        )
        enviar_whatsapp(numero, bienvenida)
        return

    # Búsqueda
    if texto_limpio.startswith('buscar '):
        termino = texto_limpio.replace('buscar ', '').strip()
        
        if len(termino) < 3:
            enviar_whatsapp(numero, "⚠️ Escribe al menos 3 letras para buscar.")
            return

        print(f"🔍 Buscando: '{termino}'")

        try:
            if df.empty:
                enviar_whatsapp(numero, "⚠️ La base de datos está vacía o no cargó correctamente.")
                return

            # Filtro flexible
            mask = (
                df['Usuario'].str.lower().str.contains(termino) |
                df['Serie'].str.lower().str.contains(termino) |
                df['Nombre Del Equipo'].str.lower().str.contains(termino) |
                df['Modelo'].str.lower().str.contains(termino)
            )
            
            resultados = df[mask]
            
            if resultados.empty:
                enviar_whatsapp(numero, f"🚫 No encontré equipos con: '{termino}'")
            else:
                # Top 3 resultados
                top = resultados.head(3)
                
                for index, row in top.iterrows():
                    tipo = row.get('Tipo Equipo', '').lower()
                    if "lap" in tipo: icono = "💻"
                    elif "desk" in tipo: icono = "🖥️"
                    elif "imp" in tipo: icono = "🖨️"
                    else: icono = "📦"
                    
                    resp = (
                        f"{icono} *{row.get('Nombre Del Equipo', 'Sin Nombre')}*\n"
                        f"👤 {row.get('Usuario', 'N/A')}\n"
                        f"🏷️ Serie: {row.get('Serie', 'N/A')}\n"
                        f"⚙️ {row.get('Marca', '')} {row.get('Modelo', '')}\n"
                        f"📍 {row.get('Area', 'N/A')}\n"
                        f"📅 Fin: {row.get('Fin Soporte', 'N/A')}"
                    )
                    enviar_whatsapp(numero, resp)
                
                if len(resultados) > 3:
                    enviar_whatsapp(numero, f"➕ ...y {len(resultados)-3} más.")

        except Exception as e:
            print(f"❌ Error en búsqueda: {e}")
            enviar_whatsapp(numero, "⚠️ Error interno al buscar.")
            
    else:
        enviar_whatsapp(numero, "🤖 Comando no reconocido. Escribe: *buscar [dato]*")

# --- ENVIAR A META ---

def enviar_whatsapp(numero, texto):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            print(f"📤 Enviado a {numero}")
        else:
            print(f"⚠️ Error Meta: {response.text}")
    except Exception as e:
        print(f"❌ Error conexión: {e}")

# --- ARRANQUE PARA NUBE ---
if __name__ == '__main__':
    # Render asigna un puerto en la variable de entorno PORT
    # Si no existe (local), usa el 5000
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' es OBLIGATORIO para que Render funcione

    app.run(host='0.0.0.0', port=port)


