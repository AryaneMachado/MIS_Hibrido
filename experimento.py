"""
Experimento comparativo: para cada tamanho N, roda todas as abordagens com o MESMO
orçamento de tempo e salva tudo em resultados/resultados.csv.

Abordagens:
  heuristica      -> só a ILS, durante todo o tempo
  exato           -> só o CBC, sem ajuda
  exato_ws        -> ILS rápida (5% do tempo) + CBC com warm start no resto
  hibrido_viz     -> ILS + Fix-and-Optimize (região = vizinhança BFS) + CBC com warm start
  hibrido_ale     -> idem, mas região livre sorteada ao acaso (para comparar a lógica)

Uso: python experimento.py [tempo_limite_em_segundos]   (padrão: 60)
"""
import csv
import os
import sys
import time

from exato import resolver_exato
from gerador import FAMILIA, gerar, nome_instancia, salvar_dimacs
from heuristica import eh_independente, heuristica, lista_adjacencia
from hibrido import hibrido

SEMENTE_ALGORITMOS = 0  # semente da parte aleatória da heurística / F&O


def rodar_heuristica(V, E, T):
    t = time.perf_counter()
    S, hist = heuristica(V, E, T, SEMENTE_ALGORITMOS)
    return dict(conjunto=S, lb=len(S), ub=None, otimo=False, tempo=time.perf_counter() - t,
                tempo_melhor=hist[-1][0])


def rodar_exato_ws(V, E, T):
    t = time.perf_counter()
    S, _ = heuristica(V, E, 0.05 * T, SEMENTE_ALGORITMOS)
    r = resolver_exato(V, E, T - (time.perf_counter() - t), solucao_inicial=S)
    r.update(tempo=time.perf_counter() - t, valor_heuristica=len(S))
    return r


ABORDAGENS = {
    "heuristica": rodar_heuristica,
    "exato": lambda V, E, T: resolver_exato(V, E, T),
    "exato_ws": rodar_exato_ws,
    "hibrido_viz": lambda V, E, T: hibrido(V, E, T, "vizinhanca", SEMENTE_ALGORITMOS),
    "hibrido_ale": lambda V, E, T: hibrido(V, E, T, "aleatoria", SEMENTE_ALGORITMOS),
}


def main(T):
    os.makedirs("instancias", exist_ok=True)
    os.makedirs("resultados", exist_ok=True)
    linhas = []
    for n, p, semente in FAMILIA:
        V, E = gerar(n, p, semente)
        salvar_dimacs(V, E, nome_instancia(n, p, semente), f"G(n={n}, p={p}), semente={semente}")
        print(f"\n=== n={n}  p={p}  semente={semente}  arestas={len(E)}  (T={T}s) ===")
        for nome, rodar in ABORDAGENS.items():
            r = rodar(V, E, T)
            assert eh_independente(r["conjunto"], E), f"{nome} devolveu solução inválida!"
            linhas.append(dict(n=n, p=p, semente=semente, arestas=len(E), abordagem=nome,
                               lb=r["lb"], ub=r["ub"], otimo=r["otimo"],
                               tempo=round(r["tempo"], 2),
                               tempo_melhor=round(r.get("tempo_melhor", r["tempo"]), 2),
                               valor_heuristica=r.get("valor_heuristica", ""),
                               valor_fo=r.get("valor_fo", ""),
                               rodadas_fo=r.get("rodadas_fo", "")))
            ub = "-" if r["ub"] is None else r["ub"]
            print(f"  {nome:12s} LB={r['lb']:4d}  UB={ub!s:>4}  ótimo={str(r['otimo']):5s}  "
                  f"tempo={r['tempo']:6.1f}s")

    # Melhor limitante conhecido de cada instância (menor UB entre os métodos com bound)
    # e gap de cada abordagem em relação a ele. Assim a heurística também ganha um "gap".
    for linha in linhas:
        ubs = [l["ub"] for l in linhas if l["n"] == linha["n"] and l["ub"] is not None]
        lbs = [l["lb"] for l in linhas if l["n"] == linha["n"]]
        linha["melhor_ub"] = min(ubs)
        linha["melhor_lb"] = max(lbs)
        linha["gap_proprio"] = "" if linha["ub"] is None else \
            round(100 * (linha["ub"] - linha["lb"]) / linha["lb"], 2)
        linha["gap_melhor_ub"] = round(100 * (linha["melhor_ub"] - linha["lb"]) / linha["lb"], 2)

    with open("resultados/resultados.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    print("\nSalvo em resultados/resultados.csv")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 60)
