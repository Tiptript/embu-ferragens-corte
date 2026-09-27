"""Retalhos (retangulos vazios maximais), area de uniao e sequencia de cortes."""


def retangulos_maximais(pecas, W, H):
    """Todos os retangulos vazios maximais. Podem se sobrepor — e esperado."""
    xs = {0, W}
    ys = {0, H}
    for p in pecas:
        xs.add(p['x']); xs.add(p['x'] + p['w'])
        ys.add(p['y']); ys.add(p['y'] + p['h'])
    X = sorted(xs); Y = sorted(ys)
    nc, nr = len(X) - 1, len(Y) - 1
    if nc <= 0 or nr <= 0:
        return []

    occ = [[False] * nc for _ in range(nr)]
    for p in pecas:
        c0, c1 = X.index(p['x']), X.index(p['x'] + p['w'])
        r0, r1 = Y.index(p['y']), Y.index(p['y'] + p['h'])
        for r in range(r0, r1):
            for c in range(c0, c1):
                occ[r][c] = True

    out = []
    for r0 in range(nr):
        for c0 in range(nc):
            if occ[r0][c0]:
                continue
            maxC = nc
            for r1 in range(r0, nr):
                c1 = c0
                while c1 < maxC and not occ[r1][c1]:
                    c1 += 1
                maxC = min(maxC, c1)
                if maxC == c0:
                    break
                out.append({'x': X[c0], 'y': Y[r0],
                            'w': X[maxC] - X[c0], 'h': Y[r1 + 1] - Y[r0]})

    # descarta os contidos em outro (mantem so os maximais)
    return [r for r in out if not any(
        u is not r and u['x'] <= r['x'] and u['y'] <= r['y']
        and u['x'] + u['w'] >= r['x'] + r['w']
        and u['y'] + u['h'] >= r['y'] + r['h'] for u in out)]


def selecionar_sem_sobreposicao(maximais, larg_min):
    """
    Escolhe um subconjunto de retalhos que NAO se sobrepoem — e este
    conjunto que vai para o desenho e para a tabela do operador.
    Guloso: pega o de maior area, remove o que colide, repete.
    """
    cands = sorted(maximais, key=lambda r: r['w'] * r['h'], reverse=True)
    escolhidos = []
    for r in cands:
        if min(r['w'], r['h']) < larg_min:
            continue
        colide = any(not (r['x'] + r['w'] <= e['x'] or e['x'] + e['w'] <= r['x']
                          or r['y'] + r['h'] <= e['y'] or e['y'] + e['h'] <= r['y'])
                     for e in escolhidos)
        if not colide:
            escolhidos.append(r)
    return escolhidos


def area_uniao(rects):
    """Area da uniao (evita dupla contagem de retangulos sobrepostos)."""
    if not rects:
        return 0
    xs = sorted({v for r in rects for v in (r['x'], r['x'] + r['w'])})
    ys = sorted({v for r in rects for v in (r['y'], r['y'] + r['h'])})
    total = 0
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = xs[i], ys[j]
            larg, alt = xs[i + 1] - cx, ys[j + 1] - cy
            if any(r['x'] <= cx and cx + larg <= r['x'] + r['w']
                   and r['y'] <= cy and cy + alt <= r['y'] + r['h'] for r in rects):
                total += larg * alt
    return total


def sequencia_cortes(faixas, W, H, kerf, off_x=0, off_y=0):
    """
    Sequencia de corte para plano de 2 estagios.
    Suporta faixas horizontais (estágio 1 horizontal) e faixas verticais (estágio 1 vertical).
    """
    if not faixas:
        return []
    
    tipo = faixas[0].get('tipo', 'horizontal')
    cortes = []
    ordem = 1

    if tipo == 'vertical':
        # Estagio 1: cortes verticais que atravessam a chapa inteira (de y=0 ate y=H)
        # Estagio 2: cortes horizontais dentro de cada faixa vertical
        for f in faixas:
            x_corte = off_x + f['x'] + f['w']
            if x_corte < off_x + W:
                cortes.append({'ordem': ordem, 'estagio': 1,
                               'x1': x_corte, 'y1': off_y,
                               'x2': x_corte, 'y2': off_y + H})
                ordem += 1
            for p in f['pecas'][:-1]:
                y_corte = off_y + p['y'] + p['h']
                cortes.append({'ordem': ordem, 'estagio': 2,
                               'x1': off_x + f['x'], 'y1': y_corte,
                               'x2': off_x + f['x'] + f['w'], 'y2': y_corte})
                ordem += 1
            ultima = f['pecas'][-1]
            y_fim = off_y + ultima['y'] + ultima['h']
            if y_fim < off_y + H:
                cortes.append({'ordem': ordem, 'estagio': 2,
                               'x1': off_x + f['x'], 'y1': y_fim,
                               'x2': off_x + f['x'] + f['w'], 'y2': y_fim})
                ordem += 1
    else:
        # Estágio 1: cortes horizontais que atravessam a chapa inteira
        # Estágio 2: cortes verticais dentro de cada faixa horizontal
        for f in faixas:
            y_corte = off_y + f['y'] + f['h']
            if y_corte < off_y + H:
                cortes.append({'ordem': ordem, 'estagio': 1,
                               'x1': off_x, 'y1': y_corte,
                               'x2': off_x + W, 'y2': y_corte})
                ordem += 1
            for p in f['pecas'][:-1]:
                x_corte = off_x + p['x'] + p['w']
                cortes.append({'ordem': ordem, 'estagio': 2,
                               'x1': x_corte, 'y1': off_y + f['y'],
                               'x2': x_corte, 'y2': off_y + f['y'] + f['h']})
                ordem += 1
            ultima = f['pecas'][-1]
            x_fim = off_x + ultima['x'] + ultima['w']
            if x_fim < off_x + W:
                cortes.append({'ordem': ordem, 'estagio': 2,
                               'x1': x_fim, 'y1': off_y + f['y'],
                               'x2': x_fim, 'y2': off_y + f['y'] + f['h']})
                ordem += 1
    return cortes


