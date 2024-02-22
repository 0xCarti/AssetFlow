from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'


@login_manager.user_loader
def load_user(user_id):
    from .models.models import User
    return User.query.get(int(user_id))


def create_admin_user():
    from app.models.models import User
    # Check if any admin exists
    admin_exists = User.query.filter_by(is_admin=True).first()
    if not admin_exists:

        # Create an admin user
        admin_email = "brycecotton@mail.com"  # Use your desired admin email
        admin_password = generate_password_hash("Snotsuh1")  # Use a secure password
        admin_user = User(email=admin_email, password=admin_password, is_admin=True, active=True)

        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created.")


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'Snotsuh1'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'

    db.init_app(app)
    login_manager.init_app(app)
    Bootstrap(app)

    with app.app_context():
        from .models import models
        from .routes import auth_routes, routes
        from .routes.routes import main, location, item, transfer
        from .routes.auth_routes import auth, admin
        from app.models.models import User

        app.register_blueprint(auth, url_prefix='/auth')
        app.register_blueprint(main)
        app.register_blueprint(location)
        app.register_blueprint(item)
        app.register_blueprint(transfer)
        app.register_blueprint(admin)

        db.create_all()
        create_admin_user()
        CSRFProtect(app)

    return app
