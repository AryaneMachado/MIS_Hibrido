"""
Gera os gráficos comparativos a partir de resultados/resultados.csv.

  resultados/grafico_tempo.png     tempo até provar o ótimo (ou bater no limite)
  resultados/grafico_gap.png       gap final de cada método com limitante
  resultados/grafico_qualidade.png quantos vértices cada abordagem ficou atrás da melhor
  resultados/tabela.md             tabela com todos os números
"""
import csv
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from gerador import GRAU_MEDIO

ROTULOS = {
    "heuristica": "Heurística pura (ILS)",
    "exato": "Exato puro (CBC)",
    "exato_ws": "Exato + warm start",
    "hibrido_viz": "Híbrido F&O (vizinhança)",
    "hibrido_ale": "Híbrido F&O (aleatória)",
}
CORES = {"heuristica": "#2a78d6", "exato": "#eb6834", "exato_ws": "#1baf7a",
         "hibrido_viz": "#eda100", "hibrido_ale": "#e87ba4"}
MARCADORES = {"heuristica": "o", "exato": "s", "exato_ws": "^",
              "hibrido_viz": "D", "hibrido_ale": "v"}
TINTA, TINTA_2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRADE, "axes.labelcolor": TINTA_2,
    "xtick.color": TINTA_2, "ytick.color": TINTA_2, "axes.titlecolor": TINTA,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.8,
    "legend.frameon": False, "figure.dpi": 130,
})


def carregar(caminho="resultados/resultados.csv"):
    with open(caminho, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for l in linhas:
        for c in ("n", "lb", "melhor_lb", "melhor_ub"):
            l[c] = int(l[c])
        l["ub"] = int(l["ub"]) if l["ub"] else None
        l["tempo"] = float(l["tempo"])
        l["otimo"] = l["otimo"] == "True"
        l["gap_proprio"] = float(l["gap_proprio"]) if l["gap_proprio"] else None
    return linhas


def serie(linhas, abordagem, campo):
    ls = sorted((l for l in linhas if l["abordagem"] == abordagem), key=lambda l: l["n"])
    return [l["n"] for l in ls], [l[campo] for l in ls], [l["otimo"] for l in ls]


def eixo_n(ax, ns):
    ax.set_xticks(range(len(ns)))
    ax.set_xticklabels([str(n) for n in ns])
    ax.set_xlabel(f"Tamanho da instância (n vértices, grau médio {GRAU_MEDIO})")


def grafico_tempo(linhas, T, ns):
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for ab in ("exato", "exato_ws", "hibrido_viz", "hibrido_ale"):
        _, tempos, otimos = serie(linhas, ab, "tempo")
        xs = range(len(tempos))
        ax.plot(xs, tempos, color=CORES[ab], lw=2, label=ROTULOS[ab], zorder=2)
        for x, t, o in zip(xs, tempos, otimos):  # marcador cheio = provou; vazado = não provou
            ax.plot(x, t, MARCADORES[ab], ms=8, color=CORES[ab],
                    mfc=CORES[ab] if o else "white", mew=2, zorder=3)
    ax.axhline(T, color=TINTA_2, ls="--", lw=1)
    ax.text(-0.1, T + 1, f"limite de tempo ({T:.0f}s)", color=TINTA_2,
            ha="left", va="bottom", fontsize=9)
    eixo_n(ax, ns)
    ax.set_ylabel("Tempo (s)")
    ax.set_title("Tempo para provar o ótimo  (marcador vazado = não fechou o gap)", loc="left")
    ax.set_ylim(0, T * 1.2)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig("resultados/grafico_tempo.png")


def grafico_gap(linhas, ns):
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for ab in ("exato", "exato_ws", "hibrido_viz", "hibrido_ale"):
        _, gaps, _ = serie(linhas, ab, "gap_proprio")
        ax.plot(range(len(gaps)), gaps, color=CORES[ab], lw=2, marker=MARCADORES[ab],
                ms=8, label=ROTULOS[ab])
    eixo_n(ax, ns)
    ax.set_ylabel("Gap final (%)  =  (UB − LB) / LB")
    ax.set_title("Gap ao fim do orçamento de tempo", loc="left")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig("resultados/grafico_gap.png")


def grafico_qualidade(linhas, ns):
    abordagens = list(ROTULOS)
    largura = 0.8 / len(abordagens)
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for i, ab in enumerate(abordagens):
        _, lbs, _ = serie(linhas, ab, "lb")
        _, melhores, _ = serie(linhas, ab, "melhor_lb")
        atraso = [m - lb for m, lb in zip(melhores, lbs)]
        xs = [x - 0.4 + largura * (i + 0.5) for x in range(len(ns))]
        ax.bar(xs, atraso, width=largura * 0.9, color=CORES[ab], label=ROTULOS[ab])
        for x, a in zip(xs, atraso):
            if a == 0:  # zero não aparece como barra: marca um ponto na base
                ax.plot(x, 0, MARCADORES[ab], ms=5, color=CORES[ab])
    eixo_n(ax, ns)
    ax.set_ylabel("Vértices a menos que a melhor solução")
    ax.set_title("Qualidade da solução (0 = empatou com a melhor encontrada)", loc="left")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig("resultados/grafico_qualidade.png")


def tabela(linhas, ns):
    with open("resultados/tabela.md", "w", encoding="utf-8") as f:
        f.write("| n | arestas | semente | abordagem | LB (solução) | UB (limitante) | gap (%) | ótimo? | tempo (s) |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for n in ns:
            for ab in ROTULOS:
                l = next(l for l in linhas if l["n"] == n and l["abordagem"] == ab)
                ub = "—" if l["ub"] is None else l["ub"]
                gap = "—" if l["gap_proprio"] is None else f"{l['gap_proprio']:.1f}"
                f.write(f"| {n} | {l['arestas']} | {l['semente']} | {ROTULOS[ab]} | {l['lb']} | "
                        f"{ub} | {gap} | {'sim' if l['otimo'] else 'não'} | {l['tempo']:.1f} |\n")


if __name__ == "__main__":
    T = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    linhas = carregar()
    ns = sorted({l["n"] for l in linhas})
    grafico_tempo(linhas, T, ns)
    grafico_gap(linhas, ns)
    grafico_qualidade(linhas, ns)
    tabela(linhas, ns)
    print("Gráficos e tabela salvos em resultados/")
