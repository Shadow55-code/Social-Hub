from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Post, Comment, Notification

app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.static_folder = 'static'
app.template_folder = 'templates'

# Initialize DB
db.init_app(app)

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Create tables
with app.app_context():
    db.create_all()


@app.route("/")
def index():
    return redirect(url_for("landing"))


@app.route("/landing")
def landing():
    return render_template("landing.html")


@app.route("/home")
@login_required
def home():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template("home.html", posts=posts)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect(url_for("home"))
        flash("Invalid credentials")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if User.query.filter_by(username=request.form["username"]).first():
            flash("Username already taken")
            return redirect(url_for("register"))
        user = User(
            username=request.form["username"],
            password=generate_password_hash(request.form["password"])
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing"))


@app.route("/create_post", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        new_post = Post(title=title, content=content, user_id=current_user.id)
        db.session.add(new_post)

        # Notify all users except the author
        users_to_notify = User.query.filter(User.id != current_user.id).all()
        for user in users_to_notify:
            notif = Notification(
                user_id=user.id,
                message=f"{current_user.username} posted: '{title}'"
            )
            db.session.add(notif)

        db.session.commit()
        flash("Post created successfully!")
        return redirect(url_for("home"))
    return render_template("create_post.html")


@app.route("/post/<int:post_id>")
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.timestamp).all()
    return render_template("post_detail.html", post=post, comments=comments)


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        return render_template("403.html"), 403
    if request.method == "POST":
        post.content = request.form["content"]
        db.session.commit()
        return redirect(url_for("post_detail", post_id=post.id))
    return render_template("edit_post.html", post=post)


@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    content = request.form["content"]
    parent_id = request.form.get("parent_id")
    comment = Comment(
        content=content,
        post_id=post_id,
        user_id=current_user.id,
        parent_id=parent_id if parent_id else None
    )
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for("post_detail", post_id=post_id))


@app.route("/user/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()
    return render_template("profile.html", profile_user=user, posts=posts)


@app.route("/notifications")
@login_required
def notifications():
    notes = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).all()
    return render_template("notification.html", notifications=notes)


@app.route("/notification/<int:id>/read")
@login_required
def mark_as_read(id):
    note = db.session.get(Notification, id)
    if note and note.user_id == current_user.id:
        note.is_read = True
        db.session.commit()
    return redirect(url_for("notifications"))


@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
