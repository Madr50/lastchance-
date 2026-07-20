# admin_panel.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from config import ADMIN_ID, ACCOUNTS_DIR
from database import add_account, get_all_accounts, get_account, update_account, delete_account

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = ACCOUNTS_DIR
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== API Endpoints ====================

@app.route('/api/accounts', methods=['GET'])
def api_get_accounts():
    status = request.args.get('status', 'available')
    accounts = get_all_accounts(status)
    
    result = []
    for acc in accounts:
        result.append({
            'id': acc[0],
            'name': acc[1],
            'description': acc[2],
            'price': acc[3],
            'category': acc[4],
            'image': f'/images/{os.path.basename(acc[5])}' if acc[5] else '',
            'status': acc[6],
            'created': acc[7]
        })
    
    return jsonify(result)

@app.route('/api/accounts', methods=['POST'])
def api_add_account():
    name = request.form.get('name')
    price = float(request.form.get('price', 0))
    description = request.form.get('description', '')
    category = request.form.get('category', 'twitter')
    
    image_path = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_path = filepath
    
    account_id = add_account(name, description, price, category, image_path)
    return jsonify({'success': True, 'id': account_id})

@app.route('/api/accounts/<int:account_id>', methods=['PUT'])
def api_update_account(account_id):
    updates = {}
    if 'name' in request.form: updates['name'] = request.form['name']
    if 'price' in request.form: updates['price'] = float(request.form['price'])
    if 'description' in request.form: updates['description'] = request.form['description']
    if 'status' in request.form: updates['status'] = request.form['status']
    
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            updates['image_path'] = filepath
    
    update_account(account_id, **updates)
    return jsonify({'success': True})

@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def api_delete_account(account_id):
    delete_account(account_id)
    return jsonify({'success': True})

# تقديم صور الحسابات
@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# تقديم Mini App
@app.route('/mini_app/<path:filename>')
def serve_mini_app(filename):
    return send_from_directory('mini_app', filename)

@app.route('/')
def index():
    return send_from_directory('mini_app', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
