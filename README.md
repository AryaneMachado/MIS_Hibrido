# MIS — TP-III: heurística + método exato (híbrido)

Continuação do TP-II (Conjunto Independente Máximo resolvido por PLI com PuLP + CBC).
Aqui combinamos uma heurística com o método exato e comparamos as três abordagens
(heurística pura, exato puro, híbrido) com o **mesmo orçamento de tempo** e o tamanho da instância crescendo.

Requisitos: `pip install -r requirements.txt` (o solver CBC já vem com o PuLP).

## Arquivos

| Arquivo | O que faz |
|---|---|
| `gerador.py` | Gerador de instâncias G(n, p) parametrizado por n, com semente documentada |
| `heuristica.py` | Heurística: guloso por menor grau + busca local "troca 1 por 2" + perturbação (ILS) |
| `exato.py` | O modelo PLI do TP-II resolvido pelo CBC, com warm start opcional |
| `hibrido.py` | Híbrido: heurística → **Fix-and-Optimize** → CBC com warm start |
| `experimento.py` | Roda todas as abordagens em todos os tamanhos e salva `resultados/resultados.csv` |
| `graficos.py` | Gera os gráficos e a `resultados/tabela.md` a partir do CSV |
| `comparar_logicas.py` | Compara as duas lógicas do F&O com 3 sementes |
| `convergencia.py` | Curva "melhor solução × tempo" na maior instância |

## Como reproduzir

```bash
python gerador.py              # gera as 6 instâncias em instancias/
python experimento.py 60       # ~35 min: 6 tamanhos x 5 abordagens x 60 s
python graficos.py 60
python comparar_logicas.py 30  # ~14 min
python convergencia.py 5000 30
```

## Instâncias

Grafos aleatórios G(n, p), o mesmo processo do TP-II. A diferença: em vez de p fixo, fixamos o
**grau médio = 6**, ou seja, p = 6 / (n − 1). Com o p = 0,10 do TP-II, um grafo de 1000 vértices teria
~100 vizinhos por vértice: denso demais, com conjunto independente minúsculo. Com grau médio fixo,
as instâncias crescem como redes reais, que são esparsas. A semente de cada instância é o próprio n.

| n | p | semente | arestas | comportamento do exato (60 s) |
|---|---|---|---|---|
| 50 | 0,122449 | 50 | 144 | resolve em 0,2 s |
| 200 | 0,030151 | 200 | 579 | resolve em 22,5 s |
| 300 | 0,020067 | 300 | 950 | não fecha (gap 11%) |
| 1000 | 0,006006 | 1000 | 2.979 | não fecha (gap 29%) |
| 3000 | 0,002001 | 3000 | 8.982 | não fecha (gap 36%) |
| 5000 | 0,001200 | 5000 | 15.045 | não fecha (gap 38%) |

Para gerar um grafo avulso: `python gerador.py <n> <p> <semente>`.

## As abordagens

**Heurística pura (ILS).** Guloso por menor grau (o vértice com menos vizinhos bloqueia menos gente)
→ busca local "troca 1 por 2" (tira 1 vértice e coloca 2 que só ele bloqueava) → perturbação (força
a entrada de 1 a 3 vértices aleatórios) e busca local de novo, repetindo até acabar o tempo.

**Exato puro.** O mesmo modelo do TP-II: `max Σ x_v` com `x_u + x_v ≤ 1` para cada aresta, no CBC.

**Warm start.** A heurística roda por 5% do tempo e a solução vai para o CBC como incumbente
(limite primal) logo na largada (`setInitialValue` + `warmStart=True`).

**Híbrido (Fix-and-Optimize).** Orçamento dividido em 3 fases:
1. Heurística por 5% do tempo (solução inicial).
2. Fix-and-Optimize por até 45% do tempo. A cada rodada:
   - escolhemos um grupo **D de vértices da solução** para "soltar";
   - ficam **fixados** os outros vértices da solução (x = 1) e todos os vizinhos deles (x = 0);
   - ficam **livres** os vértices de D e todo vértice que só era bloqueado por D;
   - o CBC resolve, de forma exata, só esse pedaço. Se couberem mais vértices do que |D|, a solução cresce.
     Como D já é viável no pedaço, nunca piora.
