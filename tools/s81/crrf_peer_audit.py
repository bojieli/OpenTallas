#!/usr/bin/env python3
"""Audit proposed C0 output pins against actual first-ctile assigned pins.

Uses the v20 grant, not a claim that the canonical HC parent is regenerated.
No unplaced relay or capture-leaf home is invented.
"""
import argparse,hashlib,json
from pathlib import Path
import crrf_locality_candidate as C
R=C.R

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 contract=R/'results/arch/hier_contract_1011/s81_v20_hc.json'
 pins=R/'physical/s81_die_pins/v20_hc_inherited/ot_s81_hc_ctfn.json'
 cap=R/'physical/s81_die_pins/v20_hc_capture/ot_s81_hc_ctfx_cap.json'
 p=json.loads(contract.read_text());s={q['name']:q for q in p['slots']}
 src=s['sp_hc_s/crootr_c0/f'];root=s['sp_hc_s/crootr_c0'];cth=s['sp_hc_s/ctile_0']
 rows=p['sub_layouts']['ot_s81_hc_cth']['rows'];row=next(q for q in rows if q['tile']=='ctfn')
 fn=json.loads(pins.read_text());fx=json.loads(cap.read_text())
 source_xy=[root['origin']['x']+src['origin']['x'],root['origin']['y']+src['origin']['y']]
 target_xy=[cth['origin']['x'],cth['origin']['y']+cth['outline']['h']-row['y']]
 before,h=C.P.plans(True)['crrf'];after=C.remap(before)
 results={}
 for label,pp in [('before',before),('after',after)]:
  dic={n:(face,L,x) for face,n,L,x in pp};aa=[];bb=[]
  for i,(face,L,x,_) in enumerate(fn['ports']['fd_in']['per_bit']):
   q=dic[f'ch_fd[{i}]'];aa.append((source_xy[0]+q[2],source_xy[1],'S',q[1]));bb.append((target_xy[0]+x,target_xy[1],face,L))
  ll=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(aa,bb)]
  results[label]=dict(bits=len(ll),sum_bit_um=sum(ll),max_um=max(ll),bits_over_500um=sum(x>500 for x in ll),pin_alignment=C.PA.bundle(aa,bb))
 caprow=next(q for q in rows if q['tile']=='ctfx')
 files=[contract,pins,cap,R/'rtl/dsrom_sys/s81_suhc/dsfd_sp_hc.sv',R/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv',Path(__file__)]
 report=dict(scope='V20_ASSIGNED_PEER_GEOMETRY_NOT_CANONICAL_NATIVE_CLOSURE',source_sha256={str(q.relative_to(R)):hashlib.sha256(q.read_bytes()).hexdigest() for q in files},
  connection='crootr_c0/f.ch_fd[2919:0] -> first p0 C0 cth.fd_in -> u_fn.fd_in; additionally low1128bits fan out to u_fx.fd_in',
  source_local_to_sp_hc_s=source_xy,target_N_local_to_sp_hc_s=target_xy,gap_um=source_xy[1]-target_xy[1],**results,
  ctfx_cap=dict(actual_fd_in_bits=fx['ports']['fd_in']['bits'],assigned_outline_um=fx['outline_um'],existing_ctfx_row_um=[caprow['w'],caprow['h']],status='HOME_UNRESOLVED:25.92um capture leaf does not fit inherited12.96um row; no coordinate invented'),
  conclusion='Output-order change reduces external wire sum and pair crossing share too; direct source-to-peer still needs staged physical integration. No native route or timing pass claimed.',
  open=['Regenerate actual canonical HC parent and all source/peer relay homes','Resolve ctfx_cap grown home and exact native leaf pin versions','Rebind each bit using y_peer_rebind.csv and prove full parent fixed cycles','Use measured native pin launch/capture reach and delivered phi-R;500um is only geometric reference'])
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(results))
if __name__=='__main__':main()
