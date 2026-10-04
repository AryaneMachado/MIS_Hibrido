"""
Curva de convergência (tamanho da melhor solução x tempo) na maior instância:
heurística pura vs. heurística + Fix-and-Optimize (as duas lógicas de escolha).
Mostra ONDE o tempo do híbrido rende mais que o da heurística.

Uso: python convergencia.py [n] [tempo]    (padrão: maior n da família, 30 s)
Gera resultados/grafico_convergencia.png
"""
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from gerador import FAMILIA, gerar
from graficos import CORES, ROTULOS, TINTA_2
from heuristica import heuristica, lista_adjacencia
from hibrido import fix_and_optimize


def degraus(hist, t_final):
    """Converte [(t, valor)] numa curva em degraus até t_final."""
    xs, ys = [], []
    for i, (t, v) in enumerate(hist):
        if i:
            xs.append(t); ys.append(hist[i - 1][1])
        xs.append(t); ys.append(v)
    xs.append(t_final); ys.append(hist[-1][1])
    return xs, ys


def main(n, T):
    _, p, semente = next(f for f in FAMILIA if f[0] == n)
    V, E = gerar(n, p, semente)
    adj = lista_adjacencia(V, E)
    curvas = {}

    _, curvas["heuristica"] = heuristica(V, E, T, 0, adj)

    T_heur = 0.05 * T / 0.5  # mesma proporção do híbrido: 5% heurística para 45% F&O
    for logica, chave in (("vizinhanca", "hibrido_viz"), ("aleatoria", "hibrido_ale")):
        t0 = time.perf_counter()
        S, hist_h = heuristica(V, E, T_heur, 0, adj)
        t_fo = time.perf_counter() - t0
        # aqui o F&O não desiste por estagnação: queremos ver a curva até o fim
        _, _, hist_fo, _ = fix_and_optimize(V, E, adj, S, T - t_fo, logica=logica,
                                            tempo_sem_melhora=float("inf"))
        curvas[chave] = hist_h + [(t_fo + t, v) for t, v in hist_fo]

    fig, ax = plt.subplots(figsize=(8, 4.6))
    for chave, hist in curvas.items():
        xs, ys = degraus(hist, T)
        rotulo = ROTULOS[chave] if chave == "heuristica" else "Heurística + " + ROTULOS[chave].split(" ", 1)[1]
        ax.plot(xs, ys, color=CORES[chave], lw=2, label=rotulo)
        ax.annotate(str(hist[-1][1]), (T, hist[-1][1]), xytext=(4, 0), textcoords="offset points",
                    va="center", color=TINTA_2, fontsize=9)
    ax.axvline(T_heur, color=TINTA_2, ls=":", lw=1)
    ax.text(T_heur, ax.get_ylim()[0], " início do F&O", color=TINTA_2, fontsize=9, va="bottom")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Tamanho da melhor solução |S|")
    ax.set_title(f"Convergência na instância n = {n}", loc="left")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig("resultados/grafico_convergencia.png")
    for chave, hist in curvas.items():
        print(f"{chave:12s} final = {hist[-1][1]}  (última melhoria em {hist[-1][0]:.1f}s)")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else FAMILIA[-1][0]
    T = float(sys.argv[2]) if len(sys.argv) > 2 else 30
    main(n, T)
