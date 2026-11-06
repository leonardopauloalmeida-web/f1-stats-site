from flask import Flask, render_template, request, abort
import pandas as pd
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Corrigido: a chave secreta NÃO fica mais no código (o repositório é público).
# No PythonAnywhere, crie a variável SECRET_KEY (veja as instruções na conversa).
# Esta chave de reserva serve só para rodar no seu computador.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-apenas-para-desenvolvimento')

# Corrigido: caminho absoluto da pasta do projeto.
# Assim os .csv são achados em qualquer lugar (PythonAnywhere inclusive),
# e não dependem da pasta em que o servidor foi iniciado.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Campeão mundial de 2026 (título garantido no GP da Cidade do México, 1º/11/2026).
# Deve ser IGUAL ao nome na coluna "piloto" do temporada_2026.csv.
# Para a temporada que vem, é só trocar o nome aqui (ou deixar vazio: "").
CAMPEAO_2026 = "Kimi Antonelli"


def ler_csv(nome, **kwargs):
    return pd.read_csv(os.path.join(BASE_DIR, nome), **kwargs)


def carregar_construtores(df_pilotos):
    """Monta a classificação de construtores da temporada 2026.

    1) Se existir o arquivo construtores_2026.csv (colunas: equipe,pontos,vitorias,podios),
       usa ele. É o jeito mais fiel ao campeonato oficial.
    2) Se NÃO existir, soma os pontos dos pilotos de cada equipe.
       Atenção: se algum piloto trocou de equipe no meio do ano, essa soma pode
       ficar diferente da tabela oficial.
    """
    caminho = os.path.join(BASE_DIR, 'construtores_2026.csv')
    if os.path.exists(caminho):
        df = pd.read_csv(caminho)
        calculado = False
    else:
        df = df_pilotos.groupby('equipe', as_index=False)[['pontos', 'vitorias', 'podios']].sum()
        calculado = True

    df = df.sort_values(['pontos', 'vitorias', 'podios'], ascending=False).reset_index(drop=True)
    df['posicao'] = df.index + 1

    # Percentual em relação ao líder (usado na barra de pontos)
    maior = df['pontos'].max() if not df.empty else 0
    df['percentual'] = (df['pontos'] / maior * 100).round(1) if maior else 0
    return df, calculado


def montar_comparacao(linha1, linha2, chave):
    """Prepara os dados de duas linhas (pilotos ou equipes) para a página de comparação."""
    def limpar(serie):
        dados = {}
        for k, v in serie.items():
            if hasattr(v, 'item'):      # converte tipos do numpy para Python puro
                v = v.item()
            if isinstance(v, float) and v != v:   # NaN vira 0
                v = 0
            dados[k] = v
        return dados

    d1, d2 = limpar(linha1), limpar(linha2)
    ignorar = {chave, 'id', 'posicao'}
    palavras_info = ('ano', 'estreia', 'nascimento')

    numericas = [
        k for k, v in d1.items()
        if k not in ignorar
        and isinstance(v, (int, float)) and not isinstance(v, bool)
        and not any(p in k.lower() for p in palavras_info)
    ]

    def num(valor):
        # Garante que o valor é estritamente numérico. Se for texto, tenta converter, se não der, vira 0.
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return valor
        try:
            return float(valor)
        except (ValueError, TypeError):
            return 0

    # Constrói a lista de estatísticas convertendo TUDO para número
    stats = []
    for k in numericas:
        nome_formatado = str(k).replace('_', ' ').capitalize()
        v1 = num(d1.get(k, 0))
        v2 = num(d2.get(k, 0))
        stats.append([nome_formatado, v1, v2])

    info1 = {k: v for k, v in d1.items() if k not in numericas and k != chave}
    info2 = {k: v for k, v in d2.items() if k not in numericas and k != chave}

    return {
        'stats': stats,
        'info1': info1,
        'info2': info2,
        'vitorias1': sum(1 for x in stats if x[1] > x[2]),
        'vitorias2': sum(1 for x in stats if x[2] > x[1]),
    }


