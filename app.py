from flask import Flask, render_template
import pandas as pd

app = Flask(__name__)

# ============================================
# DADOS HISTÓRICOS (1950-2026)
# ============================================
df_vitorias = pd.read_csv('historico_f1.csv')

# Vitórias por piloto (histórico)
vitorias_piloto = df_vitorias.groupby('piloto')['vitorias'].sum().sort_values(ascending=False)

# Vitórias por equipe (histórico)
vitorias_equipe = df_vitorias.groupby('equipe')['vitorias'].sum().sort_values(ascending=False)

# ============================================
# DADOS DOS CAMPEÕES
# ============================================
df_campeoes = pd.read_csv('campeoes_f1.csv')

# Títulos por piloto
titulos_piloto = df_campeoes['piloto'].value_counts().sort_values(ascending=False)

# Títulos por equipe
titulos_equipe = df_campeoes['equipe'].value_counts().sort_values(ascending=False)

# Títulos por país
titulos_pais = df_campeoes['pais'].value_counts().sort_values(ascending=False)

# Lista completa de campeões
campeoes_lista = df_campeoes.sort_values('ano', ascending=False).to_dict('records')

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
                         titulos_equipe_labels=titulos_equipe.index.tolist(),
                         titulos_equipe_values=titulos_equipe.values.tolist(),
                         titulos_pais_labels=titulos_pais.index.tolist(),
                         titulos_pais_values=titulos_pais.values.tolist(),
                         campeoes=campeoes_lista)

if __name__ == '__main__':
    app.run(debug=True)