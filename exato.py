"""
Método exato para o MIS: o mesmo modelo PLI do TP-II, resolvido pelo CBC (via PuLP).

    max  sum_v x_v
    s.a. x_u + x_v <= 1     para toda aresta (u, v)
         x_v in {0, 1}

Opcionalmente recebe uma solução inicial (warm start): ela é entregue ao CBC como
incumbente logo na largada, ou seja, o solver já começa com um limite primal (LB).

ATENÇÃO (bug que encontramos): com "max" o CBC lê a solução inicial com o sinal trocado
(log: "MIPStart provided solution with cost 41" quando deveria ser -41) e logo a troca
por uma solução vazia de custo 0, que ele acha "melhor". O warm start era descartado
em silêncio. Por isso escrevemos o modelo como minimização equivalente:
    max  sum x_v   <=>   min  -sum x_v

Segundo bug (Windows): se os arquivos temporários do PuLP ficam numa pasta com caminho
absoluto, o CBC procura o arquivo da solução inicial em ".\\C:\\Users\\..." e não acha
(log: "opening mipstart file .\\C:\\..."). Por isso usamos uma pasta temporária RELATIVA.
"""
import math
import os
import re
import tempfile
import time

import pulp

PASTA_TMP = "tmp_cbc"  # relativa de propósito (ver aviso acima)


def construir_modelo(V, E, relaxado=False):
    modelo = pulp.LpProblem("MIS", pulp.LpMinimize)  # min -sum x  (ver aviso acima)
    categoria = pulp.LpContinuous if relaxado else pulp.LpBinary
    x = pulp.LpVariable.dicts("x", V, lowBound=0, upBound=1, cat=categoria)
    modelo += -pulp.lpSum(x[v] for v in V)
    for u, v in E:
        modelo += x[u] + x[v] <= 1
    return modelo, x


def ler_log(caminho_log):
    """Lê do log do CBC se o ótimo foi provado e o limitante superior (UB), se houver.
    Como o modelo é 'min -sum x', o 'Lower bound' do CBC vale -UB do MIS."""
    with open(caminho_log, errors="ignore") as f:
        texto = f.read()
    provou = "Result - Optimal solution found" in texto
    m = re.search(r"Lower bound:\s*([-\d.eE+]+)", texto)
    return provou, (-float(m.group(1)) if m else None)


def resolver_exato(V, E, limite_tempo, solucao_inicial=None):
    """
    Resolve o MIS com CBC em até 'limite_tempo' segundos.
    solucao_inicial: conjunto de vértices (warm start) ou None.
    Devolve dict com: conjunto, lb (melhor solução), ub (limitante), gap (%), otimo, tempo.
    """
    modelo, x = construir_modelo(V, E)
    if solucao_inicial is not None:
        for v in V:
            x[v].setInitialValue(1 if v in solucao_inicial else 0)

    fd, log = tempfile.mkstemp(suffix=".log")
    os.close(fd)
    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=max(1, limite_tempo),
                               warmStart=solucao_inicial is not None, logPath=log)
    os.makedirs(PASTA_TMP, exist_ok=True)
    solver.tmpDir = PASTA_TMP
    inicio = time.perf_counter()
    try:
        modelo.solve(solver)
        S = {v for v in V if x[v].value() is not None and x[v].value() > 0.5}
        provou, ub = ler_log(log)
    except pulp.PulpSolverError:  # CBC morreu (ex.: quase sem tempo): fica com o que já tinha
        S, provou, ub = set(solucao_inicial or ()), False, None
    tempo = time.perf_counter() - inicio
    os.remove(log)
    lb = len(S)
    if provou:
        ub = lb
    elif ub is None:  # parou antes de ter qualquer limitante: o único teto garantido é n
        ub = len(V)
    # alpha(G) é inteiro, então o teto real é floor(UB).
    ub = max(lb, math.floor(ub + 1e-6))
    gap = 100 * (ub - lb) / max(lb, 1)
    return dict(conjunto=S, lb=lb, ub=ub, gap=gap, otimo=(ub == lb), tempo=tempo)


if __name__ == "__main__":
    import sys
    from gerador import ler_dimacs
    V, E = ler_dimacs(sys.argv[1])
    T = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    r = resolver_exato(V, E, T)
    print(f"Exato: LB={r['lb']} UB={r['ub']} gap={r['gap']:.1f}% ótimo={r['otimo']} tempo={r['tempo']:.1f}s")
