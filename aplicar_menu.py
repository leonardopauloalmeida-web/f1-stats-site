#!/usr/bin/env python3
"""
Coloca o menu lateral (_menu.html) em TODAS as páginas da pasta templates
que ainda não têm.

Como usar (na pasta do projeto, a mesma onde está o app.py):
    python aplicar_menu.py

O que ele faz em cada página:
  1. Faz uma cópia de segurança na pasta "backup_templates".
  2. Apaga o cabeçalho antigo (<header>...</header>), se existir.
  3. Coloca {% include '_menu.html' %} logo depois de <body>.
  4. Avisa se sobrou algum menu antigo (<nav>) para você conferir.

Páginas que já têm o menu são puladas, então dá para rodar de novo sem medo.
"""
import os
import re
import shutil

PASTA = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(PASTA, "templates")
BACKUP = os.path.join(PASTA, "backup_templates")
INCLUDE = "{% include '_menu.html' %}"


def main():
    if not os.path.isdir(TEMPLATES):
        print("Não achei a pasta 'templates'. Rode este arquivo dentro da pasta do projeto.")
        return
    if not os.path.exists(os.path.join(TEMPLATES, "_menu.html")):
        print("Falta o arquivo templates/_menu.html. Copie ele para a pasta templates primeiro.")
        return

    os.makedirs(BACKUP, exist_ok=True)
    alteradas, puladas, conferir = [], [], []

    for nome in sorted(os.listdir(TEMPLATES)):
        if not nome.endswith(".html") or nome.startswith("_"):
            continue
        caminho = os.path.join(TEMPLATES, nome)
        with open(caminho, encoding="utf-8") as f:
            texto = f.read()

        if "_menu.html" in texto:
            puladas.append(nome)
            continue
        achou_body = re.search(r"<body[^>]*>", texto, flags=re.I)
        if not achou_body:
            conferir.append(f"{nome}: não tem a tag <body>, nada foi alterado")
            continue

        shutil.copy2(caminho, os.path.join(BACKUP, nome))

        # 1) apaga o cabeçalho antigo (<header ...> ... </header>)
        novo, n = re.subn(r"\s*<header\b[^>]*>.*?</header>\n?", "\n", texto, flags=re.S | re.I)

        # 2) coloca o menu logo depois de <body>
        novo = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + "\n    " + INCLUDE, novo, count=1, flags=re.I)

        with open(caminho, "w", encoding="utf-8") as f:
            f.write(novo)
        alteradas.append(nome + ("  (cabeçalho antigo removido)" if n else ""))

        # 3) sobrou algum menu antigo?
        if re.search(r"<nav\b", novo, flags=re.I):
            conferir.append(f"{nome}: ainda tem um <nav> antigo; abra a página e apague se aparecer dois menus")

    print("\nPáginas com o menu colocado agora:")
    for a in alteradas or ["(nenhuma)"]:
        print("  +", a)
    print("\nPáginas que já tinham o menu:")
    for p in puladas or ["(nenhuma)"]:
        print("  =", p)
    if conferir:
        print("\nConfira estas:")
        for c in conferir:
            print("  !", c)
    print(f"\nCópias de segurança em: {BACKUP}")
    print("Teste com 'python app.py' antes de enviar para o GitHub.")


if __name__ == "__main__":
    main()