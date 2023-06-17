# Criar rotas do site
from datetime import datetime
import pandas as pd
from flask import render_template, url_for, redirect, request, flash, jsonify, send_file
from sqlalchemy.exc import IntegrityError
from Hefestus import app, bcrypt, database
from flask_login import login_required, current_user, login_user, logout_user
from Hefestus.forms import FormLogin, FormCriarConta, FormAtualizarPerfil, FormAdicaoModelo, FormAdicaoMaquina, \
    FormAtividade, UsuarioForm, CompartimentoForm, FormAtualizarAtividade, FormAtualizarHorimetro, \
    FormExcluirMaquina, FormExcluirCompartimento, FormExcluirModelo
from Hefestus.models import Usuario, Modelo, Compartimento, Maquina, Atividade
from wtforms.validators import ValidationError
import os
from werkzeug.utils import secure_filename
import csv
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func

def verificar_permissao(permissao_requerida):
    if current_user.permissao != permissao_requerida:
        return "Acesso não autorizado"


@app.route("/", methods=["GET", "POST"])
def homepage():
    form_login = FormLogin()
    if form_login.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form_login.email.data).first()
        if usuario and bcrypt.check_password_hash(usuario.senha, form_login.senha.data):
            login_user(usuario)
            return redirect(url_for("perfil", id_usuario=usuario.id))
        else:
            flash('Credenciais incorretas!', 'danger')
    return render_template("homepage.html", form=form_login)


@app.route('/criar-conta', methods=['GET', 'POST'])
@login_required
def criar_conta():
    if current_user.permissao != 'admin':
        return 'Acesso Não Autorizado'
    form_criarconta = FormCriarConta()
    if form_criarconta.validate_on_submit():
        senha = bcrypt.generate_password_hash(form_criarconta.senha.data)
        usuario = Usuario(username=form_criarconta.username.data.strip().upper(),
                          senha=senha, email=form_criarconta.email.data)
        database.session.add(usuario)
        database.session.commit()
        login_user(usuario, remember=True)
        return redirect(url_for('perfil', id_usuario=usuario.id))
    return render_template('criarconta.html', form=form_criarconta)


@app.route('/perfil/<id_usuario>', methods=['GET', 'POST'])
@login_required
def perfil(id_usuario):
    usuario = Usuario.query.get(int(id_usuario))
    form_atualizar_perfil = FormAtualizarPerfil()

    if form_atualizar_perfil.validate_on_submit():
        if form_atualizar_perfil.nova_senha.data != form_atualizar_perfil.confirmacao_nova_senha.data:
            flash('As senhas não correspondem.', 'danger')
            return redirect(url_for('perfil', id_usuario=id_usuario))

        # Verifica se a senha atual fornecida é válida
        if not bcrypt.check_password_hash(usuario.senha, form_atualizar_perfil.senha_atual.data):
            flash('A senha atual está incorreta.', 'danger')
            return redirect(url_for('perfil', id_usuario=id_usuario))

        # Atualiza as informações do perfil do usuário atual
        usuario.username = form_atualizar_perfil.username.data.strip().upper()
        usuario.email = form_atualizar_perfil.email.data
        nova_senha = form_atualizar_perfil.nova_senha.data
        if nova_senha:
            usuario.senha = bcrypt.generate_password_hash(nova_senha)
        # Salva as alterações no banco de dados
        database.session.commit()

        flash('Perfil atualizado com sucesso!', 'success')  # Adiciona mensagem de sucesso

        return redirect(url_for('perfil', id_usuario=id_usuario))

    return render_template('perfil.html', usuario=usuario, form=form_atualizar_perfil)


@app.route('/inserir-modelo', methods=['GET', 'POST'])
@login_required
def inserirmodelo():
    if current_user.permissao != 'admin':
        return 'Acesso Não Autorizado'
    form_adicao_modelo = FormAdicaoModelo()

    if form_adicao_modelo.validate_on_submit():
        modelo = Modelo(nome=form_adicao_modelo.nome.data.upper().strip())

        try:
            database.session.add(modelo)
            database.session.commit()
            flash('Modelo Adicionado Com Sucesso')
        except IntegrityError:
            database.session.rollback()
            flash('O modelo já existe no banco de dados.', 'error')

        return redirect(url_for('inserirmodelo'))

        # Flash the validation error message if it exists
    for field, errors in form_adicao_modelo.errors.items():
        for error in errors:
            flash(error)

    return render_template('inserirmodelo.html', form_modelo=form_adicao_modelo, )


