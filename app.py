from flask import Flask, request, render_template_string, jsonify
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)

def get_status(app_number, captcha_solution):
    session = requests.Session()
    base_url = "https://edistrict.up.gov.in/edistrict/showStatushome.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://edistrict.up.gov.in/edistrict/showStatushome.aspx',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    try:
        # Step 1: GET request to fetch ViewState
        response = session.get(base_url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract hidden fields
        viewstate = soup.find('input', {'id': '__VIEWSTATE'})
        viewstate_generator = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})
        event_validation = soup.find('input', {'id': '__EVENTVALIDATION'})
        
        if not all([viewstate, viewstate_generator, event_validation]):
            return {'error': 'Could not fetch required form fields from website'}
        
        # Step 2: Prepare POST data
        post_data = {
            '__VIEWSTATE': viewstate.get('value', ''),
            '__VIEWSTATEGENERATOR': viewstate_generator.get('value', ''),
            '__EVENTVALIDATION': event_validation.get('value', ''),
            'txtApplicationNo': app_number,
            'txtCaptcha': captcha_solution,
            'btnSubmit': 'Search'
        }
        
        # Step 3: POST request to check status
        post_response = session.post(base_url, data=post_data, headers=headers, timeout=30)
        post_soup = BeautifulSoup(post_response.text, 'html.parser')
        
        # Step 4: Extract status from response
        status_info = extract_status_info(post_soup)
        
        return {
            'success': True,
            'application_number': app_number,
            'status': status_info,
            'message': 'Status check completed'
        }
        
    except requests.exceptions.Timeout:
        return {'error': 'Request timed out. Please try again.'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Request failed: {str(e)}'}
    except Exception as e:
        return {'error': f'Error: {str(e)}'}

def extract_status_info(soup):
    status_data = {}
    try:
        # Look for tables
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            table_text = str(table).lower()
            if any(keyword in table_text for keyword in ['status', 'application', 'result']):
                status_data[f'table_{i}'] = 'found'
        
        # Look for divs with status-related classes
        status_divs = soup.find_all('div', class_=re.compile(r'status|result|info|message', re.I))
        if status_divs:
            status_data['divs_found'] = len(status_divs)
            for i, div in enumerate(status_divs[:3]):
                status_data[f'div_{i}_text'] = div.get_text(strip=True)[:200]
                
        # Look for spans
        spans = soup.find_all('span')
        for span in spans:
            text = span.get_text(strip=True)
            if len(text) > 10 and len(text) < 500:
                if 'status' in text.lower() or 'application' in text.lower():
                    status_data['span_found'] = text
                    
    except Exception as e:
        status_data['extraction_error'] = str(e)
    
    return status_data

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/check-status', methods=['POST'])
def check_status_api():
    data = request.get_json() or request.form
    
    app_number = data.get('application_number', '').strip()
    captcha = data.get('captcha', '').strip()
    
    if not app_number:
        return jsonify({'error': 'Application number is required'}), 400
    
    if not captcha:
        return jsonify({'error': 'Captcha is required'}), 400
    
    result = get_status(app_number, captcha)
    return jsonify(result)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'message': 'Service is running'})

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
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 700px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 15px 50px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
            font-size: 32px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }
        .form-group {
            margin-bottom: 25px;
        }
        label {
            display: block;
            margin-bottom: 10px;
            color: #555;
            font-weight: 600;
            font-size: 15px;
        }
        input[type="text"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: all 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
        }
        button {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102,126,234,0.4);
        }
        button:active {
            transform: translateY(0);
        }
        #result {
            margin-top: 25px;
            padding: 25px;
            border-radius: 8px;
            display: none;
            animation: slideIn 0.3s ease;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .success {
            background: #d4edda;
            border: 2px solid #c3e6cb;
            color: #155724;
        }
        .error {
            background: #f8d7da;
            border: 2px solid #f5c6cb;
            color: #721c24;
        }
        .loading {
            text-align: center;
            color: #667eea;
            font-weight: 600;
            font-size: 16px;
        }
        .info-box {
            background: #e7f3ff;
            border-left: 5px solid #2196F3;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 5px;
        }
        .info-box h3 {
            color: #1976D2;
            margin-bottom: 12px;
            font-size: 18px;
        }
        .info-box p {
            color: #555;
            font-size: 15px;
            line-height: 1.8;
        }
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
        <h1>🎯 eDistrict UP Status Checker</h1>
        <p class="subtitle">अपने application का status तुरंत चेक करें</p>
        
        <div class="info-box">
            <h3>📋 Instructions / निर्देश:</h3>
            <p>
                1. अपना Application Number डालें<br>
                2. Captcha को manually solve करें और यहाँ डालें<br>
                3. "Check Status" बटन दबाएं<br>
                4. कुछ सेकंड में status दिख जाएगा
            </p>
        </div>
        
        <div class="form-group">
            <label for="appNumber">Application Number / आवेदन संख्या:</label>
            <input type="text" id="appNumber" placeholder="उदाहरण: UP1234567890">
        </div>
        
        <div class="form-group">
            <label for="captcha">Captcha Code / कैप्चा:</label>
            <input type="text" id="captcha" placeholder="Captcha यहाँ टाइप करें">
        </div>
        
        <button onclick="checkStatus()">Check Status / स्थिति जांचें</button>
        
        <div id="result"></div>
    </div>

    <script>
        async function checkStatus() {
            const appNumber = document.getElementById('appNumber').value.trim();
            const captcha = document.getElementById('captcha').value.trim();
            const resultDiv = document.getElementById('result');
            
            if (!appNumber) {
                alert('कृपया Application Number डालें');
                document.getElementById('appNumber').focus();
                return;
            }
            
            if (!captcha) {
                alert('कृपया Captcha Code डालें');
                document.getElementById('captcha').focus();
                return;
            }
            
            resultDiv.style.display = 'block';
            resultDiv.className = 'loading';
            resultDiv.innerHTML = '⏳ Processing... कृपया प्रतीक्षा करें (15-30 सेकंड)';
            
            try {
                const response = await fetch('/check-status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        application_number: appNumber,
                        captcha: captcha
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = `<strong> Error:</strong> ${data.error}`;
                } else if (data.success) {
                    resultDiv.className = 'success';
                    let statusHTML = `
                        <h3>✅ Status Found!</h3>
                        <p><strong>Application Number:</strong> ${data.application_number}</p>
                        <p><strong>Status:</strong> ${JSON.stringify(data.status, null, 2)}</p>
                    `;
                    resultDiv.innerHTML = statusHTML;
                } else {
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = '<strong>❌ Error:</strong> Unexpected response';
                }
            } catch (error) {
                resultDiv.className = 'error';
                resultDiv.innerHTML = `<strong> Error:</strong> ${error.message}<br><br>
                    <small>यदि यह error बार-बार आ रहा है, तो 1-2 मिनट बाद try करें।</small>`;
            }
        }
        
        // Enter key support
        document.getElementById('appNumber').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') document.getElementById('captcha').focus();
        });
        
        document.getElementById('captcha').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') checkStatus();
        });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
