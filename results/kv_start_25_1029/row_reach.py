#!/usr/bin/env python3
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);s=json.load(open(r/'emitted/start_stages.json'));g=json.load(open(r/'native_graph.json'))
st={x['region']:x['rect_um'] for x in s['stages']}
t={x['part']:x['xy_um'] for x in json.load(open(r/'inputs/proof/tap_arrivals_TT.json'))['taps'] if x['port'].endswith('__clk')}
def rect(n):
    if n in st:return st[n]
    x,y=t[n];return[x,y,x,y]
def hop(a,b):return max(abs(a[x]-b[u])+abs(a[y]-b[v]) for x in (0,2) for y in(1,3) for u in(0,2) for v in(1,3))
rows=[dict(src=x['src'],dst=x['dst'],hop_um=hop(rect(x['src']),rect(x['dst']))) for x in g['start_edges']]
result=dict(stages=len(st),edges=len(rows),max_hop_um=max(x['hop_um'] for x in rows),over405=[x for x in rows if x['hop_um']>405],clock_pin_reach_um=s['counts']['max_cell_to_stage_um'],native_endpoint_pin_delta_not_materialized=True)
(r/'row_reach.json').write_text(json.dumps(result,indent=1));print(json.dumps({k:v for k,v in result.items() if k!='over405'}), 'over405=',len(result['over405']))
