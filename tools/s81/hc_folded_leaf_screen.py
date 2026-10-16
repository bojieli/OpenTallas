#!/usr/bin/env python3
"""Expand a pinned literal NT parent into64 folded CTH groups, without fake leaf views."""
import argparse,copy,gzip,hashlib,json,math,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--parent',required=True);p.add_argument('--parent-commit',required=True);a=p.parse_args();ip=Path(a.inventory);d=json.loads(ip.read_text());raw=Path(a.parent).read_bytes();parent=json.loads(raw);pw,ph=parent['outline_um'];assert parent['overlap_count']==0
 views=d['historical_real_views'];options=[]
 for cols in [4,6,8]:
  gap=43.2;rows=math.ceil(64/cols);groups=[];leaves=[]
  # Consecutive logical IDs run down a column. No implied mirror/clock ABI.
  for i in range(64):
   col,row=divmod(i,rows);x=col*(pw+gap);y=(rows-row-1)*(ph+gap)
   groups.append(dict(id=i,origin_um=[x,y],outline_um=[pw,ph],orient='R0'))
   for n in parent['instances']:
    exact=[v for v in views if v['cell']==n['cell'] and abs(v['outline_um'][0]-n['w'])<.025 and abs(v['outline_um'][1]-n['h'])<.025]
    leaves.append(dict(name=f'cth{i}/'+n['name'],cell=n['cell'],origin_um=[x+n['x'],y+ph-n['y_from_N']-n['h']],outline_um=[n['w'],n['h']],orient='R0',params=n.get('params',{}),candidate_real_views=exact,source_status=n['instantiation_status'],binding_status='UNSELECTED_CANDIDATE_VIEWS' if exact else 'NO_MATCHING_REAL_VIEW',clock_binding='OPEN: select exact child root and phi-R from selected native view'))
  width=cols*pw+(cols-1)*gap;height=rows*ph+(rows-1)*gap
  assert len(leaves)==64*len(parent['instances'])
  # Exact independent overlap check within each group; groups are disjoint.
  for i,g in enumerate(groups):
   ls=leaves[i*len(parent['instances']):(i+1)*len(parent['instances'])]
   for j,u in enumerate(ls):
    x,y=u['origin_um'];w,h=u['outline_um']
    assert x>=g['origin_um'][0] and y>=g['origin_um'][1]-.001 and x+w<=g['origin_um'][0]+pw+.001 and y+h<=g['origin_um'][1]+ph+.001
    for v in ls[:j]:
     xx,yy=v['origin_um'];ww,hh=v['outline_um'];assert not(x<xx+ww-.001 and x+w>xx+.001 and y<yy+hh-.001 and y+h>yy+.001)
  options.append(dict(columns=cols,rows=rows,outline_um=[round(width,3),round(height,3)],cth_groups=groups,leaf_count=len(leaves),leaves=leaves,overlap_count=0,view_gaps=sorted(set(n['cell'] for n in leaves if not n['candidate_real_views'])),qualification='HELD ENGINEERING GEOMETRY. Not die/source/clock/calendar qualification.'))
 report=dict(parent_source=dict(commit=a.parent_commit,path=a.parent,sha256=hashlib.sha256(raw).hexdigest()),source_inventory_commit=d['source_commit'],literal_cth_outline_um=[pw,ph],options=options,residual_components=['crooty/crootr, combCCF/pads and controller must be packed from source-current actual leaves along VM+collective-facing side; these are not included in64CTH envelope.','Collective8192bY, VM5401b, HC_s-HC_t15660b need actual source/current per-bit joins at each folded turn.','Every new column turn can require explicit physical relay stages; no static schedule latency is inherited.','Literal NT candidate is held and source/current CTH elaboration binding remains OPEN.','CTNL/CTPL/return/NT native-view variants cannot be selected just from size matches.'],adoption='Owner review Explorer candidate, then actual source-bound realviews/fulltrial required; no adoption by this screen.')
 (ip.parent/'folded_hc_leaf_options.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps([dict(columns=o['columns'],rows=o['rows'],outline_um=o['outline_um'],leaves=o['leaf_count'],view_gaps=o['view_gaps']) for o in options]))
if __name__=='__main__':main()
