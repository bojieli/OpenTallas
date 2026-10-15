#!/usr/bin/env python3
"""Build only a proposed S/M3 output-pin correction for the measured grown parent.
All actual native/PG/timing/route and current GEN source adoption remain required.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'s81_suhc'))
from nt_bottom_pairs import pins
p=argparse.ArgumentParser();p.add_argument('--contract',type=Path,required=True);p.add_argument('--source-lef',type=Path,required=True);p.add_argument('--sink-lef',type=Path,required=True);p.add_argument('--assigned',type=Path,required=True);p.add_argument('--assigned-tcl',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
x=json.loads(a.contract.read_text())['sub_layouts']['ot_s81_hc_cth'];rows={q['tile']:q for q in x['rows']};H=x['outline']['h'];src=pins(a.source_lef);dst=pins(a.sink_lef);plan=json.loads(a.assigned.read_text());assert plan['outline_um']==[576.72,51.84];sy=H-rows['ctfx']['y']-51.84;tcl=a.assigned_tcl.read_text();occupied=set();moves=[];checks=[]
for sp,dp,count in [('fdx_local','fdx',1128),('fv_local','fv',7)]:
 for bit in range(count):
  source=f'{sp}[{bit}]';sx,syp=src[source];dx,dyp=dst[f'{dp}[{bit}]'];lo=.012;hi=576.708;targets=[]
  for gx in x['x_cols']:
   for half in [0,1]:
    row=rows[f'ctpl[g][half{half}]'];dy=H-row['y']-row['h'];rad=499.8-abs(sy+syp-dy-dyp);lo=max(lo,gx+dx-rad);hi=min(hi,gx+dx+rad);targets.append((gx+dx,dy+dyp))
  choices=[round(.012+.048*n,3) for n in range(math.ceil((lo-.012)/.048),math.floor((hi-.012)/.048)+1) if round(.012+.048*n,3) not in occupied];assert choices,(source,'no free actualtrack',lo,hi);new=min(choices,key=lambda v:abs(v-sx));occupied.add(new)
  old=plan['ports'][sp]['per_bit'][bit];assert old[:2]==['S','M3'];assert abs(old[2]-sx)<.024,(source,old,sx)
  if abs(new-sx)>.024:
   moves.append(dict(port=source,old_x_um=sx,new_x_um=new,delta_um=round(new-sx,4)));old[2]=new
   lines=tcl.splitlines();hits=[i for i,l in enumerate(lines) if ('-pin_name {'+source+'}') in l];assert len(hits)==1;lines[hits[0]]=f'place_pin -pin_name {{{source}}} -layer M3 -location {{{new:.3f} 0.042}} -force_to_die_boundary';tcl='\n'.join(lines)+'\n'
  checks.extend(abs(new-tx)+abs(sy+syp-ty) for tx,ty in targets)
assert max(checks)<=499.8+1e-6
plan['case']='norm_margin_CAP_REPIN_UNADOPTED';plan['qualification']='UNADOPTED geometry candidate only; native model/routedpin/PG/clock/TTFFDRC and actualGENsource remainrequired';plan['source']='tools/s81_norm_physical/cap_repin_candidate.py'
(a.out/'ot_s81_hc_ctfx_cap.json').write_text(json.dumps(plan,indent=1)+'\n');(a.out/'ot_s81_hc_ctfx_cap.tcl').write_text(tcl)
receipt=dict(scope='Geometric candidate only; all actualconnectedCPLinputs included, no timingorclockqualification',moves=moves,hops=len(checks),worst_um=max(checks),hashes={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [a.contract,a.source_lef,a.sink_lef,a.assigned,a.assigned_tcl]});(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(len(moves),'moves;',len(checks),'hops; worst',max(checks),'um')
