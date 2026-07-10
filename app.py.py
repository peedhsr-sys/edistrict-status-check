from flask import Flask, request, render_template_string, jsonify
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def get_status(app_number, captcha_solution):
    """
    eDistrict UP से status चेक करें
    """
    session = requests.Session()
    base_url = "https://edistrict.up.gov.in/edistrict/showStatushome.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://edistrict.up.gov.in/edistrict/showStatushome.aspx',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    try:
        # Step 1: GET request to fetch ViewState
        response = session.get(base_url, headers=headers)
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Extract hidden fields
        viewstate = soup.find('input', {'id': '__VIEWSTATE'})
        viewstate_generator = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})
        event_validation = soup.find('input', {'id': '__EVENTVALIDATION'})
        
        if not all([viewstate, viewstate_generator, event_validation]):
            return {'error': 'Could not fetch required form fields'}
        
        # Step 2: Prepare POST data
        post_data = {
            '__VIEWSTATE': viewstate.get('value', ''),
            '__VIEWSTATEGENERATOR': viewstate_generator.get('value', ''),
            '__EVENTVALIDATION': event_validation.get('value', ''),
            'txtApplicationNo': app_number,
            'txtCaptcha': captcha_solution,  # Captcha solution यहाँ डालो
            'btnSubmit': 'Search'
        }
        
        # Step 3: POST request to check status
        post_response = session.post(base_url, data=post_data, headers=headers)
        post_soup = BeautifulSoup(post_response.text, 'lxml')
        
        # Step 4: Extract status from response
        # यह HTML structure पर निर्भर करता है - तुम्हें inspect करके सही selector ढूंढना होगा
        status_info = extract_status_info(post_soup)
        
        return {
            'success': True,
            'application_number': app_number,
            'status': status_info,
            'raw_html': str(post_soup.find('body'))[:500]  # First 500 chars for debugging
        }
        
    except Exception as e:
        return {'error': str(e)}

def extract_status_info(soup):
    """
    Response HTML से status information extract करें
    """
    status_data = {}
    
    # Common selectors try करें - तुम्हें अपने response के हिसाब से adjust करना होगा
    try:
        # Table में data हो सकता है
        tables = soup.find_all('table')
        for table in tables:
            if 'status' in str(table).lower() or 'application' in str(table).lower():
                status_data['table_found'] = True
                break
        
        # Div में data हो सकता है
        status_divs = soup.find_all('div', class_=re.compile(r'status|result|info', re.I))
        if status_divs:
            status_data['divs_found'] = len(status_divs)
            
    except:
        pass
    
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
        return jsonify({'error': 'Application number is required'})
    
    result = get_status(app_number, captcha)
    return jsonify(result)

@app.route('/api/status/<app_number>')
def api_status(app_number):
    """
    Direct API endpoint - Captcha manually handle करना होगा
    """
    captcha = request.args.get('captcha', '')
    result = get_status(app_number, captcha)
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
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 600;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        button:active {
            transform: translateY(0);
        }
        #result {
            margin-top: 20px;
            padding: 20px;
            border-radius: 5px;
            display: none;
        }
        .success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .loading {
            text-align: center;
            color: #667eea;
            font-weight: 600;
        }
        .info-box {
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 3px;
        }
        .info-box h3 {
            color: #1976D2;
            margin-bottom: 10px;
            font-size: 16px;
        }
        .info-box p {
            color: #555;
            font-size: 14px;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 eDistrict UP Status Checker</h1>
        <p class="subtitle">अपने application का status तुरंत चेक करें</p>
        
        <div class="info-box">
            <h3>📋 Instructions:</h3>
            <p>
                1. अपना Application Number डालें<br>
                2. Captcha को manually solve करें और यहाँ डालें<br>
                3. "Check Status" बटन दबाएं
            </p>
        </div>
        
        <div class="form-group">
            <label for="appNumber">Application Number:</label>
            <input type="text" id="appNumber" placeholder="उदाहरण: UP1234567890">
        </div>
        
        <div class="form-group">
            <label for="captcha">Captcha Code:</label>
            <input type="text" id="captcha" placeholder="Captcha यहाँ टाइप करें">
        </div>
        
        <button onclick="checkStatus()">Check Status</button>
        
        <div id="result"></div>
    </div>

    <script>
        async function checkStatus() {
            const appNumber = document.getElementById('appNumber').value.trim();
            const captcha = document.getElementById('captcha').value.trim();
            const resultDiv = document.getElementById('result');
            
            if (!appNumber) {
                alert('कृपया Application Number डालें');
                return;
            }
            
            if (!captcha) {
                alert('कृपया Captcha Code डालें');
                return;
            }
            
            resultDiv.style.display = 'block';
            resultDiv.className = 'loading';
            resultDiv.innerHTML = '⏳ Processing... कृपया प्रतीक्षा करें';
            
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
                    resultDiv.innerHTML = `<strong>Error:</strong> ${data.error}`;
                } else {
                    resultDiv.className = 'success';
                    resultDiv.innerHTML = `
                        <h3>✅ Status Found!</h3>
                        <p><strong>Application Number:</strong> ${data.application_number}</p>
                        <p><strong>Status:</strong> ${JSON.stringify(data.status, null, 2)}</p>
                        ${data.raw_html ? `<details><summary>View Raw HTML</summary><pre>${data.raw_html}</pre></details>` : ''}
                    `;
                }
            } catch (error) {
                resultDiv.className = 'error';
                resultDiv.innerHTML = `<strong>Error:</strong> ${error.message}`;
            }
        }
        
        // Enter key press पर भी check हो
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
    app.run(debug=True, port=5000)