# ---------------------------------------------------------------
# TÍTULO MATEMÁTICO (pilotos e construtores)
# ---------------------------------------------------------------
# Pontos máximos que UM piloto ou UMA equipe ainda pode somar:
#   - Piloto: 25 por corrida (vitória) + 8 por sprint (vitória no sprint)
#   - Construtor: 43 por corrida (1º + 2º = 25 + 18) + 15 por sprint (8 + 7)
PONTOS_CORRIDA_PILOTO, PONTOS_SPRINT_PILOTO = 25, 8
PONTOS_CORRIDA_EQUIPE, PONTOS_SPRINT_EQUIPE = 43, 15


def corridas_restantes_e_sprints():
    """Conta as corridas que ainda faltam (e quantas são sprint) no corridas_2026.csv.

    Para marcar um fim de semana de sprint, crie no CSV a coluna "sprint"
    com o valor "sim" nessas corridas. Sem a coluna, considera que não há sprint.
    Devolve (None, None) se não conseguir ler o arquivo (aí nada é afirmado).
    """
    try:
        df = ler_csv('corridas_2026.csv')
        df['data'] = pd.to_datetime(df['data'])
    except Exception:
        return None, None
    futuras = df[df['data'] + timedelta(days=1) > datetime.now()]
    sprints = 0
    if 'sprint' in futuras.columns:
        marcados = futuras['sprint'].astype(str).str.strip().str.lower()
        sprints = int(marcados.isin(['1', 'sim', 's', 'true', 'x', 'yes']).sum())
    return len(futuras), sprints


def analisar_titulo(df, coluna, max_corrida, max_sprint, corridas, sprints):
    """Diz se o líder já é campeão MATEMATICAMENTE.

    A conta é a do pior caso para o líder: ele não soma mais nenhum ponto e
    cada rival soma o máximo possível em todas as corridas que faltam.
    O líder só é campeão se nenhum rival consegue alcançá-lo (empate em
    pontos conta como "ainda dá", pois o desempate é por vitórias).
    """
    if df is None or len(df) < 2 or corridas is None:
        return None
    df = df.sort_values(['pontos', 'vitorias', 'podios'], ascending=False).reset_index(drop=True)
    max_restante = corridas * max_corrida + sprints * max_sprint
    lider, segundo = df.iloc[0], df.iloc[1]
    pontos_lider = int(lider['pontos'])

    vivos = []
    for _, linha in df.iloc[1:].iterrows():
        diferenca = pontos_lider - int(linha['pontos'])
        if diferenca <= max_restante:
            vivos.append({'nome': linha[coluna], 'pontos': int(linha['pontos']), 'diferenca': diferenca})

    vantagem = pontos_lider - int(segundo['pontos'])
    campeao = len(vivos) == 0
    return {
        'lider': {'nome': lider[coluna], 'pontos': pontos_lider},
        'segundo': {'nome': segundo[coluna], 'pontos': int(segundo['pontos'])},
        'vantagem': vantagem,
        'max_restante': max_restante,
        'corridas': corridas,
        'sprints': sprints,
        'max_corrida': max_corrida,
        'max_sprint': max_sprint,
        'campeao': campeao,
        'faltam': max(0, max_restante - vantagem + 1),   # vantagem que ainda falta abrir
        'percentual': 100 if campeao else min(100, round(vantagem / (max_restante + 1) * 100, 1)),
        'vivos': vivos,
    }


def obter_campeao():
    """Nome do campeão de pilotos: o manual (CAMPEAO_2026) ou o calculado pela matemática."""
    if CAMPEAO_2026:
        return CAMPEAO_2026
    try:
        corridas, sprints = corridas_restantes_e_sprints()
        analise = analisar_titulo(ler_csv('temporada_2026.csv'), 'piloto',
                                  PONTOS_CORRIDA_PILOTO, PONTOS_SPRINT_PILOTO, corridas, sprints)
        if analise and analise['campeao']:
            return analise['lider']['nome']
    except Exception:
        pass
    return ""


