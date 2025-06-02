
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
import json
from datetime import datetime
import hashlib
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'chatnell-secret-key-2024'

# Data storage files
USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'
FRIENDSHIPS_FILE = 'friendships.json'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static', exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_friendships():
    if os.path.exists(FRIENDSHIPS_FILE):
        with open(FRIENDSHIPS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_friendships(friendships):
    with open(FRIENDSHIPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(friendships, f, ensure_ascii=False, indent=2)

def get_user_friends(username):
    friendships = load_friendships()
    return friendships.get(username, {'friends': [], 'sent_requests': [], 'received_requests': []})

def are_friends(user1, user2):
    user1_friends = get_user_friends(user1)
    return user2 in user1_friends['friends']

def can_send_message(sender, recipient):
    users = load_users()
    recipient_data = users.get(recipient, {})
    
    # Eğer alıcı herkesten mesaj almayı kapattıysa
    if not recipient_data.get('allow_messages_from_all', True):
        # Sadece arkadaşlardan mesaj alabilir
        return are_friends(sender, recipient)
    
    return True

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
            'created_at': datetime.now().isoformat(),
            'profile_photo': None,
            'bio': '',
            'last_seen': datetime.now().isoformat(),
            'status': 'online',
            'allow_messages_from_all': True
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
            users[username]['last_seen'] = datetime.now().isoformat()
            users[username]['status'] = 'online'
            save_users(users)
            return redirect(url_for('dashboard'))
        else:
            flash('Geçersiz kullanıcı adı veya şifre!')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'username' in session:
        users = load_users()
        if session['username'] in users:
            users[session['username']]['status'] = 'offline'
            users[session['username']]['last_seen'] = datetime.now().isoformat()
            save_users(users)
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
    
    # Mesaj gönderme yetkisi kontrolü
    if not can_send_message(session['username'], recipient):
        return jsonify({'success': False, 'error': 'Bu kişiye mesaj göndermek için arkadaş olmanız gerekiyor'})
    
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

@app.route('/profile/<username>')
def profile(username):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    users = load_users()
    
    if username not in users:
        flash('Kullanıcı bulunamadı!')
        return redirect(url_for('dashboard'))
    
    user_info = users[username]
    is_own_profile = username == session['username']
    
    return render_template('profile.html', 
                         profile_user=username, 
                         user_info=user_info,
                         is_own_profile=is_own_profile)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    users = load_users()
    current_user = session['username']
    
    if request.method == 'POST':
        bio = request.form.get('bio', '')
        
        # Handle profile photo upload
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{current_user}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                users[current_user]['profile_photo'] = f"uploads/{filename}"
        
        users[current_user]['bio'] = bio
        save_users(users)
        flash('Profil başarıyla güncellendi!')
        return redirect(url_for('profile', username=current_user))
    
    return render_template('edit_profile.html', user_info=users[current_user])

@app.route('/delete_message', methods=['POST'])
def delete_message():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Oturum açmanız gerekli'})
    
    data = request.get_json()
    message_id = data.get('message_id')
    
    if message_id is None:
        return jsonify({'success': False, 'error': 'Mesaj ID gerekli'})
    
    messages = load_messages()
    
    # Find and delete the message if user owns it
    for i, msg in enumerate(messages):
        if msg.get('id') == message_id and msg['sender'] == session['username']:
            messages[i]['deleted'] = True
            messages[i]['message'] = 'Bu mesaj silindi'
            save_messages(messages)
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Mesaj bulunamadı veya yetkiniz yok'})

@app.route('/search_messages')
def search_messages():
    if 'username' not in session:
        return jsonify([])
    
    query = request.args.get('q', '').lower()
    recipient = request.args.get('recipient', '')
    
    if not query or not recipient:
        return jsonify([])
    
    messages = load_messages()
    results = []
    
    for msg in messages:
        if (msg['sender'] == session['username'] and msg['recipient'] == recipient) or \
           (msg['sender'] == recipient and msg['recipient'] == session['username']):
            if query in msg['message'].lower() and not msg.get('deleted', False):
                results.append(msg)
    
    return jsonify(results[:10])  # Limit to 10 results

@app.route('/get_user_status/<username>')
def get_user_status(username):
    if 'username' not in session:
        return jsonify({'status': 'unknown'})
    
    users = load_users()
    if username in users:
        last_seen = datetime.fromisoformat(users[username].get('last_seen', datetime.now().isoformat()))
        now = datetime.now()
        minutes_ago = (now - last_seen).total_seconds() / 60
        
        if minutes_ago < 5:
            status = 'online'
        elif minutes_ago < 30:
            status = 'away'
        else:
            status = 'offline'
        
        return jsonify({
            'status': status,
            'last_seen': users[username].get('last_seen')
        })
    
    return jsonify({'status': 'unknown'})

@app.route('/send_friend_request', methods=['POST'])
def send_friend_request():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Oturum açmanız gerekli'})
    
    data = request.get_json()
    target_user = data.get('username')
    current_user = session['username']
    
    if not target_user or target_user == current_user:
        return jsonify({'success': False, 'error': 'Geçersiz kullanıcı'})
    
    users = load_users()
    if target_user not in users:
        return jsonify({'success': False, 'error': 'Kullanıcı bulunamadı'})
    
    friendships = load_friendships()
    
    # Mevcut arkadaşlık verilerini al
    current_user_data = friendships.get(current_user, {'friends': [], 'sent_requests': [], 'received_requests': []})
    target_user_data = friendships.get(target_user, {'friends': [], 'sent_requests': [], 'received_requests': []})
    
    # Zaten arkadaş mı kontrol et
    if target_user in current_user_data['friends']:
        return jsonify({'success': False, 'error': 'Zaten arkadaşsınız'})
    
    # Zaten istek gönderilmiş mi kontrol et
    if target_user in current_user_data['sent_requests']:
        return jsonify({'success': False, 'error': 'Zaten arkadaşlık isteği gönderilmiş'})
    
    # İsteği ekle
    current_user_data['sent_requests'].append(target_user)
    target_user_data['received_requests'].append(current_user)
    
    friendships[current_user] = current_user_data
    friendships[target_user] = target_user_data
    
    save_friendships(friendships)
    
    return jsonify({'success': True, 'message': 'Arkadaşlık isteği gönderildi'})

@app.route('/accept_friend_request', methods=['POST'])
def accept_friend_request():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Oturum açmanız gerekli'})
    
    data = request.get_json()
    requester = data.get('username')
    current_user = session['username']
    
    if not requester:
        return jsonify({'success': False, 'error': 'Geçersiz kullanıcı'})
    
    friendships = load_friendships()
    
    current_user_data = friendships.get(current_user, {'friends': [], 'sent_requests': [], 'received_requests': []})
    requester_data = friendships.get(requester, {'friends': [], 'sent_requests': [], 'received_requests': []})
    
    # İstek var mı kontrol et
    if requester not in current_user_data['received_requests']:
        return jsonify({'success': False, 'error': 'Arkadaşlık isteği bulunamadı'})
    
    # Arkadaş listelerine ekle
    current_user_data['friends'].append(requester)
    requester_data['friends'].append(current_user)
    
    # İstekleri kaldır
    current_user_data['received_requests'].remove(requester)
    requester_data['sent_requests'].remove(current_user)
    
    friendships[current_user] = current_user_data
    friendships[requester] = requester_data
    
    save_friendships(friendships)
    
    return jsonify({'success': True, 'message': 'Arkadaşlık isteği kabul edildi'})

@app.route('/reject_friend_request', methods=['POST'])
def reject_friend_request():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Oturum açmanız gerekli'})
    
    data = request.get_json()
    requester = data.get('username')
    current_user = session['username']
    
    if not requester:
        return jsonify({'success': False, 'error': 'Geçersiz kullanıcı'})
    
    friendships = load_friendships()
    
    current_user_data = friendships.get(current_user, {'friends': [], 'sent_requests': [], 'received_requests': []})
    requester_data = friendships.get(requester, {'friends': [], 'sent_requests': [], 'received_requests': []})
    
    # İstek var mı kontrol et
    if requester not in current_user_data['received_requests']:
        return jsonify({'success': False, 'error': 'Arkadaşlık isteği bulunamadı'})
    
    # İstekleri kaldır
    current_user_data['received_requests'].remove(requester)
    requester_data['sent_requests'].remove(current_user)
    
    friendships[current_user] = current_user_data
    friendships[requester] = requester_data
    
    save_friendships(friendships)
    
    return jsonify({'success': True, 'message': 'Arkadaşlık isteği reddedildi'})

@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Oturum açmanız gerekli'})
    
    data = request.get_json()
    friend_username = data.get('username')
    current_user = session['username']
    
    if not friend_username:
        return jsonify({'success': False, 'error': 'Geçersiz kullanıcı'})
    
    friendships = load_friendships()
    
    current_user_data = friendships.get(current_user, {'friends': [], 'sent_requests': [], 'received_requests': []})
    friend_data = friendships.get(friend_username, {'friends': [], 'sent_requests': [], 'received_requests': []})
    
    # Arkadaş mı kontrol et
    if friend_username not in current_user_data['friends']:
        return jsonify({'success': False, 'error': 'Bu kişi arkadaş listenizde değil'})
    
    # Arkadaş listelerinden kaldır
    current_user_data['friends'].remove(friend_username)
    friend_data['friends'].remove(current_user)
    
    friendships[current_user] = current_user_data
    friendships[friend_username] = friend_data
    
    save_friendships(friendships)
    
    return jsonify({'success': True, 'message': 'Arkadaş çıkarıldı'})

@app.route('/get_friendship_data')
def get_friendship_data():
    if 'username' not in session:
        return jsonify({})
    
    current_user = session['username']
    user_data = get_user_friends(current_user)
    
    return jsonify(user_data)

@app.route('/update_message_settings', methods=['POST'])
def update_message_settings():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Oturum açmanız gerekli'})
    
    data = request.get_json()
    allow_messages_from_all = data.get('allow_messages_from_all', True)
    
    users = load_users()
    users[session['username']]['allow_messages_from_all'] = allow_messages_from_all
    save_users(users)
    
    return jsonify({'success': True, 'message': 'Mesaj ayarları güncellendi'})

@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
