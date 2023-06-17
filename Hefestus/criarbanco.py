from efestos import database, app
from efestos.models import Usuario, Modelo, Compartimento, Maquina, Atividade

with app.app_context():
    database.create_all()
