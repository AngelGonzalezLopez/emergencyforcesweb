from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secret_key_prototipo'

DATABASE = 'database.db'

app.config['UPLOAD_FOLDER'] = 'static/uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        image TEXT,
        youtube_link TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT,
        user_id INTEGER,
        topic_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS blog_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT,
        user_id INTEGER,
        post_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute("SELECT * FROM users WHERE email = ?", ("admin@admin.com",))
    if not cursor.fetchone():
        cursor.execute('''INSERT INTO users (username, email, password, role)
        VALUES (?, ?, ?, ?)''', (
            "admin",
            "admin@admin.com",
            generate_password_hash("1234"),
            "admin"
        ))
        conn.commit()

    conn.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return redirect(url_for('dashboard') if user['role']=='admin' else url_for('index'))

    return "Credenciales incorrectas"


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT * FROM posts ORDER BY created_at DESC")
    posts = cursor.fetchall()

    cursor.execute('''
    SELECT topics.*, users.username
    FROM topics
    JOIN users ON users.id = topics.user_id
    ORDER BY topics.created_at DESC
    ''')
    topics = cursor.fetchall()

    cursor.execute('''
    SELECT replies.*, users.username, topics.title
    FROM replies
    JOIN users ON users.id = replies.user_id
    JOIN topics ON topics.id = replies.topic_id
    ''')
    replies = cursor.fetchall()

    conn.close()

    return render_template('dashboard.html',
                           users=users,
                           posts=posts,
                           topics=topics,
                           replies=replies)

# ================= REGISTRO =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        username = nombre + " " + apellido

        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            return "Las contraseñas no coinciden"

        password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            INSERT INTO users (username, email, password, role)
            VALUES (?, ?, ?, ?)
            ''', (username, email, password, 'user'))
            conn.commit()
        except:
            return "El usuario ya existe"

        conn.close()
        return redirect(url_for('index'))

    return render_template('registro.html')


# ================= BLOG =================
@app.route('/blog')
def blog():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM posts ORDER BY created_at DESC")
    posts = cursor.fetchall()

    cursor.execute('''
    SELECT blog_comments.*, users.username
    FROM blog_comments
    JOIN users ON users.id = blog_comments.user_id
    ORDER BY created_at ASC
    ''')
    comments = cursor.fetchall()

    conn.close()

    return render_template('blog.html', posts=posts, comments=comments)


@app.route('/comment_post/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('blog'))

    content = request.form['content']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO blog_comments (content, user_id, post_id)
    VALUES (?, ?, ?)''',
                   (content, session['user_id'], post_id))

    conn.commit()
    conn.close()

    return redirect(url_for('blog'))


# ================= POSTS =================
@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    title = request.form['title']
    content = request.form['content']
    youtube = request.form['youtube']
    file = request.files['image']

    filename = file.filename
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO posts (title, content, image, youtube_link)
    VALUES (?, ?, ?, ?)''',
                   (title, content, filename, youtube))

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


# ================= FORO =================
@app.route('/foro')
def foro():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT topics.*, users.username,
    (SELECT COUNT(*) FROM replies WHERE topic_id = topics.id) as replies_count
    FROM topics
    JOIN users ON users.id = topics.user_id
    ORDER BY topics.created_at DESC
    ''')

    topics = cursor.fetchall()
    conn.close()

    return render_template('foro.html', topics=topics)


@app.route('/create_topic', methods=['POST'])
def create_topic():
    if 'user_id' not in session:
        return redirect(url_for('foro'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO topics (title, content, user_id)
    VALUES (?, ?, ?)''',
                   (request.form['title'], request.form['content'], session['user_id']))

    conn.commit()
    conn.close()

    return redirect(url_for('foro'))


@app.route('/topic/<int:id>')
def topic(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT topics.*, users.username
    FROM topics
    JOIN users ON users.id = topics.user_id
    WHERE topics.id = ?''', (id,))
    topic = cursor.fetchone()

    cursor.execute('''
    SELECT replies.*, users.username
    FROM replies
    JOIN users ON users.id = replies.user_id
    WHERE topic_id = ?
    ORDER BY created_at ASC''', (id,))
    replies = cursor.fetchall()

    conn.close()

    return render_template('topic.html', topic=topic, replies=replies)


@app.route('/reply/<int:topic_id>', methods=['POST'])
def reply(topic_id):
    if 'user_id' not in session:
        return redirect(url_for('topic', id=topic_id))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO replies (content, user_id, topic_id)
    VALUES (?, ?, ?)''',
                   (request.form['content'], session['user_id'], topic_id))

    conn.commit()
    conn.close()

    return redirect(url_for('topic', id=topic_id))


# ================= DELETE =================
@app.route('/delete_user/<int:id>')
def delete_user(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))


@app.route('/delete_topic/<int:id>')
def delete_topic(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM replies WHERE topic_id = ?", (id,))
    cursor.execute("DELETE FROM topics WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))


@app.route('/delete_reply/<int:id>')
def delete_reply(id):
    # 🔒 Validar que sea admin
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM replies WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    # 🔁 regresar a la página anterior (mejor UX)
    return redirect(request.referrer or url_for('dashboard'))


# ================= RUN =================
if __name__ == '__main__':
    init_db()
    app.run(debug=True)