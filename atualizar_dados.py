#!/usr/bin/env python3
"""
Atualiza os CSVs da temporada de Fórmula 1 direto da API Jolpica-F1
(sucessora da Ergast), sem precisar digitar nada à mão.

O que ele atualiza:
  - temporada_2026.csv   -> classificação de pilotos (pontos, vitórias, pódios)
  - construtores_2026.csv -> classificação de construtores
  - corridas_2026.csv    -> vencedor e equipe de cada corrida já realizada

Como usar (na pasta do projeto):
    python atualizar_dados.py

Depois, para publicar:
    git add .
    git commit -m "Atualiza resultados"
    git push
"""
import csv
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta

TEMPORADA = 2026
BASE_API = "https://api.jolpi.ca/ergast/f1"
PASTA = os.path.dirname(os.path.abspath(__file__))
AVISOS = []


# ---------------------------------------------------------------
# Comunicação com a API
# ---------------------------------------------------------------
def pegar(caminho):
    """Faz uma consulta à API. Se ela pedir para esperar (erro 429), tenta de novo."""
    url = f"{BASE_API}/{caminho}"
    for tentativa in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "f1-stats-site"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)["MRData"]
        except urllib.error.HTTPError as erro:
            if erro.code == 429:
                espera = 5 * (tentativa + 1)
                print(f"  A API pediu para esperar. Tentando de novo em {espera}s...")
                time.sleep(espera)
                continue
            raise
        except urllib.error.URLError as erro:
            print(f"Sem conexão com a API: {erro}")
            sys.exit(1)
    raise RuntimeError(f"A API não respondeu: {url}")


# ---------------------------------------------------------------
# Nomes: faz o nome da API combinar com o nome que já está nos seus CSVs
# ---------------------------------------------------------------
def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def escolher_nome(nome_api, existentes, tipo):
    """existentes: dict {nome normalizado: nome como está no seu CSV}"""
    chave = normalizar(nome_api)
    if chave in existentes:
        return existentes[chave]
    # procura nomes parecidos (ex.: "Haas F1 Team" ~ "Haas"), do maior para o menor
    for k in sorted(existentes, key=len, reverse=True):
        if k and (k in chave or chave in k):
            return existentes[k]
    AVISOS.append(f"{tipo} '{nome_api}' não existe nos seus CSVs; usei o nome da API.")
    return nome_api


def nome_piloto(driver):
    return f"{driver['givenName']} {driver['familyName']}"


# ---------------------------------------------------------------
# Leitura e escrita de CSV
# ---------------------------------------------------------------
def ler_csv(nome):
    caminho = os.path.join(PASTA, nome)
    if not os.path.exists(caminho):
        return [], []
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        leitor = csv.DictReader(f)
        return list(leitor), leitor.fieldnames or []


def escrever_csv(nome, linhas, colunas):
    caminho = os.path.join(PASTA, nome)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(linhas)


