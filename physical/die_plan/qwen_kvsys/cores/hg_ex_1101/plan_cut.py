#!/usr/bin/env python3
"""Common zero-cycle EX hard cut for the eight HG types; leaves their external ABI unchanged."""
import argparse,copy,json
from pathlib import Path
MODULE='qkd_astk_ex_s'
OUTLINE=[95.04,190.08]
SLOTS=[([235.008,682.56],'R0'),([235.008,889.92],'R0'),([554.688,864.0],'R0'),([874.368,813.888],'MY')]
PIN_FILE='pins/qkd_astk_ex_s_hg1101.json'
def inside(x,y,r,pad=0):
 a,b,w,h=r;return a-pad<=x<=a+w+pad and b-pad<=y<=b+h+pad
def pins():
 ps=[dict(name='ck',layer='M5',x=47.544,y=95.04),dict(name='rst_n',layer='M4',x=94.944,y=95.016)]
 ps += [dict(name=f'xa[{i}]',layer='M4',x=94.944,y=round(78.024+.192*i,3)) for i in range(66)]
 ps += [dict(name=f'xe[{i}]',layer='M4',x=.096,y=round(100.008+.192*i,3)) for i in range(34)]
 return dict(schema='opentallas.die_plan.core_pins.v1',core=MODULE,frame='core R0 origin(0,0),95.04x190.08',source='HG-EX common cut1101; exact existing xa/xe boundary; 0 added cycles',faces={'E':dict(pins=67,layers=['M4']),'W':dict(pins=34,layers=['M4'])},pins=ps)
def apply(p):
 p=copy.deepcopy(p);types=[]
 for tn,t in p['partition_types'].items():
  leaves=[c for c in t.get('contents',[]) if c.get('module')==MODULE]
  if not leaves:continue
  assert len(leaves)==4,(tn,len(leaves));types.append(tn)
  assert not any(h['module']==MODULE for h in t.get('hard_cores',[])),f'already cut: {tn}'
  rects=[]
  for k,(c,(xy,orient)) in enumerate(zip(leaves,SLOTS)):
   inst=c['inst'];physical='u_bound.u_'+inst.replace('__','_');rects.append([*xy,*OUTLINE])
   t.setdefault('hard_cores',[]).append(dict(inst=inst,module=MODULE,origin_um=[round(int((v+1e-6)/8.64)*8.64,3) for v in xy],track_offset_um=[round(v-round(int((v+1e-6)/8.64)*8.64,3),3) for v in xy],outline_um=OUTLINE,orient=orient,halo_um=1.728,pins_file=PIN_FILE,physical_inst=physical,physical_master=MODULE,note=f'HG-EX1101 common native leaf{k}; mapped81000cells/10612um2; no RTL change or extra cycle; view PENDING, parent route held'))
   cx=OUTLINE[0]-47.544 if orient=='MY' else 47.544
   t['clock'].setdefault('taps',[]).append(dict(name=inst+'.ck',kind='core',xy=[round(xy[0]+cx,3),round(xy[1]+95.04,3)],insertion_ps=250.0,insertion_ff_ps=202.5,budget_owner='plan estimate HG-EX1101; not SIGNED; actual leaf view required'))
  ft=next(s for s in t['ft_slots'] if s['name']=='ft2');assert ft['stations']==5 and abs(ft['regs_um'][3][1]-912.06)<.01,(tn,ft)
  old=ft['regs_um'][3][1];ft['regs_um'][3][1]=1010.88
  for point in ft['bit_sites_um'][2]:point[1]=round(point[1]+1010.88-old,3)
  # Existing island shapes under the newly hardened logic cannot remain die-top drivers.
  # Parent infra and clocks must be regenerated before its prototype/release; this delta is not a freeze.
  ck=t['clock'];islands=ck.get('die_islands_um',[])
  ck['die_islands_um']=[r for r in islands if not any(inside((r[0]+r[2])/2,(r[1]+r[3])/2,q) for q in rects)]
  t['note']+=' | HG-EX1101: 4 common native EX hard cuts; parent<=235487 mapped instances, 0 extra cycles; ft2 stage3 y912.06->1010.88 (402.84/205.2um); parent clock regeneration and actual views pending'
 return p,types
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('plan');a.add_argument('out');a=a.parse_args();p,ts=apply(json.load(open(a.plan)));o=Path(a.out);o.write_text(json.dumps(p,indent=1)+'\n');q=o.parent/PIN_FILE;q.parent.mkdir(exist_ok=True);q.write_text(json.dumps(pins(),indent=1)+'\n');print('HG_EX_CUT',len(ts),ts)
