from flask import Flask, request, render_template_string, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import re
import os
from io import BytesIO

app = Flask(__name__)

# Global session to maintain cookies
sessions = {}

def get_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = requests.Session()
    return sessions[session_id]

@app.route('/captcha-image')
def get_captcha_image():
    """Captcha image fetch करें और display करें"""
    session_id = request.args.get('session', 'default')
    session = get_session(session_id)
    
    base_url = "https://edistrict.up.gov.in/edistrict/showStatushome.aspx"
    
    try:
        # First visit to get captcha
        response = session.get(base_url, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find captcha image
        captcha_img = soup.find('img', {'id': 'imgCaptcha'})
        
        if captcha_img and 'src' in captcha_img.attrs:
            captcha_src = captcha_img['src']
            
            # If relative URL, make it absolute
            if captcha_src.startswith('/'):
                captcha_url = f"https://edistrict.up.gov.in{captcha_src}"
            else:
                captcha_url = captcha_src
            
            # Fetch captcha image
            img_response = session.get(captcha_url, timeout=30)
            
            return send_file(
                BytesIO(img_response.content),
                mimetype='image/jpeg'
            )
        
        return jsonify({'error': 'Captcha image not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_status(app_number, captcha_solution, session_id='default'):
    session = get_session(session_id)
    base_url = "https://edistrict.up.gov.in/edistrict/showStatushome.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://edistrict.up.gov.in/edistrict/showStatushome.aspx',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    try:
        # GET request to fetch ViewState
        response = session.get(base_url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract hidden fields
        viewstate = soup.find('input', {'id': '__VIEWSTATE'})
        viewstate_generator = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})
        event_validation = soup.find('input', {'id': '__EVENTVALIDATION'})
        
        if not all([viewstate, viewstate_generator, event_validation]):
            return {'error': 'Could not fetch required form fields'}
        
        # Prepare POST data
        post_data = {
            '__VIEWSTATE': viewstate.get('value', ''),
            '__VIEWSTATEGENERATOR': viewstate_generator.get('value', ''),
            '__EVENTVALIDATION': event_validation.get('value', ''),
            'txtApplicationNo': app_number,
            'txtCaptcha': captcha_solution,
            'btnSubmit': 'Search'
        }
        
        # POST request
        post_response = session.post(base_url, data=post_data, headers=headers, timeout=30)
        post_soup = BeautifulSoup(post_response.text, 'html.parser')
        
        # Extract status
        status_info = extract_status_info(post_soup)
        
        return {
            'success': True,
            'application_number': app_number,
            'status': status_info
        }
        
    except Exception as e:
        return {'error': str(e)}

def extract_status_info(soup):
    status_data = {}
    try:
        tables = soup.find_all('table')
        for table in tables:
            if 'status' in str(table).lower():
                status_data['table_found'] = True
                break
        
        status_divs = soup.find_all('div', class_=re.compile(r'status|result|info', re.I))
        if status_divs:
            status_data['divs_found'] = len(status_divs)
            for i, div in enumerate(status_divs[:3]):
                status_data[f'div_{i}'] = div.get_text(strip=True)[:200]
                
    except Exception as e:
        status_data['error'] = str(e)
    
    return status_data

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/check-status', methods=['POST'])
def check_status_api():
    data = request.get_json() or request.form
    app_number = data.get('application_number', '').strip()
    captcha = data.get('captcha', '').strip()
    session_id = data.get('session_id', 'default')
    
    if not app_number:
        return jsonify({'error': 'Application number required'}), 400
    if not captcha:
        return jsonify({'error': 'Captcha required'}), 400
    
    result = get_status(app_number, captcha, session_id)
    return jsonify(result)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>eDistrict UP Status Checker</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        h1 { text-align: center; color: #333; margin-bottom: 20px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #555; }
        input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        .captcha-box {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
            margin-bottom: 20px;
        }
        .captcha-box img {
            border: 2px solid #333;
            border-radius: 5px;
            margin: 10px 0;
            max-width: 100%;
            background: white;
        }
        .refresh-captcha {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-captcha:hover { background: #5568d3; }
        button[type="submit"] {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
        }
        button[type="submit"]:hover { transform: translateY(-2px); }
        #result {
            margin-top: 20px;
            padding: 20px;
            border-radius: 5px;
            display: none;
        }
        .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .loading { text-align: center; color: #667eea; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 eDistrict UP Status Checker</h1>
        
        <div class="form-group">
            <label>Application Number:</label>
            <input type="text" id="appNumber" placeholder="UP1234567890">
        </div>
        
        <div class="captcha-box">
            <label>Captcha:</label>
            <img id="captchaImg" src="/captcha-image?session=default" alt="Captcha" style="display:none;">
            <br>
            <button type="button" class="refresh-captcha" onclick="refreshCaptcha()">🔄 Refresh Captcha</button>
            <br><br>
            <input type="text" id="captcha" placeholder="Captcha यहाँ टाइप करें" style="width:200px;">
        </div>
        
        <button type="submit" onclick="checkStatus()">Check Status</button>
        
        <div id="result"></div>
    </div>

    <script>
        let sessionId = 'default_' + Date.now();
        
        // Show captcha image when it loads
        document.getElementById('captchaImg').onload = function() {
            this.style.display = 'inline-block';
        };
        
        function refreshCaptcha() {
            sessionId = 'session_' + Date.now();
            document.getElementById('captchaImg').src = '/captcha-image?session=' + sessionId + '&t=' + Date.now();
            document.getElementById('captcha').value = '';
            document.getElementById('captcha').focus();
        }
        
        async function checkStatus() {
            const appNumber = document.getElementById('appNumber').value.trim();
            const captcha = document.getElementById('captcha').value.trim();
            const resultDiv = document.getElementById('result');
            
            if (!appNumber) { alert('Application Number डालें'); return; }
            if (!captcha) { alert('Captcha डालें'); return; }
            
            resultDiv.style.display = 'block';
            resultDiv.className = 'loading';
            resultDiv.innerHTML = '⏳ Processing...';
            
            try {
                const response = await fetch('/check-status', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        application_number: appNumber,
                        captcha: captcha,
                        session_id: sessionId
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = `<strong>Error:</strong> ${data.error}`;
                } else {
                    resultDiv.className = 'success';
                    resultDiv.innerHTML = `<h3>✅ Status Found!</h3><pre>${JSON.stringify(data, null, 2)}</pre>`;
                }
            } catch (error) {
                resultDiv.className = 'error';
                resultDiv.innerHTML = `<strong>Error:</strong> ${error.message}`;
            }
        }
        
        // Auto load captcha on page load
        window.onload = function() {
            refreshCaptcha();
        };
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
