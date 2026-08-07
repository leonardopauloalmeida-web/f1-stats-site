from flask import Flask, render_template, request, session, redirect, url_for
from flask_babel import Babel, _
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f1-stats-secret-key-2026'
app.config['BABEL_DEFAULT_LOCALE'] = 'pt'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

# Idiomas suportados
LANGUAGES = ['pt', 'en', 'ko']

babel = Babel(app)

# ===== CORREÇÃO: Usando o método correto para o Babel =====
def get_locale():
    # Verifica se o usuário escolheu um idioma na sessão
    if 'language' in session:
        lang = session['language']
        if lang in LANGUAGES:
            return lang
    # Se não, tenta detectar pelo navegador
    return request.accept_languages.best_match(LANGUAGES)

babel.locale_selector_func = get_locale

# Rota para mudar o idioma
@app.route('/language/<lang>')
def set_language(lang):
    if lang in LANGUAGES:
        session['language'] = lang
    return redirect(request.referrer or url_for('home'))

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

if __name__ == '__main__':
    app.run(debug=True)