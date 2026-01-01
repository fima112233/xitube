from flask import Flask, request, redirect, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'xitube-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///xitube.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Telegram бот для админ-действий
TELEGRAM_TOKEN = '8354653771:AAEPEoRVHmNxIJzDCKcqCXWxy8JZfWr5n3w'
TELEGRAM_CHAT_ID = '7575398090'

# Модели - УПРОЩЕННЫЕ И ЕДИНООБРАЗНЫЕ
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Telegram функции
def send_telegram(text, buttons=None):
    """Отправляет сообщение в Telegram с кнопками"""
    try:
        if TELEGRAM_TOKEN == 'ВАШ_ТОКЕН' or TELEGRAM_CHAT_ID == 'ВАШ_ID':
            print(f"Telegram сообщение (бот не настроен): {text[:50]}...")
            return True
            
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        if buttons:
            data['reply_markup'] = {'inline_keyboard': buttons}
        
        requests.post(url, json=data, timeout=5)
        return True
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False

def boost_likes(video_id, count=100):
    """Накрутка лайков через Telegram"""
    try:
        video = Video.query.get(video_id)
        if not video:
            return False
        
        # Используем существующего пользователя для накрутки (например, первого пользователя)
        fake_user = User.query.first()
        if not fake_user:
            return False
        
        # Добавляем лайки
        for _ in range(count):
            like = Like(user_id=fake_user.id, video_id=video_id, created_at=datetime.utcnow())
            db.session.add(like)
        
        db.session.commit()
        return True
    except Exception as e:
        print(f"Ошибка накрутки лайков: {e}")
        db.session.rollback()
        return False

def boost_views(video_id, count=1000):
    """Накрутка просмотров"""
    try:
        video = Video.query.get(video_id)
        if video:
            video.views += count
            db.session.commit()
            return True
        return False
    except Exception as e:
        print(f"Ошибка накрутки просмотров: {e}")
        db.session.rollback()
        return False

