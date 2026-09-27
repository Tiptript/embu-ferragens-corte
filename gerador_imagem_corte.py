"""
Módulo gerador de imagem PNG de Alta Resolução do Plano de Corte para Seccionadora.
Gera um diagrama profissional com cotas milimétricas nítidas, crachás de alto contraste
para cada peça, dimensões exatas de sobras úteis e tabela de medidas integrada.
"""

import io
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Tuple
from geometria import retangulos_maximais, selecionar_sem_sobreposicao


# Paleta de cores contrastantes e harmoniosas para peças
CORES_PECAS = [
    (59, 130, 246),   # Azul Cobalto
    (16, 185, 129),  # Verde Esmeralda
    (245, 158, 11),  # Âmbar
    (139, 92, 246),  # Roxo
    (236, 72, 153),  # Rosa
    (6, 182, 212),   # Ciano
    (249, 115, 22),  # Laranja
    (20, 184, 166),  # Teal
    (99, 102, 241),  # Índigo
    (168, 85, 247),  # Violeta
]


def _limpar_id(pid: str) -> str:
    """Limpa identificadores gerados pelo solver (ex: 'P5__1' -> 'P5.1')."""
    return pid.replace("__", ".")


def gerar_imagem_plano_chapa(
    chapa_dict: Dict[str, Any],
    chapa_w: int,
    chapa_h: int,
    refilo: int = 0,
    kerf: int = 4,
    chapa_idx: int = 1,
    total_chapas: int = 1,
    material_nome: str = "MDF",
    sequencia_cortes_list: List[Dict[str, Any]] = None,
    df_pecas_info: Any = None
) -> bytes:
    """
    Renderiza um diagrama gráfico em PNG de 1600x1200px com máxima legibilidade:
    - Crachás brancos de alto contraste centralizados dentro de cada peça
    - Dimensões grandes em negrito (Comprimento x Largura mm)
    - Indicação de rotação quando aplicável
    - Dimensões e área das sobras úteis de MDF
    - Cotas de faixas para o operador da seccionadora
    - Tabela de conferência rápida no rodapé
    """
    LARGURA_IMG = 1600
    ALTURA_IMG = 1200

    # Margens ajustadas para incluir régua de faixas na esquerda
    MARGEM_ESQ = 100
    MARGEM_DIR = 60
    MARGEM_TOPO = 110
    MARGEM_INFERIOR_CHAPA = 250  # Reserva espaço para a tabela no rodapé

    AREA_W = LARGURA_IMG - MARGEM_ESQ - MARGEM_DIR
    AREA_H = ALTURA_IMG - MARGEM_TOPO - MARGEM_INFERIOR_CHAPA

    escala = min(AREA_W / chapa_w, AREA_H / chapa_h)
    desenho_w = int(chapa_w * escala)
    desenho_h = int(chapa_h * escala)

    offset_x = MARGEM_ESQ + (AREA_W - desenho_w) // 2
    offset_y = MARGEM_TOPO + (AREA_H - desenho_h) // 2

    # Canvas principal em cinza muito claro
    img = Image.new("RGB", (LARGURA_IMG, ALTURA_IMG), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Carrega fontes com fallback
    try:
        fonte_titulo = ImageFont.truetype("arialbd.ttf", 28)
        fonte_sub = ImageFont.truetype("arial.ttf", 17)
        fonte_badge_id = ImageFont.truetype("arialbd.ttf", 22)
        fonte_badge_medida = ImageFont.truetype("arialbd.ttf", 20)
        fonte_badge_mini = ImageFont.truetype("arialbd.ttf", 15)
        fonte_sobra = ImageFont.truetype("arialbd.ttf", 16)
        fonte_corte = ImageFont.truetype("arialbd.ttf", 14)
        fonte_tabela = ImageFont.truetype("arial.ttf", 15)
        fonte_tabela_bold = ImageFont.truetype("arialbd.ttf", 15)
    except Exception:
        fonte_titulo = ImageFont.load_default()
        fonte_sub = ImageFont.load_default()
        fonte_badge_id = ImageFont.load_default()
        fonte_badge_medida = ImageFont.load_default()
        fonte_badge_mini = ImageFont.load_default()
        fonte_sobra = ImageFont.load_default()
        fonte_corte = ImageFont.load_default()
        fonte_tabela = ImageFont.load_default()
        fonte_tabela_bold = ImageFont.load_default()

    # =========================================================================
    # 1. CABEÇALHO PROFISSIONAL
    # =========================================================================
    # Barra decorativa no topo
    draw.rectangle([0, 0, LARGURA_IMG, 6], fill=(56, 189, 248))

    # Título principal
    draw.text((MARGEM_ESQ, 22), "EMBU FERRAGENS — PLANO DE CORTE SECCIONADORA", fill=(15, 23, 42), font=fonte_titulo)

    # Subtítulo com dados técnicos
    sub_txt = f"Chapa #{chapa_idx} de {total_chapas}  •  Material: {material_nome}  •  Dimensão: {chapa_w} x {chapa_h} mm  •  Serra (Kerf): {kerf} mm"
    if refilo > 0:
        sub_txt += f"  •  Refilo: {refilo} mm"
    draw.text((MARGEM_ESQ, 62), sub_txt, fill=(71, 85, 105), font=fonte_sub)

    # Métricas da chapa
    pecas = chapa_dict.get("pecas", [])
    area_pecas = sum(p["w"] * p["h"] for p in pecas)
    area_total_chapa = chapa_w * chapa_h
    aproveitamento = (area_pecas / area_total_chapa) * 100.0 if area_total_chapa > 0 else 0

    # Badge de Aproveitamento no topo direito
    kpi_txt = f"Aproveitamento: {aproveitamento:.1f}%"
    kpi_w = 230
    kpi_h = 42
    kpi_x0 = LARGURA_IMG - MARGEM_DIR - kpi_w
    kpi_y0 = 30
    draw.rounded_rectangle([kpi_x0, kpi_y0, kpi_x0 + kpi_w, kpi_y0 + kpi_h], radius=8, fill=(16, 185, 129), outline=(5, 150, 105), width=2)
    draw.text((kpi_x0 + 16, kpi_y0 + 10), kpi_txt, fill=(255, 255, 255), font=fonte_badge_mini)

    # =========================================================================
    # 2. CONTORNO DA CHAPA & RETALHOS (SOBRAS)
    # =========================================================================
    x0_chapa = offset_x
    y0_chapa = offset_y
    x1_chapa = offset_x + desenho_w
    y1_chapa = offset_y + desenho_h

    # Fundo da chapa (representando a chapa bruta de MDF)
    draw.rectangle([x0_chapa, y0_chapa, x1_chapa, y1_chapa], fill=(226, 232, 240), outline=(30, 41, 59), width=3)

    # Cálculo das sobras úteis (retângulos vazios sem sobreposição)
    locais_pecas = [{'x': p['x'] + refilo, 'y': p['y'] + refilo, 'w': p['w'], 'h': p['h']} for p in pecas]
    W_util = chapa_w - 2 * refilo
    H_util = chapa_h - 2 * refilo
    maximais = retangulos_maximais(
        [{'x': p['x'], 'y': p['y'], 'w': p['w'], 'h': p['h']} for p in pecas],
        W_util, H_util
    )
    sobras_visiveis = selecionar_sem_sobreposicao(maximais, larg_min=120)

    # Desenha as sobras com preenchimento diferenciado e crachá de medidas
    for s in sobras_visiveis:
        sx0 = offset_x + int((s['x'] + refilo) * escala)
        sy0 = offset_y + int((s['y'] + refilo) * escala)
        sx1 = offset_x + int((s['x'] + refilo + s['w']) * escala)
        sy1 = offset_y + int((s['y'] + refilo + s['h']) * escala)

        sw_px = sx1 - sx0
        sh_px = sy1 - sy0

        # Desenha retângulo de sobra com tracejado sutil
        draw.rectangle([sx0, sy0, sx1, sy1], fill=(241, 245, 249), outline=(148, 163, 184), width=2)

        # Se a sobra for relevante (>= 150mm em ambos os eixos ou grande em um eixo), adiciona crachá
        if s['w'] >= 200 and s['h'] >= 150 and sw_px >= 90 and sh_px >= 50:
            badge_sobra_w = min(sw_px - 16, 180)
            badge_sobra_h = min(sh_px - 12, 54)
            sbx0 = sx0 + (sw_px - badge_sobra_w) // 2
            sby0 = sy0 + (sh_px - badge_sobra_h) // 2
            sbx1 = sbx0 + badge_sobra_w
            sby1 = sby0 + badge_sobra_h

            draw.rounded_rectangle([sbx0, sby0, sbx1, sby1], radius=6, fill=(254, 243, 199), outline=(217, 119, 6), width=2)
            draw.text((sbx0 + 10, sby0 + 6), "SOBRA ÚTIL", fill=(146, 64, 14), font=fonte_sobra)
            draw.text((sbx0 + 10, sby0 + 28), f"{s['w']} x {s['h']} mm", fill=(180, 83, 9), font=fonte_sobra)

    # =========================================================================
    # 3. RÉGUA DE FAIXAS NO EIXO ESQUERDO (COTAS DA SECCIONADORA)
    # =========================================================================
    faixas = chapa_dict.get("faixas", [])
    if faixas and faixas[0].get("tipo", "horizontal") == "horizontal":
        for idx_f, f in enumerate(faixas):
            fy0 = offset_y + int((f['y'] + refilo) * escala)
            fy1 = offset_y + int((f['y'] + refilo + f['h']) * escala)
            f_alt_mm = f['h']

            # Linha de cota vertical com setas
            x_cota = offset_x - 14
            draw.line([(x_cota, fy0 + 2), (x_cota, fy1 - 2)], fill=(100, 116, 139), width=2)
            draw.line([(x_cota - 4, fy0), (x_cota + 4, fy0)], fill=(100, 116, 139), width=2)
            draw.line([(x_cota - 4, fy1), (x_cota + 4, fy1)], fill=(100, 116, 139), width=2)

            # Texto da altura da faixa
            if fy1 - fy0 >= 24:
                lbl_f = f"{f_alt_mm}"
                ty_f = (fy0 + fy1) // 2 - 8
                draw.text((x_cota - 58, ty_f), lbl_f, fill=(15, 23, 42), font=fonte_corte)

    # =========================================================================
    # 4. DESENHO DAS PEÇAS COM CRACHÁ DE ALTO CONTRASTE
    # =========================================================================
    for i, p in enumerate(pecas):
        px = p["x"] + refilo
        py = p["y"] + refilo
        pw = p["w"]
        ph = p["h"]

        px0 = offset_x + int(px * escala)
        py0 = offset_y + int(py * escala)
        px1 = offset_x + int((px + pw) * escala)
        py1 = offset_y + int((py + ph) * escala)

        rect_w = px1 - px0
        rect_h = py1 - py0

        cor_base = CORES_PECAS[i % len(CORES_PECAS)]

        # Retângulo da peça com borda escura nítida
        draw.rectangle([px0, py0, px1, py1], fill=cor_base, outline=(15, 23, 42), width=3)

        # Identificação e medidas da peça
        nome_bruto = str(p.get("nome", f"P{i+1}"))
        pid_limpo = _limpar_id(nome_bruto)
        
        # Se contiver split de instância (ex: 'P5.1'), extrai ID base
        rotulo_topo = pid_limpo
        rot_str = " (Girado)" if p.get("rotated") else ""
        rotulo_medida = f"{pw} x {ph} mm{rot_str}"

        # -------------------------------------------------------------
        # CRACHÁ CENTRAL BRANCO DE ALTO CONTRASTE
        # -------------------------------------------------------------
        # Peça Normal/Grande
        if rect_w >= 110 and rect_h >= 55:
            bw = min(rect_w - 20, 240)
            bh = min(rect_h - 16, 68)

            bx0 = px0 + (rect_w - bw) // 2
            by0 = py0 + (rect_h - bh) // 2
            bx1 = bx0 + bw
            by1 = by0 + bh

            # Desenha crachá branco com borda preta
            draw.rounded_rectangle([bx0, by0, bx1, by1], radius=8, fill=(255, 255, 255), outline=(15, 23, 42), width=2)

            # Centraliza o texto dentro do crachá
            tx_id = bx0 + 14
            ty_id = by0 + 8
            draw.text((tx_id, ty_id), rotulo_topo[:22], fill=(15, 23, 42), font=fonte_badge_id)

            ty_med = by0 + 36
            draw.text((tx_id, ty_med), rotulo_medida, fill=(30, 58, 138), font=fonte_badge_medida)

        # Peça Média ou Estreita Horizontal (ex: rodapé ou travessa)
        elif rect_w >= 75 and rect_h >= 32:
            bw = min(rect_w - 10, 180)
            bh = min(rect_h - 8, 42)

            bx0 = px0 + (rect_w - bw) // 2
            by0 = py0 + (rect_h - bh) // 2
            bx1 = bx0 + bw
            by1 = by0 + bh

            draw.rounded_rectangle([bx0, by0, bx1, by1], radius=6, fill=(255, 255, 255), outline=(15, 23, 42), width=2)
            draw.text((bx0 + 8, by0 + 4), f"{pid_limpo}: {pw}x{ph}", fill=(15, 23, 42), font=fonte_badge_mini)
            if p.get("rotated"):
                draw.text((bx0 + 8, by0 + 22), "(GIRADO)", fill=(185, 28, 28), font=fonte_badge_mini)

        # Peça Muito Estreita Vertical (ex: lateral fina em pé)
        elif rect_h >= 90 and rect_w >= 30:
            bw = rect_w - 6
            bh = min(rect_h - 14, 120)
            bx0 = px0 + 3
            by0 = py0 + (rect_h - bh) // 2
            bx1 = bx0 + bw
            by1 = by0 + bh

            draw.rounded_rectangle([bx0, by0, bx1, by1], radius=4, fill=(255, 255, 255), outline=(15, 23, 42), width=1)
            draw.text((bx0 + 4, by0 + 6), pid_limpo, fill=(15, 23, 42), font=fonte_badge_mini)
            draw.text((bx0 + 4, by0 + 26), f"{pw}", fill=(30, 58, 138), font=fonte_badge_mini)
            draw.text((bx0 + 4, by0 + 44), "x", fill=(100, 116, 139), font=fonte_badge_mini)
            draw.text((bx0 + 4, by0 + 62), f"{ph}", fill=(30, 58, 138), font=fonte_badge_mini)

        # Peça Pequena
        else:
            draw.rectangle([px0 + 2, py0 + 2, px1 - 2, py1 - 2], fill=(255, 255, 255), outline=(15, 23, 42), width=1)
            draw.text((px0 + 4, py0 + 2), pid_limpo, fill=(15, 23, 42), font=fonte_badge_mini)

    # =========================================================================
    # 5. LINHAS DE CORTE GUILHOTINADO COM BADGES EXTERNAS
    # =========================================================================
    if sequencia_cortes_list:
        for c in sequencia_cortes_list:
            cx1 = offset_x + int(c["x1"] * escala)
            cy1 = offset_y + int(c["y1"] * escala)
            cx2 = offset_x + int(c["x2"] * escala)
            cy2 = offset_y + int(c["y2"] * escala)

            estagio = c.get("estagio", 1)
            ordem = c.get("ordem", 1)

            if estagio == 1:
                # Estágio 1: Faixas de ponta a ponta (Linha Vermelha Forte)
                draw.line([(cx1, cy1), (cx2, cy2)], fill=(220, 38, 38), width=3)
                # Badge circular vermelha com número do passo posicionada na margem direita
                bx = min(x1_chapa + 18, LARGURA_IMG - MARGEM_DIR + 14)
                by = (cy1 + cy2) // 2
                draw.ellipse([bx - 12, by - 12, bx + 12, by + 12], fill=(220, 38, 38), outline=(255, 255, 255), width=2)
                num_str = str(ordem)
                draw.text((bx - (5 if len(num_str) == 1 else 9), by - 8), num_str, fill=(255, 255, 255), font=fonte_corte)
            else:
                # Estágio 2: Destopo nas faixas (Linha Azul Forte)
                draw.line([(cx1, cy1), (cx2, cy2)], fill=(37, 99, 235), width=2)

    # =========================================================================
    # 5.1 DESENHA CRACHÁS DAS SOBRAS ÚTEIS (APÓS AS LINHAS PARA NÃO SER CORTADO)
    # =========================================================================
    for s in sobras_visiveis:
        sx0 = offset_x + int((s['x'] + refilo) * escala)
        sy0 = offset_y + int((s['y'] + refilo) * escala)
        sx1 = offset_x + int((s['x'] + refilo + s['w']) * escala)
        sy1 = offset_y + int((s['y'] + refilo + s['h']) * escala)

        sw_px = sx1 - sx0
        sh_px = sy1 - sy0

        # Se a sobra for relevante (>= 200mm em um eixo e >= 140mm no outro)
        if s['w'] >= 200 and s['h'] >= 140 and sw_px >= 90 and sh_px >= 50:
            badge_sobra_w = min(sw_px - 20, 190)
            badge_sobra_h = min(sh_px - 14, 56)
            sbx0 = sx0 + (sw_px - badge_sobra_w) // 2
            sby0 = sy0 + (sh_px - badge_sobra_h) // 2
            sbx1 = sbx0 + badge_sobra_w
            sby1 = sby0 + badge_sobra_h

            draw.rounded_rectangle([sbx0, sby0, sbx1, sby1], radius=8, fill=(254, 243, 199), outline=(217, 119, 6), width=2)
            draw.text((sbx0 + 12, sby0 + 7), "SOBRA ÚTIL", fill=(146, 64, 14), font=fonte_sobra)
            draw.text((sbx0 + 12, sby0 + 30), f"{s['w']} x {s['h']} mm", fill=(180, 83, 9), font=fonte_sobra)

    # =========================================================================
    # 6. TABELA INTEGRADA DE MEDIDAS NO RODAPÉ DA IMAGEM
    # =========================================================================
    tabela_y0 = y1_chapa + 25
    tabela_w = LARGURA_IMG - MARGEM_ESQ - MARGEM_DIR
    draw.rectangle([MARGEM_ESQ, tabela_y0, MARGEM_ESQ + tabela_w, tabela_y0 + 130], fill=(255, 255, 255), outline=(203, 213, 225), width=2)

    # Cabeçalho da tabela
    draw.rectangle([MARGEM_ESQ, tabela_y0, MARGEM_ESQ + tabela_w, tabela_y0 + 32], fill=(241, 245, 249))
    draw.text((MARGEM_ESQ + 16, tabela_y0 + 7), "TABELA DE MEDIDAS DESTA CHAPA (PARA A OFICINA)", fill=(15, 23, 42), font=fonte_tabela_bold)

    # Agrupa peças por dimensão para tabela compacta
    resumo_pecas = {}
    for p in pecas:
        nome_p = _limpar_id(str(p.get('nome', '')))
        chave = (p['w'], p['h'], nome_p)
        if chave not in resumo_pecas:
            resumo_pecas[chave] = {"nomes": [], "qtd": 0, "w": p['w'], "h": p['h']}
        resumo_pecas[chave]["qtd"] += 1
        resumo_pecas[chave]["nomes"].append(nome_p)

    # Desenha colunas da tabela (até 2 colunas para caber muitas peças)
    itens = list(resumo_pecas.values())
    col1_itens = itens[:4]
    col2_itens = itens[4:8]

    def _render_col(lista, x_offset):
        for idx, item in enumerate(lista):
            y_item = tabela_y0 + 40 + idx * 22
            id_txt = ", ".join(item["nomes"][:3])
            if len(item["nomes"]) > 3:
                id_txt += f" (+{len(item['nomes'])-3})"
            linha_txt = f"- {item['qtd']}x  [{id_txt}]  {item['w']} x {item['h']} mm"
            draw.text((x_offset, y_item), linha_txt, fill=(30, 41, 59), font=fonte_tabela)

    _render_col(col1_itens, MARGEM_ESQ + 16)
    if col2_itens:
        _render_col(col2_itens, MARGEM_ESQ + tabela_w // 2 + 10)

    # Rodapé final da folha
    txt_legenda = "Legenda: [Branco] Crachá com Medida da Peça  |  [Amarelo] Sobra Útil  |  [Vermelho] Corte Estágio 1  |  [Azul] Corte Estágio 2"
    draw.text((MARGEM_ESQ, ALTURA_IMG - 32), txt_legenda, fill=(100, 116, 139), font=fonte_badge_mini)

    # Retorna buffer PNG otimizado
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
