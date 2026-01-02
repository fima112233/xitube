from flask import Flask, request, redirect, send_from_directory, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

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

@app.route('/health')
def health_check():
    try:
        db.session.execute('SELECT 1')
        return jsonify({'status': 'ok'}), 200
    except:
        return jsonify({'status': 'error'}), 500

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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

@app.route('/')
def index():
    try:
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
                likes = Like.query.filter_by(video_id=video.id).count()
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
                                👍 {likes}
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
        
        <h2>📹 Последние видео</h2>
        <div class="video-grid">
            {video_html if video_html else '<p>Пока нет видео. Будьте первым!</p>'}
        </div>
        '''
        return render_page('Главная', content)
    except Exception as e:
        return render_page('Главная', '''
        <h1>🎬 Xitube - Видео платформа</h1>
        <p>Система загружается...</p>
        <p><a href="/upload">📤 Загрузить видео</a> | <a href="/login">🔑 Войти</a></p>
        ''')

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
    
    likes = Like.query.filter_by(video_id=video_id).count()
    user_liked = Like.query.filter_by(user_id=current_user.id, video_id=video_id).first() if current_user.is_authenticated else None
    
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
                        {'❤️' if user_liked else '🤍'} {likes}
                    </button>
                </form>
                ''' or f'<span style="font-size: 20px;">❤️ {likes}</span>'}
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
    
    existing = Like.query.filter_by(user_id=current_user.id, video_id=video_id).first()
    if existing:
        db.session.delete(existing)
    else:
        like = Like(user_id=current_user.id, video_id=video_id)
        db.session.add(like)
    
    db.session.commit()
    return redirect(f'/video/{video_id}')