def ler_data(texto):
    texto = (texto or "").strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto[:10], formato).date()
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------
def main():
    print(f"Buscando dados da temporada {TEMPORADA} na API Jolpica...")

    # 1) Classificações
    listas = pegar(f"{TEMPORADA}/driverstandings/?limit=100")["StandingsTable"]["StandingsLists"]
    if not listas:
        print("A API ainda não tem a classificação desta temporada. Nada foi alterado.")
        return
    pilotos_api = listas[0]["DriverStandings"]
    equipes_api = pegar(f"{TEMPORADA}/constructorstandings/?limit=100")["StandingsTable"]["StandingsLists"][0]["ConstructorStandings"]

    # 2) Resultados do pódio (1º, 2º e 3º de cada corrida) para contar pódios
    podios_piloto, podios_equipe, vencedores = {}, {}, {}
    for pos in (1, 2, 3):
        corridas = pegar(f"{TEMPORADA}/results/{pos}/?limit=100")["RaceTable"]["Races"]
        for corrida in corridas:
            r = corrida["Results"][0]
            piloto = nome_piloto(r["Driver"])
            equipe = r["Constructor"]["name"]
            podios_piloto[piloto] = podios_piloto.get(piloto, 0) + 1
            podios_equipe[equipe] = podios_equipe.get(equipe, 0) + 1
            if pos == 1:
                vencedores[corrida["date"]] = (piloto, equipe, corrida["raceName"])
        time.sleep(0.5)  # respeita o limite da API

    # Nomes que já existem nos seus CSVs
    antigos, _ = ler_csv("temporada_2026.csv")
    nomes_pilotos = {normalizar(l["piloto"]): l["piloto"] for l in antigos if l.get("piloto")}
    nomes_equipes = {normalizar(l["equipe"]): l["equipe"] for l in antigos if l.get("equipe")}

    # 3) Monta temporada_2026.csv
    linhas = []
    for item in pilotos_api:
        piloto_api = nome_piloto(item["Driver"])
        equipe_api = item["Constructors"][-1]["name"]  # equipe mais recente
        linhas.append({
            "piloto": escolher_nome(piloto_api, nomes_pilotos, "Piloto"),
            "equipe": escolher_nome(equipe_api, nomes_equipes, "Equipe"),
            "pontos": int(float(item["points"])),
            "vitorias": int(item["wins"]),
            "podios": podios_piloto.get(piloto_api, 0),
        })
    linhas.sort(key=lambda l: (l["pontos"], l["vitorias"], l["podios"]), reverse=True)
    for i, l in enumerate(linhas, start=1):
        l["posicao"] = i
    escrever_csv("temporada_2026.csv", linhas, ["posicao", "piloto", "equipe", "pontos", "vitorias", "podios"])
    print(f"  temporada_2026.csv: {len(linhas)} pilotos")

    # 4) Monta construtores_2026.csv
    nomes_equipes_final = {normalizar(l["equipe"]): l["equipe"] for l in linhas}
    construtores = []
    for item in equipes_api:
        nome_api = item["Constructor"]["name"]
        construtores.append({
            "equipe": escolher_nome(nome_api, nomes_equipes_final, "Construtor"),
            "pontos": int(float(item["points"])),
            "vitorias": int(item["wins"]),
            "podios": podios_equipe.get(nome_api, 0),
        })
    construtores.sort(key=lambda l: (l["pontos"], l["vitorias"], l["podios"]), reverse=True)
    for i, l in enumerate(construtores, start=1):
        l["posicao"] = i
    escrever_csv("construtores_2026.csv", construtores, ["posicao", "equipe", "pontos", "vitorias", "podios"])
    print(f"  construtores_2026.csv: {len(construtores)} equipes")

    # 5) Atualiza corridas_2026.csv (vencedor e equipe das corridas já realizadas)
    corridas_csv, colunas = ler_csv("corridas_2026.csv")
    if corridas_csv:
        for c in ("data", "gp", "vencedor", "equipe"):
            if c not in colunas:
                colunas.append(c)
        usa_barra = "/" in (corridas_csv[0].get("data") or "")
        calendario = pegar(f"{TEMPORADA}/races/?limit=100")["RaceTable"]["Races"]
        datas_existentes = [ler_data(l.get("data")) for l in corridas_csv]

        atualizadas = 0
        for linha, data_linha in zip(corridas_csv, datas_existentes):
            if not data_linha:
                continue
            for data_api, (piloto, equipe, _) in vencedores.items():
                d_api = ler_data(data_api)
                if d_api and abs((d_api - data_linha).days) <= 1:
                    linha["vencedor"] = escolher_nome(piloto, nomes_pilotos, "Piloto")
                    linha["equipe"] = escolher_nome(equipe, nomes_equipes_final, "Equipe")
                    atualizadas += 1
                    break

        # corridas do calendário que ainda não estão no seu CSV
        novas = 0
        for corrida in calendario:
            d_api = ler_data(corrida["date"])
            if any(d and abs((d - d_api).days) <= 1 for d in datas_existentes):
                continue
            nova = {c: "" for c in colunas}
            nova["data"] = d_api.strftime("%d/%m/%Y" if usa_barra else "%Y-%m-%d")
            nova["gp"] = corrida["raceName"]
            if corrida["date"] in vencedores:
                nova["vencedor"] = escolher_nome(vencedores[corrida["date"]][0], nomes_pilotos, "Piloto")
                nova["equipe"] = escolher_nome(vencedores[corrida["date"]][1], nomes_equipes_final, "Equipe")
            corridas_csv.append(nova)
            novas += 1

        escrever_csv("corridas_2026.csv", corridas_csv, colunas)
        print(f"  corridas_2026.csv: {atualizadas} corridas com vencedor atualizado, {novas} corridas novas")
    else:
        print("  corridas_2026.csv não encontrado; pulei essa parte.")

    if AVISOS:
        print("\nAtenção (confira estes nomes nos seus CSVs):")
        for aviso in sorted(set(AVISOS)):
            print("  -", aviso)

    print("\nPronto! Agora é só enviar para o GitHub:")
    print("  git add .")
    print('  git commit -m "Atualiza resultados"')
    print("  git push")


if __name__ == "__main__":
    main()