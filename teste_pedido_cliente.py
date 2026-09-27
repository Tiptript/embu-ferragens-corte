"""
Teste do pedido real do cliente:
MDF Preto 15 mm:
1x 1850x500
1x 1850x450
1x 1350x400
1x 1350x350
2x 1400x200
2x 650x200

MDF Preto 6 mm:
1x 1800x450
1x 1300x350
1x 1400x650
"""
import time
from solver2stage import solve_2stage
from geometria import retangulos_maximais, selecionar_sem_sobreposicao, validar_chapa, sequencia_cortes

def testar_pedido(nome, pecas_input, chapa=(2750, 1850), refilo=0, kerf=4, rot=False, tl=20):
    W = chapa[0] - 2 * refilo
    H = chapa[1] - 2 * refilo
    pieces = []
    for w, h, q, pid in pecas_input:
        for i in range(q):
            pieces.append((w, h, f"{pid}__{i+1}"))
    
    t0 = time.time()
    st, ch = None, None
    for K in range(1, 10):
        st_tmp, ch_tmp = solve_2stage(pieces, W, H, kerf, K=K, allow_rotation=rot, time_limit=tl)
        if ch_tmp:
            st, ch = st_tmp, ch_tmp
            break
            
    dt = (time.time() - t0) * 1000
    print(f"\n==========================================")
    print(f"PEDIDO: {nome}")
    print(f"Dimensões chapa: {chapa[0]}x{chapa[1]} mm | Refilo: {refilo} mm | Kerf: {kerf} mm | Rotação: {rot}")
    print(f"Total de peças: {len(pieces)} | Chapas usadas: {len(ch) if ch else 0} | Status: {st} | Tempo: {dt:.0f}ms")
    print(f"==========================================")
    
    if not ch:
        print("FALHA: Nenhuma solução encontrada!")
        return

    for i, c in enumerate(ch):
        locais = [{'x': p['x'], 'y': p['y'], 'w': p['w'], 'h': p['h']} for p in c['pecas']]
        v = validar_chapa(locais, W, H, kerf, faixas=c.get('faixas'))
        area_nominal = chapa[0] * chapa[1]
        area_pecas = sum(p['w'] * p['h'] for p in c['pecas'])
        aprov = (area_pecas / area_nominal) * 100.0
        
        maximais = retangulos_maximais(locais, W, H)
        vis = selecionar_sem_sobreposicao(maximais, 125)
        maiorR = max(vis, key=lambda r: r['w'] * r['h']) if vis else None
        
        print(f"\n--- Chapa #{i+1} ---")
        print(f"  Peças ({len(c['pecas'])}):")
        for p in c['pecas']:
            print(f"    - {p['nome']}: {p['w']}x{p['h']} mm na posição ({p['x']}, {p['y']})")
        print(f"  Aproveitamento: {aprov:.1f}%")
        print(f"  Validação: Dentro Limites={v['dentroDosLimites']}, Sem Sobreposição={v['semSobreposicao']}, Guilhotinável={v['guilhotinavel']}")
        if maiorR:
            print(f"  Maior Sobra: {maiorR['w']}x{maiorR['h']} mm ({maiorR['w']*maiorR['h']/1_000_000:.3f} m²)")

if __name__ == "__main__":
    # MDF Preto 15mm
    pecas_15mm = [
        (1850, 500, 1, "Peca_185x50"),
        (1850, 450, 1, "Peca_185x45"),
        (1350, 400, 1, "Peca_135x40"),
        (1350, 350, 1, "Peca_135x35"),
        (1400, 200, 2, "Peca_140x20"),
        (650, 200, 2, "Peca_65x20"),
    ]
    testar_pedido("MDF Preto 15mm (Sem Rotação, Refilo 0)", pecas_15mm, refilo=0, rot=False)

    # MDF Preto 6mm
    pecas_6mm = [
        (1800, 450, 1, "Peca_180x45"),
        (1300, 350, 1, "Peca_130x35"),
        (1400, 650, 1, "Peca_140x65"),
    ]
    testar_pedido("MDF Preto 6mm (Sem Rotação, Refilo 0)", pecas_6mm, refilo=0, rot=False)
