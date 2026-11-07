#!/usr/bin/env python3
# mkbatch.py host : plan -> batch (TRIM extras) + manifest
import json,sys,os,re
ROOT=os.environ.get('CP_ROOT','/tmp/cp1106')
h=sys.argv[1]; T=json.load(open(ROOT+'/plan/trim.json'))
os.makedirs(ROOT+'/manifest',exist_ok=True)
rows=[l.rstrip('\n').split('\t') for l in open(f'{ROOT}/plan/{h}.tsv')]
rows.sort(key=lambda r:-int(r[2]))
g=open(f'{ROOT}/plan/batch_{h}.tsv','w'); m=open(f'{ROOT}/manifest/CODEX-PRUNE-1-{h}.tsv','w')
m.write('path\tGB\tclass\tfiles\tnewest\treason\n'); tot={}
for p,a,b,f,n,mt,w in rows:
    tot[a]=tot.get(a,0)+int(b)
    m.write('\t'.join((p,'%.2f'%(int(b)/1e9),a,f,mt,w))+'\n')
    if a in('DELETE','GITRM'): g.write(f'{p}\t{a}\t\n')
    elif a=='TRIM':
        keep=[]
        k=T['trimkeep'].get(p)
        if k: keep.append(k[0])
        ev=T['open'][p][4]; ev=ev.split(':',1)[-1] if ev[:1]!='/' else ev
        if os.path.normpath(ev)!=p: keep.append(ev)
        g.write(f'{p}\tTRIM\t{json.dumps(dict(keep=keep))}\n')
print(h,{k:round(v/1e9,1) for k,v in tot.items()})
