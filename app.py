from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import requests
import time
import os
import traceback

app = Flask(__name__)

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
    options.add_argument('--headless=new') # El nuevo modo fantasma ultra sigiloso
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    # 💥 LA MAGIA: Quitamos la ruta manual y el Service. 
    # Selenium descargará su propio Chrome automáticamente.
    try:
        driver = webdriver.Chrome(options=options)
        driver.get("http://rrvv.fiscalizacion.cl/")
        time.sleep(3)

        img_element = driver.find_element(By.XPATH, "//img[contains(@src, 'base64')]")
        texto_captcha = resolver_captcha(img_element.screenshot_as_base64)
        if not texto_captcha: raise Exception("Fallo resolución CAPTCHA. Revisa tu saldo o API KEY.")

        driver.find_element(By.ID, "patente").send_keys(patente)
        driver.find_element(By.ID, "captcha_response").send_keys(texto_captcha)
        driver.find_element(By.ID, "bBuscarPatente").click()

        time.sleep(5)
        resultado = driver.find_element(By.ID, "containerResult").text
        
        driver.quit()
        return jsonify({"patente": patente, "resultado": resultado, "exito": True})
        
    except Exception as e:
        print("🚨 EXPLOSIÓN INTERNA:")
        traceback.print_exc()
        if 'driver' in locals(): driver.quit()
        # Cambiamos a status 200 para que Node.js no oculte el error y lo veas en la pantalla de tu compu
        return jsonify({"error": str(e), "exito": False}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