3. CBC no modelo completo com a melhor solução como warm start, no tempo que sobrar
   (é ele que dá o limitante superior e, se der, prova o ótimo).

### Decisões de projeto (o que testamos)

- **Primeira tentativa, que falhou: liberar uma região do grafo** (busca em largura a partir de um vértice).
  Quase todo vértice da região tinha um vizinho fixado em 1 fora dela e ficava bloqueado, então o
  subproblema não tinha para onde crescer. Zero melhorias. Por isso passamos a soltar **vértices da solução**.
- **Duas lógicas para escolher D:**
  - *vizinhança*: começa num vértice sorteado e depois solta sempre o vértice da solução que **libera mais
    vértices** naquele momento. Isso junta vértices que disputam os mesmos vizinhos: um vértice bloqueado
    por 3 membros da solução só fica livre se os 3 saírem juntos, e é aí que dá para trocar 3 por 4;
  - *aleatória*: solta vértices da solução em ordem sorteada (linha de base para comparar).
- **Tamanho do pedaço livre:** controlamos direto o número de variáveis livres (é isso que deixa o subproblema
  difícil). Começa em 40; se a rodada fechou sem melhorar, cresce 10%; se o CBC não fechou o subproblema em 3 s,
  encolhe 20%. Em n = 500 (p = 0,10) vimos que 66 livres resolvem em 0,6 s e 168 já não fecham em 10 s.
- **Parada por estagnação:** se o F&O passar 1/3 do seu orçamento sem melhorar, ele entrega o tempo ao exato.
  Primeiro tentamos "20 rodadas sem melhorar", mas isso cortava a lógica aleatória antes de ela começar a render.
- **Densidade:** testamos primeiro com p = 0,10 fixo, como no TP-II. Lá o F&O **nunca** melhorou a heurística:
  a solução da ILS já era ótima dentro de pedaços de até 100 variáveis livres (soltando 2/3 da solução!).
  Em grafos esparsos o F&O passou a encontrar melhorias, por isso a família final é esparsa.

### Dois bugs do CBC que achamos (e que anulavam o warm start sem avisar)

1. **Maximização + solução inicial:** o CBC lia a solução inicial com o sinal trocado
   (log: `MIPStart provided solution with cost 41`, que deveria ser −41) e a trocava logo por uma solução vazia de custo 0.
   Correção: escrever o modelo como `min −Σ x_v`, que é equivalente.
2. **Caminho no Windows:** com a pasta temporária absoluta, o CBC procurava o arquivo em `.\C:\Users\...` e não achava.
   Correção: pasta temporária relativa (`tmp_cbc/`).

Sem essas correções, o "warm start" parecia não fazer diferença porque, na verdade, nunca era usado.

## Resultados (T = 60 s por abordagem, 1 execução por tamanho)

LB = tamanho da solução encontrada, UB = limitante superior provado, gap = (UB − LB) / LB.

| n | Heurística | Exato | Exato + WS | Híbrido (vizinhança) | Híbrido (aleatória) |
|---|---|---|---|---|---|
| 50 | 20 | **20 ótimo** (0,2 s) | 20 ótimo (3,2 s) | 20 ótimo (3,5 s) | 20 ótimo (3,9 s) |
| 200 | 83 | **83 ótimo** (22,5 s) | 83 ótimo (26,5 s) | 83 ótimo (34,1 s) | 83 ótimo (34,4 s) |
| 300 | 118 | 116 / UB 129 | 118 / 129 | 118 / 129 | 118 / 129 |
| 1000 | **407** | 373 / 483 | 402 / 481 | 404 / 481 | 403 / 481 |
| 3000 | **1205** | 1084 / 1477 | 1167 / 1473 | **1205** / 1473 | 1176 / 1473 |
| 5000 | **2003** | 1799 / 2487 | 1965 / 2477 | 1990 / 2487 | 1995 / 2482 |

