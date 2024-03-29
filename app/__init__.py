import os
from dotenv import load_dotenv
from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash

load_dotenv()
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
socketio = None


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))


def create_admin_user():
    from app.models import User
    # Check if any admin exists
    admin_exists = User.query.filter_by(is_admin=True).first()
    if not admin_exists:

        # Create an admin user
        admin_email = os.getenv('ADMIN_EMAIL')
        admin_password = generate_password_hash(os.getenv('ADMIN_PASS'))
        admin_user = User(email=admin_email, password=admin_password, is_admin=True, active=True)

        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created.")


def create_app(args: list):
    global socketio
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
    app.config['UPLOAD_FOLDER'] = 'uploads'
    if '--demo' in args:
        app.config['DEMO'] = True
    else:
        app.config['DEMO'] = False

    db.init_app(app)
    login_manager.init_app(app)
    Bootstrap(app)
    socketio = SocketIO(app)

    with app.app_context():
        from app.routes import auth_routes
        from app.routes.routes import main, location, item, transfer
        from app.routes.auth_routes import auth, admin
        from app.models import User

        app.register_blueprint(auth, url_prefix='/auth')
        app.register_blueprint(main)
        app.register_blueprint(location)
        app.register_blueprint(item)
        app.register_blueprint(transfer)
        app.register_blueprint(admin)

        db.create_all()
        create_admin_user()
        CSRFProtect(app)

    return app, socketio
