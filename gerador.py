"""
Gerador de instâncias do MIS: grafos aleatórios Erdős–Rényi G(n, p).

Cada par de vértices {i, j} vira aresta com probabilidade p.
A semente fixa garante que qualquer pessoa gere exatamente o mesmo grafo.

Parâmetros da família: n e o GRAU MÉDIO desejado. Usamos p = grau_medio / (n - 1),
assim todo grafo tem, em média, o mesmo número de vizinhos por vértice.
(No TP-II usamos p fixo = 0,10. Com p fixo, n = 1000 já dá ~100 vizinhos por vértice:
o grafo fica muito denso e o conjunto independente minúsculo. Com grau médio fixo as
instâncias crescem como redes reais, que são esparsas.)

Uso:
    python gerador.py              -> gera a família inteira em instancias/
    python gerador.py 120 0.1 7    -> gera um grafo avulso (n, p, semente)
"""
import os
import random
import sys

GRAU_MEDIO = 6
TAMANHOS = [50, 200, 300, 1000, 3000, 5000]
# (n, p, semente) — a semente de cada instância é o próprio n
FAMILIA = [(n, GRAU_MEDIO / (n - 1), n) for n in TAMANHOS]


def gerar(n, p, semente):
    """
    Devolve (V, E) de um G(n, p). Vértices numerados de 1 a n.
    Sorteia um número para cada par (i, j), em ordem — mesmo processo do TP-II.
    """
    rng = random.Random(semente)
    E = [(i, j) for i in range(1, n + 1) for j in range(i + 1, n + 1) if rng.random() < p]
    return list(range(1, n + 1)), E


def salvar_dimacs(V, E, caminho, comentario=""):
    with open(caminho, "w") as f:
        f.write(f"c {comentario}\n")
        f.write(f"p edge {len(V)} {len(E)}\n")
        for u, v in E:
            f.write(f"e {u} {v}\n")


def ler_dimacs(caminho):
    """Lê um grafo no formato DIMACS: 'p edge n m' e linhas 'e u v'."""
    n, E = 0, []
    with open(caminho) as f:
        for linha in f:
            partes = linha.split()
            if not partes or partes[0] == "c":
                continue
            if partes[0] == "p":
                n = int(partes[2])
            elif partes[0] == "e":
                E.append((int(partes[1]), int(partes[2])))
    return list(range(1, n + 1)), E


def nome_instancia(n, p, semente):
    return f"instancias/gnp_n{n}_p{p:.6f}_s{semente}.txt"


def gerar_familia():
    os.makedirs("instancias", exist_ok=True)
    caminhos = []
    for n, p, semente in FAMILIA:
        V, E = gerar(n, p, semente)
        caminho = nome_instancia(n, p, semente)
        salvar_dimacs(V, E, caminho, f"G(n={n}, p={p:.6f}), semente={semente}")
        print(f"{caminho}: n={n}, p={p:.6f}, semente={semente}, arestas={len(E)}, "
              f"grau médio real={2 * len(E) / n:.2f}")
        caminhos.append(caminho)
    return caminhos


if __name__ == "__main__":
    if len(sys.argv) == 4:
        n, p, s = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
        V, E = gerar(n, p, s)
        os.makedirs("instancias", exist_ok=True)
        salvar_dimacs(V, E, nome_instancia(n, p, s), f"G(n={n}, p={p}), semente={s}")
        print(f"{nome_instancia(n, p, s)}: {len(E)} arestas")
    else:
        gerar_familia()
