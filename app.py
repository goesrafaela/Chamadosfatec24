from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///chamados.db')
db = SQLAlchemy(app)

class Chamado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    solicitante = db.Column(db.String(100), nullable=False)
    local = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_conclusao = db.Column(db.DateTime, nullable=True)
    responsavel = db.Column(db.String(100), nullable=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registrar_chamado', methods=['POST'])
def registrar_chamado():
    solicitante = request.form['solicitante']
    local = request.form['local']
    descricao = request.form['descricao']
    chamado = Chamado(solicitante=solicitante, local=local, descricao=descricao)
    db.session.add(chamado)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/admin/chamados')
def get_chamados():
    chamados = Chamado.query.all()
    return jsonify([{
        'id': chamado.id,
        'solicitante': chamado.solicitante,
        'local': chamado.local,
        'descricao': chamado.descricao,
        'data_criacao': chamado.data_criacao.strftime('%d/%m/%Y %H:%M'),
        'data_conclusao': chamado.data_conclusao.strftime('%d/%m/%Y %H:%M') if chamado.data_conclusao else None,
        'responsavel': chamado.responsavel
    } for chamado in chamados])

@app.route('/concluir_chamado/<int:id>', methods=['POST'])
def concluir_chamado(id):
    chamado = Chamado.query.get_or_404(id)
    chamado.data_conclusao = datetime.utcnow()
    chamado.responsavel = request.form['responsavel']
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/gerar_relatorio')
def gerar_relatorio():
    chamados = Chamado.query.filter(Chamado.data_conclusao.isnot(None)).all()
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    p.setFont("Helvetica", 12)
    p.drawString(100, height - 40, "Relatório de Manutenções Concluídas")
    p.drawString(100, height - 60, " ")

    y = height - 80
    for chamado in chamados:
        p.drawString(100, y, f"ID: {chamado.id}")
        p.drawString(150, y, f"Solicitante: {chamado.solicitante}")
        p.drawString(300, y, f"Local: {chamado.local}")
        y -= 20
        p.drawString(100, y, f"Descrição: {chamado.descricao}")
        y -= 20
        p.drawString(100, y, f"Data de Criação: {chamado.data_criacao.strftime('%d/%m/%Y %H:%M')}")
        if chamado.data_conclusao:
            p.drawString(300, y, f"Data de Conclusão: {chamado.data_conclusao.strftime('%d/%m/%Y %H:%M')}")
            p.drawString(100, y - 20, f"Responsável: {chamado.responsavel}")
        y -= 40
        
        if y < 40:  # Se chegar perto do final da página, cria uma nova
            p.showPage()
            y = height - 40
            p.setFont("Helvetica", 12)

    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='relatorio.pdf', mimetype='application/pdf')

@app.route('/apagar_historico')
def apagar_historico():
    try:
        db.session.query(Chamado).delete()
        db.session.commit()
        return redirect(url_for('admin'))
    except Exception as e:
        db.session.rollback()
        return f"Erro ao tentar apagar o histórico: {str(e)}"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Configuração para rodar no IP 192.168.11.221 e porta 5000
    app.run(host='192.168.11.221', port=5000, debug=True)
