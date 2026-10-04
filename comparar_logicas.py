"""
Comparação mais robusta das lógicas do Fix-and-Optimize (várias sementes).

Mesmo orçamento para todos (T segundos, padrão 30):
  - ILS pura durante T
  - ILS por 10% de T + F&O "vizinhanca" no resto
  - ILS por 10% de T + F&O "aleatoria" no resto
(aqui o F&O não desiste por estagnação: o objetivo é medir só a qualidade da busca)

Uso: python comparar_logicas.py [T]
Gera resultados/logicas.csv e resultados/grafico_logicas.png
"""
import csv
import statistics
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from gerador import FAMILIA, gerar
from graficos import CORES, TINTA_2
from heuristica import heuristica, lista_adjacencia
from hibrido import fix_and_optimize

TAMANHOS = [1000, 3000, 5000]
SEMENTES = [0, 1, 2]
METODOS = {"heuristica": "ILS pura", "hibrido_viz": "ILS + F&O vizinhança",
           "hibrido_ale": "ILS + F&O aleatória"}


def rodar(V, E, adj, T, metodo, semente):
    if metodo == "heuristica":
        S, _ = heuristica(V, E, T, semente, adj)
        return len(S)
    t0 = time.perf_counter()
    S, _ = heuristica(V, E, 0.1 * T, semente, adj)
    logica = "vizinhanca" if metodo == "hibrido_viz" else "aleatoria"
    S, _, _, _ = fix_and_optimize(V, E, adj, S, T - (time.perf_counter() - t0), logica=logica,
                                  tempo_sem_melhora=float("inf"), semente=semente)
    return len(S)


def main(T):
    linhas = []
    for n in TAMANHOS:
        _, p, semente_inst = next(f for f in FAMILIA if f[0] == n)
        V, E = gerar(n, p, semente_inst)
        adj = lista_adjacencia(V, E)
        for semente in SEMENTES:
            for metodo in METODOS:
                valor = rodar(V, E, adj, T, metodo, semente)
                linhas.append(dict(n=n, semente=semente, metodo=metodo, valor=valor))
                print(f"n={n} semente={semente} {metodo:12s} |S|={valor}", flush=True)

    with open("resultados/logicas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["n", "semente", "metodo", "valor"])
        w.writeheader()
        w.writerows(linhas)

    # Gráfico: para cada n, média de cada método em relação à média da ILS pura
    fig, ax = plt.subplots(figsize=(8, 4.6))
    largura = 0.8 / len(METODOS)
    for i, metodo in enumerate(METODOS):
        medias, mins, maxs = [], [], []
        for n in TAMANHOS:
            base = statistics.mean(l["valor"] for l in linhas if l["n"] == n and l["metodo"] == "heuristica")
            vals = [l["valor"] - base for l in linhas if l["n"] == n and l["metodo"] == metodo]
            medias.append(statistics.mean(vals)); mins.append(min(vals)); maxs.append(max(vals))
        xs = [x - 0.4 + largura * (i + 0.5) for x in range(len(TAMANHOS))]
        ax.bar(xs, medias, width=largura * 0.9, color=CORES[metodo], label=METODOS[metodo])
        ax.errorbar(xs, medias, yerr=[[m - a for m, a in zip(medias, mins)],
                                      [b - m for m, b in zip(medias, maxs)]],
                    fmt="none", ecolor=TINTA_2, capsize=3, lw=1)
    ax.axhline(0, color=TINTA_2, lw=1)
    ax.set_xticks(range(len(TAMANHOS)))
    ax.set_xticklabels([str(n) for n in TAMANHOS])
    ax.set_xlabel("Tamanho da instância (n vértices)")
    ax.set_ylabel("Vértices a mais que a ILS pura (média)")
    ax.set_title(f"Lógicas do F&O, {len(SEMENTES)} sementes, {T:.0f}s cada  (barra = mín–máx)",
                 loc="left")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig("resultados/grafico_logicas.png")
    print("Salvo em resultados/logicas.csv e resultados/grafico_logicas.png")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 30)