@app.route('/inserir-maquina', methods=['GET', 'POST'])
@login_required
def inserirmaquina():
    if current_user.permissao != 'admin':
        return 'Acesso Não Autorizado'
    form_adicao_maquina = FormAdicaoMaquina()

    if form_adicao_maquina.validate_on_submit():
        nome = form_adicao_maquina.nome.data.upper().strip()
        horimetro = form_adicao_maquina.horimetro.data
        modelo_id = form_adicao_maquina.modelo.data

        maquina = Maquina(nome=nome, horimetro=horimetro, modelo_id=modelo_id)

        try:
            database.session.add(maquina)
            database.session.commit()
            flash('Bem Adicionado Com Sucesso')

        except IntegrityError:
            database.session.rollback()
            flash('O Bem já existe no banco de dados.', 'error')
            return redirect(url_for('inserirmaquina'))

        # Flash the validation error message if it exists
        for field, errors in form_adicao_maquina.errors.items():
            for error in errors:
                flash(error)

    return render_template('inserirmaquina.html', form_maquina=form_adicao_maquina)


@app.route('/inserir-compartimentos', methods=['GET', 'POST'])
@login_required
def inserircompartimentos():
    if current_user.permissao != 'admin':
        return 'Acesso Não Autorizado'

    form_adicionar_compartimento = CompartimentoForm()

    if form_adicionar_compartimento.validate_on_submit():
        try:
            compartimentos = form_adicionar_compartimento.criar_compartimentos()
            flash('Compartimentos Adicionados Com Sucesso')

            for compartimento in compartimentos:
                print(f"Novo compartimento criado: {compartimento}")

            return redirect(url_for('inserircompartimentos'))
        except ValidationError as e:
            flash(str(e), 'danger')

    return render_template('inserircompartimentos.html', form_compartimentos=form_adicionar_compartimento)


@app.route('/painel-de-controle', methods=['GET', 'POST'])
@login_required
def painel():
    if current_user.permissao != 'admin':
        return "Acesso não autorizado"

    # Obter as máquinas com reposição de óleo sem número de ordem de serviço
    maquinas_sem_os = (
        database.session.query(Maquina)
        .join(Compartimento)
        .join(Atividade)
        .filter(Atividade.numero_os == 0)
        .group_by(Maquina.id)
        .having(func.count(Atividade.id) > 3)
        .all()
    )

    form_atualizar_atividade = FormAtualizarAtividade()
    form_atualizar_atividade.maquina_id.choices = [(str(maquina.id), maquina.nome) for maquina in Maquina.query.all()]
    form_excluir_maquina = FormExcluirMaquina()
    form_excluir_maquina.maquina_id.choices = [(str(maquina.id), maquina.nome) for maquina in Maquina.query.all()]
    form_excluir_modelo = FormExcluirModelo()
    form_excluir_modelo.modelo_id.choices = [(str(modelo.id), modelo.nome) for modelo in Modelo.query.all()]
    form_excluir_compartimento = FormExcluirCompartimento()
    form_excluir_compartimento.compartimento_id.choices = [(str(compartimento.id), compartimento.nome) for compartimento in Compartimento.query.all()]

    if form_atualizar_atividade.validate_on_submit():
        atividade_id = form_atualizar_atividade.editar_atividade_id.data
        atividade = Atividade.query.get(atividade_id)

        if not atividade:
            flash('Atividade não encontrada!', 'danger')
            return redirect(url_for('painel'))

        atividade.compartimento_id = form_atualizar_atividade.compartimento_id.data
        atividade.maquina_id = form_atualizar_atividade.maquina_id.data
        atividade.tipo = form_atualizar_atividade.tipo.data.upper()
        atividade.litros_utilizados = form_atualizar_atividade.litros_utilizados.data
        atividade.horimetro = form_atualizar_atividade.horimetro.data
        atividade.data_realizacao = form_atualizar_atividade.data_realizacao.data
        atividade.numero_os = form_atualizar_atividade.numero_os.data
        atividade.usuario_id = current_user.id

        database.session.commit()
        flash('Atividade atualizada com sucesso!', 'success')

        return redirect(url_for('painel'))

    atividades = Atividade.query.all()
    maquinas = Maquina.query.all()
    compartimentos = Compartimento.query.all()
    modelos = Modelo.query.all()

    return render_template('paineldecontrole.html', atividades=atividades,
                           form_atualizar_atividade=form_atualizar_atividade,
                           form_excluir_maquina=form_excluir_maquina,
                           form_excluir_compartimento=form_excluir_compartimento,
                           maquinas=maquinas, form_excluir_modelo=modelos, compartimentos=compartimentos,
                           modelos=modelos, maquinas_sem_os=maquinas_sem_os)


