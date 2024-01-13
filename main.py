import os
import smtplib
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_ckeditor import CKEditor, CKEditorField
from flask_bootstrap import Bootstrap
# from flask_gravatar import Gravatar
# from flask import _request_ctx_stack
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, joinedload
from werkzeug.security import generate_password_hash, check_password_hash
# from werkzeug.urls import url_quote_plus

# from werkzeug.local import _request_ctx_stack


from templates.forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['CKEDITOR_PKG_TYPE'] = 'full-all'
ckeditor = CKEditor(app)
Bootstrap(app)

# Connect to DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../blog.db'
db = SQLAlchemy(app)

# Authentication
login_manager = LoginManager()
login_manager.init_app(app)

# Gravatar Initialization
# gravatar = Gravatar(app,
#                     size=100,
#                     rating='g',
#                     default='retro',
#                     force_default=False,
#                     force_lower=False,
#                     use_ssl=False,
#                     base_url=None
#                     )


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# CONFIGURE TABLES

# Create User Table
class User(UserMixin, db.Model):
    __tablename__ = "users"

    # Relationships to blog posts and comments
    posts = db.relationship("BlogPost", back_populates="post_author")
    comments = db.relationship("Comment", back_populates="comment_author")

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    password_confirm = db.Column(db.String(100))


# Create BlogPost Table
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Relationship to author of the posts
    post_author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    post_author = db.relationship("User", back_populates="posts")

    # Relationship to comments
    comments = db.relationship("Comment", back_populates="post")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class Comment(db.Model):
    __tablename__ = "comments"

    # Relationship to posts
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    post = db.relationship("BlogPost", back_populates="comments")

    # Relationship to author of the comment posted.
    comment_author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = db.relationship("User", back_populates="comments")

    comment_id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)


# Create all the tables in the database
# with app.app_context():
#     db.create_all()

# posts = requests.get("https://api.npoint.io/c790b4d5cab58020d391").json()

# Load credentials from environment variables or a configuration file
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")
RECIPIENT_PASSWORD = "avxb mryk rckh ehlx"
# RECIPIENT_PASSWORD = "newConnection."

LIST_OF_RECIPIENTS = ["amiddabs93@gmail.com", "232a.dabor@gmail.com", "daboramidu93@gmail.com"]

is_password_match = False


# Admin_only decorator
def admin_only(function):
    # Wrapper function
    @wraps(function)
    def decorated_function(*args, **kwargs):
        # If id is not 1, then abort the request with 403 error
        if current_user.id != 1:
            return abort(403)
        # Otherwise, continue with the route function
        return function(*args, **kwargs)

    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    global is_password_match

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Find user by email entered.
        user = User.query.filter_by(email=email).first()

        if user:
            # Check stored password hash against entered password.
            is_password_match = check_password_hash(user.password, password)

            if is_password_match:
                # custom_view_to_redirect_to = request.args.get('next')

                # login and validate the user.
                login_user(user)
                flash('Logged in successfully.')
                return redirect(url_for('home'))
            else:
                flash('Password incorrect; please try again.', category="error")
                return redirect(url_for('login'))
        elif not user and is_password_match:
            flash('Email address incorrect; please try again.', category="error")
            return redirect(url_for('login'))
        else:
            flash('Email or password incorrect.', category="error")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    flash('You are logged out.')
    return redirect(url_for('home'))


@app.route("/")
def home():
    with app.app_context():
        posts = BlogPost.query.all()
        return render_template("index.html", all_posts=posts)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("forms/contact.html")


# Register new users into the User database
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data
        password_confirm = form.password_confirm.data

        # Check if the email is already registered
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('A user has already registered with the same email. Please try a different email.', category='error')
            return redirect(url_for('register'))

        # Check if passwords match
        if password != password_confirm:
            flash('Passwords do not match; please try again.', category='error')
            return redirect(url_for('register'))

        # Hash the password before storing it.
        hashed_salted_password = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

        new_user = User(
            name=name,
            email=email,
            password=hashed_salted_password,
            password_confirm=hashed_salted_password
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)  # Automatically log in the newly registered user

        flash('Logged in successfully.')
        return redirect(url_for('home'))

    return render_template("register.html", form=form)


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def get_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment_form = CommentForm()

    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Please login or sign up to make a comment.', category='error')
            return redirect(url_for('login'))

        new_comment = Comment(
            comment_author_id=current_user.id,
            post_id=requested_post.id,
            text=comment_form.comment.data
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('get_post', post_id=post_id, comment=new_comment))

    return render_template('post.html', post=requested_post, comment_form=comment_form)


@app.route("/new-post", methods=['GET', 'POST'])
@admin_only
def make_post():
    post_form = CreatePostForm()
    current_datetime = datetime.now()
    new_post = BlogPost(post_author=current_user, date=current_datetime.strftime("%B %d, %Y %X"))

    if post_form.validate_on_submit():
        post_form.populate_obj(new_post)
        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for('home'))

    return render_template('make-post.html', form=post_form, new_post=True)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(obj=post)

    if edit_form.validate_on_submit():
        edit_form.populate_obj(post)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('get_post', id=post.id))

    return render_template('make-post.html', form=edit_form, post=post, is_edit_post=True)


@app.route("/delete-post/<int:post_id>")
@admin_only
def delete_post(post_id):
    post = BlogPost.query.get(post_id)

    if post:
        db.session.delete(post)
        db.session.commit()
        return redirect(url_for('home'))


@app.route("/form-entry")
def fetch_data():
    if request.method == "POST":
        name = request.form["username"]
        email = request.form["email"]
        phone = request.form["phone"]
        message = request.form["message"]

        # Send email
        # send_email(name, email, phone, message)

        return render_template("forms/contact.html", message_sent=True)

    return render_template("forms/contact.html", message_sent=False)


def send_email(name, sender_email, phone, message):
    email_message = f"Subject: Blog Contact \n\n" \
                    f"Name: {name} \n" \
                    f"Email: {sender_email} \n" \
                    f"Phone: {phone} \n" \
                    f"Message: {message}"

    # context = ssl.create_default_context()

    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(RECIPIENT_EMAIL, RECIPIENT_PASSWORD)
        connection.sendmail(sender_email, LIST_OF_RECIPIENTS, email_message)


if __name__ == "__main__":
    app.run(debug=True)