@app.route(f'/{SECRET_ADMIN_URL}')
def secret_admin_panel():
    total_users = User.query.count()
    total_videos = Video.query.count()
    banned_users = User.query.filter_by(is_banned=True).count()
    deleted_videos = Video.query.filter_by(is_deleted=True).count()
    
    recent_videos = Video.query.order_by(Video.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    videos_html = ""
    for video in recent_videos:
        author = video.author.username if video.author else 'Неизвестно'
        status = "✅ Активно"
        if video.is_deleted:
            status = "🗑️ Удалено"
        elif video.author and video.author.is_banned:
            status = "👤 Автор заблокирован"
        
        videos_html += f'''
        <tr>
            <td>{video.id}</td>
            <td>{video.title[:30]}...</td>
            <td>{author}</td>
            <td>{video.views}</td>
            <td>{status}</td>
            <td>
                <a href="/deletevideo_{ADMIN_PASSWORD}/{video.id}" class="danger-btn" style="padding: 5px 10px; background: #cc0000; color: white; text-decoration: none; border-radius: 3px;">Удалить</a>
                <a href="/video/{video.id}" target="_blank" style="color: #4CAF50; margin-left: 5px;">Смотреть</a>
            </td>
        </tr>
        '''
    
    users_html = ""
    for user in recent_users:
        videos_count = Video.query.filter_by(user_id=user.id).count()
        status = "✅ Активен" if not user.is_banned else "🚫 Заблокирован"
        
        users_html += f'''
        <tr>
            <td>{user.id}</td>
            <td>{user.username}</td>
            <td>{user.created_at.strftime('%d.%m.%Y')}</td>
            <td>{videos_count}</td>
            <td>{status}</td>
            <td>
                {not user.is_banned and f'''
                <a href="/banuser_{ADMIN_PASSWORD}/{user.id}" class="danger-btn" style="padding: 5px 10px; background: #cc0000; color: white; text-decoration: none; border-radius: 3px;">Заблокировать</a>
                ''' or f'''
                <a href="/unbanuser_{ADMIN_PASSWORD}/{user.id}" class="success-btn" style="padding: 5px 10px; background: #00aa00; color: white; text-decoration: none; border-radius: 3px;">Разблокировать</a>
                <br><small>Причина: {user.ban_reason or "Не указана"}</small>
                '''}
            </td>
        </tr>
        '''
    
    content = f'''
    <div class="admin-panel">
        <h1>👑 СЕКРЕТНАЯ АДМИН ПАНЕЛЬ XITUBE</h1>
        
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0;">
            <div style="background: #222; padding: 20px; border-radius: 8px; text-align: center;">
                <h2>{total_users}</h2>
                <p>Пользователей</p>
            </div>
            <div style="background: #222; padding: 20px; border-radius: 8px; text-align: center;">
                <h2>{total_videos}</h2>
                <p>Видео</p>
            </div>
            <div style="background: #222; padding: 20px; border-radius: 8px; text-align: center;">
                <h2>{banned_users}</h2>
                <p>Заблокировано</p>
            </div>
            <div style="background: #222; padding: 20px; border-radius: 8px; text-align: center;">
                <h2>{deleted_videos}</h2>
                <p>Удалено видео</p>
            </div>
        </div>
        
        <h2>📹 Быстрые ссылки для управления:</h2>
        <div style="background: #222; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <p><strong>📁 Управление файлами:</strong> <a href="/filemanager_{ADMIN_PASSWORD}" style="color: #4CAF50;">/filemanager_{ADMIN_PASSWORD}</a></p>
            <p><strong>👤 Блокировка пользователя:</strong> /banuser_{ADMIN_PASSWORD}/[ID_пользователя]</p>
            <p><strong>📹 Удаление видео:</strong> /deletevideo_{ADMIN_PASSWORD}/[ID_видео]</p>
            <p><strong>👤 Разблокировка:</strong> /unbanuser_{ADMIN_PASSWORD}/[ID_пользователя]</p>
            <p><strong>📹 Восстановление видео:</strong> /restorevideo_{ADMIN_PASSWORD}/[ID_видео]</p>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 40px;">
            <div>
                <h2>📹 Последние видео</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <tr>
                            <th>ID</th>
                            <th>Название</th>
                            <th>Автор</th>
                            <th>Просмотры</th>
                            <th>Статус</th>
                            <th>Действия</th>
                        </tr>
                        {videos_html}
                    </table>
                </div>
            </div>
            
            <div>
                <h2>👥 Последние пользователи</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <tr>
                            <th>ID</th>
                            <th>Имя</th>
                            <th>Дата</th>
                            <th>Видео</th>
                            <th>Статус</th>
                            <th>Действия</th>
                        </tr>
                        {users_html}
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <div style="text-align: center; margin-top: 30px;">
        <a href="/" class="btn">← На главную</a>
    </div>
    '''
    return render_page('Секретная админка', content)

@app.route(f'/filemanager_{ADMIN_PASSWORD}')
def file_manager():
    files = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath)
                video = Video.query.filter_by(filename=filename).first()
                video_id = video.id if video else 'Не в базе'
                video_title = video.title if video else 'Неизвестно'
                author = video.author.username if video and video.author else 'Неизвестно'
                
                files.append({
                    'name': filename,
                    'size': size,
                    'video_id': video_id,
                    'title': video_title,
                    'author': author
                })
    
    files_html = ""
    for file in files:
        size_mb = file['size'] / (1024*1024)
        files_html += f'''
        <tr>
            <td>{file['name']}</td>
            <td>{file['title'][:30]}</td>
            <td>{file['author']}</td>
            <td>{size_mb:.2f} MB</td>
            <td>{file['video_id']}</td>
            <td>
                <a href="/deletefile_{ADMIN_PASSWORD}/{file['name']}" 
                   onclick="return confirm('Удалить файл {file['name']}?')"
                   style="color: red; text-decoration: none;">🗑️ Удалить</a>
                <a href="/uploads/{file['name']}" target="_blank" style="color: #4CAF50; margin-left: 10px;">▶️ Смотреть</a>
            </td>
        </tr>
        '''
    
    content = f'''
    <div class="admin-panel">
        <h1>🗑️ УПРАВЛЕНИЕ ФАЙЛАМИ</h1>
        <p style="color: #aaa;">Папка: {app.config['UPLOAD_FOLDER']} | Файлов: {len(files)}</p>
        
        <div style="margin: 20px 0;">
            <a href="/{SECRET_ADMIN_URL}" class="btn">← В админку</a>
            <a href="/" class="btn" style="background: #333; margin-left: 10px;">На главную</a>
        </div>
        
        <div style="overflow-x: auto;">
            <table>
                <tr>
                    <th>Имя файла</th>
                    <th>Название</th>
                    <th>Автор</th>
                    <th>Размер</th>
                    <th>ID видео</th>
                    <th>Действия</th>
                </tr>
                {files_html if files_html else '<tr><td colspan="6" style="text-align: center; padding: 20px;">Файлов нет</td></tr>'}
            </table>
        </div>
    </div>
    '''
    return render_page('Управление файлами', content)