@app.route('/atualizar-atividade/<int:atividade_id>', methods=['POST'])
@login_required
def atualizar_atividade(atividade_id):
    atividade = Atividade.query.get(atividade_id)

    if not atividade:
        flash('Atividade não encontrada!', 'danger')
        return redirect(url_for('painel'))

    numero_os = request.form.get('numero_os')

    if numero_os:
        atividade.numero_os = numero_os
        database.session.commit()
        flash('Número da ordem de serviço atualizado com sucesso!', 'success')

    return redirect(url_for('painel'))


@app.route('/excluir-atividade/<atividade_id>')
@login_required
def excluir_atividade(atividade_id):
    if current_user.permissao != 'admin':
        return "Acesso não autorizado"

    atividade = Atividade.query.get(atividade_id)
    if not atividade:
        flash('Atividade não encontrada!', 'danger')
        return redirect(url_for('painel'))

    database.session.delete(atividade)
    database.session.commit()
    flash('Atividade excluída com sucesso!', 'success')

    return redirect(url_for('painel'))


@app.route('/excluir-maquina/<int:maquina_id>', methods=['POST'])
@login_required
def excluir_maquina(maquina_id):
    if current_user.permissao != 'admin':
        return "Acesso não autorizado"

    maquina = Maquina.query.get(maquina_id)

    if not maquina:
        flash('Máquina não encontrada!', 'danger')
    else:
        try:
            atividades = Atividade.query.filter_by(maquina_id=maquina_id).all()
            for atividade in atividades:
                database.session.delete(atividade)

            database.session.delete(maquina)
            database.session.commit()
            flash('Máquina e atividades excluídas com sucesso!', 'success')
        except NoResultFound:
            flash('Não é possível excluir a máquina devido a atividades relacionadas.', 'danger')

    return redirect(url_for('painel'))


@app.route('/excluir_compartimento', methods=['POST'])
@login_required
def excluir_compartimento():
    if current_user.permissao != 'admin':
        return "Acesso não autorizado"

    compartimento_id = request.form['compartimento_id']
    compartimento = Compartimento.query.get(compartimento_id)

    if compartimento:
        database.session.delete(compartimento)
        database.session.commit()
        flash('Compartimento excluído com sucesso!', 'success')
    else:
        flash('Compartimento não encontrado!', 'danger')

    return redirect(url_for('painel'))


@app.route('/get-compartimentos/<maquina_id>')
def get_compartimentos(maquina_id):
    compartimentos = Compartimento.query.filter_by(maquina_id=maquina_id).all()
    compartimentos_data = [{'id': compartimento.id, 'nome': compartimento.nome} for compartimento in compartimentos]
    return jsonify({'compartimentos': compartimentos_data})


@app.route('/excluir-modelo', methods=['POST'])
@login_required
def excluir_modelo():
    if current_user.permissao != 'admin':
        return "Acesso não autorizado"

    modelo_id = request.form['modelo_id']
    modelo = Modelo.query.get(modelo_id)

    if modelo:
        database.session.delete(modelo)
        database.session.commit()
        flash('Modelo excluído com sucesso!', 'success')
    else:
        flash('Modelo não encontrado!', 'danger')

    return redirect(url_for('painel'))


@app.route('/atualizacoes', methods=['GET', 'POST'])
@login_required
def atualizacoes():
    if current_user.permissao != 'admin':
        return "Acesso não autorizado"

    form_atividade = FormAtividade()

    if form_atividade.validate_on_submit():
        compartimento_id = form_atividade.compartimento_id.data
        compartimento = Compartimento.query.get(compartimento_id)

        if compartimento:
            maquina_id = compartimento.maquina_id
            maquina = Maquina.query.get(maquina_id)

            atividade = Atividade(compartimento=compartimento,
                                  maquina=maquina,
                                  tipo=form_atividade.tipo.data.upper().strip(),
                                  litros_utilizados=form_atividade.litros_utilizados.data,
                                  horimetro=form_atividade.horimetro.data,
                                  data_realizacao=datetime.now(),
                                  numero_os=form_atividade.numero_os.data,
                                  usuario_id=current_user.id
                                  )

            # Verificar se a atividade é uma troca de óleo
            if atividade.tipo == 'TROCA':
                compartimento.ultima_troca = atividade.horimetro
                compartimento.data_ultima_troca = atividade.data_realizacao
                database.session.add(compartimento)

            database.session.add(atividade)
            database.session.commit()
            return redirect(url_for('atualizacoes'))

    return render_template('atualizacoes.html', form=form_atividade)


