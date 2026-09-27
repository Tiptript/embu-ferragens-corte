# Arquitetura — dois Repls

```
NAVEGADOR
   │
   ▼
┌─────────────────────────────┐        ┌──────────────────────────┐
│  REPL 1 — app (Node/React)  │  HTTP  │  REPL 2 — motor (Python) │
│                             │───────▶│                          │
│  • tela, formulário, SVG    │  POST  │  • OR-Tools / CP-SAT     │
│  • dedução de fita          │ /otim. │  • resolve o corte       │
│  • conversão mm/cm/dm       │◀───────│  • retalhos + cortes     │
│  • preços e custo           │  JSON  │  • validação             │
│  • agrupa por material      │        │                          │
└─────────────────────────────┘        └──────────────────────────┘
        MOTOR_URL (secret)                  sem tela, sem banco
```

O Repl 2 é sem estado: recebe peças, devolve coordenadas. Não guarda nada,
não tem banco, não tem login de usuário. Reiniciar não perde nada.

---

## REPL 1 — app (o que você já tem)

**Continua igual:**

| Arquivo | Papel |
|---|---|
| `pieceTransformer.ts` | deduz espessura da fita das bordas marcadas |
| `costCalculator.ts` | custo de chapa, fita, corte, filetamento |
| `configStore.ts` | preços, kerf, refilo, retalho mínimo (config.json) |
| `optimizerService.ts` | orquestra: converte unidade, agrupa por material, chama o motor |
| `client/` | formulário, três vistas do SVG, importação por foto |

**Muda:**
- ganha `src/engine/motorClient.ts` (cliente HTTP do Repl 2)
- perde `nestingEngine.ts` inteiro e a dependência `guillotine-packer`
- `optimizerService.ts` chama `empacotarViaMotor()` em vez de `empacotarMaterial()`

**Secret novo:** `MOTOR_URL` = URL pública do Repl 2 (sem barra final).
Opcional: `MOTOR_API_TOKEN`, se você proteger o motor.

**Limitação conhecida (não resolvida):** `config.json` mora no filesystem
do Repl. Em deploy Autoscale ele se perde. Para produção de verdade,
migrar preços para um banco. Enquanto for uso interno da loja, funciona.

---

## REPL 2 — motor (novo)

| Arquivo | Papel |
|---|---|
| `main.py` | FastAPI, endpoint `POST /otimizar`, validação de entrada |
| `solver2stage.py` | modelo CP-SAT — as restrições do problema |
| `geometria.py` | retalhos maximais, área de união, sequência de cortes, validação |
| `.replit` / `replit.nix` | configuração de execução |
| `requirements.txt` | ortools, fastapi, uvicorn, pydantic |
| `teste_e2e.py` | testes de aceitação (`python3 teste_e2e.py`) |
| `Dockerfile` | só se um dia migrar para Cloud Run — não usado no Replit |

### O que o modelo faz

Corte guilhotinado de **2 estágios**:
- estágio 1: cortes horizontais que atravessam a chapa inteira → faixas
- estágio 2: cortes verticais dentro de cada faixa → peças

Altura da faixa = altura da peça mais alta dentro dela.

**Objetivo:** minimizar `Σ (k+1) × altura_usada[k]`. O peso crescente por
índice de chapa empurra material para as primeiras e deixa a última o mais
vazia possível — é o que consolida a sobra num bloco único.

Nenhuma linha do código diz "coloque a peça X na posição Y". O código
declara as restrições; quem encontra as posições é o CP-SAT.

### Contrato

`POST /otimizar`
```json
{
  "chapa": { "largura": 2750, "altura": 1850, "refiloMm": 10 },
  "kerfMm": 4,
  "retalhoMinimoMm": 125,
  "permiteRotacao": true,
  "tempoLimiteS": 5,
  "pecas": [{ "id": "P7", "instanceId": "P7__1", "largura": 500, "altura": 635 }]
}
```

- `pecas` já chega com a fita deduzida — isso continua no Repl 1
- **não** somar kerf antes de enviar; o motor aplica internamente
- `instanceId` precisa ser único por unidade física (o motor rejeita duplicado)
- `permiteRotacao: false` quando o material tem veio

Resposta: `ChapaResultado[]` + `validacao`. Coordenadas **absolutas na chapa
física**, já com o offset do refilo. Cada corte traz `ordem` e `estagio`
(1 ou 2) — use na vista passo a passo.

### Validação

Nada sai sem passar por: todas as peças alocadas, dentro dos limites, sem
sobreposição, guilhotinável. Se falhar, o cliente TS lança erro em vez de
devolver o plano — melhor falhar que cortar chapa errada.

A checagem de guilhotina é **estrutural** (O(n)), não recursiva: layout de 2
estágios é guilhotinável por construção, então basta confirmar que a
estrutura é de fato de 2 estágios. A versão recursiva ficou como fallback
para ≤12 peças (é exponencial e travava com 27 em Python).

### Orçamento de tempo

O motor tenta K=1 chapa, depois K=2, etc. Cada tentativa recebe
`tempoLimiteS`, e o total é limitado a `tempoLimiteS × 4`. Com o padrão de
5s, o pior caso é 20s — dentro do timeout de 90s do cliente.

---

## Resultado medido

Chapa 2750×1850, kerf 4mm, refilo 10mm:

| | Chapas | Maior sobra | Rotações |
|---|---|---|---|
| Caso 1 — heurística antiga | 1 | — | 17 |
| Caso 1 — gabarito Corte Certo | 1 | 2730×620 | — |
| **Caso 1 — CP-SAT** | 1 | **2730×629** | **6** |
| Caso 2 — heurística antiga | 2 | — | 11 |
| Caso 2 — gabarito SketchCut | 2 | 2730×1240 | — |
| **Caso 2 — CP-SAT** | 2 | **2730×1458** | **0 e 6** |

Reproduzir: `python3 teste_e2e.py` no Repl 2.

---

## Decisões registradas

**Não usamos Geração de Colunas (Gilmore-Gomory).** É a técnica certa para
cutting stock de alta multiplicidade — cortar 500× a mesma peça, repetindo
padrões. Aqui os pedidos têm 15–40 peças com quantidade 1–4: a relaxação
linear fica frouxa e o "padrão" é praticamente a solução inteira.
Complexidade alta, ganho nulo. Decisão consciente.

**Não usamos heurística própria.** A versão anterior tinha ~600 linhas de
heurística acumulada (144 combinações de estratégia, algoritmo de faixas
próprio, critérios de pontuação empilhados). Foi tudo deletado. O modelo
CP-SAT tem ~150 linhas e produz resultado melhor.

**O Repl gratuito dorme.** A primeira otimização depois de um período
parado demora 10–20s enquanto o motor acorda. O cliente tem timeout de 90s,
então não quebra. Se incomodar: "Always On" no Repl 2.
