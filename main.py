
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
import json
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Data storage files
USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_messages(messages):
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        users = load_users()
        
        if username in users:
            flash('Kullanıcı adı zaten mevcut!')
            return render_template('register.html')
        
        users[username] = {
            'password': hash_password(password),
            'email': email,
            'created_at': datetime.now().isoformat()
        }
        
        save_users(users)
        flash('Kayıt başarılı! Giriş yapabilirsiniz.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users = load_users()
        
        if username in users and users[username]['password'] == hash_password(password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Geçersiz kullanıcı adı veya şifre!')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    users = load_users()
    user_list = [user for user in users.keys() if user != session['username']]
    
    return render_template('dashboard.html', users=user_list)

@app.route('/chat/<recipient>')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    recipient = request.view_args['recipient']
    users = load_users()
    
    if recipient not in users:
        flash('Kullanıcı bulunamadı!')
        return redirect(url_for('dashboard'))
    
    return render_template('chat.html', recipient=recipient)

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Oturum açmanız gerekli'})
    
    data = request.get_json()
    recipient = data.get('recipient')
    message = data.get('message')
    
    if not recipient or not message:
        return jsonify({'success': False, 'error': 'Geçersiz veri'})
    
    messages = load_messages()
    
    new_message = {
        'id': len(messages),
        'sender': session['username'],
        'recipient': recipient,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    
    messages.append(new_message)
    save_messages(messages)
    
    return jsonify({'success': True})

@app.route('/get_messages/<recipient>')
def get_messages():
    if 'username' not in session:
        return jsonify([])
    
    recipient = request.view_args['recipient']
    messages = load_messages()
    
    # Get conversation between current user and recipient
    conversation = []
    for msg in messages:
        if (msg['sender'] == session['username'] and msg['recipient'] == recipient) or \
           (msg['sender'] == recipient and msg['recipient'] == session['username']):
            conversation.append(msg)
    
    # Sort by timestamp
    conversation.sort(key=lambda x: x['timestamp'])
    
    return jsonify(conversation)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