@app.route('/api/compartimentos/<int:maquina_id>')
@login_required
def fetch_compartimentos(maquina_id):
    compartimentos = Compartimento.query.filter_by(maquina_id=maquina_id).all()
    compartimentos_data = [{'id': compartimento.id, 'nome': compartimento.nome} for compartimento in compartimentos]
    return jsonify(compartimentos_data)


@app.route('/api/maquinas/buscar/<nome>')
@login_required
def buscar_maquinas(nome):
    maquinas = Maquina.query.filter(Maquina.nome.like(f"%{nome}%")).all()
    maquinas_data = [{'id': maquina.id, 'nome': maquina.nome} for maquina in maquinas]
    return jsonify(maquinas_data)


@app.route('/relatorios')
@login_required
def relatorios():
    verificar_permissao('visualizacao' or 'admin')
    return render_template('relatorios.html')


@app.route('/testes')
def testes():
    form_login = FormLogin()
    if form_login.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form_login.email.data).first()
        if usuario and bcrypt.check_password_hash(usuario.senha, form_login.senha.data):
            login_user(usuario)
            return redirect(url_for("testes", id_usuario=usuario.id))
    return render_template("testes.html", form=form_login)


@app.route('/listar-usuarios', methods=['GET', 'POST'])
@login_required
def listar_usuarios():
    if current_user.permissao != 'admin':
        return "Acesso não autorizado"

    usuarios = Usuario.query.all()
    form_usuario = UsuarioForm()

    if form_usuario.validate_on_submit():
        usuario_id = request.form['id']
        nova_permissao = form_usuario.permissao.data

        usuario = Usuario.query.get(usuario_id)

        if not usuario:
            return "Usuário não encontrado"

        usuario.permissao = nova_permissao
        database.session.commit()

        return redirect(url_for('listar_usuarios'))

    return render_template('listarusuarios.html', usuarios=usuarios, form=form_usuario)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('homepage'))


@app.route('/maquinas-proximas-troca', methods=['GET'])
@login_required
def maquinas_proximas_troca():
    # Obtém a lista de máquinas próximas da troca de óleo
    maquinas_proximas = obter_maquinas_proximas_troca()

    # Obtém a lista de máquinas que já passaram da troca de óleo
    maquinas_passadas = obter_maquinas_passadas_troca()

    # Obtém a lista de máquinas restantes
    maquinas_restantes = obter_maquinas_restantes()

    return render_template('maquinas_proximas.html',
                           maquinas_proximas=maquinas_proximas,
                           maquinas_passadas=maquinas_passadas,
                           maquinas_restantes=maquinas_restantes)


def obter_maquinas_proximas_troca():
    maquinas_proximas = []

    maquinas = Maquina.query.all()

    for maquina in maquinas:
        compartimentos = maquina.compartimentos

        for compartimento in compartimentos:
            diferenca_horimetro = horimetro_atual(maquina, compartimento)

            if diferenca_horimetro is not None and diferenca_horimetro >= compartimento.intervalo - 40:
                maquinas_proximas.append({
                    'maquina': maquina,
                    'compartimento': compartimento,
                    'horas_faltando': compartimento.intervalo - diferenca_horimetro
                })

    return maquinas_proximas


def obter_maquinas_passadas_troca():
    maquinas_passadas = []

    maquinas = Maquina.query.all()

    for maquina in maquinas:
        compartimentos = maquina.compartimentos

        for compartimento in compartimentos:
            diferenca_horimetro = horimetro_atual(maquina, compartimento)

            if diferenca_horimetro is not None and diferenca_horimetro >= compartimento.intervalo:
                maquinas_passadas.append({
                    'maquina': maquina,
                    'compartimento': compartimento,
                    'horas_passadas': diferenca_horimetro
                })

    return maquinas_passadas


def obter_maquinas_restantes():
    maquinas_restantes = []

    maquinas = Maquina.query.all()

    for maquina in maquinas:
        compartimentos = maquina.compartimentos

        troca_realizada = False

        for compartimento in compartimentos:
            diferenca_horimetro = horimetro_atual(maquina, compartimento)

            if diferenca_horimetro is not None and compartimento.intervalo > diferenca_horimetro >= 50:
                troca_realizada = True
                break

        if not troca_realizada:
            maquinas_restantes.append(maquina)

    return maquinas_restantes


def horimetro_atual(maquina, compartimento):
    if compartimento.ultima_troca is not None:
        return maquina.horimetro - compartimento.ultima_troca
    return None


