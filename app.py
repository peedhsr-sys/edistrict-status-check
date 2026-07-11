from flask import Flask, request, render_template_string, jsonify, send_file
import requests
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract
from io import BytesIO
import os
import re

app = Flask(__name__)

def solve_captcha(image_bytes):
    """Captcha image ko text mein convert kare"""
    try:
        img = Image.open(BytesIO(image_bytes))
        img = img.convert('L')  # Grayscale
        text = pytesseract.image_to_string(img, config='--psm 7').strip()
        text = ''.join(e for e in text if e.isalnum())
        return text.upper()
    except Exception as e:
        print(f"OCR Error: {e}")
        return None

def check_status(app_number):
    """eDistrict UP se status check kare"""
    session = requests.Session()
    base_url = "https://edistrict.up.gov.in/edistrict/showStatushome.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://edistrict.up.gov.in/edistrict/showStatushome.aspx',
    }
    
    try:
        # Step 1: Page load karo
        response = session.get(base_url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Hidden fields nikalo
        viewstate = soup.find('input', {'id': '__VIEWSTATE'})
        viewstate_gen = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})
        event_val = soup.find('input', {'id': '__EVENTVALIDATION'})
        
        if not all([viewstate, viewstate_gen, event_val]):
            return {'error': 'Form fields nahi mile'}
        
        # Captcha image dhundho
        captcha_img = soup.find('img', {'id': 'imgCaptcha'})
        if not captcha_img or 'src' not in captcha_img.attrs:
            return {'error': 'Captcha image nahi mila'}
        
        # Captcha URL banayo
        captcha_src = captcha_img['src']
        if captcha_src.startswith('/'):
            captcha_url = f"https://edistrict.up.gov.in{captcha_src}"
        else:
            captcha_url = captcha_src
        
        # Captcha image download karo
        img_response = session.get(captcha_url, timeout=30)
        
        # Auto solve captcha
        captcha_text = solve_captcha(img_response.content)
        
        if not captcha_text:
            return {'error': 'Captcha solve nahi ho saka'}
        
        print(f"Solved Captcha: {captcha_text}")
        
        # POST data banayo
        post_data = {
            '__VIEWSTATE': viewstate.get('value', ''),
            '__VIEWSTATEGENERATOR': viewstate_gen.get('value', ''),
            '__EVENTVALIDATION': event_val.get('value', ''),
            'txtApplicationNo': app_number,
            'txtCaptcha': captcha_text,
            'btnSubmit': 'Search'
        }
        
        # Status check karo
        post_response = session.post(base_url, data=post_data, headers=headers, timeout=30)
        post_soup = BeautifulSoup(post_response.text, 'html.parser')
        
        # Result extract karo
        result = extract_result(post_soup)
        
        return {
            'success': True,
            'application_number': app_number,
            'captcha_used': captcha_text,
            'result': result
        }
        
    except Exception as e:
        return {'error': str(e)}

def extract_result(soup):
    """Response se result nikalo"""
    result_data = {}
    
    # Tables check karo
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key and value:
                    result_data[key] = value
    
    # Agar table mein nahi mila, to body text check karo
    if not result_data:
        body_text = soup.get_text()
        if 'Invalid' in body_text or 'incorrect' in body_text.lower():
            result_data['message'] = 'Invalid Captcha - Dobara try karein'
        elif 'No record' in body_text:
            result_data['message'] = 'Koi record nahi mila'
        else:
            result_data['message'] = 'Response mila, par format samajh nahi aaya'
    
    return result_data

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/check', methods=['POST'])
def check():
    data = request.get_json() or request.form
    app_number = data.get('application_number', '').strip()
    
    if not app_number:
        return jsonify({'error': 'Application number chahiye'}), 400
    
    result = check_status(app_number)
    return jsonify(result)

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <title>eDistrict UP Status Checker</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
            padding: 20px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            max-width: 500px;
            width: 100%;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        input[type="text"] {
            width: 100%;
            padding: 15px;
            margin-bottom: 20px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        #result {
            margin-top: 20px;
            padding: 20px;
            border-radius: 8px;
            display: none;
        }
        .success { background: #d4edda; border: 2px solid #28a745; color: #155724; }
        .error { background: #f8d7da; border: 2px solid #dc3545; color: #721c24; }
        .loading { text-align: center; color: #667eea; font-weight: bold; }
        pre {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 eDistrict UP Status</h1>
        <input type="text" id="appNumber" placeholder="Application Number (e.g., UP1234567890)">
        <button onclick="checkStatus()">Auto Check Status</button>
        <div id="result"></div>
    </div>

    <script>
        async function checkStatus() {
            const appNumber = document.getElementById('appNumber').value.trim();
            const resultDiv = document.getElementById('result');
            
            if (!appNumber) {
                alert('Application number daalo!');
                return;
            }
            
            resultDiv.style.display = 'block';
            resultDiv.className = 'loading';
            resultDiv.innerHTML = '⏳ Captcha solve kar rahe hain... (10-20 sec)';
            
            try {
                const response = await fetch('/check', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({application_number: appNumber})
                });
                
                const data = await response.json();
                
                if (data.error) {
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = `<strong>❌ Error:</strong> ${data.error}`;
                } else {
                    resultDiv.className = 'success';
                    resultDiv.innerHTML = `
                        <h3>✅ Status Found!</h3>
                        <p><strong>Application:</strong> ${data.application_number}</p>
                        <p><strong>Captcha Used:</strong> ${data.captcha_used}</p>
                        <pre>${JSON.stringify(data.result, null, 2)}</pre>
                    `;
                }
            } catch (error) {
                resultDiv.className = 'error';
                resultDiv.innerHTML = `<strong>❌ Error:</strong> ${error.message}`;
            }
        }
        
        document.getElementById('appNumber').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') checkStatus();
        });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
