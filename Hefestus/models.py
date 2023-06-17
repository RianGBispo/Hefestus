# Criar a estrutura do banco de dados
from datetime import datetime
from Hefestus import database, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_usuario(id_usuario):
    return Usuario.query.get(int(id_usuario))


class Usuario(database.Model, UserMixin):
    id = database.Column(database.Integer, primary_key=True)
    username = database.Column(database.String(50), unique=True, nullable=False)
    email = database.Column(database.String(100), unique=True, nullable=False)
    senha = database.Column(database.String(100), nullable=False)
    permissao = database.Column(database.String(20), nullable=False,
                                default='visualizar')  # Permissão do usuário (admin ou visualizar)


class Modelo(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    nome = database.Column(database.String(100), unique=True, nullable=False)
    compartimentos = database.relationship('Compartimento', backref='modelo_relacionado', lazy=True)
    bens = database.relationship('Maquina', backref='modelo', lazy=True)


class Maquina(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    nome = database.Column(database.String(100), unique=True, nullable=False)
    horimetro = database.Column(database.Integer, nullable=False)
    modelo_id = database.Column(database.Integer, database.ForeignKey('modelo.id'), nullable=False)
    compartimentos = database.relationship('Compartimento', backref='maquina', lazy=True)


class Compartimento(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    nome = database.Column(database.String(100), nullable=False)
    tipo_oleo = database.Column(database.String(100), nullable=False)
    quantidade_oleo = database.Column(database.Float, nullable=False)
    intervalo = database.Column(database.Integer, nullable=False)
    ultima_troca = database.Column(database.Integer)
    data_ultima_troca = database.Column(database.Date)
    modelo_id = database.Column(database.Integer, database.ForeignKey('modelo.id'), nullable=False)
    maquina_id = database.Column(database.Integer, database.ForeignKey('maquina.id'), nullable=False)
    atividades_feitas = database.relationship('Atividade', backref='atividades_feitas_compartimento', lazy=True,
                                              overlaps="atividades_feitas_compartimento")

    def __repr__(self):
        return f"Compartimento(id={self.id}, nome={self.nome})"


class Atividade(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    compartimento_id = database.Column(database.Integer, database.ForeignKey('compartimento.id'), nullable=False)
    maquina_id = database.Column(database.Integer, database.ForeignKey('maquina.id'), nullable=False)
    tipo = database.Column(database.String(100), nullable=False)
    litros_utilizados = database.Column(database.Integer, nullable=False)
    horimetro = database.Column(database.Integer, nullable=False)
    data_realizacao = database.Column(database.Date, nullable=False, default=datetime.now)
    numero_os = database.Column(database.Integer)
    compartimento = database.relationship('Compartimento', backref='atividades',
                                          overlaps="atividades_feitas_compartimento")
    maquina = database.relationship('Maquina', backref='atividades', lazy=True)
    usuario_id = database.Column(database.Integer, database.ForeignKey('usuario.id'))
    usuario = database.relationship('Usuario', backref=database.backref('atividades'))