@app.context_processor
def injetar_campeao():
    # Disponibiliza {{ campeao_menu }} em TODAS as páginas (usado no menu lateral)
    return {'campeao_menu': obter_campeao()}


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

    # Corrigido: usa os dados já carregados (sem reler o CSV a cada clique)
    # e responde com erro 404 se o nome não existir, em vez de quebrar com IndexError.
    linha1 = df_pilotos_detalhes[df_pilotos_detalhes['piloto'] == piloto1]
    linha2 = df_pilotos_detalhes[df_pilotos_detalhes['piloto'] == piloto2]
    if linha1.empty or linha2.empty:
        abort(404)

    dados = montar_comparacao(linha1.iloc[0], linha2.iloc[0], 'piloto')
    return render_template('resultado.html', nome1=piloto1, nome2=piloto2,
                           lista=lista_pilotos, **dados)

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

    dados = montar_comparacao(linha1.iloc[0], linha2.iloc[0], 'equipe')
    return render_template('resultado_equipes.html', nome1=equipe1, nome2=equipe2,
                           lista=lista_equipes, **dados)

@app.route('/dashboard')
def dashboard():
    # Corrigido: a temporada 2026 é lida a cada visita ao dashboard.
    # Assim, quando você atualiza os .csv, o site mostra os dados novos
    # sem precisar apertar "Reload" no PythonAnywhere.
    df_classificacao = ler_csv('temporada_2026.csv')
    df_corridas = ler_csv('corridas_2026.csv')
    df_corridas['data'] = pd.to_datetime(df_corridas['data'])

    # Corrigido: ordena por pontos (desempate: vitórias, depois pódios, como na F1)
    # e CALCULA a posição aqui. Assim a coluna "#" sempre bate com a ordem da tabela,
    # mesmo que a coluna "posicao" do CSV esteja desatualizada.
    df_classificacao = df_classificacao.sort_values(
        ['pontos', 'vitorias', 'podios'], ascending=False
    ).reset_index(drop=True)
    df_classificacao['posicao'] = df_classificacao.index + 1
    classificacao = df_classificacao.to_dict('records')

    # Classificação de construtores (equipes)
    df_construtores, construtores_calculados = carregar_construtores(df_classificacao)
    construtores = df_construtores.to_dict('records')

    # Corrigido: uma corrida só vira "realizada" quando o DIA dela termina.
    # Antes, uma corrida marcada para hoje (data 00:00) já aparecia como realizada de manhã,
    # antes mesmo de acontecer.
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

    # Título matemático (pilotos e construtores) com as corridas que ainda faltam
    sprints_restantes = 0
    if 'sprint' in corridas_futuras.columns:
        marcados = corridas_futuras['sprint'].astype(str).str.strip().str.lower()
        sprints_restantes = int(marcados.isin(['1', 'sim', 's', 'true', 'x', 'yes']).sum())
    corridas_restantes = len(corridas_futuras)
    analise_pilotos = analisar_titulo(df_classificacao, 'piloto', PONTOS_CORRIDA_PILOTO,
                                      PONTOS_SPRINT_PILOTO, corridas_restantes, sprints_restantes)
    analise_construtores = analisar_titulo(df_construtores, 'equipe', PONTOS_CORRIDA_EQUIPE,
                                           PONTOS_SPRINT_EQUIPE, corridas_restantes, sprints_restantes)

    # Campeão de pilotos: o manual, ou o que a matemática já garantiu
    campeao_nome = CAMPEAO_2026
    if not campeao_nome and analise_pilotos and analise_pilotos['campeao']:
        campeao_nome = analise_pilotos['lider']['nome']

    # Dados do campeão para a faixa de troféu (None se o nome não for achado)
    linha_campeao = df_classificacao[df_classificacao['piloto'] == campeao_nome]
    dados_campeao = linha_campeao.iloc[0].to_dict() if not linha_campeao.empty else None

    return render_template('dashboard.html',
                         classificacao=classificacao,
                         construtores=construtores,
                         construtores_calculados=construtores_calculados,
                         analise_construtores=analise_construtores,
                         analise_pilotos=analise_pilotos,
                         campeao=campeao_nome,
                         dados_campeao=dados_campeao,
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