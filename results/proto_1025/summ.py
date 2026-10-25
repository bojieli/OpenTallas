import json,subprocess,sys,collections
R='/srv/opentallas-scratch2/claude/proto1025'
for die,geo in (('s81_head','s81_head'),('qwen_compute','qwen_compute'),('qwen_kvsys','qwen_kvsys'),('B2n','B2n'),('s81','s81')):
    g=json.load(open(f'{R}/geom/{geo}.json'))['types']
    try: r=json.load(open(f'{R}/res_{die}.json'))
    except Exception: r={}
    cls=collections.defaultdict(list)
    for t,v in g.items():
        if v['verdict']=='FAIL': cls['STRUCTURAL-geom'].append(t); continue
        c=r.get(t,{}).get('classify',{}).get('cls','PENDING')
        if c=='NOT RUN': c='PENDING'
        cls[c].append((t,r.get(t,{}).get('classify',{}).get('why','')) if c not in('CLEAN','PENDING') else t)
    print(f"## {die}: "+", ".join(f"{k} {len(v)}" for k,v in sorted(cls.items())))
    print("CLEAN:", " ".join(sorted(cls['CLEAN'])))
    for k in ('HOTSPOT','STRUCTURAL'):
        for t,w in cls.get(k,[]): print(f"{k}: {t}: {w[:200]}")
    print("PENDING:", " ".join(sorted(cls['PENDING'])))
