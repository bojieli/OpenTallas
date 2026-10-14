#!/usr/bin/env python3
"""Derive gather ctl direct E face from the assigned parent, plus explicit strip endpoint pins."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 a=argparse.ArgumentParser();a.add_argument('--assigned',required=True);a=a.parse_args();p=Path(a.assigned);x=json.loads(p.read_text());ports={};ox,oy=1598.4,8.64
 for n in ('f_vm','c_cmd','c_done','c_st','t_xgo','ck','ckv'):
  bits=x['ports'][n]['per_bit'][:160] if n=='f_vm' else x['ports'][n]['per_bit']
  ports[n]=[[f,l,round(c-oy,6),d] for f,l,c,d in bits]
  assert all(0<b[2]<43.2 for b in ports[n]),n
 for n,w,start,face in [('tc',163,12.108,'S'),('f_cd',12,30.06,'S'),('tst',24,42.156,'N'),('cs',16,45.036,'N'),('rc',8,47.004,'N'),('roots_ready',8,48.924,'N')]:
  ports[n]=[[face,'M5',round(start+.096*i,6),.192] for i in range(w)]
 ports['rst']=[['W','M4',3.468,.192]];ports['rsv']=[['W','M4',3.66,.192]]
 d=ROOT/'physical/s81_ph_views/gather/control_strip';d.mkdir(parents=True,exist_ok=True)
 record={'schema':'opentallas.s81.assigned_child_pins.v1','master':'dsfd_gth_ctl','parent_assigned_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'origin_um':[ox,oy],'outline_um':[129.6,43.2],'ports':ports,'rule':'E data pins exactly mirror assigned parent; strip endpoint pins are physical candidate to gate','qualification':'OPEN'}
 (d/'dsfd_gth_ctl.json').write_text(json.dumps(record,indent=2)+'\n');lines=['# Generated gather ctl pins from v18 parent assignment.']
 for n,bits in ports.items():
  for i,(f,l,c,_) in enumerate(bits):
   name=n if len(bits)==1 else f'{n}[{i}]';pos={'E':(129.558,c),'W':(.042,c),'N':(c,43.158),'S':(c,.042)}[f]
   lines.append(f'place_pin -pin_name {{{name}}} -layer {l} -location {{{pos[0]:.6f} {pos[1]:.6f}}} -force_to_die_boundary')
 (d/'dsfd_gth_ctl.tcl').write_text('\n'.join(lines)+'\n')
 spec=json.loads((ROOT/'tools/ref_tile/specs_s81gth/dsfd_gth_ctl.json').read_text());spec['io_tcl']=str((d/'dsfd_gth_ctl.tcl').relative_to(ROOT));spec['pins']={'E':['f_vm','c_cmd','c_done','c_st','t_xgo','ck','ckv'],'S':['tc','f_cd'],'N':['rc','cs','tst','roots_ready'],'W':['rst','rsv']};spec['recipe']=2;spec['inhold']=True;spec['outhold']=True;spec['io_flop_at_pins']={'cols':4};spec['job']['branch']='codex/s81-gather-strip-v18';spec['job']['owner']='Codex:s81-gather-strip';spec['job']['hold_merge']='Candidate assigned v18 ctl pins; full strip physical/bench/price gates pending';
 for b in spec['job']['benches']:b['cmd']='CONTROL_STRIP=1 DIE_CLOCKS=1 RESTART=1 '+b['cmd']
 spec['job']['extra_paths'].append('physical/s81_ph_views/gather/control_strip');spec['floorplan_why']='Actual129.6x43.2 ctl at1598.4,8.64 in61umstrip; direct Epins mirror authoritativev18 and registered strip endpoints remain pendingqualification';(ROOT/'tools/ref_tile/specs_s81gth/dsfd_gth_ctl_strip.json').write_text(json.dumps(spec,indent=2)+'\n');print('CTL_PINS candidate generated')
if __name__=='__main__':main()
