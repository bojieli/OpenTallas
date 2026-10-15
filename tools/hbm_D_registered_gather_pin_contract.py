#!/usr/bin/env python3
"""Proposed top-down registered gather faces; no fabricated actual coordinates."""
import argparse,csv,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--source',default='/home/ubuntu/wt/hbm-static-attn-quant-1014/rtl/hdc/v41x/static/ot_hbm_attn_pv_group_gather_registered.sv');a=p.parse_args();out=Path(a.out);rows=[]
for g in range(4):
 orders={'W':0,'E':0,'N':0}
 def pin(name,d,face,src,dst=''):
  rows.append([g,name,d,face,orders[face],src,dst]);orders[face]+=1
 for b in range(8):
  face='W'if b%4<2 else'E'
  for k in range(512):pin(f'tile_data[{b*512+k}]','INPUT',face,f'g_tile[{4*b+g}].u_store.drain_data[{k}]')
  for k in range(16):pin(f'tile_flags[{b*16+k}]','INPUT',face,f'g_tile[{4*b+g}].u_store.drain_flags[{k}]')
 for k in range(512):pin(f'bankpair_data[{k}]','OUTPUT','E','',f'logicalNEbank{2*g+k//256}.WG1.payload[{k%256}]')
 for k in range(16):pin(f'bankpair_flags[{k}]','OUTPUT','E','',f'logicalNEbank{2*g+k//8}.WG1.wordflag[{k%8}]')
 pin('output_v','OUTPUT','E','','leafvalid (currently parent unconnected; hardleaf inventory retains realvalidFF)')
 for k in range(3):pin(f'block_select[{k}]','INPUT','N',f'block_q[{k}] (existingglobalclk source)')
 pin('capture_v','INPUT','N','valid_pipe[0] (existingglobalclk source)');pin('rst_n','INPUT','N','rst_n domain-local release required');pin('clk','INPUT','N',f'bank_clk[{g}]')
 assert orders=={'W':2112,'E':2641,'N':6}
with out.with_suffix('.tsv').open('w')as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['group','literal_pin','direction','proposed_face','proposed_order_on_face','source','destination']);w.writerows(rows)
r={'source_path':a.source,'source_sha256':hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),'pin_TSV_sha256':hashlib.sha256(out.with_suffix('.tsv').read_bytes()).hexdigest(),'groups':4,'pins_per_group':4759,'face_counts_per_group':{'W':2112,'E':2641,'N':6},'actual_FF_per_leaf':4757,'actual_TT_logic_um2_per_leaf':2487.59586,'nominal_combined_bank_root_sinks':11445,'added_edges':2,'physical_reservation_um':[500,450],'reservation_qualified':False,'actual_pin_centers':None,'planning_only_min_pitch_um':.096,'planning_only_max_face_fraction':.6,'required_face_length_before_PG_halo_um':{'W':2112*.096/.6,'E':2641*.096/.6},'clock_source_must_match_global_phase':True,'limits':['New actual registered leaf; supersedes combinational4755pin face request.','Track count, PG contacts, pin-above keepout, actual buffered netlist and STA must precede physical adoption.','No single .096 pitch grant across arbitrary physical layers; actual kit determines legal sites.','Existing field/VM placement is candidate; source and destination outside contracts/128commit calendar remain required.','Face slots are ordered assignments, not invented routed pin coordinates.']};out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
