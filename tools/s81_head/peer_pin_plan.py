#!/usr/bin/env python3
"""Base-port pin windows priced against every actual CLOSED C peer pin rectangle."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
from child_lint import parse_lef
from split_ctl_peer import PORTS
def plan(width):
 m=parse_lef((ROOT/'physical/s81_ph_views/closed/dsfd_mtp_seq_c/dsfd_mtp_seq.lef').read_text())
 left=-129.6;right=87.264;ranges={};rows=[]
 for dr,w,n,net in PORTS:
  if n=='f_rd':lo,hi=-86.832,-.432
  elif n=='t_td':lo,hi=.432,86.832
  elif n in ('f_tg','t_acc'):
   lo=right;hi=lo+w*.1728;right=hi+.3456
  else:
   lo=left;hi=lo+w*.1728;left=hi+.3456
  rs=[r for name,p in m['pins'].items() if name==n or name.startswith(n+'[') for r in p['rects']]
  assert rs,n
  reach=max(max(abs(lo-((r[1]+r[3])/2-75.6)),abs(hi-((r[1]+r[3])/2-75.6)))+86.4+(r[2]+r[4])/2 for r in rs)
  assert reach<405,(n,reach)
  assert w/(hi-lo)<6,(n,w,hi-lo)
  ranges['seq_'+n]=[round(width/2+lo,4),round(width/2+hi,4)]
  rows.append(dict(port=n,bits=w,lo_um=lo,hi_um=hi,worst_manhattan_um=reach))
 return ranges,dict(schema='opentallas.head.peer-pin-plan.v1',glue_width_um=width,peer_size_um=151.2,gap_um=86.4,region='clctl',max_reach_um=max(r['worst_manhattan_um'] for r in rows),rows=rows,method='Every actual old-C LEF signal rectangle against its entire base-port pin window; source data cycles unchanged')
if __name__=='__main__':print(json.dumps(plan(float(sys.argv[1]))[1],indent=2))
