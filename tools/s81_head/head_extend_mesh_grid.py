"""Extend existing HEAD M9 conductors to the published peripheral grid roots.

Retains every X, M8 row, driver, stage, and width. Reports added geometry/RC;
PG clearance is checked against the current plan, while PHY upper metal remains
an explicit integration assumption requiring actual abstract review.
"""
import argparse,json,sys
from pathlib import Path

def main():
 a=argparse.ArgumentParser();a.add_argument('--tools',required=True);a.add_argument('--plan',required=True);a.add_argument('--straps',required=True);a.add_argument('--endpoints',required=True);a.add_argument('--out',required=True);x=a.parse_args();sys.path.insert(0,x.tools)
 import schema as S,die_infra as DI,die_clock as DC,die_clock_mesh as D
 p=S.Plan(S.load(x.plan));ss=json.loads(Path(x.straps).read_text());ep=json.loads(Path(x.endpoints).read_text())['endpoints'];o=Path(x.out);o.mkdir(parents=True,exist_ok=True)
 grid=[e for e in ep if e['kind']=='published_grid_clock'];ys=[e['die_xy_um'][1] for e in grid];lo,hi=min(ys),max(ys)
 if lo<0 or hi>p.H:raise ValueError('grid outside die outline')
 pg=[z for z in DI.pg_rects(p,DI.pg_grid(p,None)) if z[1]=='M9'];added=[];conf=[];new=[];nd=D.NDR['8w'];half=nd['width']/2;off=nd['width']+nd['space']
 for row in ss:
  z=list(row)
  if z[0]=='M9':
   c,y0,y1=z[1:4];z[2]=min(y0,lo);z[3]=max(y1,hi)
   spans=[]
   if z[2]<y0:spans.append((z[2],y0))
   if z[3]>y1:spans.append((y1,z[3]))
   for aa,bb in spans:
    added.append(dict(x=c,y0=aa,y1=bb,length_um=bb-aa))
    for role,cc in [('clock',c),('shield_w',c-off),('shield_e',c+off)]:
     for net,layer,x0,a0,x1,a1 in pg:
      if min(bb,a1)-max(aa,a0)<=0:continue
      gap=max(x0-(cc+half),(cc-half)-x1)
      # Wide PG spacing threshold: same 1um used by current shared guard.
      if gap<1.0-1e-6:conf.append(dict(x=c,role=role,pg=net,pg_rect=[x0,a0,x1,a1],gap_um=gap))
  new.append(z)
 length=sum(z['length_um'] for z in added);r,c=DC.LAYER_RC['M9'];cap=length*c*nd['cf'];power=cap*1e-15*.7*.7/(833e-12)
 crossings=lambda rows:sum(h[2]<=v[1]<=h[3] and v[2]<=h[1]<=v[3] for h in rows if h[0]=='M8' for v in rows if v[0]=='M9')
 receipt=dict(status='FAIL_PG_CLEARANCE' if conf else 'PLANNED_PG_CLEAR_PHY_ABSTRACT_PENDING',m9_columns=sum(z[0]=='M9' for z in new),grid_endpoint_y_range=[lo,hi],added_segments=added,added_signal_wire_um=length,added_shield_wire_um=2*length,added_clock_cap_ff=cap,added_clock_dynamic_w_at_0p7v_833ps=power,added_signal_resistance_sum_kohm=length*r*nd['rf'],mesh_vias_before=crossings(ss),mesh_vias_after=crossings(new),pg_width_spacing_um=1.0,pg_conflicts=conf,assumptions=['unchanged current mesh M9 X phase; 8w signal and two same-width VSS shields','PHY abstract must permit M9 overflight at these X columns; actual abstract not yet certified','added capacitance is diagnostic RC table wire load; no signoff or CPPR claim'])
 (o/'straps.json').write_text(json.dumps(new)+'\n');(o/'extension_receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(10,10))
 for l,q,aa,bb,*_ in ss:ax.plot([aa,bb] if l=='M8' else [q,q],[q,q] if l=='M8' else [aa,bb],color='#aec4d1',lw=.3)
 for z in added:ax.plot([z['x']]*2,[z['y0'],z['y1']],color='#d76a1b',lw=.65)
 ax.scatter([e['die_xy_um'][0] for e in grid],[e['die_xy_um'][1] for e in grid],s=1,color='#174d75');ax.set(xlim=(0,p.W),ylim=(0,p.H),aspect='equal',title='HEAD mesh: added M9 extensions (orange), published grid roots (blue)');fig.tight_layout();fig.savefig(o/'extension.png',dpi=150)
 print(json.dumps({k:v for k,v in receipt.items() if k not in ('added_segments','pg_conflicts')}));print('PG conflicts',len(conf));return 2 if conf else 0
if __name__=='__main__':sys.exit(main())
