"""
Método híbrido para o MIS: heurística + Fix-and-Optimize + exato com warm start.

Fix-and-Optimize (nossa decisão de projeto):
  - Partimos de um conjunto independente S conhecido (vindo da heurística).
  - A cada rodada escolhemos um grupo D de vértices DA SOLUÇÃO para "soltar".
  - Ficam FIXADOS: os vértices de S fora de D (x_v = 1) e todo vértice que tem algum
    vizinho entre eles (x_v = 0, pois nunca poderia entrar mesmo).
  - Ficam LIVRES: os vértices de D e todos os vértices que SÓ eram bloqueados por D.
  - O CBC resolve, de forma exata, o MIS só nesse pedaço livre. Se ele achar mais de d
    vértices, a solução cresce. Como D já é uma resposta viável do pedaço, nunca piora.
  - Repetimos trocando o grupo D.

Por que soltar vértices DA SOLUÇÃO e não uma região qualquer do grafo?
  Na primeira versão liberávamos uma região do grafo (busca em largura). Não funcionou:
  quase todo vértice da região tinha algum vizinho fixado em 1 fora dela e ficava
  bloqueado, então o subproblema era vazio e nunca melhorava. Soltar vértices de S
  garante que o pedaço livre tenha espaço de verdade para reorganizar.

Como escolher D (testamos duas lógicas):
  - "vizinhanca": começa num vértice sorteado de S e depois sempre solta o vértice de S
    que libera MAIS vértices naquele momento. Na prática isso junta vértices de S que
    disputam os mesmos vizinhos: um vértice bloqueado por 3 membros de S só fica livre
    se os 3 saírem juntos, e é aí que mora a chance de trocar 3 por 4.
  - "aleatoria": solta vértices de S em ordem sorteada (linha de base para comparação).

Tamanho do pedaço livre: o que deixa o subproblema difícil para o CBC é o número de
variáveis livres, então controlamos isso direto (alvo). Começa em 40; se a rodada fechou
sem melhorar, cresce 10%; se o CBC não provou o ótimo do subproblema no tempo, encolhe 20%.
Se ficar 1/3 do seu orçamento sem melhorar, o F&O desiste e entrega o tempo ao exato.
(Primeiro tentamos "20 rodadas sem melhorar", mas isso era injusto com a lógica aleatória:
ela só começa a render quando o pedaço livre já cresceu, e era cortada antes disso.)
Se D virar a solução inteira, o subproblema é o problema todo: se o CBC fechar, temos o
ótimo global provado.
"""
import random
import time

from exato import resolver_exato
from heuristica import heuristica, lista_adjacencia


def soltar(S, V, adj, alvo, logica, rng):
    """
    Escolhe o grupo D (vértices de S que serão soltos) até o pedaço livre ter ~'alvo' vértices.
    Devolve (D, livres). Livre = D + vértices que só eram bloqueados por membros de D.
    """
    bloqueio = {v: len(adj[v] & S) for v in V if v not in S}  # quantos vizinhos em S
    D, livres = set(), set()
    candidatos = sorted(S)
    rng.shuffle(candidatos)
    while candidatos and len(livres) < alvo:
        if logica == "vizinhanca" and D:
            # solta quem libera mais vértices AGORA (vizinhos que só ele ainda bloqueia)
            ganho = {s: sum(1 for w in adj[s] if bloqueio.get(w) == 1) for s in candidatos}
            s = max(candidatos, key=ganho.get)
        else:  # "aleatoria" (e o 1º vértice da "vizinhanca"): ordem sorteada
            s = candidatos[-1]
        candidatos.remove(s)
        D.add(s)
        livres.add(s)
        for w in adj[s]:
            if w in bloqueio:
                bloqueio[w] -= 1
                if bloqueio[w] == 0:
                    livres.add(w)
    return D, livres


