"""
Microsserviço de plano de corte guilhotinado — motor CP-SAT (OR-Tools).

Contrato pensado para casar com as interfaces TypeScript já existentes
(RetanguloChapa, Retalho, Corte, ChapaResultado). Todas as coordenadas
devolvidas são ABSOLUTAS na chapa física, já incluindo o offset do refilo.
"""
import math
import os
import secrets
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

from solver2stage import solve_2stage
from geometria import (retangulos_maximais, selecionar_sem_sobreposicao,
                       area_uniao, sequencia_cortes, validar_chapa)

app = FastAPI(title="Motor de Plano de Corte", version="1.0")

API_TOKEN = os.environ.get("MOTOR_API_TOKEN", "")


# ----------------------------------------------------------------------
# Contrato
# ----------------------------------------------------------------------
class PecaIn(BaseModel):
    id: str
    instanceId: str
    largura: int           # mm, já com fita deduzida (o Node faz isso)
    altura: int


class ChapaIn(BaseModel):
    largura: int           # mm, dimensão nominal da chapa
    altura: int
    refiloMm: int = 0


class PedidoIn(BaseModel):
    chapa: ChapaIn
    pecas: List[PecaIn]
    kerfMm: int = 4
    retalhoMinimoMm: int = 125
    permiteRotacao: bool = True      # false quando o material tem veio
    tempoLimiteS: float = 15.0
    maxChapas: int = 30


# ----------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}


@app.post("/otimizar")
def otimizar(pedido: PedidoIn, authorization: Optional[str] = Header(None)):
    if API_TOKEN:
        esperado = f"Bearer {API_TOKEN}"
        if not authorization or not secrets.compare_digest(authorization, esperado):
            raise HTTPException(status_code=401, detail="token inválido")

    t0 = time.time()

    if not pedido.pecas:
        raise HTTPException(400, "nenhuma peça informada")
    if len(pedido.pecas) > 400:
        raise HTTPException(400, "máximo de 400 peças por pedido")

    ids = [p.instanceId for p in pedido.pecas]
    if len(set(ids)) != len(ids):
        raise HTTPException(400, "instanceId duplicado — cada unidade física precisa de um id único")

    for p in pedido.pecas:
        if p.largura <= 0 or p.altura <= 0:
            raise HTTPException(400, f"Peça {p.id} tem dimensão inválida ({p.largura}x{p.altura})")

    refilo = pedido.chapa.refiloMm
    W = pedido.chapa.largura - 2 * refilo      # área útil
    H = pedido.chapa.altura - 2 * refilo
    kerf = pedido.kerfMm
    larg_min = pedido.retalhoMinimoMm

    if W <= 0 or H <= 0:
        raise HTTPException(400, "refilo maior que a própria chapa")

    # valida encaixe individual antes de montar o modelo
    for p in pedido.pecas:
        cabe = (p.largura <= W and p.altura <= H)
        cabe_girado = pedido.permiteRotacao and (p.altura <= W and p.largura <= H)
        if not (cabe or cabe_girado):
            raise HTTPException(
                400,
                f"Peça {p.id} ({p.largura}x{p.altura}mm) não cabe na área útil "
                f"da chapa ({W}x{H}mm, refilo {refilo}mm por lado)."
            )

    pieces = [(p.largura, p.altura, p.instanceId) for p in pedido.pecas]

    # limite inferior de chapas pela área — evita tentar K impossível
    area_pecas = sum(p.largura * p.altura for p in pedido.pecas)
    k_min = max(1, math.ceil(area_pecas / (W * H)))

    resultado = None
    status_final = "INFEASIBLE"
    # Orçamento total: o loop pode tentar vários K. Sem teto, K=1..8 a 5s
    # cada estouraria o timeout do cliente. Cada tentativa recebe o que
    # sobrou do orçamento.
    orcamento = max(pedido.tempoLimiteS * 3, 45.0)
    for K in range(k_min, pedido.maxChapas + 1):
        restante = orcamento - (time.time() - t0)
        if restante <= 0.5:
            break
        status, chapas = solve_2stage(
            pieces, W, H, kerf, K=K,
            allow_rotation=pedido.permiteRotacao,
            time_limit=min(pedido.tempoLimiteS, restante),
        )
        if chapas:
            resultado, status_final = chapas, status
            break

    if resultado is None:
        raise HTTPException(422, "não foi possível gerar plano de corte")

    # ------------------------------------------------------------------
    # Monta a resposta com coordenadas ABSOLUTAS (offset do refilo)
    # ------------------------------------------------------------------
    saida, validacoes = [], []
    for i, ch in enumerate(resultado):
        pecas_abs = [{
            'pecaId': pedido.pecas[p['idx']].id,
            'instanceId': pedido.pecas[p['idx']].instanceId,
            'x': p['x'] + refilo, 'y': p['y'] + refilo,
            'w': p['w'], 'h': p['h'],
            'rotated': p['rotated'],
        } for p in ch['pecas']]

        # retalhos: calculados na área útil, devolvidos em coordenada absoluta
        locais = [{'x': p['x'], 'y': p['y'], 'w': p['w'], 'h': p['h']}
                  for p in ch['pecas']]
        maximais = retangulos_maximais(locais, W, H)
        visiveis = selecionar_sem_sobreposicao(maximais, larg_min)

        retalhos = []
        for r in visiveis:
            larg, comp = min(r['w'], r['h']), max(r['w'], r['h'])
            retalhos.append({
                'x': r['x'] + refilo, 'y': r['y'] + refilo,
                'w': r['w'], 'h': r['h'],
                'largura': larg, 'comprimento': comp,
                'aproveitavel': larg >= larg_min,
                'areaM2': round(r['w'] * r['h'] / 1_000_000, 4),
            })
        retalhos.sort(key=lambda r: -r['largura'])

        area_retalhos = area_uniao(
            [r for r in maximais if min(r['w'], r['h']) >= larg_min])
        area_pecas_ch = sum(p['w'] * p['h'] for p in ch['pecas'])
        area_nominal = pedido.chapa.largura * pedido.chapa.altura

        cortes = sequencia_cortes(ch['faixas'], W, H, kerf, refilo, refilo)

        v = validar_chapa(locais, W, H, kerf, faixas=ch['faixas'])
        v['todasPecasAlocadas'] = True
        validacoes.append(v)

        saida.append({
            'numero': i + 1,
            'larguraChapa': pedido.chapa.largura,
            'comprimentoChapa': pedido.chapa.altura,
            'refiloMm': refilo,
            'pecas': pecas_abs,
            'retalhos': retalhos,
            'sequenciaCortes': cortes,
            'areaUtilizadaMm2': area_pecas_ch,
            'areaTotalMm2': area_nominal,
            'areaRetalhosMm2': area_retalhos,
            'perdaMm2': area_nominal - area_pecas_ch - area_retalhos,
            'aproveitamentoPercentual': round(area_pecas_ch / area_nominal * 100, 2),
        })

    total_alocadas = sum(len(c['pecas']) for c in saida)
    ok = (total_alocadas == len(pedido.pecas)
          and all(v['dentroDosLimites'] and v['semSobreposicao']
                  and v['guilhotinavel'] for v in validacoes))

    return {
        'chapas': saida,
        'totalChapasUtilizadas': len(saida),
        'validacao': {
            'ok': ok,
            'porChapa': validacoes,
            'pecasEsperadas': len(pedido.pecas),
            'pecasAlocadas': total_alocadas,
        },
        'solverStatus': status_final,
        'tempoMs': int((time.time() - t0) * 1000),
    }
