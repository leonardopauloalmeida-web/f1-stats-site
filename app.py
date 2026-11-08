from flask import Flask, render_template, request, abort
import pandas as pd
import os
from datetime import datetime, timedelta
import requests
import time

app = Flask(__name__)

# Chave secreta para desenvolvimento
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-apenas-para-desenvolvimento')

# Caminho absoluto da pasta do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Campeão mundial de 2026
CAMPEAO_2026 = "Kimi Antonelli"

# ---------------------------------------------------------------
# CONFIGURAÇÃO DA API JOLPICA (DADOS AUTOMÁTICOS)
# ---------------------------------------------------------------
API_BASE_URL = "https://api.jolpi.ca/ergast/f1"
HEADERS = {"User-Agent": "EstatisticasF1/1.0.0"}

# Cache simples em memória (10 minutos) para não sobrecarregar a API
_cache = {}
CACHE_TTL = 600

def fetch_api(endpoint):
    """Busca dados da API Jolpica com cache e tratamento de erro."""
    agora = time.time()
    if endpoint in _cache and (agora - _cache[endpoint]['timestamp'] < CACHE_TTL):
        return _cache[endpoint]['data']
    
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        resposta = requests.get(url, headers=HEADERS, timeout=10)
        resposta.raise_for_status()
        dados = resposta.json()
        _cache[endpoint] = {'data': dados, 'timestamp': agora}
        return dados
    except Exception as e:
        print(f"Erro na API Jolpica ({endpoint}): {e}")
        if endpoint in _cache:
            return _cache[endpoint]['data']
        return None

def obter_classificacao_pilotos(ano):
    dados = fetch_api(f"{ano}/driverStandings.json")
    if not dados: return pd.DataFrame()
    lista = dados.get('MRData', {}).get('StandingsTable', {}).get('StandingsLists', [])
    if not lista: return pd.DataFrame()
    
    df = pd.DataFrame(lista[0]['DriverStandings'])
    if df.empty: return df
    
    df['piloto'] = df['Driver'].apply(lambda x: f"{x['givenName']} {x['familyName']}")
    df['equipe'] = df['Constructors'].apply(lambda x: x[0]['name'] if x else "N/A")
    df['pontos'] = df['points'].astype(int)
    df['vitorias'] = df['wins'].astype(int)
    df['posicao'] = df['position'].astype(int)
    
    # Criando colunas fictícias de pódios para não quebrar o HTML se ele esperar
    df['podios'] = 0 
    return df[['posicao', 'piloto', 'equipe', 'pontos', 'vitorias', 'podios']]

def obter_classificacao_construtores(ano):
    dados = fetch_api(f"{ano}/constructorStandings.json")
    if not dados: return pd.DataFrame()
    lista = dados.get('MRData', {}).get('StandingsTable', {}).get('StandingsLists', [])
    if not lista: return pd.DataFrame()
    
    df = pd.DataFrame(lista[0]['ConstructorStandings'])
    if df.empty: return df
    
    df['equipe'] = df['Constructor'].apply(lambda x: x['name'])
    df['pontos'] = df['points'].astype(int)
    df['vitorias'] = df['wins'].astype(int)
    df['posicao'] = df['position'].astype(int)
    df['podios'] = 0 
    return df[['posicao', 'equipe', 'pontos', 'vitorias', 'podios']]

def obter_calendario(ano):
    dados = fetch_api(f"{ano}/races.json")
    if not dados: return pd.DataFrame()
    corridas = dados.get('MRData', {}).get('RaceTable', {}).get('Races', [])
    df = pd.DataFrame(corridas)
    if df.empty: return df
    
    df['data'] = pd.to_datetime(df['date'])
    df['gp'] = df['raceName']
    return df[['gp', 'data']]

# ---------------------------------------------------------------
# FUNÇÕES AUXILIARES (CSV de fallback)
# ---------------------------------------------------------------
def ler_csv(nome, **kwargs):
    return pd.read_csv(os.path.join(BASE_DIR, nome), **kwargs)

def carregar_construtores(df_pilotos):
    if df_pilotos.empty: return pd.DataFrame(), True
    df = df_pilotos.groupby('equipe', as_index=False)[['pontos', 'vitorias']].sum()
    df = df.sort_values(['pontos', 'vitorias'], ascending=False).reset_index(drop=True)
    df['posicao'] = df.index + 1
    df['podios'] = 0
    return df, True

