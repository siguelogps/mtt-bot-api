from flask import Flask, request, jsonify
from flask_cors import CORS  # 👈 1. IMPORTAMOS CORS AQUÍ
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import requests
import time
import os
import traceback

app = Flask(__name__)
CORS(app)  # 👈 2. LE DAMOS EL PASE VIP A LA APP

# --- RUTA PARA QUE RENDER NO LLORE CON EL 404 ---
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return "El Bot del MTT está vivito y coleando 🤖💚", 200

# Tu API KEY de 2Captcha
API_KEY_2CAPTCHA = os.environ.get('API_KEY_2CAPTCHA', 'bc98524218c99fabc1ed5991aa984b38')

def resolver_captcha(base64_img):
    print("Enviando imagen a 2Captcha...")
    url_in = "http://2captcha.com/in.php"
    payload = {'key': API_KEY_2CAPTCHA, 'method': 'base64', 'body': base64_img, 'json': 1}
    response = requests.post(url_in, data=payload).json()
    if response.get('status') != 1: return None
    
    captcha_id = response.get('request')
    url_res = f"http://2captcha.com/res.php?key={API_KEY_2CAPTCHA}&action=get&id={captcha_id}&json=1"
    
    for _ in range(15):
        time.sleep(5)
        res = requests.get(url_res).json()
        if res.get('status') == 1: return res.get('request')
        elif res.get('request') != 'CAPCHA_NOT_READY': return None
    return None

@app.route('/api/multas', methods=['POST'])
def consultar():
    data = request.json
    patente = data.get('patente')
    if not patente:
        return jsonify({"error": "Falta la patente"}), 400

    print(f"Buscando patente: {patente}")
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.get("http://rrvv.fiscalizacion.cl/")
        time.sleep(15)

        img_element = driver.find_element(By.XPATH, "//img[contains(@src, 'base64')]")
        texto_captcha = resolver_captcha(img_element.screenshot_as_base64)
        if not texto_captcha: raise Exception("Fallo resolución CAPTCHA. Revisa tu saldo o API KEY.")

        driver.find_element(By.ID, "patente").send_keys(patente)
        driver.find_element(By.ID, "captcha_response").send_keys(texto_captcha)
        driver.find_element(By.ID, "bBuscarPatente").click()
        time.sleep(5)

        texto_general = driver.find_element(By.ID, "containerResult").text.lower()
        
        # 1. CASO FELIZ: No hay multas
        if "no presenta infracciones" in texto_general or "no se encontraron" in texto_general:
            driver.quit()
            return jsonify({"patente": patente, "multas": [], "total": 0, "exito": True}), 200

        # 2. CASO ALERTA: Hay multas. Vamos a raspar la tabla y buscar la paginación.
        multas_extraidas = []
        
        while True:
            # Extraemos las filas de la tabla de resultados (saltando la cabecera)
            filas = driver.find_elements(By.XPATH, "//div[@id='containerResult']//table//tr")
            for fila in filas[1:]:
                columnas = fila.find_elements(By.TAG_NAME, "td")
                if len(columnas) >= 3:
                    multas_extraidas.append({
                        "fecha": columnas[0].text.strip(),
                        "motivo": columnas[1].text.strip(),
                        "juzgado": columnas[2].text.strip()
                    })
            
            # Buscamos el botón de Siguiente Página (usualmente un link con '>>' o la palabra 'Siguiente')
            try:
                btn_siguiente = driver.find_element(By.XPATH, "//a[contains(text(), '>>') or contains(text(), 'Siguiente')]")
                btn_siguiente.click()
                time.sleep(3) # Esperamos a que cargue la nueva página
            except:
                break # Si no hay botón de siguiente, salimos del bucle

        driver.quit()
        return jsonify({"patente": patente, "multas": multas_extraidas, "total": len(multas_extraidas), "exito": True}), 200
        
    except Exception as e:
        print("🚨 EXPLOSIÓN INTERNA:")
        traceback.print_exc()
        if 'driver' in locals(): driver.quit()
        return jsonify({"error": str(e), "exito": False}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