@app.route(f'/deletefile_{ADMIN_PASSWORD}/<filename>')
def delete_file(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(filepath):
        os.remove(filepath)
        
        video = Video.query.filter_by(filename=filename).first()
        if video:
            video.is_deleted = True
            video.delete_reason = "Удалено администратором через файловый менеджер"
            db.session.commit()
        
        return f'''
        <div class="container">
            <h1>✅ Файл удален</h1>
            <p>Файл <strong>{filename}</strong> успешно удален с сервера.</p>
            <p>Видео помечено как удаленное в базе данных.</p>
            <div style="margin-top: 30px;">
                <a href="/filemanager_{ADMIN_PASSWORD}" class="btn">← Назад к файлам</a>
                <a href="/{SECRET_ADMIN_URL}" class="btn" style="background: #333; margin-left: 10px;">В админку</a>
            </div>
        </div>
        '''
    
    return f'''
    <div class="container">
        <h1>❌ Файл не найден</h1>
        <p>Файл <strong>{filename}</strong> не существует.</p>
        <a href="/filemanager_{ADMIN_PASSWORD}" class="btn">← Назад</a>
    </div>
    '''

@app.route(f'/banuser_{ADMIN_PASSWORD}/<int:user_id>')
def ban_user(user_id):
    user = User.query.get(user_id)
    
    if user:
        user.is_banned = True
        user.ban_reason = request.args.get('reason', 'Нарушение правил Xitube')
        db.session.commit()
        
        videos = Video.query.filter_by(user_id=user_id).all()
        for video in videos:
            video.is_deleted = True
            video.delete_reason = f"Автор заблокирован: {user.ban_reason}"
        db.session.commit()
        
        return f'''
        <div class="container">
            <h1>✅ Пользователь заблокирован</h1>
            <p>Пользователь <strong>{user.username}</strong> (ID: {user.id}) заблокирован.</p>
            <p>Причина: {user.ban_reason}</p>
            <p>Заблокировано видео: {len(videos)}</p>
            <div style="margin-top: 30px;">
                <a href="/{SECRET_ADMIN_URL}" class="btn">← В админку</a>
                <a href="/unbanuser_{ADMIN_PASSWORD}/{user_id}" class="btn" style="background: #00aa00;">Разблокировать</a>
            </div>
        </div>
        '''
    
    return f'''
    <div class="container">
        <h1>❌ Пользователь не найден</h1>
        <p>Пользователь с ID {user_id} не существует.</p>
        <a href="/{SECRET_ADMIN_URL}" class="btn">← Назад</a>
    </div>
    '''

@app.route(f'/unbanuser_{ADMIN_PASSWORD}/<int:user_id>')
def unban_user(user_id):
    user = User.query.get(user_id)
    
    if user:
        user.is_banned = False
        user.ban_reason = None
        db.session.commit()
        
        videos = Video.query.filter_by(user_id=user_id).all()
        for video in videos:
            if video.delete_reason and "Автор заблокирован" in video.delete_reason:
                video.is_deleted = False
                video.delete_reason = None
        db.session.commit()
        
        return f'''
        <div class="container">
            <h1>✅ Пользователь разблокирован</h1>
            <p>Пользователь <strong>{user.username}</strong> (ID: {user.id}) разблокирован.</p>
            <p>Восстановлено видео: {len(videos)}</p>
            <div style="margin-top: 30px;">
                <a href="/{SECRET_ADMIN_URL}" class="btn">← В админку</a>
                <a href="/banuser_{ADMIN_PASSWORD}/{user_id}" class="btn" style="background: #cc0000;">Заблокировать снова</a>
            </div>
        </div>
        '''
    
    return f'''
    <div class="container">
        <h1>❌ Пользователь не найден</h1>
        <p>Пользователь с ID {user_id} не существует.</p>
        <a href="/{SECRET_ADMIN_URL}" class="btn">← Назад</a>
    </div>
    '''

@app.route(f'/deletevideo_{ADMIN_PASSWORD}/<int:video_id>')
def delete_video(video_id):
    video = Video.query.get(video_id)
    
    if video:
        video.is_deleted = True
        video.delete_reason = request.args.get('reason', 'Удалено администрацией Xitube')
        db.session.commit()
        
        return f'''
        <div class="container">
            <h1>✅ Видео удалено</h1>
            <p>Видео <strong>"{video.title}"</strong> (ID: {video.id}) удалено.</p>
            <p>Причина: {video.delete_reason}</p>
            <p>Автор: {video.author.username if video.author else 'Неизвестно'}</p>
            <div style="margin-top: 30px;">
                <a href="/{SECRET_ADMIN_URL}" class="btn">← В админку</a>
                <a href="/restorevideo_{ADMIN_PASSWORD}/{video_id}" class="btn" style="background: #00aa00;">Восстановить</a>
                <a href="/banuser_{ADMIN_PASSWORD}/{video.user_id}" class="btn" style="background: #cc0000; margin-left: 10px;">Заблокировать автора</a>
            </div>
        </div>
        '''
    
    return f'''
    <div class="container">
        <h1>❌ Видео не найдено</h1>
        <p>Видео с ID {video_id} не существует.</p>
        <a href="/{SECRET_ADMIN_URL}" class="btn">← Назад</a>
    </div>
    '''

@app.route(f'/restorevideo_{ADMIN_PASSWORD}/<int:video_id>')
def restore_video(video_id):
    video = Video.query.get(video_id)
    
    if video:
        video.is_deleted = False
        video.delete_reason = None
        db.session.commit()
        
        return f'''
        <div class="container">
            <h1>✅ Видео восстановлено</h1>
            <p>Видео <strong>"{video.title}"</strong> (ID: {video.id}) восстановлено.</p>
            <p>Теперь оно снова доступно для просмотра.</p>
            <div style="margin-top: 30px;">
                <a href="/{SECRET_ADMIN_URL}" class="btn">← В админку</a>
                <a href="/video/{video_id}" class="btn" style="background: #4CAF50;">Смотреть видео</a>
            </div>
        </div>
        '''
    
    return f'''
    <div class="container">
        <h1>❌ Видео не найдено</h1>
        <p>Видео с ID {video_id} не существует.</p>
        <a href="/{SECRET_ADMIN_URL}" class="btn">← Назад</a>
    </div>
    '''

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
