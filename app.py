from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from deepface import DeepFace
from datetime import datetime
import os
import json
import webbrowser

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

USERS_FILE = 'users.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()

        if username in users:
            return "<p>User already exists. Try logging in.</p>"

        hashed_pw = generate_password_hash(password)
        users[username] = {"password": hashed_pw, "wishlist": {}, "history": []}
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()
        user = users.get(username)

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        return "<p>Invalid credentials.</p>"
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    users = load_users()
    username = session['username']
    user_data = users[username]

    if request.method == 'POST':
        emotion = request.form.get('emotion')
        platform = request.form.get('platform')
        link = request.form.get('link')

        if emotion and platform and link:
            if emotion not in user_data['wishlist']:
                user_data['wishlist'][emotion] = {}
            user_data['wishlist'][emotion][platform] = link
            save_users(users)

    return render_template('dashboard.html', wishlist=user_data['wishlist'])

@app.route('/detect', methods=['GET', 'POST'])
def detect():
    if 'username' not in session:
        return redirect(url_for('login'))

    users = load_users()
    user_data = users[session['username']]

    if request.method == 'POST':
        image = request.files.get('image')
        platform = request.form.get('platform')
        if image:
            path = os.path.join(UPLOAD_FOLDER, image.filename)
            image.save(path)
            try:
                result = DeepFace.analyze(img_path=path, actions=['emotion'], enforce_detection=False)
                emotion = result[0]['dominant_emotion']
                link = user_data['wishlist'].get(emotion, {}).get(platform)

                # Save to history
                user_data['history'].append({
                    "emotion": emotion,
                    "platform": platform,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "link": link if link else ""
                })
                save_users(users)

                if link:
                    # Redirect to the correct platform based on the user's choice (YouTube/Spotify)
                    if platform == "youtube":
                        return redirect(link)  # Redirect to the YouTube URL
                    elif platform == "spotify":
                        return redirect(link)  # Redirect to the Spotify URL
                    else:
                        return f"<p>Unsupported platform: {platform}</p>"
                else:
                    return f"""
                        <h2>Emotion: {emotion.capitalize()}</h2>
                        <p>No {platform.capitalize()} link found in your wishlist.</p>
                        <p><a href='/dashboard'>Add one in Dashboard</a></p>
                    """
            except Exception as e:
                return f"<p>Error during emotion detection: {str(e)}</p>"

    return render_template('detect.html')

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))

    users = load_users()
    username = session['username']
    user_data = users[username]

    if request.method == 'POST':
        current = request.form.get('current')
        new = request.form.get('new')

        if check_password_hash(user_data['password'], current):
            user_data['password'] = generate_password_hash(new)
            save_users(users)
            return "<p>Password changed successfully.</p><a href='/dashboard'>Back</a>"
        else:
            return "<p>Incorrect current password.</p>"

    return render_template('change_password.html')

@app.route('/history')
def history():
    if 'username' not in session:
        return redirect(url_for('login'))
    users = load_users()
    history = users[session['username']].get('history', [])
    return render_template('history.html', history=history)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