def montar_comparacao(linha1, linha2, chave):
    def limpar(serie):
        dados = {}
        for k, v in serie.items():
            if hasattr(v, 'item'): v = v.item()
            if isinstance(v, float) and v != v: v = 0
            dados[k] = v
        return dados
    d1, d2 = limpar(linha1), limpar(linha2)
    ignorar = {chave, 'id', 'posicao'}
    palavras_info = ('ano', 'estreia', 'nascimento')
    numericas = [k for k, v in d1.items() if k not in ignorar and isinstance(v, (int, float)) and not isinstance(v, bool) and not any(p in k.lower() for p in palavras_info)]
    def num(valor):
        if isinstance(valor, (int, float)) and not isinstance(valor, bool): return valor
        try: return float(valor)
        except: return 0
    stats = []
    for k in numericas:
        stats.append([str(k).replace('_', ' ').capitalize(), num(d1.get(k, 0)), num(d2.get(k, 0))])
    info1 = {k: v for k, v in d1.items() if k not in numericas and k != chave}
    info2 = {k: v for k, v in d2.items() if k not in numericas and k != chave}
    return {'stats': stats, 'info1': info1, 'info2': info2, 'vitorias1': sum(1 for x in stats if x[1] > x[2]), 'vitorias2': sum(1 for x in stats if x[2] > x[1])}

@app.context_processor
def injetar_campeao():
    return {'campeao_menu': CAMPEAO_2026}

# ============================================
# CARREGANDO DADOS HISTÓRICOS (CSVs LOCAIS)
# ============================================
df_vitorias = ler_csv('historico_f1.csv')
vitorias_piloto = df_vitorias.groupby('piloto')['vitorias'].sum().sort_values(ascending=False)
vitorias_equipe = df_vitorias.groupby('equipe')['vitorias'].sum().sort_values(ascending=False)
evolucao_anos = df_vitorias.groupby('ano')['vitorias'].count().index.tolist()
evolucao_valores = df_vitorias.groupby('ano')['vitorias'].count().values.tolist()

df_pilotos_campeoes = ler_csv('pilotos_campeoes.csv')
titulos_piloto = df_pilotos_campeoes['piloto'].value_counts().sort_values(ascending=False)
titulos_pais = df_pilotos_campeoes['pais'].value_counts().sort_values(ascending=False)
campeoes_lista = df_pilotos_campeoes.sort_values('ano', ascending=False).to_dict('records')

df_construtores_campeoes = ler_csv('construtores_campeoes.csv')
titulos_construtor = df_construtores_campeoes['equipe'].value_counts().sort_values(ascending=False)

df_quiz = ler_csv('quiz_perguntas.csv')
perguntas_quiz = df_quiz.to_dict('records')

df_pilotos_detalhes = ler_csv('pilotos_detalhes.csv')
lista_pilotos = df_pilotos_detalhes['piloto'].tolist()

df_equipes_detalhes = ler_csv('equipes_detalhes.csv')
lista_equipes = df_equipes_detalhes['equipe'].tolist()

df_pistas = ler_csv('pistas_detalhes.csv')
df_curiosidades = ler_csv('curiosidades.csv', quoting=1, quotechar='"')
lista_curiosidades = df_curiosidades.to_dict('records')

df_poles = ler_csv('poles_f1_historico.csv')
poles_lista = df_poles.sort_values('poles', ascending=False).to_dict('records')

# ============================================
# ROTAS
# ============================================

@app.route('/')
def home():
    return render_template('index.html', piloto_labels=vitorias_piloto.index.tolist(), piloto_values=vitorias_piloto.values.tolist(), equipe_labels=vitorias_equipe.index.tolist(), equipe_values=vitorias_equipe.values.tolist(), evolucao_anos=evolucao_anos, evolucao_valores=evolucao_valores)

@app.route('/sobre')
def sobre(): return render_template('sobre.html')

@app.route('/campeoes')
def campeoes():
    return render_template('campeoes.html', titulos_piloto_labels=titulos_piloto.index.tolist(), titulos_piloto_values=titulos_piloto.values.tolist(), titulos_construtor_labels=titulos_construtor.index.tolist(), titulos_construtor_values=titulos_construtor.values.tolist(), titulos_pais_labels=titulos_pais.index.tolist(), titulos_pais_values=titulos_pais.values.tolist(), campeoes=campeoes_lista)

@app.route('/quiz')
def quiz(): return render_template('quiz.html', perguntas=perguntas_quiz)

@app.route('/comparar')
def comparar(): return render_template('comparar.html', pilotos=lista_pilotos)

