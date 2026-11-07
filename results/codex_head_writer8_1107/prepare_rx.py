#!/usr/bin/env python3
"""Private HEAD RX candidate; input is the immutable l48uj cohort, never POR."""
import json,hashlib,shutil,sys
from pathlib import Path
src=Path(sys.argv[1]); out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
p=json.loads((src/'source_plan.json').read_text());t=p['partition_types']['hd_spn_wshim_rx'];c=t['clock']
c['landing_ring_wreg']={'buses':['link_i'],'dsrep':8,'write_chunk':8,'freg':True}
b=c['landing_contract']['bands']['link_i'];b['freg_rect_um']=[4.32,708.48,12.96,1008.512];b['rect_um']=[17.28,708.48,60.48,1008.512]
# Six physical hops replace three ~233um wires with ~117um wires.
for s in t['ft_slots']:
 if s['name']=='link':s['stations']=6
(out/'source_plan.json').write_text(json.dumps(p,indent=1)+'\n');shutil.copyfile(src/'source_sidecar.json',out/'source_sidecar.json')
ledger={'base':'hd_spn_wshim_rx vB l48uj','candidate':'hd_spn_wshim_rx vC','DO_NOT_COUNT':True,'PIN CYCLES':{'input_link_FREG':1,'feedthrough_link':3,'end_to_end_link':4},'count_aligned_strap_k_delta':2,'changed':['kept writer enables per8bits instead of broadcast','8 read select copies per64bit chunk','input face capture','six FT hops instead ofthree','M6 signals'], 'compiler_token':'Not integrated; candidateonly. POR/event update owed after physical qualification.','input_plan_sha256':hashlib.sha256((src/'source_plan.json').read_bytes()).hexdigest(),'candidate_plan_sha256':hashlib.sha256((out/'source_plan.json').read_bytes()).hexdigest()}
(out/'added_rx_clk_PIN_cycles.json').write_text(json.dumps(ledger,indent=2)+'\n')
