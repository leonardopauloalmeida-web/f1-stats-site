from flask import Flask, render_template, request, session, redirect, url_for
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f1-stats-secret-key-2026'

# ============================================
# DADOS HISTÓRICOS DE VITÓRIAS (1950-2026)
# ============================================
df_vitorias = pd.read_csv('historico_f1.csv')

# Vitórias por piloto (histórico)
vitorias_piloto = df_vitorias.groupby('piloto')['vitorias'].sum().sort_values(ascending=False)

# Vitórias por equipe (histórico)
vitorias_equipe = df_vitorias.groupby('equipe')['vitorias'].sum().sort_values(ascending=False)

# ============================================
# DADOS DOS CAMPEÕES (PILOTOS)
# ============================================
df_pilotos_campeoes = pd.read_csv('pilotos_campeoes.csv')

# Títulos por piloto
titulos_piloto = df_pilotos_campeoes['piloto'].value_counts().sort_values(ascending=False)

# Títulos por país (dos pilotos)
titulos_pais = df_pilotos_campeoes['pais'].value_counts().sort_values(ascending=False)

# Lista completa de campeões (pilotos)
campeoes_lista = df_pilotos_campeoes.sort_values('ano', ascending=False).to_dict('records')

# ============================================
# DADOS DOS CAMPEÕES (CONSTRUTORES)
# ============================================
df_construtores_campeoes = pd.read_csv('construtores_campeoes.csv')

# Títulos por construtor
titulos_construtor = df_construtores_campeoes['equipe'].value_counts().sort_values(ascending=False)

# ============================================
# DADOS DO QUIZ
# ============================================
df_quiz = pd.read_csv('quiz_perguntas.csv')
perguntas_quiz = df_quiz.to_dict('records')

# ============================================
# DADOS DE COMPARAÇÃO DE PILOTOS
# ============================================
df_pilotos_detalhes = pd.read_csv('pilotos_detalhes.csv')
lista_pilotos = df_pilotos_detalhes['piloto'].tolist()

# ============================================
# DADOS DE COMPARAÇÃO DE EQUIPES
# ============================================
df_equipes_detalhes = pd.read_csv('equipes_detalhes.csv')
lista_equipes = df_equipes_detalhes['equipe'].tolist()

# ============================================
# DADOS DA TEMPORADA 2026 (DASHBOARD)
# ============================================
df_classificacao = pd.read_csv('temporada_2026.csv')
df_corridas = pd.read_csv('corridas_2026.csv')

# Converter datas
df_corridas['data'] = pd.to_datetime(df_corridas['data'])

# ============================================
# DADOS DAS PISTAS
# ============================================
df_pistas = pd.read_csv('pistas_detalhes.csv')

# ============================================
# ROTAS
# ============================================

@app.route('/')
def home():
    return render_template('index.html',
                         piloto_labels=vitorias_piloto.index.tolist(),
                         piloto_values=vitorias_piloto.values.tolist(),
                         equipe_labels=vitorias_equipe.index.tolist(),
                         equipe_values=vitorias_equipe.values.tolist())

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/campeoes')
def campeoes():
    return render_template('campeoes.html',
                         titulos_piloto_labels=titulos_piloto.index.tolist(),
                         titulos_piloto_values=titulos_piloto.values.tolist(),
                         titulos_construtor_labels=titulos_construtor.index.tolist(),
                         titulos_construtor_values=titulos_construtor.values.tolist(),
                         titulos_pais_labels=titulos_pais.index.tolist(),
                         titulos_pais_values=titulos_pais.values.tolist(),
                         campeoes=campeoes_lista)

@app.route('/quiz')
def quiz():
    return render_template('quiz.html', perguntas=perguntas_quiz)

@app.route('/comparar')
def comparar():
    return render_template('comparar.html', pilotos=lista_pilotos)

@app.route('/comparar/resultado', methods=['POST'])
def comparar_resultado():
    piloto1 = request.form['piloto1']
    piloto2 = request.form['piloto2']
    df_pilotos = pd.read_csv('pilotos_detalhes.csv')
    
    dados1 = df_pilotos[df_pilotos['piloto'] == piloto1].iloc[0]
    dados2 = df_pilotos[df_pilotos['piloto'] == piloto2].iloc[0]
    
    return render_template('resultado.html', p1=dados1, p2=dados2)

@app.route('/comparar-equipes')
def comparar_equipes():
    return render_template('comparar_equipes.html', equipes=lista_equipes)

@app.route('/comparar-equipes/resultado', methods=['POST'])
def comparar_equipes_resultado():
    equipe1 = request.form['equipe1']
    equipe2 = request.form['equipe2']
    df_equipes = pd.read_csv('equipes_detalhes.csv')
    
    dados1 = df_equipes[df_equipes['equipe'] == equipe1].iloc[0]
    dados2 = df_equipes[df_equipes['equipe'] == equipe2].iloc[0]
    
    return render_template('resultado_equipes.html', e1=dados1, e2=dados2)

@app.route('/dashboard')
def dashboard():
    classificacao = df_classificacao.to_dict('records')
    
    # Separar corridas realizadas (passado) e próximas (futuro)
    agora = datetime.now()
    corridas_realizadas = df_corridas[df_corridas['data'] <= agora]
    corridas_futuras = df_corridas[df_corridas['data'] > agora]
    
    total_corridas_realizadas = len(corridas_realizadas)
    total_pilotos = len(df_classificacao)
    lider_pontos = df_classificacao.iloc[0]['pontos'] if not df_classificacao.empty else 0
    
    # Últimas 5 corridas realizadas
    ultimas_corridas = corridas_realizadas.sort_values('data', ascending=False).head(5).to_dict('records')
    
    # Próximas 5 corridas
    proximas_corridas = corridas_futuras.sort_values('data', ascending=True).head(5).to_dict('records')
    
    return render_template('dashboard.html', 
                         classificacao=classificacao,
                         ultimas_corridas=ultimas_corridas,
                         proximas_corridas=proximas_corridas,
                         total_corridas=total_corridas_realizadas,
                         total_pilotos=total_pilotos,
                         lider_pontos=lider_pontos)

# ============================================
# ROTAS DAS PISTAS
# ============================================

@app.route('/pistas')
def pistas():
    pistas = df_pistas.to_dict('records')
    return render_template('pistas.html', pistas=pistas)

@app.route('/pista/<nome_pista>')
def pista_detalhe(nome_pista):
    nome_pista_formatado = nome_pista.replace('_', ' ')
    
    # Buscar a pista pelo nome
    pista = df_pistas[df_pistas['pista'] == nome_pista_formatado]
    
    if pista.empty:
        return "Pista não encontrada", 404
    
    pista = pista.iloc[0].to_dict()
    return render_template('pista_detalhe.html', pista=pista)

if __name__ == '__main__':
    app.run(debug=True)