def fix_and_optimize(V, E, adj, S, limite_tempo, logica="vizinhanca", alvo0=40,
                     tempo_sub=3, tempo_sem_melhora=None, semente=0):
    """
    Melhora S por Fix-and-Optimize. Para quando o tempo acaba ou quando passa
    'tempo_sem_melhora' segundos sem melhorar (aí o tempo que sobra vai para o exato).
    Padrão: 1/3 de limite_tempo. Use float("inf") para nunca desistir.
    Devolve (S, provou_otimo, historico, rodadas).
    """
    inicio = time.perf_counter()
    rng = random.Random(semente)
    S = set(S)
    alvo = min(alvo0, len(V))
    historico = [(0.0, len(S))]
    rodadas = 0
    if tempo_sem_melhora is None:
        tempo_sem_melhora = limite_tempo / 3
    ultima_melhora = inicio

    while (time.perf_counter() - inicio < limite_tempo - 0.5
           and time.perf_counter() - ultima_melhora < tempo_sem_melhora):
        restante = limite_tempo - (time.perf_counter() - inicio)
        D, livres = soltar(S, V, adj, alvo, logica, rng)
        fixos_em_1 = S - D          # ficam x_v = 1; todo o resto fora de 'livres' fica x_v = 0
        livres = sorted(livres)
        livres_set = set(livres)
        E_sub = [(u, v) for u in livres for v in adj[u] if u < v and v in livres_set]

        sub = resolver_exato(livres, E_sub, min(tempo_sub, restante), solucao_inicial=D)
        rodadas += 1

        if sub["lb"] > len(D):  # achou um jeito de colocar mais vértices no pedaço livre
            S = fixos_em_1 | sub["conjunto"]
            historico.append((time.perf_counter() - inicio, len(S)))
            ultima_melhora = time.perf_counter()
            continue
        if sub["otimo"]:
            if D == S:  # soltamos a solução inteira e o CBC fechou: ótimo global provado
                return S, True, historico, rodadas
            S = fixos_em_1 | sub["conjunto"]  # empate: aceita a solução nova (diversifica)
            alvo = min(len(V), int(alvo * 1.1) + 1)
        if not sub["otimo"]:
            alvo = max(10, int(alvo * 0.8))
    return S, False, historico, rodadas


def hibrido(V, E, limite_tempo, logica="vizinhanca", semente=0,
            frac_heuristica=0.05, frac_fo=0.45):
    """
    Orçamento total = limite_tempo, dividido em 3 fases:
      1) heurística (warm start)               ~ 5% do tempo
      2) Fix-and-Optimize a partir dela        até 45% do tempo (para antes se estagnar)
      3) CBC no modelo completo, com a melhor solução como warm start, no tempo que sobrar
         (é ele que fornece o limitante superior e, se der, a prova de otimalidade).
    """
    inicio = time.perf_counter()
    adj = lista_adjacencia(V, E)

    S, _ = heuristica(V, E, frac_heuristica * limite_tempo, semente, adj)
    valor_heuristica = len(S)

    S, provou, hist_fo, rodadas = fix_and_optimize(
        V, E, adj, S, frac_fo * limite_tempo, logica=logica, semente=semente)
    valor_fo = len(S)

    if provou:
        res = dict(conjunto=S, lb=len(S), ub=len(S), gap=0.0, otimo=True)
    else:
        restante = limite_tempo - (time.perf_counter() - inicio)
        res = resolver_exato(V, E, restante, solucao_inicial=S)
        if res["lb"] < len(S):  # segurança: nunca devolver pior que o incumbente entregue
            res.update(conjunto=S, lb=len(S), gap=100 * (res["ub"] - len(S)) / len(S))
    res.update(tempo=time.perf_counter() - inicio, valor_heuristica=valor_heuristica,
               valor_fo=valor_fo, rodadas_fo=rodadas, hist_fo=hist_fo)
    return res


if __name__ == "__main__":
    import sys
    from gerador import ler_dimacs
    V, E = ler_dimacs(sys.argv[1])
    T = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    logica = sys.argv[3] if len(sys.argv) > 3 else "vizinhanca"
    r = hibrido(V, E, T, logica)
    print(f"Híbrido ({logica}): heurística={r['valor_heuristica']} -> F&O={r['valor_fo']} "
          f"({r['rodadas_fo']} rodadas) -> final LB={r['lb']} UB={r['ub']} "
          f"gap={r['gap']:.1f}% ótimo={r['otimo']} tempo={r['tempo']:.1f}s")
