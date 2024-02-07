from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import csv

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_upload_folder():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

last_page_data = []

def read_csv_page(page_size, page_number):
    global last_page_data

    with open(os.path.join(app.config['UPLOAD_FOLDER'], 'input.csv'), 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        data = list(csv_reader)

    start_index = (page_number - 1) * page_size
    end_index = start_index + page_size

    paginated_data = data[start_index:end_index]

    last_page_data = paginated_data

    return paginated_data

@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    global total_rows

    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE')
        response.headers.add('Access-Control-Expose-Headers', 'Content-Type')
        response.headers.add('Referrer-Policy', 'no-referrer-when-downgrade')
        return response

    create_upload_folder()

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Contar as linhas do arquivo CSV
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            total_rows = sum(1 for row in csv_reader)

        response = jsonify({'success': True, 'totalRows': total_rows})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Expose-Headers', 'Content-Type')
        response.headers.add('Referrer-Policy', 'no-referrer-when-downgrade')
        return response

    return jsonify({'error': 'Invalid file format'}), 400

@app.route('/api/data', methods=['GET'])
def get_paginated_data():
    global total_rows

    page_size = int(request.args.get('pageSize', 1000))
    page_number = int(request.args.get('pageNumber', 1))

    paginated_data = read_csv_page(page_size, page_number)

    return jsonify({'data': paginated_data, 'prevData': last_page_data, 'totalRows': total_rows})

@app.route('/api/gerar-boleto', methods=['POST'])
def gerar_boleto():
    try:
        dados_cliente = request.get_json()

        boleto = Boleto(dados_cliente)
        boleto.gerar()

        return jsonify({'success': True, 'boleto': boleto.dados})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/enviar-email', methods=['POST'])
def enviar_email():
    try:
        dados_cliente = request.get_json()

        corpo_email = f"Olá {dados_cliente['nome']},\n\nSegue o seu boleto em anexo."

        msg = MIMEText(corpo_email)
        msg['Subject'] = 'Assunto do E-mail'
        msg['From'] = FROM_EMAIL
        msg['To'] = dados_cliente['email']

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, [dados_cliente['email']], msg.as_string())

        return jsonify({'success': True, 'message': 'E-mail enviado com sucesso'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=1810, debug=True)
