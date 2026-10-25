import json,glob,collections
rows=[]
for f in glob.glob('*.jsonl'):
    for l in open(f):
        try: rows.append(json.loads(l))
        except: pass
rows=[r for r in rows if '/wt/' not in r['f'] and '/results/geom' not in r['f']]
signed=set(r['name'] for r in rows if r['verdict']=='SIGNED')
by=collections.defaultdict(list)
for r in rows: by[r['name']].append(r)
out=[]
for n,rs in by.items():
    if n in signed: continue
    rs.sort(key=lambda r:r['mtime'])
    last=rs[-1]
    cand=[r for r in rs if r['setup'] is not None and r['hold'] is not None and r['setup']>=-30 and r['hold']>=-30 and (r['drc'] or 0)<=50 and r['fg']=='PASS' and r['sdc']=='PASS']
    if not cand: continue
    best=max(cand,key=lambda r:r['mtime'])
    out.append((best,len(rs),last['mtime']))
for b,nr,lm in sorted(out,key=lambda x:x[0]['f']):
    print(f"{b['host']}\t{b['mtime']}\t{b['name']}\tS {b['setup']}/{b['setup_n']}\tH {b['hold']}/{b['hold_n']}\tdrc {b['drc']}\tdrv {b['drv']} {b['drvf'] if b['drv']!='PASS' else ''}\tclk {b['clock']}\tcells {b['cells']}\truns {nr} last {lm}\t{b['f']}")
print(len(out))
