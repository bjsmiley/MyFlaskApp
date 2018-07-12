from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
# from data import Articles
from password import root_password
#from flask_mysqldb import MySQL
import mysql.connector as mysql
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
# from functools import wraps
import functools

app = Flask(__name__)

# Config MySQL
# app.config['MYSQL_HOST'] = 'localhost'
# app.config['MYSQL_USER'] = 'root'
# app.config['MYSQL_PASSWORD'] = root_password
# app.config['MYSQL_DB'] = 'myflaskapp'
# app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

cnx = mysql.connect(user='root',password=root_password, database='myflaskapp', host='localhost', auth_plugin='mysql_native_password')


# init MYSQL
#mysql = MySQL(app)

# Articles = Articles()

# Index
@app.route('/')
def index():
    return render_template('home.html')

# About
@app.route('/about')
def about():
    return render_template('about.html')

# Articles
@app.route('/articles')
def articles():
    # Create Cursor
    cur = cnx.cursor()
    # Get articles
    cur.execute('SELECT * FROM articles')

    articles = cur.fetchall()
    cur.close()

    if articles is not None:
        app.logger.info(articles)
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)

# Single Article Page
@app.route('/article/<string:id>/')
def article(id):
    # Create Cursor
    cur = cnx.cursor()
    # Get articles
    cur.execute('SELECT * FROM articles WHERE id = %s',[id])

    article = cur.fetchone()
    cur.close()
    return render_template('article.html', article=article)

# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1,max=50)])
    username = StringField('Username',[validators.Length(min=4,max=25)])
    email = StringField('Email',[validators.Length(min=6,max=50)])
    password = PasswordField('Password',[
        validators.DataRequired(),
        validators.EqualTo('confirm',message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

# User Register
@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        '''
        # Create cursor
        cur = mysql.connect.cursor()
        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, $s)", (name, email, username, password))
        # Commit to DB
        mysql.connection.commit()
        # Close connection
        cur.close()
        '''
        # Windows Way
        
        cur = cnx.cursor()
        cur.execute("INSERT INTO users (name, email, username, password) VALUES (%s, %s, %s, %s)", (name, email, username, password))
        cnx.commit()
        cur.close()
        


        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))

    return render_template('register.html', form=form)

# Login   
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        #get form fields
        username = request.form['username']
        password_candidate = request.form['password']

        # create cursor
        cur = cnx.cursor()
        
        # get user by username

        cur.execute("SELECT * FROM users WHERE username = %s",[username])

        data = cur.fetchone()

        if data is not None:
            # get the stored hash
            app.logger.info(data)
            password = data[4]

            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in','success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error )
            # Close Connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error )

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login','danger')
            return redirect(url_for('login'))
    return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create Cursor
    cur = cnx.cursor()
    # Get articles
    cur.execute('SELECT * FROM articles')

    articles = cur.fetchall()
    cur.close()

    if articles is not None:
        app.logger.info(articles)
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)

# Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1,max=200)])
    body = TextAreaField('Body',[validators.Length(min=30)])

# Add Article
@app.route('/add_article', methods=['GET','POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create Cursor
        cur = cnx.cursor()
        # Execute
        cur.execute('INSERT INTO articles (title, body, author) VALUES(%s, %s, %s)',
                    (title,body, session['username']))
        # Commit
        cnx.commit()
        cur.close()

        flash('Article Created','success')

        return redirect(url_for('dashboard'))
    
    return render_template('add_article.html', form=form)

# Edit article
@app.route('/edit_article/<string:id>', methods=['GET','POST'])
@is_logged_in
def edit(id):
    
    # Create cursor
    cur = cnx.cursor()

    # Get article by id
    cur.execute('SELECT * FROM articles WHERE id = %s',[id])

    article = cur.fetchone()

    form = ArticleForm(request.form)
    # Now Populate the form fields
    form.title.data = article[1]
    form.body.data = article[3]

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # Create Cursor
        cur = cnx.cursor()
        # Execute
        cur.execute('UPDATE articles SET title=%s, body=%s WHERE id = %s',
                    (title,body,id))
        # Commit
        cnx.commit()
        cur.close()

        flash('Article Updated','success')

        return redirect(url_for('dashboard'))
    
    return render_template('edit_article.html', form=form)

# Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    #Create Cursor
    cur = cnx.cursor()

    #Execute Delete
    cur.execute('DELETE FROM articles WHERE id = %s',[id])
    cnx.commit()
    cur.close()

    flash('Article Deleted','success')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)