Quanto o F&O somou à solução da heurística curta (3 s), no experimento principal:

| n | vizinhança | aleatória |
|---|---|---|
| 1000 | 403 → 404 (+1) | 402 → 403 (+1) |
| 3000 | 1173 → 1205 (+32) | 1176 → 1176 (+0) |
| 5000 | 1965 → 1990 (+25) | 1965 → 1995 (+30) |

Gráficos em `resultados/`:
- `grafico_tempo.png`: tempo até provar o ótimo (marcador vazado = não fechou);
- `grafico_gap.png`: gap final;
- `grafico_qualidade.png`: quantos vértices cada abordagem ficou atrás da melhor;
- `grafico_logicas.png`: as duas lógicas do F&O com 3 sementes;
- `grafico_convergencia.png`: melhor solução × tempo em n = 5000.

## Respostas às perguntas

**1. A partir de que tamanho o exato deixa de fechar o gap em 60 s?**
Fecha n = 200 (22,5 s) e não fecha n = 300. Numa sonda extra, n = 250 também não fechou
(gap 103 / 112), então a fronteira fica entre **200 e 250 vértices**.

**2. O híbrido empurra esse limite? Em quanto?**
**Não.** O híbrido fecha os mesmos tamanhos (50 e 200) e em n = 200 é até mais lento (34 s contra 22,5 s),
porque gasta tempo melhorando uma solução que já era ótima. Em n = 300 em diante, todos param com o mesmo
UB (129, 481, 1473…). O ganho do híbrido é todo do **lado primal** (soluções melhores), não da prova.

**3. Existe um tamanho a partir do qual a heurística pura já é tão boa quanto o híbrido?**
Sim, e aqui isso acontece cedo. Até n = 300 todas as abordagens com heurística acham a mesma solução.
De n = 1000 em diante, a heurística pura com os 60 s inteiros **empata ou ganha** do híbrido
(407 × 404; 1205 × 1205; 2003 × 1995). O híbrido só dá ~30 s ao lado primal; a outra metade vai para um
CBC que não acha nada melhor. Em comparação justa só do lado primal (`comparar_logicas.py`, 30 s, 3 sementes),
o F&O fica no máximo +5 vértices à frente da ILS (≤ 0,4%), dentro da variação entre sementes.
Em relação ao **exato puro**, porém, combinar vale muito: em n = 5000 o CBC sozinho acha 1799 e
com warm start 1965.

**4. A estratégia acelerou o solver?**
**Para provar o ótimo, não.** Nem o warm start (n = 200: 26,5 s contra 22,5 s) nem o F&O. Na nossa opinião
o motivo é o mesmo do slide 7 do TP-II: a relaxação linear do MIS vale pelo menos n/2 (todo vértice = ½),
então o limitante superior é fraco. O CBC acha a solução ótima sozinho bem cedo; quase todo o tempo vai para
**provar** que não existe nada melhor. Dar a ele uma boa solução inicial não muda esse limitante.
**Para achar boas soluções, sim:** o F&O melhorou a heurística em +25 a +32 vértices nas instâncias grandes,
e a curva de convergência mostra que ele sobe mais rápido que a ILS. Mas a ILS, com tempo suficiente,
chega quase no mesmo lugar. Comparando as lógicas, a "vizinhança" foi a mais estável (ganhou em n = 3000 e não
perdeu da ILS em nenhum tamanho) e a "aleatória" oscilou mais (+0 em n = 3000 no experimento principal, mas a
melhor média em n = 5000). A explicação provável: em grafos grandes e esparsos existem pequenas melhorias
espalhadas por todo o grafo, e soltar vértices aleatórios ataca várias delas de uma vez.

## Limitações

- Uma instância por tamanho e uma execução por abordagem no experimento principal; a comparação das lógicas
  mostra que a variação entre sementes é da ordem das diferenças observadas.
- O CBC respeita o limite de tempo de forma aproximada (até ~71 s em n = 3000), porque só confere o relógio
  entre etapas.
- Resultados em uma máquina só, CBC padrão do PuLP.