@app.route('/comparar/resultado', methods=['POST'])
def comparar_resultado():
    piloto1 = request.form.get('piloto1', '')
    piloto2 = request.form.get('piloto2', '')
    linha1 = df_pilotos_detalhes[df_pilotos_detalhes['piloto'] == piloto1]
    linha2 = df_pilotos_detalhes[df_pilotos_detalhes['piloto'] == piloto2]
    if linha1.empty or linha2.empty: abort(404)
    dados = montar_comparacao(linha1.iloc[0], linha2.iloc[0], 'piloto')
    return render_template('resultado.html', nome1=piloto1, nome2=piloto2, lista=lista_pilotos, **dados)

@app.route('/comparar-equipes')
def comparar_equipes(): return render_template('comparar_equipes.html', equipes=lista_equipes)

@app.route('/comparar-equipes/resultado', methods=['POST'])
def comparar_equipes_resultado():
    equipe1 = request.form.get('equipe1', '')
    equipe2 = request.form.get('equipe2', '')
    linha1 = df_equipes_detalhes[df_equipes_detalhes['equipe'] == equipe1]
    linha2 = df_equipes_detalhes[df_equipes_detalhes['equipe'] == equipe2]
    if linha1.empty or linha2.empty: abort(404)
    dados = montar_comparacao(linha1.iloc[0], linha2.iloc[0], 'equipe')
    return render_template('resultado_equipes.html', nome1=equipe1, nome2=equipe2, lista=lista_equipes, **dados)

@app.route('/dashboard')
def dashboard():
    ano_atual = datetime.now().year
    
    # 1. Tenta buscar da API
    df_classificacao = obter_classificacao_pilotos(ano_atual)
    df_construtores = obter_classificacao_construtores(ano_atual)
    df_corridas = obter_calendario(ano_atual)
    construtores_calculados = False

    # 2. Se a API falhar, usa o CSV como plano B
    if df_classificacao.empty:
        print("API falhou para pilotos. Usando CSV local.")
        try:
            df_classificacao = ler_csv('temporada_2026.csv')
            df_classificacao = df_classificacao.sort_values(['pontos', 'vitorias'], ascending=False).reset_index(drop=True)
            df_classificacao['posicao'] = df_classificacao.index + 1
        except: df_classificacao = pd.DataFrame()

    if df_construtores.empty:
        print("API falhou para construtores. Usando CSV local.")
        df_construtores, construtores_calculados = carregar_construtores(df_classificacao)

    if df_corridas.empty:
        print("API falhou para corridas. Usando CSV local.")
        try:
            df_corridas = ler_csv('corridas_2026.csv')
            df_corridas['data'] = pd.to_datetime(df_corridas['data'])
        except: df_corridas = pd.DataFrame()

    # 3. Processa para o HTML
    classificacao = df_classificacao.to_dict('records') if not df_classificacao.empty else []
    construtores = df_construtores.to_dict('records') if not df_construtores.empty else []
    
    total_pilotos = len(df_classificacao) if not df_classificacao.empty else 0
    lider_pontos = df_classificacao.iloc[0]['pontos'] if not df_classificacao.empty else 0

    ultimas_corridas, proximas_corridas = [], []
    total_corridas_realizadas = 0
    
    if not df_corridas.empty:
        agora = datetime.now()
        df_corridas['data_dt'] = pd.to_datetime(df_corridas['data'])
        realizadas = df_corridas[df_corridas['data_dt'] <= agora]
        futuras = df_corridas[df_corridas['data_dt'] > agora]
        
        total_corridas_realizadas = len(realizadas)
        ultimas_corridas = realizadas.sort_values('data_dt', ascending=False).head(5).to_dict('records')
        proximas_corridas = futuras.sort_values('data_dt', ascending=True).head(5).to_dict('records')

    return render_template('dashboard.html',
                         classificacao=classificacao,
                         construtores=construtores,
                         construtores_calculados=construtores_calculados,
                         campeao=CAMPEAO_2026,
                         ultimas_corridas=ultimas_corridas,
                         proximas_corridas=proximas_corridas,
                         total_corridas=total_corridas_realizadas,
                         total_pilotos=total_pilotos,
                         lider_pontos=lider_pontos)

@app.route('/pistas')
def pistas(): return render_template('pistas.html', pistas=df_pistas.to_dict('records'))

@app.route('/pista/<nome_pista>')
def pista_detalhe(nome_pista):
    pista = df_pistas[df_pistas['pista'] == nome_pista.replace('_', ' ')]
    if pista.empty: return "Pista não encontrada", 404
    return render_template('pista_detalhe.html', pista=pista.iloc[0].to_dict())

@app.route('/curiosidades')
def curiosidades(): return render_template('curiosidades.html', curiosidades=lista_curiosidades)

@app.route('/poles')
def poles(): return render_template('poles.html', poles=poles_lista)

if __name__ == '__main__':
    app.run(debug=True)