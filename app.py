from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash, make_response
from pymongo import MongoClient
from datetime import datetime
import os
import pytz
from functools import wraps
from dotenv import load_dotenv
from bson.objectid import ObjectId
import pdfkit

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração do fuso horário para horário de Brasília
timezone = pytz.timezone('America/Sao_Paulo')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mysecretkey')

# Conexão com MongoDB Atlas usando a variável de ambiente MONGO_URI
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db_mongo = client['meu_banco_de_dados']
chamados_collection = db_mongo['chamados']

# Definir login e senha para o administrador a partir de variáveis de ambiente
ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'senha123')

# Rota para a página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Usuário ou senha inválidos!', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# Rota para logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Você foi desconectado!', 'success')
    return redirect(url_for('login'))

# Verificação se o usuário está logado para acessar a área administrativa
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

# Rota para o painel de administração, protegida pelo login
@app.route('/admin')
@login_required
def admin():
    chamados = list(chamados_collection.find())
    for chamado in chamados:
        chamado['status'] = 'Concluído' if chamado.get('data_conclusao') else 'Pendente'
    return render_template('admin.html', chamados=chamados)

@app.route('/')
def index():
    return render_template('index.html')

# Rota para exibir a página de registro de chamado
@app.route('/registrar_chamado', methods=['GET', 'POST'])
def registrar_chamado():
    if request.method == 'POST':
        solicitante = request.form['solicitante']
        local = request.form['local']
        descricao = request.form['descricao']

        chamado = {
            "solicitante": solicitante,
            "local": local,
            "descricao": descricao,
            "data_criacao": datetime.now(timezone),
            "data_conclusao": None,
            "responsavel": None
        }
        chamados_collection.insert_one(chamado)
        flash('Chamado registrado com sucesso!', 'success')
        return redirect(url_for('registrar_chamado'))

    return render_template('registrar_chamado.html')

# Rota para exibir o relatório de chamados
@app.route('/relatorio', methods=['GET'])
@login_required
def relatorio():
    chamados = list(chamados_collection.find())
    return render_template('relatorio.html', chamados=chamados)

# Rota para gerar HTML
@app.route('/gerar_html', methods=['POST'])
@login_required
def gerar_html():
    chamados = list(chamados_collection.find())
    rendered = render_template('relatorio.html', chamados=chamados)

    response = make_response(rendered)
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = 'attachment; filename=relatorio.html'
    return response

@app.route('/admin/chamados')
@login_required
def get_chamados():
    chamados = chamados_collection.find()
    return jsonify([{
        'id': idx + 1,
        'solicitante': chamado['solicitante'],
        'local': chamado['local'],
        'descricao': chamado['descricao'],
        'data_criacao': chamado['data_criacao'].strftime('%d/%m/%Y %H:%M'),
        'data_conclusao': chamado['data_conclusao'].strftime('%d/%m/%Y %H:%M') if chamado.get('data_conclusao') else None,
        'responsavel': chamado.get('responsavel', 'Não definido'),
        'status': 'Concluído' if chamado.get('data_conclusao') else 'Pendente'
    } for idx, chamado in enumerate(chamados)])

# Rota para concluir um chamado
@app.route('/concluir_chamado/<chamado_id>', methods=['POST'])
@login_required
def concluir_chamado(chamado_id):
    try:
        chamado = chamados_collection.find_one({"_id": ObjectId(chamado_id)})
        if not chamado:
            flash('Chamado não encontrado.', 'danger')
            return redirect(url_for('admin'))

        # Verifica se o chamado já está concluído
        if chamado.get("data_conclusao") is not None:
            flash('Chamado já está concluído.', 'info')
            return redirect(url_for('admin'))

        # Atualiza o chamado como concluído
        result = chamados_collection.update_one(
            {"_id": ObjectId(chamado_id)},
            {"$set": {
                "data_conclusao": datetime.now(timezone)
            }}
        )

        if result.modified_count > 0:
            flash('Chamado concluído com sucesso!', 'success')
        else:
            flash('Erro ao concluir o chamado.', 'danger')

    except Exception as e:
        flash(f'Erro ao concluir chamado: {str(e)}', 'danger')

    return redirect(url_for('admin'))

# Rota para excluir um chamado
@app.route('/excluir_chamado/<chamado_id>', methods=['POST'])
@login_required
def excluir_chamado(chamado_id):
    try:
        result = chamados_collection.delete_one({"_id": ObjectId(chamado_id)})
        if result.deleted_count > 0:
            flash('Chamado excluído com sucesso!', 'success')
        else:
            flash('Chamado não encontrado.', 'danger')
    except Exception as e:
        flash(f'Erro ao excluir chamado: {str(e)}', 'danger')
    
    return redirect(url_for('admin'))

# Rota para apagar o histórico de chamados concluídos
@app.route('/apagar_historico', methods=['POST'])
@login_required
def apagar_historico():
    chamados_collection.delete_many({"data_conclusao": {"$exists": True}})
    flash('Histórico de chamados concluídos apagado com sucesso!', 'success')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
