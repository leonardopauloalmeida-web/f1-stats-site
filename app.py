from flask import Flask, render_template, request, abort
import pandas as pd
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# A chave secreta NÃO fica mais no código (o repositório é público).
# No PythonAnywhere, crie a variável SECRET_KEY na aba Web.
# Esta chave de reserva serve só para rodar no seu computador.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-apenas-para-desenvolvimento')

# Caminho absoluto da pasta do projeto.
# Assim os .csv são achados em qualquer lugar (PythonAnywhere inclusive).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def ler_csv(nome, **kwargs):
    return pd.read_csv(os.path.join(BASE_DIR, nome), **kwargs)


# ============================================
# DADOS HISTÓRICOS DE VITÓRIAS (1950-2026)
# ============================================
df_vitorias = ler_csv('historico_f1.csv')

# Vitórias por piloto (histórico)
vitorias_piloto = df_vitorias.groupby('piloto')['vitorias'].sum().sort_values(ascending=False)

# Vitórias por equipe (histórico)
vitorias_equipe = df_vitorias.groupby('equipe')['vitorias'].sum().sort_values(ascending=False)

# Evolução por temporada (para gráfico de linha)
evolucao_anos = df_vitorias.groupby('ano')['vitorias'].count().index.tolist()
evolucao_valores = df_vitorias.groupby('ano')['vitorias'].count().values.tolist()

# ============================================
# DADOS DOS CAMPEÕES (PILOTOS)
# ============================================
df_pilotos_campeoes = ler_csv('pilotos_campeoes.csv')

# Títulos por piloto
titulos_piloto = df_pilotos_campeoes['piloto'].value_counts().sort_values(ascending=False)

# Títulos por país (dos pilotos)
titulos_pais = df_pilotos_campeoes['pais'].value_counts().sort_values(ascending=False)

# Lista completa de campeões (pilotos)
campeoes_lista = df_pilotos_campeoes.sort_values('ano', ascending=False).to_dict('records')

# ============================================
# DADOS DOS CAMPEÕES (CONSTRUTORES)
# ============================================
df_construtores_campeoes = ler_csv('construtores_campeoes.csv')

# Títulos por construtor
titulos_construtor = df_construtores_campeoes['equipe'].value_counts().sort_values(ascending=False)

# ============================================
# DADOS DO QUIZ
# ============================================
df_quiz = ler_csv('quiz_perguntas.csv')
perguntas_quiz = df_quiz.to_dict('records')

# ============================================
# DADOS DE COMPARAÇÃO DE PILOTOS
# ============================================
df_pilotos_detalhes = ler_csv('pilotos_detalhes.csv')
lista_pilotos = df_pilotos_detalhes['piloto'].tolist()

# ============================================
# DADOS DE COMPARAÇÃO DE EQUIPES
# ============================================
df_equipes_detalhes = ler_csv('equipes_detalhes.csv')
lista_equipes = df_equipes_detalhes['equipe'].tolist()

# ============================================
# DADOS DAS PISTAS
# ============================================
df_pistas = ler_csv('pistas_detalhes.csv')

# ============================================
# DADOS DE CURIOSIDADES
# ============================================
df_curiosidades = ler_csv('curiosidades.csv', quoting=1, quotechar='"')
lista_curiosidades = df_curiosidades.to_dict('records')

# ============================================
# DADOS DE POLE POSITIONS
# ============================================
df_poles = ler_csv('poles_f1_historico.csv')
poles_lista = df_poles.sort_values('poles', ascending=False).to_dict('records')

# ============================================
# ROTAS
# ============================================

@app.route('/')
def home():
    return render_template('index.html',
                         piloto_labels=vitorias_piloto.index.tolist(),
                         piloto_values=vitorias_piloto.values.tolist(),
                         equipe_labels=vitorias_equipe.index.tolist(),
                         equipe_values=vitorias_equipe.values.tolist(),
                         evolucao_anos=evolucao_anos,
                         evolucao_valores=evolucao_valores)

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
    piloto1 = request.form.get('piloto1', '')
    piloto2 = request.form.get('piloto2', '')

    # Usa os dados já carregados e responde 404 se o nome não existir
    linha1 = df_pilotos_detalhes[df_pilotos_detalhes['piloto'] == piloto1]
    linha2 = df_pilotos_detalhes[df_pilotos_detalhes['piloto'] == piloto2]
    if linha1.empty or linha2.empty:
        abort(404)

    return render_template('resultado.html', p1=linha1.iloc[0], p2=linha2.iloc[0])

@app.route('/comparar-equipes')
def comparar_equipes():
    return render_template('comparar_equipes.html', equipes=lista_equipes)

@app.route('/comparar-equipes/resultado', methods=['POST'])
def comparar_equipes_resultado():
    equipe1 = request.form.get('equipe1', '')
    equipe2 = request.form.get('equipe2', '')

    linha1 = df_equipes_detalhes[df_equipes_detalhes['equipe'] == equipe1]
    linha2 = df_equipes_detalhes[df_equipes_detalhes['equipe'] == equipe2]
    if linha1.empty or linha2.empty:
        abort(404)

    return render_template('resultado_equipes.html', e1=linha1.iloc[0], e2=linha2.iloc[0])

@app.route('/dashboard')
def dashboard():
    # A temporada 2026 é lida a cada visita ao dashboard.
    # Assim, quando você atualiza os .csv, o site mostra os dados novos
    # sem precisar apertar "Reload" no PythonAnywhere.
    df_classificacao = ler_csv('temporada_2026.csv')
    df_corridas = ler_csv('corridas_2026.csv')
    df_corridas['data'] = pd.to_datetime(df_corridas['data'])

    # Ordena por pontos (desempate: vitórias, depois pódios, como na F1)
    # e CALCULA a posição aqui. Assim a coluna "#" sempre bate com a ordem
    # da tabela, mesmo que a coluna "posicao" do CSV esteja desatualizada.
    df_classificacao = df_classificacao.sort_values(
        ['pontos', 'vitorias', 'podios'], ascending=False
    ).reset_index(drop=True)
    df_classificacao['posicao'] = df_classificacao.index + 1
    classificacao = df_classificacao.to_dict('records')

    # Uma corrida só vira "realizada" quando o DIA dela termina.
    agora = datetime.now()
    fim_do_dia = df_corridas['data'] + timedelta(days=1)
    corridas_realizadas = df_corridas[fim_do_dia <= agora]
    corridas_futuras = df_corridas[fim_do_dia > agora]

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

# ============================================
# ROTA DAS CURIOSIDADES
# ============================================

@app.route('/curiosidades')
def curiosidades():
    return render_template('curiosidades.html', curiosidades=lista_curiosidades)

# ============================================
# ROTA DAS POLE POSITIONS
# ============================================

@app.route('/poles')
def poles():
    return render_template('poles.html', poles=poles_lista)

if __name__ == '__main__':
    # debug=True só no seu computador. Nunca ligue isso em um site publicado.
    app.run(debug=True)