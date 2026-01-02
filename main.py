from flask import Flask, request, redirect, send_from_directory, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'xitube-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///xitube.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv'}

ADMIN_PASSWORD = 'fima1456Game!'
SECRET_ADMIN_URL = 'fima1456admin'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_banned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.Text)
    
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
    is_deleted = db.Column(db.Boolean, default=False)
    delete_reason = db.Column(db.Text)
    
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

with app.app_context():
    db.create_all()
    
    if not User.query.first():
        user = User(
            username='test',
            password_hash=generate_password_hash('test123')
        )
        db.session.add(user)
        db.session.commit()

# КЕШ ДЛЯ ГЛАВНОЙ СТРАНИЦЫ
index_cache = None
index_cache_time = 0
CACHE_TIMEOUT = 30  # секунд

def get_cached_index():
    global index_cache, index_cache_time
    current_time = time.time()
    
    if index_cache is None or (current_time - index_cache_time) > CACHE_TIMEOUT:
        try:
            # БЕЗ ОГРАНИЧЕНИЙ - получаем все видео
            videos = Video.query.filter_by(is_deleted=False).order_by(Video.created_at.desc()).all()
            
            video_html = ""
            for video in videos:
                author_banned = video.author.is_banned if video.author else False
                
                if author_banned:
                    video_html += f'''
                    <div class="video-card banned">
                        <div class="video-info">
                            <div class="video-title">❌ Видео заблокировано</div>
                            <div class="video-meta">Автор заблокирован администрацией</div>
                        </div>
                    </div>
                    '''
                else:
                    # Быстрый подсчет лайков через отношения
                    likes_count = len(video.likes) if video.likes else 0
                    video_html += f'''
                    <a href="/video/{video.id}" style="text-decoration: none; color: inherit;">
                        <div class="video-card">
                            <div style="background: #333; height: 160px; display: flex; align-items: center; justify-content: center; font-size: 40px;">
                                ▶️
                            </div>
                            <div class="video-info">
                                <div class="video-title">{video.title[:50]}{'...' if len(video.title) > 50 else ''}</div>
                                <div class="video-meta">
                                    👤 {video.author.username if video.author else 'Неизвестно'} • 
                                    👁️ {video.views} • 
                                    👍 {likes_count}
                                </div>
                            </div>
                        </div>
                    </a>
                    '''
            
            content = f'''
            <h1>🎬 Xitube - Видео платформа</h1>
            <p style="color: #aaa;">Добро пожаловать на видеохостинг</p>
            
            {current_user.is_authenticated and current_user.is_banned and 
            '<div class="alert">⚠️ ВАШ АККАУНТ ЗАБЛОКИРОВАН! Причина: ' + (current_user.ban_reason or 'Нарушение правил') + '</div>' or ''}
            
            <div class="rules-box">
                <h3>📜 ПРАВИЛА XITUBE:</h3>
                <p>0.1 Администрация имеет полное право блокировать автора</p>
                <p>0.2 Администрация имеет полное право удалять видео</p>
                <p>0.3 Порно +18 и т.д. → блокировка автора</p>
                <p>0.4 Нелегальный контент → бан автора</p>
                <p><a href="/rules" style="color: white; font-weight: bold;">→ Полные правила ←</a></p>
            </div>
            
            <h2>📹 Все видео ({len(videos)})</h2>
            <div class="video-grid">
                {video_html if video_html else '<p>Пока нет видео. Будьте первым!</p>'}
            </div>
            '''
            
            index_cache = render_page('Главная', content)
            index_cache_time = current_time
            
        except Exception as e:
            # Простой fallback HTML
            index_cache = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Xitube</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { font-family: Arial; background: #0f0f0f; color: white; margin: 0; padding: 20px; }
                    a { color: #ff0000; }
                </style>
            </head>
            <body>
                <h1>🎬 Xitube</h1>
                <p>Видео платформа работает</p>
                <p><a href="/login">Войти</a> | <a href="/register">Регистрация</a></p>
            </body>
            </html>
            '''
            index_cache_time = current_time
    
    return index_cache

# ГЛАВНАЯ СТРАНИЦА С КЕШИРОВАНИЕМ
@app.route('/')
def index():
    # ОЧЕНЬ быстрый ответ для health check без генерации страницы
    user_agent = request.headers.get('User-Agent', '')
    if request.method == 'GET' and len(request.args) == 0 and 'curl' not in user_agent.lower() and 'python' not in user_agent.lower():
        # Это может быть health check от Replit
        return get_cached_index(), 200
    
    return get_cached_index(), 200

def render_page(title, content):
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Xitube - {title}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: Arial, sans-serif; background: #0f0f0f; color: white; }}
            .header {{ background: linear-gradient(90deg, #ff0000, #cc0000); padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }}
            .header a {{ color: white; text-decoration: none; margin: 0 10px; font-weight: bold; }}
            .container {{ max-width: 1200px; margin: 20px auto; padding: 0 20px; }}
            .video-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-top: 20px; }}
            .video-card {{ background: #1f1f1f; border-radius: 8px; overflow: hidden; }}
            .video-info {{ padding: 15px; }}
            .video-title {{ font-weight: bold; margin-bottom: 5px; }}
            .video-meta {{ color: #aaa; font-size: 14px; }}
            .btn {{ background: #ff0000; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}
            .danger-btn {{ background: #cc0000; }}
            .success-btn {{ background: #00aa00; }}
            .banned {{ opacity: 0.5; background: #333; }}
            .rules-box {{ background: #ff0000; color: white; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            .alert {{ background: #ff9900; color: black; padding: 15px; border-radius: 8px; margin: 15px 0; }}
            .deleted-video {{ background: #333; padding: 50px; text-align: center; border-radius: 8px; margin: 50px 0; }}
            .admin-panel {{ background: #1a1a1a; padding: 30px; border-radius: 10px; margin: 20px 0; border: 2px solid #ff0000; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 10px; border: 1px solid #333; text-align: left; }}
            th {{ background: #333; }}
            @media (max-width: 768px) {{
                .header {{ flex-direction: column; text-align: center; }}
                .video-grid {{ grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <a href="/">🏠 Xitube</a>
                {current_user.is_authenticated and not current_user.is_banned and '<a href="/upload">📤 Загрузить</a>' or ''}
            </div>
            <div>
                {current_user.is_authenticated and f'<span>👤 {current_user.username}{current_user.is_banned and " (ЗАБЛОКИРОВАН)" or ""}</span> <a href="/logout">🚪 Выйти</a>' or '<a href="/login">🔑 Войти</a> <a href="/register">📝 Регистрация</a>'}
            </div>
        </div>
        <div class="container">
            {content}
        </div>
    </body>
    </html>
    '''

@app.route('/health')
def health_check():
    return 'OK', 200

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/rules')
def rules():
    content = '''
    <div class="rules-box" style="background: #1f1f1f; border: 2px solid #ff0000;">
        <h1>📜 ОФИЦИАЛЬНЫЕ ПРАВИЛА XITUBE</h1>
        
        <h3>🔴 АДМИНИСТРАЦИЯ:</h3>
        <p>1.1 Администрация имеет полное право блокировать любого автора</p>
        <p>1.2 Администрация может удалять любое видео</p>
        <p>1.3 Решения администрации окончательны</p>
        
        <h3>🚫 ЗАПРЕЩЕННЫЙ КОНТЕНТ:</h3>
        <p>2.1 Порнография, эротика 18+</p>
        <p>2.2 Экстремизм, нацизм, терроризм</p>
        <p>2.3 Насилие, жестокость</p>
        <p>2.4 Мошенничество, вредоносный софт</p>
        <p>2.5 Контент нарушающий законы РФ</p>
        
        <h3>⚠️ НАКАЗАНИЯ:</h3>
        <p>3.1 Нарушение правил → блокировка аккаунта</p>
        <p>3.2 Повторные нарушения → перманентный бан</p>
        <p>3.3 Серьезные нарушения → блокировка IP</p>
        
        <p style="margin-top: 30px; font-size: 18px; font-weight: bold;">
            ⚠️ Загружая видео, вы автоматически соглашаетесь с этими правилами!
        </p>
    </div>
    
    <div style="text-align: center; margin-top: 30px;">
        <a href="/" class="btn">← Вернуться на главную</a>
    </div>
    '''
    return render_page('Правила', content)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            return "Этот логин уже занят", 400
        
        if len(password) < 4:
            return "Пароль должен быть не менее 4 символов", 400
        
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect('/')
    
    content = '''
    <h2>📝 Регистрация</h2>
    <div class="alert">
        ⚠️ Регистрируясь, вы соглашаетесь с <a href="/rules" style="color: #000; font-weight: bold;">правилами Xitube</a>
    </div>
    <form method="POST" style="max-width: 400px; margin: 30px auto;">
        <input type="text" name="username" placeholder="Придумайте логин" required style="width: 100%; padding: 12px; margin: 10px 0;">
        <input type="password" name="password" placeholder="Придумайте пароль" required style="width: 100%; padding: 12px; margin: 10px 0;">
        <button type="submit" class="btn" style="width: 100%; padding: 12px;">Создать аккаунт</button>
    </form>
    <p style="text-align: center;"><a href="/login">Уже есть аккаунт?</a></p>
    '''
    return render_page('Регистрация', content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            if user.is_banned:
                return f"Ваш аккаунт заблокирован. Причина: {user.ban_reason}", 403
            login_user(user)
            return redirect('/')
        
        return "Неверный логин или пароль", 400
    
    content = '''
    <h2>🔑 Вход в аккаунт</h2>
    <form method="POST" style="max-width: 400px; margin: 30px auto;">
        <input type="text" name="username" placeholder="Ваш логин" required style="width: 100%; padding: 12px; margin: 10px 0;">
        <input type="password" name="password" placeholder="Ваш пароль" required style="width: 100%; padding: 12px; margin: 10px 0;">
        <button type="submit" class="btn" style="width: 100%; padding: 12px;">Войти</button>
    </form>
    <p style="text-align: center;"><a href="/register">Нет аккаунта?</a></p>
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
    if current_user.is_banned:
        return "Ваш аккаунт заблокирован", 403
    
    if request.method == 'POST':
        title = request.form.get('title')
        file = request.files.get('video')
        
        if not title:
            return "Введите название видео", 400
        
        if not file:
            return "Выберите файл видео", 400
        
        if not allowed_file(file.filename):
            return "Неподдерживаемый формат файла", 400
        
        timestamp = int(datetime.now().timestamp())
        filename = f"{current_user.id}_{timestamp}_{file.filename.replace(' ', '_')}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        video = Video(
            title=title,
            filename=filename,
            user_id=current_user.id
        )
        db.session.add(video)
        db.session.commit()
        
        # Сбросить кеш главной страницы
        global index_cache
        index_cache = None
        
        return redirect(f'/video/{video.id}')
    
    content = '''
    <h2>📤 Загрузить видео</h2>
    
    <div class="alert">
        ⚠️ <strong>ВНИМАНИЕ!</strong> Перед выкладыванием ознакомьтесь с <a href="/rules" style="color: #000; font-weight: bold;">правилами Xitube</a>
    </div>
    
    <form method="POST" enctype="multipart/form-data" style="max-width: 500px; margin: 30px auto;">
        <input type="text" name="title" placeholder="Название видео" required style="width: 100%; padding: 12px; margin: 10px 0;">
        
        <div style="border: 2px dashed #666; padding: 30px; text-align: center; margin: 20px 0; border-radius: 8px;">
            <input type="file" name="video" accept="video/*" required style="font-size: 16px;">
            <p style="color: #aaa; margin-top: 10px;">MP4, AVI, MOV, MKV, WEBM, FLV, WMV</p>
        </div>
        
        <button type="submit" class="btn" style="width: 100%; padding: 15px; font-size: 18px;">
            📤 Опубликовать видео
        </button>
    </form>
    '''
    return render_page('Загрузка', content)

@app.route('/video/<int:video_id>')
def video_page(video_id):
    video = Video.query.get_or_404(video_id)
    
    if video.is_deleted:
        content = f'''
        <div class="deleted-video">
            <h1>🚫 Видео недоступно</h1>
            <p style="font-size: 24px; margin: 20px 0;">
                Данное видео удалено администрацией
            </p>
            <p style="color: #aaa;">Причина: {video.delete_reason or "Нарушение правил Xitube"}</p>
            <a href="/" class="btn" style="margin-top: 20px;">Вернуться на главную</a>
        </div>
        '''
        return render_page('Видео удалено', content)
    
    if video.author and video.author.is_banned:
        content = f'''
        <div class="deleted-video">
            <h1>🚫 Видео недоступно</h1>
            <p style="font-size: 24px; margin: 20px 0;">
                Автор видео заблокирован администрацией
            </p>
            <p style="color: #aaa;">Причина блокировки автора: {video.author.ban_reason or "Нарушение правил Xitube"}</p>
            <a href="/" class="btn" style="margin-top: 20px;">Вернуться на главную</a>
        </div>
        '''
        return render_page('Автор заблокирован', content)
    
    video.views += 1
    db.session.commit()
    
    likes_count = len(video.likes) if video.likes else 0
    user_liked = any(like.user_id == current_user.id for like in video.likes) if current_user.is_authenticated else False
    
    content = f'''
    <div style="max-width: 800px; margin: 0 auto;">
        <video controls style="width: 100%; border-radius: 8px; background: #000;">
            <source src="/uploads/{video.filename}" type="video/mp4">
            Ваш браузер не поддерживает видео.
        </video>
        
        <h1 style="margin: 20px 0 10px 0;">{video.title}</h1>
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div style="color: #aaa;">
                👤 {video.author.username if video.author else 'Неизвестно'} • 
                👁️ {video.views} просмотров • 
                📅 {video.created_at.strftime('%d.%m.%Y %H:%M')}
            </div>
            
            <div>
                {current_user.is_authenticated and not current_user.is_banned and f'''
                <form action="/like/{video.id}" method="POST" style="display: inline;">
                    <button type="submit" class="btn" style="background: {'#333' if user_liked else '#ff0000'}">
                        {'❤️' if user_liked else '🤍'} {likes_count}
                    </button>
                </form>
                ''' or f'<span style="font-size: 20px;">❤️ {likes_count}</span>'}
            </div>
        </div>
    </div>
    '''
    return render_page(video.title, content)

@app.route('/like/<int:video_id>', methods=['POST'])
@login_required
def like_video(video_id):
    if current_user.is_banned:
        return "Ваш аккаунт заблокирован", 403
    
    video = Video.query.get(video_id)
    if not video or video.is_deleted or (video.author and video.author.is_banned):
        return "Видео недоступно", 404
    
    existing_like = None
    for like in video.likes:
        if like.user_id == current_user.id:
            existing_like = like
            break
    
    if existing_like:
        db.session.delete(existing_like)
    else:
        like = Like(user_id=current_user.id, video_id=video_id)
        db.session.add(like)
    
    db.session.commit()
    
    # Сбросить кеш главной страницы
    global index_cache
    index_cache = None
    
    return redirect(f'/video/{video_id}')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# АДМИН МАРШРУТЫ...

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Xitube запущен на порту {port}")
    print(f"✅ Health check: http://0.0.0.0:{port}/health")
    print(f"🔐 Админка: /{SECRET_ADMIN_URL}")
    print(f"👤 Тестовый пользователь: test / test123")
    app.run(host='0.0.0.0', port=port, debug=False)
