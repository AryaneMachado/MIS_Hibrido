"""
Heurística para o MIS: Guloso + Busca Local + Perturbação (Busca Local Iterada, ILS).

1) Guloso por menor grau: escolhe sempre o vértice com menos vizinhos restantes
   (ele "bloqueia" menos gente), coloca no conjunto e remove ele e seus vizinhos.
2) Busca local "troca 1 por 2": tira 1 vértice v do conjunto e coloca 2 vértices
   que só estavam bloqueados por v (e não são vizinhos entre si). O conjunto cresce 1.
3) Perturbação: força a entrada de alguns vértices aleatórios (expulsando os vizinhos)
   e roda a busca local de novo. Isso tira a solução de um ótimo local.
Repete (3) até acabar o tempo e devolve o melhor conjunto encontrado.
"""
import heapq
import random
import time


def lista_adjacencia(V, E):
    adj = {v: set() for v in V}
    for u, v in E:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def guloso_menor_grau(V, adj, rng):
    """Conjunto independente maximal escolhendo sempre o vértice de menor grau restante."""
    restantes = set(V)
    grau = {v: len(adj[v]) for v in V}
    # fila de prioridade (grau, desempate aleatório, vértice); entradas velhas são ignoradas
    fila = [(grau[v], rng.random(), v) for v in V]
    heapq.heapify(fila)
    S = set()
    while fila:
        g, _, v = heapq.heappop(fila)
        if v not in restantes or g != grau[v]:
            continue
        S.add(v)
        removidos = (adj[v] & restantes) | {v}
        restantes -= removidos
        for r in removidos:  # atualiza o grau de quem perdeu vizinhos
            for w in adj[r] & restantes:
                grau[w] -= 1
                heapq.heappush(fila, (grau[w], rng.random(), w))
    return S


def busca_local(S, V, adj):
    """Aplica trocas (1 sai, 2 entram) e inserções livres até não melhorar mais."""
    S = set(S)
    # bloqueio[u] = quantos vizinhos de u estão no conjunto
    bloqueio = {u: len(adj[u] & S) for u in V}

    def inserir(u):
        S.add(u)
        for w in adj[u]:
            bloqueio[w] += 1

    def remover(u):
        S.discard(u)
        for w in adj[u]:
            bloqueio[w] -= 1

    melhorou = True
    while melhorou:
        melhorou = False
        # inserção livre: vértice fora do conjunto sem nenhum vizinho dentro
        for u in V:
            if u not in S and bloqueio[u] == 0:
                inserir(u)
        # troca 1 por 2
        for v in list(S):
            candidatos = [u for u in adj[v] if bloqueio[u] == 1]  # só v bloqueia u
            achou = None
            for i in range(len(candidatos)):
                for j in range(i + 1, len(candidatos)):
                    if candidatos[j] not in adj[candidatos[i]]:
                        achou = (candidatos[i], candidatos[j])
                        break
                if achou:
                    break
            if achou:
                remover(v)
                inserir(achou[0])
                inserir(achou[1])
                melhorou = True
                break
    return S


def perturbar(S, adj, rng, forca):
    """Força 'forca' vértices de fora a entrar, expulsando os vizinhos deles."""
    S = set(S)
    fora = [v for v in adj if v not in S]
    for v in rng.sample(fora, min(forca, len(fora))):
        S -= adj[v]
        S.add(v)
    return S


def heuristica(V, E, limite_tempo, semente=0, adj=None):
    """ILS com tempo limite. Devolve (melhor conjunto, histórico [(tempo, valor)])."""
    inicio = time.perf_counter()
    rng = random.Random(semente)
    adj = adj or lista_adjacencia(V, E)

    atual = busca_local(guloso_menor_grau(V, adj, rng), V, adj)
    melhor = set(atual)
    historico = [(time.perf_counter() - inicio, len(melhor))]

    while time.perf_counter() - inicio < limite_tempo:
        forca = rng.choice([1, 1, 2, 3])  # perturbação quase sempre pequena
        candidato = busca_local(perturbar(atual, adj, rng, forca), V, adj)
        if len(candidato) >= len(atual):  # aceita empates para "andar" no platô
            atual = candidato
        elif rng.random() < 0.02:  # de vez em quando aceita piora (diversifica)
            atual = candidato
        if len(atual) > len(melhor):
            melhor = set(atual)
            historico.append((time.perf_counter() - inicio, len(melhor)))
    return melhor, historico


def eh_independente(S, E):
    return all(not (u in S and v in S) for u, v in E)


if __name__ == "__main__":
    import sys
    from gerador import ler_dimacs
    V, E = ler_dimacs(sys.argv[1])
    T = float(sys.argv[2]) if len(sys.argv) > 2 else 10
    S, hist = heuristica(V, E, T)
    print(f"Heurística: |S| = {len(S)}  válido = {eh_independente(S, E)}  melhorias = {hist}")
