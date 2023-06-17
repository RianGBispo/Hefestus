from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
import webview

# criando a aplicação
app = Flask(__name__)



app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dataset.db'
app.config['SECRET_KEY'] = 'ae6c7c54507087244fe52cc9e85c375786a05320'
app.config['UPLOAD_FOLDER'] = 'static/atualizar_horimetros'


database = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'homepage'


from Hefestus import routes
