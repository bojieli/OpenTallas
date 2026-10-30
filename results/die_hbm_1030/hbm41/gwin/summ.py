#!/usr/bin/env python3
"""Summarise windowed GRT probes: per-layer overflow table from grt.log (final GRT resource table), runtime."""
import re,glob,os,json
rows=[]
for d in sorted(x.rstrip('/') for x in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),'w?_d38?_i*/'))):
    L=open(d+'/grt.log').read() if os.path.exists(d+'/grt.log') else ''
    ex=open(d+'/probe.exit').read().strip() if os.path.exists(d+'/probe.exit') else 'RUNNING'
    lay={m.group(1):int(m.group(2)) for m in re.finditer(r'^(M\d)\s+\d+\s+\d+\s+[\d.]+%\s+\d+ /\s*\d+ /\s*(\d+)',L,re.M)}
    tot=re.search(r'^Total\s+\d+\s+\d+\s+[\d.]+%\s+(\d+) /\s*(\d+) /\s*(\d+)',L,re.M)
    it=re.findall(r'extra iteration (\d+)/',L); s=re.search(r'OT_GRT_S (\d+)',L)
    rows.append(dict(probe=os.path.basename(d),exit=ex,iters_done=int(it[-1]) if it else 0,grt_s=int(s.group(1)) if s else None,
                     total_ov=int(tot.group(3)) if tot else None,maxHV=(int(tot.group(1)),int(tot.group(2))) if tot else None,layers=lay))
for r in rows: print(r['probe'],r['exit'],'it',r['iters_done'],'s',r['grt_s'],'TOTAL',r['total_ov'],'maxH/V',r['maxHV'],r['layers'])
json.dump(rows,open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'summary.json'),'w'),indent=1)
