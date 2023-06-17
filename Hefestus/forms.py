# Criar os formularios do programa
from flask_wtf import FlaskForm
from sqlalchemy.testing import db
from sqlalchemy import or_
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, DateField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from efestos.models import Usuario, Modelo, Maquina, Compartimento
from efestos import database
import requests
from flask_wtf.file import FileField

class FormLogin(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    botao_confirmacao = SubmitField('Fazer Login')


class FormCriarConta(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    username = StringField('Nome de Usuário', validators=[DataRequired()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(6, 20)])
    confirmacao_senha = PasswordField('Confirmação de Senha', validators=[DataRequired(), EqualTo('senha')])
    botao_confirmacao = SubmitField('Criar Conta')

    def validate_email(self, email):
        usuario = Usuario.query.filter_by(email=email.data).first()
        if usuario:
            raise ValidationError('E-mail já cadastrado. Faça login para continuar')

    def save_usuario(self):
        usuario = Usuario(
            email=self.email.data,
            username=self.username.data,
            senha=self.senha.data
        )
        usuario.permissao = 'visualizar'
        db.session.add(usuario)
        db.session.commit()


class FormAtualizarPerfil(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha_atual = PasswordField('Senha Atual', validators=[DataRequired()])
    nova_senha = PasswordField('Nova Senha', validators=[Length(6, 20)])
    confirmacao_nova_senha = PasswordField('Confirmação da Nova Senha', validators=[EqualTo('nova_senha')])
    botao_confirmacao = SubmitField('Atualizar Perfil')


class CompartimentoForm(FlaskForm):
    nome = StringField('Nome do Compartimento', validators=[DataRequired()])
    tipo_oleo = StringField('Tipo de Óleo', validators=[DataRequired()])
    quant_oleo = IntegerField('Capacidade do Compartimento', validators=[DataRequired()])
    intervalo = IntegerField('Intervalo para Troca de Óleo', validators=[DataRequired()])
    modelo = SelectField('Modelo', coerce=int, validators=[DataRequired()])
    botao_confirmacao = SubmitField('Inserir Compartimentos')

    def __init__(self, *args, **kwargs):
        super(CompartimentoForm, self).__init__(*args, **kwargs)
        self.modelo.choices = [(modelo.id, modelo.nome) for modelo in Modelo.query.all()]

    def criar_compartimentos(self):
        compartimentos = []
        modelo_id = self.modelo.data
        maquinas = Maquina.query.filter_by(modelo_id=modelo_id).all()

        for maquina in maquinas:
            nome_compartimento = self.nome.data.upper().strip()

            # Verificar se já existe um compartimento com o mesmo nome para a mesma máquina
            if Compartimento.query.filter_by(nome=nome_compartimento, maquina_id=maquina.id).first():
                raise ValidationError(
                    f"Já existe um compartimento com o nome '{nome_compartimento}' para a máquina '{maquina.nome}'")

            compartimento = Compartimento(
                nome=nome_compartimento,
                tipo_oleo=self.tipo_oleo.data.upper().strip(),
                quantidade_oleo=self.quant_oleo.data,
                intervalo=self.intervalo.data,
                modelo_id=modelo_id,
                maquina_id=maquina.id
            )
            compartimentos.append(compartimento)
            database.session.add(compartimento)

        database.session.commit()
        return compartimentos


class FormAdicaoModelo(FlaskForm):
    nome = StringField('Nome do Modelo', validators=[DataRequired()])
    botao_confirmacao = SubmitField('Adicionar Modelo')

    def validate_nome(self, nome):
        modelo = Modelo.query.filter_by(nome=nome.data).first()
        if modelo:
            raise ValidationError('Modelo já cadastrado.')


class FormAdicaoMaquina(FlaskForm):
    nome = StringField('Nome da Máquina', validators=[DataRequired()])
    horimetro = IntegerField('Horímetro', validators=[DataRequired()])
    modelo = SelectField('Modelo', coerce=int)
    botao_confirmacao = SubmitField('Adicionar Máquina')

    def __init__(self, *args, **kwargs):
        super(FormAdicaoMaquina, self).__init__(*args, **kwargs)
        self.modelo.choices = [(modelo.id, modelo.nome) for modelo in Modelo.query.all()]

    def validate_modelo(self, modelo):
        modelo_obj = Modelo.query.get(modelo.data)
        if not modelo_obj:
            raise ValidationError('Modelo inválido.')

    def criar_maquina(self):
        maquina = Maquina(
            nome=self.nome.data,
            horimetro=self.horimetro.data,
            modelo_id=self.modelo.data
        )
        db.session.add(maquina)
        db.session.commit()
        return maquina


class FormAtividade(FlaskForm):
    data_realizacao = DateField('Data', validators=[DataRequired()])
    compartimento_id = SelectField('Compartimento', coerce=int, validators=[DataRequired()])
    maquina_id = SelectField('Máquina', coerce=int, validators=[DataRequired()])
    numero_os = IntegerField('Número da Ordem de Serviço')
    litros_utilizados = FloatField('Quantidade de Litros Utilizados', validators=[DataRequired()])
    horimetro = FloatField('Horímetro/Odômetro', validators=[DataRequired()])
    tipo = SelectField('Tipo de Atividade', choices=[('troca', 'Troca de Óleo'), ('reposicao', 'Reposição de Óleo')],
                       validators=[DataRequired()])
    busca_maquina = StringField('Buscar Máquina')
    botao_confirmacao = SubmitField('Adicionar Atividade de Óleo')

    def validate_maquina(self, field):
        maquina_obj = Maquina.query.get(field.data)

        if not maquina_obj or maquina_obj not in self.maquina_id.choices:
            raise ValidationError('Máquina inválida.')

        compartimentos = Compartimento.query.filter_by(maquina_id=field.data).all()  # Definir a variável compartimentos

        self.compartimento_id.choices = [(compartimento.id, compartimento.nome) for compartimento in compartimentos]

    def update_compartimentos_choices(self, maquina_id):
        maquina_obj = Maquina.query.get(maquina_id)
        if not maquina_obj or maquina_obj not in self.maquina_id.choices:
            raise ValidationError('Máquina inválida.')

        # Atualizar as opções do campo "compartimento" com base na máquina selecionada
        compartimentos = Compartimento.query.filter_by(maquina_id=maquina_id).all()
        self.compartimento_id.choices = [(compartimento.id, compartimento.nome) for compartimento in compartimentos]

    def update_choices(self):
        busca = self.busca_maquina.data

        if busca:
            maquinas = Maquina.query.filter(
                or_(Maquina.nome.ilike(f'%{busca}%'), Maquina.id.ilike(f'%{busca}%'))).all()
        else:
            maquinas = Maquina.query.all()

        self.maquina_id.choices = [(maquina.id, maquina.nome) for maquina in maquinas]

    def __init__(self, *args, **kwargs):
        super(FormAtividade, self).__init__(*args, **kwargs)
        self.update_choices()

        compartimentos = Compartimento.query.all()
        self.compartimento_id.choices = [(compartimento.id, compartimento.nome) for compartimento in compartimentos]


class FormAtualizarAtividade(FlaskForm):
    editar_atividade_id = StringField('Editar Atividade', validators=[DataRequired()])
    compartimento_id = SelectField('Compartimento', validators=[DataRequired()])
    maquina_id = SelectField('Máquina', validators=[DataRequired()])
    tipo = SelectField('Tipo de Atividade', choices=[('troca', 'Troca de Óleo'), ('reposicao', 'Reposição de Óleo')],
                       validators=[DataRequired()])
    litros_utilizados = FloatField('Quantidade de Litros Utilizados', validators=[DataRequired()])
    horimetro = FloatField('Horímetro/Odômetro', validators=[DataRequired()])
    data_realizacao = DateField('Data', validators=[DataRequired()])
    numero_os = IntegerField('Número da O.S.', default=0)
    botao_confirmacao = SubmitField('Adicionar Atividade de Óleo')


class FormExcluirModelo(FlaskForm):
    modelo_id = SelectField('Modelo', validators=[DataRequired()], coerce=int)


class FormExcluirMaquina(FlaskForm):
    maquina_id = SelectField('Máquina', validators=[DataRequired()], coerce=int)


class FormExcluirCompartimento(FlaskForm):
    compartimento_id = SelectField('Compartimento', validators=[DataRequired()], coerce=int)



class UsuarioForm(FlaskForm):
    permissao = SelectField('Permissão', choices=[('visualizar', 'Visualizar'), ('editar', 'Editar'), ('admin', 'Admin')])


class FormAtualizarHorimetro(FlaskForm):
    file = FileField('Selecione o arquivo Excel', validators=[DataRequired()])
    botao_confirmacao = SubmitField('Enviar')