def eh_guilhotinavel(pecas, w, h, ox=0, oy=0, eps=1e-6):
    """Verificacao recursiva: existe corte de ponta a ponta que separa tudo?"""
    if not pecas:
        return True
    if len(pecas) == 1:
        p = pecas[0]
        if (abs(p['x'] - ox) < eps and abs(p['y'] - oy) < eps
                and abs(p['w'] - w) < eps and abs(p['h'] - h) < eps):
            return True

    for cut in {v for p in pecas for v in (p['x'], p['x'] + p['w'])}:
        if cut <= ox + eps or cut >= ox + w - eps:
            continue
        e = [p for p in pecas if p['x'] + p['w'] <= cut + eps]
        d = [p for p in pecas if p['x'] >= cut - eps]
        if len(e) + len(d) != len(pecas):
            continue
        if (eh_guilhotinavel(e, cut - ox, h, ox, oy)
                and eh_guilhotinavel(d, w - (cut - ox), h, cut, oy)):
            return True

    for cut in {v for p in pecas for v in (p['y'], p['y'] + p['h'])}:
        if cut <= oy + eps or cut >= oy + h - eps:
            continue
        c = [p for p in pecas if p['y'] + p['h'] <= cut + eps]
        b = [p for p in pecas if p['y'] >= cut - eps]
        if len(c) + len(b) != len(pecas):
            continue
        if (eh_guilhotinavel(c, w, cut - oy, ox, oy)
                and eh_guilhotinavel(b, w, h - (cut - oy), ox, cut)):
            return True

    return False


def validar_2estagios(faixas, W, H, kerf):
    """
    Verificação ESTRUTURAL de 2 estágios — O(n), não recursiva.
    Suporta faixas horizontais e faixas verticais.
    """
    if not faixas:
        return True

    tipo = faixas[0].get('tipo', 'horizontal')

    if tipo == 'vertical':
        x_ant = -1
        for f in faixas:
            if f['x'] < x_ant:
                return False
            if f['x'] + f['w'] > W + 1e-6:
                return False
            x_ant = f['x'] + f['w']
            y_ant = -1
            for p in f['pecas']:
                if p['y'] < y_ant:
                    return False
                if p['y'] + p['h'] > H + 1e-6:
                    return False
                y_ant = p['y'] + p['h']
        return True
    else:
        y_ant = -1
        for f in faixas:
            if f['y'] < y_ant:
                return False
            if f['y'] + f['h'] > H + 1e-6:
                return False
            y_ant = f['y'] + f['h']
            x_ant = -1
            for p in f['pecas']:
                if p['x'] < x_ant:
                    return False
                if p['x'] + p['w'] > W + 1e-6:
                    return False
                x_ant = p['x'] + p['w']
        return True


def validar_chapa(pecas, W, H, kerf, faixas=None):
    """Checagens que rodam antes de qualquer resultado sair do servico."""
    dentro = all(p['x'] >= 0 and p['y'] >= 0
                 and p['x'] + p['w'] <= W + 1e-6
                 and p['y'] + p['h'] <= H + 1e-6 for p in pecas)
    sem_sobrep = True
    for i in range(len(pecas)):
        for j in range(i + 1, len(pecas)):
            a, b = pecas[i], pecas[j]
            if (a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w']
                    and a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h']):
                sem_sobrep = False
                break
        if not sem_sobrep:
            break

    if faixas is not None:
        guilhotina = validar_2estagios(faixas, W, H, kerf)
    else:
        # fallback recursivo — só para layouts pequenos (custo exponencial)
        guilhotina = eh_guilhotinavel(
            [{'x': p['x'], 'y': p['y'], 'w': p['w'], 'h': p['h']}
             for p in pecas], W, H) if len(pecas) <= 12 else None

    return {
        'dentroDosLimites': dentro,
        'semSobreposicao': sem_sobrep,
        'guilhotinavel': guilhotina,
    }
