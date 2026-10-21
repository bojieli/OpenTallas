#!/usr/bin/env python3
"""Selected72-frame floorplan construction preserving the existing2x8 service hierarchy.
No hard outline shrink or rotation. Normal frame/return/HBM lanes use existing relay families.
"""
import argparse,copy,json
from pathlib import Path

def construct(template):
 d=copy.deepcopy(template);allb={b['name']:b for b in d['rectangles']+d['fixed']};bs=[]
 def put(name,x,y):
  b=copy.deepcopy(allb[name]);b.update(x=round(x,6),y=round(y,6));bs.append(b)
 # Five seven-frame columns per side; the two remaining h10s sit above the SerDes strips.
 # Keep edge area free by moving unchanged SerDes columns into the wide inner side streets.
 fw=1436.832;gap=86.4;pitch=fw+gap;h9=3369.6;h10=3672.;n9=n10=0
 for side in range(2):
  for c in range(5):
   x=86.4+c*pitch;x=x if side==0 else 32000-x-fw;y=86.4
   for row in range(7):
    if row==3:name=f'h10_{n10:02}';n10+=1;h=h10
    else:name=f'h9_{n9:02}';n9+=1;h=h9
    put(name,x,y);y+=h+gap
 xextra=86.4+5*pitch;linkstart=2000.;lpitch=3596.4+gap;extra_y=linkstart+4*3596.4+3*gap+172.8
 for side in range(2):
  xe=xextra if side==0 else 32000-xextra-fw
  put(f'h10_{n10:02}',xe,extra_y);n10+=1
  lx=xextra if side==0 else 32000-xextra-259.2
  for j in range(4):put(f'link_{side}_{j}',lx,linkstart+j*lpitch)
 assert(n9,n10)==(60,12)
 # Existing service adjacency: evens lower, odds upper, preserving every named wide-bus face.
 sw,sh=1728.,3758.4;gw=8*sw+7*gap;gx=(32000-gw)/2;gy=1846.4
 for i in range(16):put(f'svc_full_{i}',gx+(i//2)*(sw+gap),gy+(i%2)*(sh+gap))
 # Twelve real normal slices and four conservatively enlarged MU parents above the service group.
 sx=xextra+fw;sy=gy+2*sh+gap+86.4;vp=6825.6+gap
 for i in range(12):put(f'slice_{i:02}',sx+(i//2)*(1252.8+gap),sy+(i%2)*vp)
 ex=sx+6*(1252.8+gap)
 for i in range(4):put(f'end_parent_{i}',ex+(i//2)*(2764.8+gap),sy+(i%2)*vp)
 # Independent small units use the remaining top/inner streets; no understated old void slots.
 put('bk_sel_00',xextra,extra_y+h10+172.8)
 top=sy+2*6825.6+gap+172.8
 for i in range(8):put(f'idx_{i:02}',sx+i*(1036.8+gap),top)
 xx=sx+8*(1036.8+gap)
 for name in('gunit_00','seqhost_00','bk_col_00','iqf_00'):
  put(name,xx,top);xx+=allb[name]['w']+gap
 for b in d['fixed']:
  if b['name'].startswith('link_'):continue
  put(b['name'],b['x'],b['y'])
 assert len(bs)==len(allb),(len(bs),len(allb))
 assert len({b['name']for b in bs})==len(bs)
 for i,b in enumerate(bs):
  assert min(b['x'],b['y'])>=0 and b['x']+b['w']<=32000 and b['y']+b['h']<=25000,b
  for c in bs[i+1:]:
   assert min(b['x']+b['w'],c['x']+c['w'])<=max(b['x'],c['x']) or min(b['y']+b['h'],c['y']+c['h'])<=max(b['y'],c['y']),(b['name'],c['name'])
 return dict(scope='OWNER72 SELECTED IMPLEMENTATION CONSTRUCTION, not routed closure',die=[32000,25000],clearance=gap,best=dict(blocks=bs,unplaced=[],trial=dict(strategy='graph-aware selected construction',placed=len(bs),unplaced=0)),service_group=dict(at=[gx,gy],outline=[gw,2*sh+gap],order='even lower/odd upper; original sgN/S/E/W faces'),obligations=['MU parents actual child/source reassembly','service parent source and clocks/reset integration','actual pin projection and existing relay station legalization/cycle pricing','currentGU72 capacity/map pending'])
def main():
 a=argparse.ArgumentParser();a.add_argument('template');a.add_argument('out');v=a.parse_args();d=construct(json.load(open(v.template)));Path(v.out).write_text(json.dumps(d,indent=1));print('SELECTED72_CONSTRUCTED',len(d['best']['blocks']))
if __name__=='__main__':main()
