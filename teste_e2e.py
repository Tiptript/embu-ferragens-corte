import json, time, math
from solver2stage import solve_2stage
from geometria import (retangulos_maximais, selecionar_sem_sobreposicao,
                       area_uniao, sequencia_cortes, validar_chapa)

def rodar(nome, pecas_def, chapa=(2750,1850), refilo=10, kerf=4, larg_min=125, rot=True, tl=5):
    pieces=[]
    for (w,h,q,pid) in pecas_def:
        for i in range(q): pieces.append((w,h,f'{pid}__{i+1}'))
    W,H = chapa[0]-2*refilo, chapa[1]-2*refilo
    area=sum(w*h for w,h,_ in pieces); k_min=max(1,math.ceil(area/(W*H)))
    t0=time.time(); res=None
    for K in range(k_min, 12):
        st,ch = solve_2stage(pieces,W,H,kerf,K=K,allow_rotation=rot,time_limit=tl)
        if ch: res,status=ch,st; break
    dt=(time.time()-t0)*1000
    print(f'\n=== {nome} ===')
    print(f'  {len(pieces)} pecas | area util {W}x{H} (refilo {refilo}) | {len(res)} chapas | {st} | {dt:.0f}ms')
    tot_aloc=0
    for i,c in enumerate(res):
        locais=[{'x':p['x'],'y':p['y'],'w':p['w'],'h':p['h']} for p in c['pecas']]
        tot_aloc+=len(locais)
        maximais=retangulos_maximais(locais,W,H)
        vis=selecionar_sem_sobreposicao(maximais,larg_min)
        v=validar_chapa(locais,W,H,kerf,faixas=c['faixas'])
        cortes=sequencia_cortes(c['faixas'],W,H,kerf,refilo,refilo)
        aprov=sum(p['w']*p['h'] for p in c['pecas'])/(chapa[0]*chapa[1])*100
        nrot=sum(1 for p in c['pecas'] if p['rotated'])
        maiorR=max(vis,key=lambda r:r['w']*r['h']) if vis else None
        print(f'  Chapa {i+1}: {len(locais)}pc | aprov {aprov:.1f}% | {nrot} rot | {len(c["faixas"])} faixas | {len(cortes)} cortes')
        print(f'     validacao: limites={v["dentroDosLimites"]} semSobrep={v["semSobreposicao"]} guilhotina={v["guilhotinavel"]}')
        if maiorR:
            print(f'     maior retalho: {min(maiorR["w"],maiorR["h"])}x{max(maiorR["w"],maiorR["h"])}mm | {len(vis)} retalhos sem sobreposicao')
    print(f'  TOTAL alocado: {tot_aloc}/{len(pieces)} {"OK" if tot_aloc==len(pieces) else "FALHOU"}')
    return res

rodar('CASO 1 — 27 pecas',
  [(430,295,1,'P1'),(374,135,4,'P2'),(500,135,4,'P3'),(374,250,2,'P4'),
   (430,155,2,'P5'),(500,250,2,'P6'),(500,635,1,'P7'),(470,635,2,'P8'),
   (745,150,1,'P9'),(692,145,2,'P10'),(500,145,2,'P11'),(745,165,2,'P12'),
   (475,110,2,'P13')])

rodar('CASO 2 — Modulo 1600',
  [(800,500,2,'Lateral'),(1570,500,1,'BaseInf'),(1570,500,1,'Tampo'),
   (770,500,1,'Divisoria'),(770,500,4,'Prateleira'),(1600,100,1,'FrenteBase'),
   (470,100,2,'LatBase'),(1570,100,1,'Travessa'),(1570,80,1,'CanaletaSup'),
   (1570,80,1,'CanaletaInf')])

rodar('TESTE VEIO (rotacao proibida)',
  [(400,1200,4,'PortaVeio'),(300,800,4,'LateralVeio')], rot=False)
