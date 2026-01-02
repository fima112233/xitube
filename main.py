from flask import Flask, request, redirect, send_from_directory, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'xitube-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///xitube.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Создаем папку uploads
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Telegram бот (опционально)
TELEGRAM_TOKEN = 'ВАШ_ТОКЕН'
TELEGRAM_CHAT_ID = 'ВАШ_ID'

# Модели
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    videos = db.relationship('Video', backref='author', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True)

class Video(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    likes = db.relationship('Like', backref='video', lazy=True)

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Инициализация базы данных
with app.app_context():
    db.create_all()  # Это создаст все таблицы!
    
    # Создаем тестового пользователя
    if not User.query.first():
        user = User(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(user)
        db.session.commit()
        print("✅ База инициализирована. Логин: admin / admin123")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# HTML шаблон
def render_page(title, content):
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Xitube - {title}</title>
        <style>
            body {{ font-family: Arial; margin: 0; background: #0f0f0f; color: white; }}
            .header {{ background: #ff0000; padding: 15px; }}
            .header a {{ color: white; text-decoration: none; margin: 0 10px; }}
            .container {{ max-width: 1200px; margin: 20px auto; padding: 0 20px; }}
            .video-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }}
            .video-card {{ background: #1f1f1f; padding: 15px; border-radius: 8px; }}
            .btn {{ background: #ff0000; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }}
            input, textarea {{ width: 100%; padding: 10px; margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/">🏠 Xitube</a>
            {f'<a href="/upload">📤 Загрузить</a><a href="/logout">🚪 Выйти</a><span style="float:right;">👤 {current_user.username}</span>' if current_user.is_authenticated else '<a href="/login">🔑 Войти</a><a href="/register">📝 Регистрация</a>'}
            <a href="/filemanager" style="color: yellow;">🗑️ Управление файлами</a>
        </div>
        <div class="container">
            {content}
        </div>
    </body>
    </html>
    '''

# Роуты
@app.route('/')
def index():
    videos = Video.query.order_by(Video.created_at.desc()).all()
    
    video_html = ""
    for video in videos:
        likes = Like.query.filter_by(video_id=video.id).count()
        video_html += f'''
        <div class="video-card">
            <h3><a href="/video/{video.id}" style="color: white;">{video.title}</a></h3>
            <p>👤 {video.author.username} • 👁️ {video.views} • 👍 {likes}</p>
        </div>
        '''
    
    content = f'''
    <h1>🎬 Xitube</h1>
    <div class="video-grid">
        {video_html if video_html else '<p>Пока нет видео. Будьте первым!</p>'}
    </div>
    '''
    return render_page('Главная', content)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            return "Логин занят", 400
        
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect('/')
    
    content = '''
    <h2>Регистрация</h2>
    <form method="POST">
        <input type="text" name="username" placeholder="Логин" required>
        <input type="password" name="password" placeholder="Пароль" required>
        <button class="btn" type="submit">Регистрация</button>
    </form>
    <p><a href="/login">Уже есть аккаунт?</a></p>
    '''
    return render_page('Регистрация', content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect('/')
        
        return "Неверный логин или пароль", 400
    
    content = '''
    <h2>Вход</h2>
    <form method="POST">
        <input type="text" name="username" placeholder="Логин" required>
        <input type="password" name="password" placeholder="Пароль" required>
        <button class="btn" type="submit">Войти</button>
    </form>
    <p><a href="/register">Нет аккаунта?</a></p>
    '''
    return render_page('Вход', content)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        title = request.form.get('title')
        file = request.files.get('video')
        
        if file and allowed_file(file.filename):
            filename = f"{current_user.id}_{datetime.now().timestamp()}.mp4"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            video = Video(title=title, filename=filename, user_id=current_user.id)
            db.session.add(video)
            db.session.commit()
            
            return redirect(f'/video/{video.id}')
    
    content = '''
    <h2>Загрузить видео</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="text" name="title" placeholder="Название" required>
        <input type="file" name="video" accept="video/*" required>
        <button class="btn" type="submit">Загрузить</button>
    </form>
    '''
    return render_page('Загрузка', content)

@app.route('/video/<int:video_id>')
def video_page(video_id):
    video = Video.query.get_or_404(video_id)
    video.views += 1
    db.session.commit()
    
    likes = Like.query.filter_by(video_id=video_id).count()
    
    content = f'''
    <h1>{video.title}</h1>
    <video controls width="100%">
        <source src="/uploads/{video.filename}" type="video/mp4">
    </video>
    <p>👤 {video.author.username} • 👁️ {video.views} • 👍 {likes}</p>
    <form action="/like/{video.id}" method="POST">
        <button class="btn" type="submit">❤️ Лайк</button>
    </form>
    '''
    return render_page(video.title, content)

@app.route('/like/<int:video_id>', methods=['POST'])
@login_required
def like_video(video_id):
    existing = Like.query.filter_by(user_id=current_user.id, video_id=video_id).first()
    if existing:
        db.session.delete(existing)
    else:
        like = Like(user_id=current_user.id, video_id=video_id)
        db.session.add(like)
    
    db.session.commit()
    return redirect(f'/video/{video_id}')

# Управление файлами
@app.route('/filemanager', methods=['GET', 'POST'])
@login_required
def file_manager():
    if current_user.username != 'admin':
        return "Доступ только для админа", 403
    
    if request.method == 'POST':
        filename = request.form.get('filename')
        if filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                
                # Удаляем из базы
                video = Video.query.filter_by(filename=filename).first()
                if video:
                    db.session.delete(video)
                    db.session.commit()
                
                return redirect('/filemanager')
    
    # Список файлов
    files = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        files = os.listdir(app.config['UPLOAD_FOLDER'])
    
    file_html = ""
    for file in files:
        size = os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], file))
        file_html += f'''
        <div style="background: #1f1f1f; padding: 10px; margin: 5px 0; border-radius: 4px;">
            {file} ({size} bytes)
            <form method="POST" style="display:inline;">
                <input type="hidden" name="filename" value="{file}">
                <button type="submit" style="background: red; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">🗑️ Удалить</button>
            </form>
            <a href="/uploads/{file}" target="_blank" style="color: #4CAF50; margin-left: 10px;">▶️ Смотреть</a>
        </div>
        '''
    
    content = f'''
    <h1>🗑️ Управление файлами</h1>
    <p>Папка: {app.config['UPLOAD_FOLDER']}</p>
    <p>Всего файлов: {len(files)}</p>
    {file_html if files else '<p>Файлов нет</p>'}
    
    <h2>Информация о системе (Replit)</h2>
    <pre>{os.uname()}</pre>
    '''
    return render_page('Управление файлами', content)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
