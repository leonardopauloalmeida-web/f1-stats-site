from flask import Flask, render_template
import pandas as pd

app = Flask(__name__)

# Carregar os dados
df = pd.read_csv('f1_2019_2023.csv')

# Contar vitórias (COM LETRA MAIÚSCULA!)
vitorias_piloto = df['Vencedor'].value_counts()
vitorias_equipe = df.groupby('Equipe')['Vencedor'].count().sort_values(ascending=False)

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

if __name__ == '__main__':
    app.run(debug=True)