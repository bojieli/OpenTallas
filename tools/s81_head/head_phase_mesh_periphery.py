"""COPY candidate: bridge core/PHY PG phases with real M8 boundary jogs.

No buffers/stages removed or added. All conductor crossings become VIA89 in the
existing explicit-mesh graph. Actual RCX/PHY abstracts and clock-metal/shield
census remain trial gates. Wide PG clearance is 1um without relaxation.
"""
import argparse,json,sys,math
from pathlib import Path

def main():
 a=argparse.ArgumentParser();a.add_argument('--tools',required=True);a.add_argument('--plan',required=True);a.add_argument('--straps',required=True);a.add_argument('--endpoints',required=True);a.add_argument('--out',required=True);x=a.parse_args();sys.path.insert(0,x.tools)
 import schema as S,die_infra as DI,die_clock as DC,die_clock_mesh as D,explicit_clock_mesh as E
 p=S.Plan(S.load(x.plan));ss=json.loads(Path(x.straps).read_text());ep=json.loads(Path(x.endpoints).read_text())['endpoints'];o=Path(x.out);o.mkdir(parents=True,exist_ok=True)
 pg=DI.pg_rects(p,DI.pg_grid(p,None));grid=[e for e in ep if e['kind']=='published_grid_clock'];lo=min(e['die_xy_um'][1] for e in grid);hi=max(e['die_xy_um'][1] for e in grid)
 # Domain boundary is from actual plan, not a guessed row phase.
 domains=p.die['pg']['domains'];r=[d['rect_um'] for d in domains if d.get('name','').startswith('phy_')]
 lower=max(z[3] for z in r if z[1]<=lo<=z[3]);upper=min(z[1] for z in r if z[1]<=hi<=z[3])
 nd=D.NDR['8w'];envelope=1.5*nd['width']+nd['space'];gap=1.0;errors=[];new=[list(z) for z in ss if z[0]=='M8'];bridges=[]
 def candidates(ideal,limit=8.64):
  k=round((ideal-.04)/.08);return sorted((.04+.08*j for j in range(k-int(limit/.08),k+int(limit/.08)+1)),key=lambda t:(abs(t-ideal),t))
 def clear(l,c,aa,bb):
  return all(max(q0-(c+envelope),(c-envelope)-q1)>=gap-1e-6 for n,lay,x0,y0,x1,y1 in pg if lay==l for q0,q1,a0,a1 in [(x0,x1,y0,y1) if l=='M9' else (y0,y1,x0,x1)] if min(bb,a1)-max(aa,a0)>1e-6)
 for row in (z for z in ss if z[0]=='M9'):
  _,xx,oldlo,oldhi,*tail=row;parts=[]
  for side,edge,target in [('bottom',lower,lo),('top',upper,hi)]:
   # Boundaries sit in the actual PG-domain transition gap, on legal M8 tracks.
   yy=next((v for v in candidates(edge,3.0) if clear('M8',v,xx-8.64,xx+8.64)),None)
   if yy is None:errors.append(dict(kind='no_boundary_M8',x=xx,side=side));continue
   aa,bb=sorted([yy,target]);near=[z for z in pg if z[1]=='M9' and min(bb,z[5])-max(aa,z[3])>1e-6 and z[2]<xx+10.5 and z[4]>xx-10.5]
   def ok(v):return all(max(z[2]-(v+envelope),(v-envelope)-z[4])>=gap-1e-6 for z in near)
   nx=next((v for v in candidates(xx) if ok(v)),None)
   if nx is None:errors.append(dict(kind='no_peripheral_M9',x=xx,side=side));continue
   parts.append((side,yy,nx,target));new.append(['M9',nx,aa,bb,'phy_phase_extension'])
   if abs(nx-xx)>1e-6:new.append(['M8',yy,min(xx,nx),max(xx,nx),'pg_phase_bridge'])
   bridges.append(dict(side=side,old_x=xx,new_x=nx,y=yy,target_y=target,dx=nx-xx))
  yl=min([oldlo]+[z[1] for z in parts]);yh=max([oldhi]+[z[1] for z in parts]);new.append(['M9',xx,yl,yh,*tail])
 # Verify full actual geometry including old-X extension segments to transition.
 new_signal=[]
 for z in new:
  if z[0]=='M8' and z[-1]=='pg_phase_bridge':new_signal.append(z)
  elif z[0]=='M9':
   old=next((q for q in ss if q[0]=='M9' and q[1]==z[1]),None)
   if old is None:new_signal.append(z)
   else:
    if z[2]<old[2]:new_signal.append(['M9',z[1],z[2],old[2]])
    if z[3]>old[3]:new_signal.append(['M9',z[1],old[3],z[3]])
 for l,c,aa,bb,*_ in new_signal:
  if not clear(l,c,aa,bb):errors.append(dict(kind='new_segment_PG_clearance',segment=[l,c,aa,bb]))
 mesh=dict(M8=[dict(y=z[1],x0=z[2],x1=z[3]) for z in new if z[0]=='M8'],M9=[dict(x=z[1],y0=z[2],y1=z[3]) for z in new if z[0]=='M9'],drivers=[],taps=[])
 mesh['vias']=[dict(x=v['x'],y=h['y']) for h in mesh['M8'] for v in mesh['M9'] if h['x0']<=v['x']<=h['x1'] and v['y0']<=h['y']<=v['y1']]
 graph=E.conductor_graph(mesh);length=sum(z[3]-z[2] for z in new)-sum(z[3]-z[2] for z in ss);cap=sum((z[3]-z[2])*DC.LAYER_RC[z[0]][1]*nd['cf'] for z in new_signal)
 receipt=dict(status='FAIL' if errors else 'COPY_GEOMETRY_PG_PASS_PHY_ABSTRACT_PENDING',errors=errors,bridge_count=len(bridges),bridges=bridges,mesh_vias=len(mesh['vias']),components=graph['connected_components'],added_signal_um=length,added_shield_um=2*length,added_wire_cap_ff=cap,added_clock_dynamic_w_0p7v_833ps=cap*1e-15*.49/833e-12,scope='COPY physical mesh only; actual shield tie/cross-clock census, PHY abstract M9 permission, RCX and STA required')
 for name,data in [('straps',new),('phase_receipt',receipt)]: (o/(name+'.json')).write_text(json.dumps(data,indent=1)+'\n')
 print(json.dumps({k:v for k,v in receipt.items() if k not in ('errors','bridges')}));print('errors',errors[:5]);return 2 if errors else 0
if __name__=='__main__':sys.exit(main())