# HTML шаблоны
def render_page(title, content):
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Xitube - {title}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: Arial, sans-serif; background: #0a0a0a; color: white; }}
            .header {{ background: linear-gradient(90deg, #ff0000, #cc0000); padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 10px rgba(255,0,0,0.3); }}
            .header a {{ color: white; text-decoration: none; margin: 0 15px; font-weight: bold; font-size: 16px; transition: opacity 0.2s; }}
            .header a:hover {{ opacity: 0.8; }}
            .container {{ max-width: 1200px; margin: 20px auto; padding: 0 20px; }}
            .video-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 25px; margin-top: 30px; }}
            .video-card {{ background: #1a1a1a; border-radius: 12px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s; cursor: pointer; border: 1px solid #333; }}
            .video-card:hover {{ transform: translateY(-5px); box-shadow: 0 10px 20px rgba(255,0,0,0.2); }}
            .video-thumb {{ width: 100%; height: 180px; background: linear-gradient(135deg, #ff0000, #ff5555); display: flex; align-items: center; justify-content: center; font-size: 48px; }}
            .video-info {{ padding: 20px; }}
            .video-title {{ font-weight: bold; margin-bottom: 8px; font-size: 18px; color: white; }}
            .video-meta {{ color: #aaa; font-size: 14px; line-height: 1.5; }}
            .btn {{ background: linear-gradient(90deg, #ff0000, #cc0000); color: white; border: none; padding: 12px 25px; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; transition: transform 0.2s; }}
            .btn:hover {{ transform: scale(1.05); }}
            .form-box {{ background: #1a1a1a; padding: 40px; border-radius: 12px; max-width: 500px; margin: 50px auto; border: 1px solid #333; }}
            input, textarea {{ width: 100%; padding: 14px; margin: 12px 0; background: #222; border: 1px solid #444; border-radius: 6px; color: white; font-size: 16px; }}
            input:focus, textarea:focus {{ outline: none; border-color: #ff0000; box-shadow: 0 0 0 2px rgba(255,0,0,0.2); }}
            .player {{ background: #000; border-radius: 12px; overflow: hidden; margin-bottom: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.5); }}
            video {{ width: 100%; display: block; }}
            .like-btn {{ background: none; border: none; font-size: 32px; cursor: pointer; padding: 10px; transition: transform 0.2s; }}
            .like-btn:hover {{ transform: scale(1.2); }}
            .flash {{ padding: 15px; border-radius: 8px; margin: 15px 0; text-align: center; font-weight: bold; }}
            .error {{ background: rgba(255, 50, 50, 0.2); border: 1px solid #ff3333; color: #ff6666; }}
            .success {{ background: rgba(50, 255, 50, 0.2); border: 1px solid #33ff33; color: #66ff66; }}
            h1 {{ color: #ff0000; margin-bottom: 20px; font-size: 36px; }}
            h2 {{ color: #ff3333; margin-bottom: 25px; font-size: 28px; }}
            h3 {{ color: #ff5555; margin-bottom: 15px; font-size: 22px; border-bottom: 2px solid #ff0000; padding-bottom: 8px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <a href="/">🏠 Xitube</a>
                {current_user.is_authenticated and '<a href="/upload">📤 Загрузить</a>' or ''}
            </div>
            <div>
                {current_user.is_authenticated and f'<span style="margin-right: 15px;">👤 {current_user.username}</span><a href="/logout">🚪 Выйти</a>' or '<a href="/login">🔑 Войти</a><a href="/register">📝 Регистрация</a>'}
            </div>
        </div>
        <div class="container">
            {content}
        </div>
        <script>
            async function likeVideo(videoId) {{
                const response = await fetch(`/api/like/${{videoId}}`, {{ method: 'POST' }});
                if (response.ok) {{
                    location.reload();
                }}
            }}
        </script>
    </body>
    </html>
    '''

# Флеш сообщения
flashes = []

def flash(message, category='error'):
    flashes.append((message, category))

def get_flashed_messages():
    global flashes
    messages = flashes.copy()
    flashes = []
    return messages

# Роуты
@app.route('/')
def index():
    videos = Video.query.order_by(Video.created_at.desc()).all()
    
    html = ''
    for video in videos:
        likes = Like.query.filter_by(video_id=video.id).count()
        html += f'''
        <a href="/video/{video.id}" class="video-card">
            <div class="video-thumb">🎬</div>
            <div class="video-info">
                <div class="video-title">{video.title[:60]}{'...' if len(video.title) > 60 else ''}</div>
                <div class="video-meta">
                    👤 {video.author.username if video.author else 'Unknown'} • 
                    👁️ {video.views} просмотров • 
                    👍 {likes} лайков<br>
                    📅 {video.created_at.strftime('%d.%m.%Y %H:%M')}
                </div>
            </div>
        </a>
        '''
    
    flash_html = ''
    for msg, cat in get_flashed_messages():
        flash_html += f'<div class="flash {cat}">{msg}</div>'
    
    content = f'''
    {flash_html}
    <h1>🎬 Xitube - Платформа для видео</h1>
    <p style="color: #aaa; font-size: 18px; margin-bottom: 20px;">Смотри, загружай, делись видео!</p>
    <div class="video-grid">
        {html or '<div style="grid-column: 1/-1; text-align: center; padding: 50px; color: #666;"><h3>Пока нет видео</h3><p>Будьте первым, кто загрузит видео!</p></div>'}
    </div>
    '''
    return render_page('Главная', content)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Заполните все поля')
            return redirect('/register')
        
        if User.query.filter_by(username=username).first():
            flash('Этот логин уже занят')
            return redirect('/register')
        
        if len(password) < 4:
            flash('Пароль должен быть не менее 4 символов')
            return redirect('/register')
        
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash('🎉 Регистрация успешна! Добро пожаловать на Xitube!', 'success')
        return redirect('/')
    
    content = '''
    <div class="form-box">
        <h2>📝 Создать аккаунт</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Придумайте логин" required>
            <input type="password" name="password" placeholder="Придумайте пароль" required>
            <button class="btn" type="submit" style="width: 100%; margin-top: 20px;">
                🚀 Создать аккаунт
            </button>
        </form>
        <p style="text-align: center; margin-top: 25px; color: #aaa;">
            Уже есть аккаунт? <a href="/login" style="color: #ff5555;">Войти</a>
        </p>
    </div>
    '''
    return render_page('Регистрация', content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'👋 Добро пожаловать, {username}!', 'success')
            return redirect('/')
        
        flash('❌ Неверный логин или пароль')
        return redirect('/login')
    
    content = '''
    <div class="form-box">
        <h2>🔑 Вход в аккаунт</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Ваш логин" required>
            <input type="password" name="password" placeholder="Ваш пароль" required>
            <button class="btn" type="submit" style="width: 100%; margin-top: 20px;">
                🔐 Войти
            </button>
        </form>
        <p style="text-align: center; margin-top: 25px; color: #aaa;">
            Нет аккаунта? <a href="/register" style="color: #ff5555;">Зарегистрироваться</a>
        </p>
    </div>
    '''
    return render_page('Вход', content)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('👋 Вы вышли из системы. Возвращайтесь скорее!', 'success')
    return redirect('/')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        file = request.files.get('video')
        
        if not title:
            flash('Введите название видео')
            return redirect('/upload')
        
        if not file:
            flash('Выберите файл видео')
            return redirect('/upload')
        
        if not allowed_file(file.filename):
            flash('Неподдерживаемый формат файла. Используйте MP4, AVI, MOV, MKV или WEBM')
            return redirect('/upload')
        
        # Сохраняем файл
        timestamp = int(datetime.now().timestamp())
        filename = f"{current_user.id}_{timestamp}_{file.filename.replace(' ', '_')}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Создаем запись в базе
        video = Video(
            title=title,
            filename=filename,
            user_id=current_user.id
        )
        db.session.add(video)
        db.session.commit()
        
        # Отправляем в Telegram
        message = f"🎬 <b>НОВОЕ ВИДЕО НА XITUBE!</b>\n\n📹 <b>{title}</b>\n👤 Автор: {current_user.username}\n🆔 ID: {video.id}\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        buttons = [
            [
                {"text": "👍 +100 лайков", "callback_data": f"like_{video.id}_100"},
                {"text": "👁️ +500 просмотров", "callback_data": f"view_{video.id}_500"}
            ],
            [
                {"text": "🚀 МАКСИМАЛЬНАЯ НАКРУТКА", "callback_data": f"max_{video.id}"}
            ]
        ]
        send_telegram(message, buttons)
        
        flash('🎉 Видео успешно загружено! Уведомление отправлено в Telegram.', 'success')
        return redirect(f'/video/{video.id}')
    
    content = '''
    <div class="form-box">
        <h2>📤 Загрузить видео</h2>
        <form method="POST" enctype="multipart/form-data">
            <input type="text" name="title" placeholder="Название видео" required>
            <input type="file" name="video" accept="video/*" required 
                   style="padding: 25px; border: 2px dashed #555; border-radius: 8px; background: #222; text-align: center; font-size: 16px; color: #aaa;">
            <button class="btn" type="submit" style="width: 100%; margin-top: 25px; font-size: 18px;">
                📤 Загрузить видео
            </button>
        </form>
        <div style="margin-top: 20px; padding: 15px; background: #222; border-radius: 8px; color: #aaa; font-size: 14px;">
            <p>📋 <b>Поддерживаемые форматы:</b> MP4, AVI, MOV, MKV, WEBM</p>
            <p>⚠️ <b>Максимальный размер:</b> без ограничений</p>
        </div>
    </div>
    '''
    return render_page('Загрузка', content)

@app.route('/video/<int:video_id>')
def video_page(video_id):
    video = Video.query.get(video_id)
    if not video:
        flash('Видео не найдено')
        return redirect('/')
    
    likes = Like.query.filter_by(video_id=video.id).count()
    user_liked = Like.query.filter_by(video_id=video.id, user_id=current_user.id).first() if current_user.is_authenticated else None
    
    # Увеличиваем просмотры
    video.views += 1
    db.session.commit()
    
    flash_html = ''
    for msg, cat in get_flashed_messages():
        flash_html += f'<div class="flash {cat}">{msg}</div>'
    
    # Рекомендуемые видео
    recommended = Video.query.filter(Video.id != video.id).order_by(Video.views.desc()).limit(5).all()
    recommended_html = ''
    for rec in recommended:
        rec_likes = Like.query.filter_by(video_id=rec.id).count()
        recommended_html += f'''
        <a href="/video/{rec.id}" style="text-decoration: none; color: inherit;">
            <div style="background: #1a1a1a; padding: 15px; margin-bottom: 15px; border-radius: 8px; display: flex; gap: 15px; border: 1px solid #333; transition: all 0.2s;"
                 onmouseover="this.style.background='#222'; this.style.borderColor='#ff0000'"
                 onmouseout="this.style.background='#1a1a1a'; this.style.borderColor='#333'">
                <div style="min-width: 140px; height: 80px; background: linear-gradient(135deg, #ff0000, #ff5555); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 28px;">
                    ▶️
                </div>
                <div style="flex-grow: 1;">
                    <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 15px;">
                        {rec.title[:35]}{'...' if len(rec.title) > 35 else ''}
                    </p>
                    <p style="margin: 0; font-size: 14px; color: #aaa;">
                        {rec.author.username if rec.author else 'Unknown'}
                    </p>
                    <p style="margin: 8px 0 0 0; font-size: 13px; color: #666;">
                        👁️ {rec.views} • 👍 {rec_likes}
                    </p>
                </div>
            </div>
        </a>
        '''
    
    content = f'''
    {flash_html}
    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 30px;">
        <div>
            <div class="player">
                <video controls style="width: 100%;">
                    <source src="/file/{video.filename}" type="video/mp4">
                    Ваш браузер не поддерживает видео тег.
                </video>
            </div>
            
            <h1>{video.title}</h1>
            <div style="color: #aaa; margin-bottom: 25px; font-size: 17px; display: flex; align-items: center; gap: 20px;">
                <span>👤 {video.author.username if video.author else 'Unknown'}</span>
                <span>👁️ {video.views} просмотров</span>
                <span>📅 {video.created_at.strftime('%d.%m.%Y %H:%M')}</span>
            </div>
            
            <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 30px;">
                <button class="like-btn" onclick="likeVideo({video.id})" 
                        style="color: {'#ff0000' if user_liked else '#666'};">
                    {'❤️' if user_liked else '🤍'}
                </button>
                <span style="font-size: 28px; font-weight: bold; color: {'#ff0000' if user_liked else 'white'}">
                    {likes}
                </span>
                <span style="color: #666; font-size: 18px;">лайков</span>
            </div>
            
            <h3>💬 Комментарии</h3>
            <div style="background: #1a1a1a; padding: 25px; border-radius: 10px; margin-top: 20px; border: 1px solid #333;">
                <p style="text-align: center; color: #666; padding: 20px; font-size: 16px;">
                    Система комментариев в разработке. Скоро будет доступна!
                </p>
            </div>
        </div>
        
        <div>
            <h3>🎬 Рекомендуемые видео</h3>
            {recommended_html or '<p style="color: #666; text-align: center; padding: 20px;">Нет других видео</p>'}
        </div>
    </div>
    '''
    return render_page(video.title, content)

@app.route('/api/like/<int:video_id>', methods=['POST'])
@login_required
def api_like(video_id):
    existing = Like.query.filter_by(user_id=current_user.id, video_id=video_id).first()
    if existing:
        db.session.delete(existing)
    else:
        like = Like(user_id=current_user.id, video_id=video_id)
        db.session.add(like)
    
    db.session.commit()
    return '', 200

@app.route('/file/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    """Webhook для Telegram бота - ВСЕ админ-действия здесь"""
    try:
        data = request.json
        
        if 'callback_query' in data:
            callback = data['callback_query']
            action = callback['data']
            
            # Отвечаем сразу
            requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery', json={
                'callback_query_id': callback['id'],
                'text': '⚡ Накрутка начинается...'
            })
            
            success = False
            if action.startswith('like_'):
                _, video_id, count = action.split('_')
                success = boost_likes(int(video_id), int(count))
                
            elif action.startswith('view_'):
                _, video_id, count = action.split('_')
                success = boost_views(int(video_id), int(count))
                
            elif action.startswith('max_'):
                _, video_id = action.split('_')
                boost_likes(int(video_id), 1000)
                boost_views(int(video_id), 5000)
                success = True
            
            # Обновляем сообщение
            if success:
                new_text = callback['message']['text'] + f"\n\n✅ Накрутка выполнена! ({action})"
                requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText', json={
                    'chat_id': callback['message']['chat']['id'],
                    'message_id': callback['message']['message_id'],
                    'text': new_text,
                    'parse_mode': 'HTML'
                })
    
    except Exception as e:
        print(f"Ошибка Telegram webhook: {e}")
    
    return 'OK'

# Инициализация базы
def init_db():
    with app.app_context():
        # Удаляем старую базу
        if os.path.exists('xitube.db'):
            try:
                os.remove('xitube.db')
                print("🗑️ Удалена старая база данных")
            except:
                pass
        
        # Создаем все таблицы
        db.create_all()
        print("✅ Созданы таблицы базы данных")
        
        # Создаем тестового пользователя если нет
        if not User.query.first():
            user = User(
                username='test',
                password_hash=generate_password_hash('test123')
            )
            db.session.add(user)
            db.session.commit()
            print("👤 Создан тестовый пользователь: test / test123")

# Запуск приложения
if __name__ == '__main__':
    # Настройка для Replit
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "True") == "True"
    
    print("=" * 70)
    print("🎬 XITUBE - Видео платформа")
    print("=" * 70)
    print(f"\n🌐 Сайт доступен по адресу: https://ВАШ-ПРОЕКТ.replit.app")
    print(f"📁 Папка загрузок: {app.config['UPLOAD_FOLDER']}")
    print(f"🔧 Debug mode: {debug}")
    print("=" * 70)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=False
    )