def processar_arquivo_excel(caminho_arquivo, arquivo):
    # Ler o arquivo Excel usando o pandas
    df = pd.read_excel(caminho_arquivo)

    # Percorrer as linhas do arquivo Excel
    for index, row in df.iterrows():
        # Extrair os dados relevantes do arquivo
        nome_maquina = row['Maquina']
        modelo_maquina = row['Modelo']
        horimetro = row['Horimetro']

        # Verificar se o modelo já existe no banco de dados
        modelo = Modelo.query.filter_by(nome=modelo_maquina).first()
        if modelo is None:
            # Se o modelo não existir, criar um novo registro no banco de dados
            modelo = Modelo(nome=modelo_maquina)
            database.session.add(modelo)
            flash(f"Novo modelo adicionado: {modelo.nome}", "success")

        # Verificar se a máquina já existe no banco de dados
        maquina = Maquina.query.filter_by(nome=nome_maquina).first()
        if maquina is None:
            # Se a máquina não existir, criar um novo registro no banco de dados
            maquina = Maquina(nome=nome_maquina, modelo=modelo)
            database.session.add(maquina)
            flash(f"Nova máquina adicionada: {maquina.nome}", "success")

        # Atualizar o horímetro da máquina
        maquina.horimetro = horimetro

    # Salvar as alterações no banco de dados
    database.session.commit()

    # Renomear o arquivo com base na data e no ID do usuário
    data_upload = datetime.now().strftime('%Y%m%d')
    novo_nome = f"{data_upload}_user_{current_user.id}_{secure_filename(arquivo.filename)}"
    novo_caminho = os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], novo_nome)
    os.rename(caminho_arquivo, novo_caminho)


@app.route('/atualizar-horimetro', methods=['GET', 'POST'])
@login_required
def atualizar_horimetro():
    if current_user.permissao != 'admin':
        return "Acesso não autorizado"
    form_atualizar_horimetro = FormAtualizarHorimetro()
    if form_atualizar_horimetro.validate_on_submit():
        arquivo = form_atualizar_horimetro.file.data
        nome_seguro = secure_filename(arquivo.filename)
        caminho = os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], nome_seguro)
        arquivo.save(caminho)

        # Processar o arquivo Excel e atualizar o horímetro das máquinas
        try:
            processar_arquivo_excel(caminho, arquivo)
            flash("Horímetro atualizado com sucesso!", "success")
        except Exception as e:
            flash(f"Erro ao processar o arquivo Excel: {str(e)}", "error")

        return redirect(url_for('atualizar_horimetro'))

    return render_template('atualizar_horimetro.html', form=form_atualizar_horimetro)


@app.route('/exportar-dados')
@login_required
def exportar_dados():
    verificar_permissao('admin')

    # Obtenha todos os dados da base de dados
    usuarios = Usuario.query.all()
    modelos = Modelo.query.all()
    compartimentos = Compartimento.query.all()
    maquinas = Maquina.query.all()
    atividades = Atividade.query.all()

    # Defina o diretório de destino do arquivo CSV
    diretorio_destino = os.path.join(app.static_folder, 'exportar_dados')

    # Verifique se o diretório existe, caso contrário, crie-o
    if not os.path.exists(diretorio_destino):
        os.makedirs(diretorio_destino)

    # Defina o nome do arquivo CSV
    arquivo_csv = 'dados.csv'

    # Defina o caminho absoluto para o arquivo CSV
    caminho_absoluto = os.path.join(diretorio_destino, arquivo_csv)

    # Escreva os dados no arquivo CSV
    with open(caminho_absoluto, 'w', newline='') as file:
        writer = csv.writer(file)

        # Escreva o cabeçalho do arquivo CSV
        writer.writerow(['ID', 'Compartimento', 'Máquina', 'Tipo', 'Litros Utilizados', 'Data', 'Número OS'])  # Exemplo para a tabela 'Atividade'
        # Escreva os dados de cada tabela no arquivo CSV
        for atividade in atividades:
            compartimento_nome = atividade.compartimento.nome
            maquina_nome = atividade.maquina.nome
            writer.writerow([atividade.id, compartimento_nome, maquina_nome, atividade.tipo, atividade.litros_utilizados, atividade.data_realizacao, atividade.numero_os])
        # Repita o processo para as outras tabelas

    flash('Base de dados exportada com sucesso!', 'success')

    # Retorne o arquivo CSV como uma resposta para download
    return send_file(caminho_absoluto, as_attachment=True)

