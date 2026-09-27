# Motor de Plano de Corte — CP-SAT (2 estágios)

Microsserviço Python que resolve corte guilhotinado em 2 estágios usando
CP-SAT (OR-Tools). Substitui o nesting heurístico que rodava no Node.

## Por que CP-SAT e não heurística

Medido nos dois casos reais (chapa 2750×1850, kerf 4mm):

| | Chapas | Consolidação da sobra | Rotações |
|---|---|---|---|
| Caso 1 — motor heurístico antigo | 1 | 70% | 17 |
| Caso 1 — gabarito Corte Certo | 1 | — | — |
| **Caso 1 — CP-SAT** | 1 | **81%** | **6** |
| Caso 2 — motor heurístico antigo | 2 | 70% | 11 |
| Caso 2 — gabarito SketchCut | 2 | sobra 2730×1240 | — |
| **Caso 2 — CP-SAT** | 2 | **sobra 2730×1458** | **0 e 6** |

5 segundos de limite bastam: resultado em 5s é idêntico ao de 30s.

## Por que NÃO Geração de Colunas (Gilmore-Gomory)

Column generation / Branch-and-Price ganha em cutting stock de **alta
multiplicidade** (cortar 500× a peça A, repetindo padrões). Aqui os pedidos
têm 15–40 peças com quantidade 1–4: a relaxação linear fica frouxa e o
"padrão" é praticamente a solução inteira. Complexidade alta, ganho nulo.
Decisão consciente, não esquecimento.

## Arquitetura do modelo

Corte guilhotinado de **2 estágios**:
- Estágio 1: cortes horizontais que atravessam a chapa inteira → faixas
- Estágio 2: cortes verticais dentro de cada faixa → peças

Altura da faixa = altura da peça mais alta dentro dela.

**Objetivo:** minimizar `Σ (k+1) × altura_usada[k]`. O peso crescente por
índice de chapa empurra material para as chapas iniciais e deixa a última o
mais vazia possível — é assim que a sobra vira um bloco único grande, em vez
de espalhada. É o que produz o visual limpo dos softwares comerciais.

## Arquivos

```
main.py           FastAPI — endpoint POST /otimizar
solver2stage.py   modelo CP-SAT
geometria.py      retalhos maximais, área de união, sequência de cortes, validação
motorClient.ts    cliente TypeScript (vai para o projeto Node)
Dockerfile        imagem para Cloud Run
requirements.txt
```

## Rodar local

```bash
pip install -r requirements.txt
uvicorn main:app --port 8080
curl localhost:8080/health
```

## Deploy no Cloud Run

```bash
gcloud run deploy motor-corte \
  --source . \
  --region southamerica-east1 \
  --memory 1Gi \
  --cpu 2 \
  --timeout 120 \
  --min-instances 0 \
  --allow-unauthenticated \
  --set-env-vars MOTOR_API_TOKEN=<gere-um-token>
```

`--cpu 2` importa: CP-SAT usa múltiplos workers de busca.
`--min-instances 0` mantém custo em zero quando ninguém usa (cold start de
~10s no primeiro pedido do dia; o cliente TS já tem timeout de 90s).

## Contrato

**POST /otimizar**

```json
{
  "chapa":   { "largura": 2750, "altura": 1850, "refiloMm": 10 },
  "kerfMm": 4,
  "retalhoMinimoMm": 125,
  "permiteRotacao": true,
  "tempoLimiteS": 5,
  "pecas": [ { "id": "P7", "instanceId": "P7__1", "largura": 500, "altura": 635 } ]
}
```

`pecas` já chega com a fita deduzida (isso continua no Node).
`permiteRotacao: false` quando o material tem veio.

**Resposta:** `ChapaResultado[]` + validação. Todas as coordenadas são
**absolutas na chapa física**, já incluindo o offset do refilo — o frontend
desenha a moldura de refilo sem recalcular nada.

Cada chapa traz `sequenciaCortes` com `estagio` (1 ou 2) e `ordem`, pronta
para a vista passo a passo.

## Validação

Nenhum resultado sai sem passar por:
- todas as peças alocadas
- dentro dos limites da chapa
- sem sobreposição
- guilhotinável (verificação **estrutural** de 2 estágios, O(n))

A verificação estrutural substituiu a recursiva: a recursiva é exponencial e
travava com 27 peças em Python. Como o layout de 2 estágios é guilhotinável
por construção, basta confirmar que a estrutura é de fato de 2 estágios —
faixas não se sobrepõem, peças dentro da faixa não se sobrepõem, nada
ultrapassa os limites.

Se a validação falhar, o cliente TS lança erro em vez de devolver o plano.
Melhor falhar do que cortar chapa errada.

---

## 👥 Papéis & Engenharia de IA

Este ecossistema foi construído, auditado e operacionalizado pela sinergia de múltiplos modelos de inteligência artificial:

- 🏗️ **Antigravity**: **Arquiteto de Sistemas, Engenheiro de Execução e Orquestrador Autônomo** — responsável pela implementação completa do motor de corte matemático (OR-Tools CP-SAT de 2 estágios), modelagem geométrica de guilhotina, integração da interface Streamlit, gerador Pix EMVCo e orquestração de ponta a ponta.
- 🔍 **Claude (Fable)**: **Revisor Técnico e Auditor de Arquitetura** — auditoria crítica de código, validação de regras de marcenaria, verificação de casos de borda e garantia de qualidade de engenharia.
- 🎯 **Gemini**: **Prompter, Extrator Multimodal e Motor de Visão** — decomposição de fotos e rascunhos de marcenaria, extração de texto não estruturado e engenharia de prompts do assistente paramétrico de móveis.

