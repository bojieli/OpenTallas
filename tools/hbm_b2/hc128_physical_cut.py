#!/usr/bin/env python3
"""Extract native W128 HC pair tiles without changing arithmetic or register depth.
Consumes the elaborated native128.json (proc/flatten, HC lane leaves retained,
splitcells) and emits a Yosys submod script plus a counted physical contract.
This is a candidate physical cut, not timing closure or a release plan.
"""
import argparse,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('netlist',type=Path);ap.add_argument('--top',default='ot_hbm_hc_bankq_static');ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
j=json.loads(a.netlist.read_text());top=a.top;t=j['modules'][top]
assert len(t['ports']['sum_out']['bits'])==4096
assert len(t['ports']['d_nv']['bits'])==8
cells=t['cells'];nets=t['netnames'];pairs=[];used=set()
for k in range(8):
 lo=2*k;hi=lo+2;wb=set(nets['u_c.u_b.wdat']['bits'][lo*256:hi*256]);xb=set(nets['u_c.u_b.xdat']['bits'][lo*128:hi*128]);cap=wb|xb
 names=[]
 for n,c in cells.items():
  leaf=re.search(r'\.g_grp\[(\d+)\]\.u_lg$',n)
  wm=re.search(r'\.g_w\[(\d+)\]\.u_m$',n)
  xm=re.search(r'\.g_x\[(\d+)\]\.u_m$',n)
  take=(leaf and lo<=int(leaf[1])<hi) or (wm and lo<=int(wm[1])<hi) or (xm and int(xm[1])==k)
  if c['type'] in ('$dff','$adff'):
   q=set(c['connections'].get('Q',[]));over=q&cap
   if over:
    assert q<=cap,('capture crosses pair boundary',n,len(over),len(q));take=True
  if take:names.append(n)
 assert not (set(names)&used);used.update(names)
 counts={typ:sum(cells[n]['type']==typ for n in names) for typ in sorted({cells[n]['type'] for n in names})}
 assert counts.get('ot_hdc_v41x_hcp_lanes')==2,counts
 assert counts.get('ot_sram_1r1w_1024x256_m2_r2c2')==2,counts
 assert counts.get('ot_sram_1r1w_128x256_m1_r2c2')==1,counts
 pairs.append(dict(pair=k,lane_groups=list(range(lo,hi)),cells=names,cell_types=counts,capture_bits=len(cap),module=f'ot_hbm_hc_bank128_pair{k}'))
script=[f'read_json {a.netlist.resolve()}',f'select {top}','splitnets','select -clear',f'cd {top}']
for p in pairs:
 # Glob '?' matches the literal bracket/backslash characters in Yosys escaped names.
 pats=['c:'+n.replace('\\','?').replace('[','?').replace(']','?') for n in p['cells']]
 script += ['select -set CUT '+ ' '.join(pats),f'tee -o {a.out.resolve()}/pair{p["pair"]}_selection.txt select -list @CUT',f'submod -name {p["module"]} @CUT']
script += ['cd ..',f'write_json {a.out.resolve()}/split128.json',f'write_verilog {a.out.resolve()}/split128.v','stat']
(a.out/'cut.ys').write_text('\n'.join(script)+'\n')
macro_area=2*174.744*70.488+94.824*41.064
contract=dict(schema='opentallas.hbm.hc128.physical_cut.v1',status='CANDIDATE_NOT_ROUTED',source_sha='591bcf802',W=128,bank_instances=16,pairs_per_bank=8,lanes_per_pair=16,groups_per_bank=16,weight_macros_per_bank=16,x_macros_per_bank=8,macro_area_per_pair_um2=macro_area,macro_area_per_bank_um2=8*macro_area,split_cycle_delta=0,face_shell_cycle_delta='not inserted here; price +1 in/+1 out if adopted',pairs=pairs,remainder_cell_count=len(cells)-len(used),model=dict(measured_old_lane3_cells=189957,measured_old_lane3_std_area_um2=23292.4,estimated_pair_logic_cells=round(189957*2/3)+768,estimated_pair_logic_area_um2=23292.4*2/3,estimated_pair_outline_um=[250.56,280.8],estimate_only=True),pending=['equivalence plus deliberately wrong boundary control','actual placement/pin-density/channel review','native qhub/qcen W128 physical inventory','gate and model adoption before release'])
(a.out/'physical_contract.json').write_text(json.dumps(contract,indent=2)+'\n');print(json.dumps({k:v for k,v in contract.items() if k not in ('pairs','model')}))
