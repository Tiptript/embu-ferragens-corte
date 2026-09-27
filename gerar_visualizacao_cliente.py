"""
Gera o relatório visual em HTML do pedido do cliente (MDF 15mm e MDF 6mm).
"""
from teste_pedido_cliente import testar_pedido
from solver2stage import solve_2stage
from geometria import retangulos_maximais, selecionar_sem_sobreposicao, sequencia_cortes
import json

def gerar_html_pedido():
    chapa_dim = (2750, 1850)
    kerf = 4
    
    pedidos = [
        ("MDF Preto 15mm", [
            (1850, 500, 1, "Peca_185x50"),
            (1850, 450, 1, "Peca_185x45"),
            (1350, 400, 1, "Peca_135x40"),
            (1350, 350, 1, "Peca_135x35"),
            (1400, 200, 2, "Peca_140x20"),
            (650, 200, 2, "Peca_65x20"),
        ]),
        ("MDF Preto 6mm", [
            (1800, 450, 1, "Peca_180x45"),
            (1300, 350, 1, "Peca_130x35"),
            (1400, 650, 1, "Peca_140x65"),
        ])
    ]

    html_parts = []
    colors = ["#38bdf8", "#fbbf24", "#34d399", "#f472b6", "#a78bfa", "#f87171", "#fb923c", "#2dd4bf"]

    for mat_nome, pecas_input in pedidos:
        pieces = []
        for w, h, q, pid in pecas_input:
            for i in range(q):
                pieces.append((w, h, f"{pid}__{i+1}"))
        
        st, ch = solve_2stage(pieces, chapa_dim[0], chapa_dim[1], kerf, K=1, allow_rotation=False)
        
        for ch_idx, c in enumerate(ch):
            locais = [{'x': p['x'], 'y': p['y'], 'w': p['w'], 'h': p['h']} for p in c['pecas']]
            maximais = retangulos_maximais(locais, chapa_dim[0], chapa_dim[1])
            vis = selecionar_sem_sobreposicao(maximais, 125)
            cortes = sequencia_cortes(c['faixas'], chapa_dim[0], chapa_dim[1], kerf)
            
            area_pecas = sum(p['w'] * p['h'] for p in c['pecas'])
            area_chapa = chapa_dim[0] * chapa_dim[1]
            aprov = (area_pecas / area_chapa) * 100.0

            svg_elements = []
            # Desenha Sobras
            for r in vis:
                svg_elements.append(
                    f'<rect x="{r["x"]}" y="{r["y"]}" width="{r["w"]}" height="{r["h"]}" '
                    f'fill="rgba(100, 116, 139, 0.2)" stroke="#94a3b8" stroke-dasharray="6,6" stroke-width="2">'
                    f'<title>Sobra Útil: {r["w"]}x{r["h"]} mm ({r["w"]*r["h"]/1_000_000:.3f} m²)</title></rect>'
                )

            # Desenha Peças
            for p_idx, p in enumerate(c['pecas']):
                color = colors[p_idx % len(colors)]
                cx = p['x'] + p['w'] / 2
                cy = p['y'] + p['h'] / 2
                svg_elements.append(
                    f'<g>'
                    f'<rect x="{p["x"]}" y="{p["y"]}" width="{p["w"]}" height="{p["h"]}" '
                    f'fill="{color}" stroke="#0f172a" stroke-width="3">'
                    f'<title>{p["nome"]}: {p["w"]}x{p["h"]} mm em ({p["x"]}, {p["y"]})</title></rect>'
                    f'<text x="{cx}" y="{cy - 10}" fill="#0f172a" font-size="32" font-weight="bold" text-anchor="middle">{p["nome"].split("__")[0]}</text>'
                    f'<text x="{cx}" y="{cy + 25}" fill="#1e293b" font-size="24" font-weight="600" text-anchor="middle">{p["w"]}x{p["h"]} mm</text>'
                    f'</g>'
                )

            html_parts.append(f"""
            <div style="background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 32px; border: 1px solid #334155;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <div>
                        <h2 style="margin: 0; color: #38bdf8;">{mat_nome} — Chapa #{ch_idx+1} ({chapa_dim[0]}x{chapa_dim[1]} mm)</h2>
                        <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 14px;">Sem rotação | Kerf: {kerf} mm | Cortes de 2 estágios para seccionadora</p>
                    </div>
                    <div style="background: #065f46; color: #34d399; font-weight: bold; font-size: 18px; padding: 8px 16px; border-radius: 8px;">
                        Aproveitamento: {aprov:.1f}% ({len(c['pecas'])} peças)
                    </div>
                </div>
                <svg viewBox="0 0 {chapa_dim[0]} {chapa_dim[1]}" style="width: 100%; height: auto; max-height: 600px; background: #0f172a; border-radius: 8px; border: 2px solid #475569;">
                    {''.join(svg_elements)}
                </svg>
            </div>
            """)

    full_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Plano de Corte - Pedido do Cliente (Embu Ferragens)</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #0b1120;
            color: #f8fafc;
            padding: 32px;
            margin: 0;
        }}
        h1 {{ margin: 0 0 8px 0; color: #f8fafc; font-size: 26px; }}
    </style>
</head>
<body>
    <h1>Plano de Corte Otimizado — Embu Ferragens</h1>
    <p style="color: #94a3b8; margin-bottom: 32px;">Resultados calculados com o novo motor OR-Tools CP-SAT Reforçado (Alta Qualidade)</p>
    {''.join(html_parts)}
</body>
</html>"""

    with open("c:/Users/123vi/Downloads/motor-corte/plano_de_corte_cliente.html", "w", encoding="utf-8") as f:
        f.write(full_html)
    print("HTML gerado com sucesso!")

if __name__ == "__main__":
    gerar_html_pedido()
