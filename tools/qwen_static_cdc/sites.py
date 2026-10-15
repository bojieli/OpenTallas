#!/usr/bin/env python3
"""Place the actual twelve static channels in the retained C14 IO CDC slot.

This emits physical child homes and actual port-to-leaf bindings, not an
aggregate area substitution. Clock phi-R values remain absent until each
clock of the actual native leaf has a measured CLOSED view.
"""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PAIR=[('up','dp'),('ur','dr'),('sx0','sr0'),('sx1','sr1'),('sx2','sr2'),('seq','cq')]
FRAME=dict(x=15925.68,y=21.6,w=700.248,h=1563.816)

def build():
 rtl=(ROOT/'rtl/physical/ot_qfd_io_xfifo_static.sv').read_text()
 actual=re.findall(r'qfd_static_ch546 u_(\w+)\s*\(',rtl)
 assert set(actual)=={n for pair in PAIR for n in pair} and len(actual)==12
 pins=json.loads((ROOT/'physical/ref_tile/qfd_static_ch546/assigned_pins.json').read_text())
 assert pins['outline']=={'w':233.28,'h':151.2}
 sites=[]
 for row,pair in enumerate(PAIR):
  for col,ch in enumerate(pair):
   x=[53.568,371.52][col];y=43.2+216*row
   width=int(re.search(r'input wire \[(\d+):0\] '+ch+r'_i_data',rtl)[1])+1
   item=dict(channel=ch,instance='u_'+ch,master='qfd_static_ch546',data_bits=width,
       local_bbox=[x,y,233.28,151.2],die_bbox=[round(FRAME['x']+x,3),round(FRAME['y']+y,3),233.28,151.2],orient='R0',ports={})
   for port,p in pins['ports'].items():
    face=p['face'];coords=p['positions_um'];clock=port in ('wck','rck')
    if face in ('W','E'):
     leaf_x=x+(233.28 if face=='E' else 0);parent_x=FRAME['w'] if face=='E' else 0
     dy=[-27.216,32.4][col]
     reach=abs(parent_x-leaf_x)+abs(dy)
     assert reach<500,(ch,port,reach)
     bound=dict(face=face,leaf_x=round(leaf_x,3),leaf_y_range=[round(y+min(coords),3),round(y+max(coords),3)],
       parent_x=parent_x,parent_y_range=[round(y+min(coords)+dy,3),round(y+max(coords)+dy,3)],manhattan_um=round(reach,3))
    else:
     bound=dict(face=face,die_entry=[round(FRAME['x']+x+coords[0],3),round(FRAME['y']+y+151.2,3)],
        qualification='needs actual die global-clock route and per-clock child insertion' if clock else 'needs actual die reset route')
    bound['parent_port']=ch+'_'+port
    bound['child_port']=port
    if clock:bound.update(phi_ps=None,R_ps=None)
    item['ports'][port]=bound
   sites.append(item)
 for i,a in enumerate(sites):
  x,y,w,h=a['local_bbox'];assert x>=0 and y>=0 and x+w<=FRAME['w'] and y+h<=FRAME['h']
  for b in sites[:i]:
   X,Y,W,H=b['local_bbox'];assert x>=X+W or X>=x+w or y>=Y+H or Y>=y+h,(a['channel'],b['channel'])
 # Distinct parent's W/E pin ranges even for both columns sharing each row.
 for face in ('W','E'):
  ranges=sorted((p['parent_y_range'][0],p['parent_y_range'][1],s['channel'],n) for s in sites for n,p in s['ports'].items() if p['face']==face)
  for a,b in zip(ranges,ranges[1:]):assert a[1]<b[0],(face,a,b)
 return dict(schema='opentallas.qwen.static-cdc-sites.v1',source_geometry='C14 smoke rom_tp8b.json io_xfifo',frame=FRAME,
  actual_rtl='rtl/physical/ot_qfd_io_xfifo_static.sv',channels=sites,containment='PASS12 nonoverlap inside retained frame',
  direct_data_command_reach='PASS each <500um; route congestion and RC pending',
  fixed_edges=dict(write_slot_to_sram_wck=1,read_slot_to_output_rck=3,reset_deassert_guard_each_domain=2),
  added_data_relays=0,added_data_relays_qualification='geometric direct reach only, requires actual route timing',
  clocks='24 actual scalar child roots; global clock routes, per-clock R, phi-R and compiler phase bindings OPEN',
  endpoint_composition='OPEN: actual static producer/consumer ports and compiler address/version calendar must replace legacy credit bindings')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=ROOT/'results/arch/qwen_static_cdc_1014/sites.json');a=ap.parse_args()
 d=build();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n')
 print('PASS actual12channel inventory/containment/nonoverlap/per-port reach;24clock phases and real endpoint binding remain OPEN')
