#!/usr/bin/env python3
"""One source compiler schedule and explicit model-only state/area ledger."""
import hashlib
import itertools
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'tools'))
from qwen_coll_tp8_static_bench import schedule
BASE = Path(__file__).resolve().parent
widths = [150]*4 + [152]*4 + [154,153,153,153] + [139,139,139,138]
rows = []
for label, delta in [('current',0),('A_unqualified_E2_target',8),('B_gated_final_capture_model',12)]:
    lu, ls = 53+delta, 378+delta
    spans = {}
    for name, mode, n in [('AR256',0,256),('ARGMAX1',1,1)]:
        prog = schedule([mode],[n],lu,ls,shared_ucie=True)
        spans[name] = max(p['last_out'] for p in prog)-prog[0]['first_slot']+1
        (BASE/(label+'_'+name+'_program.json')).write_text(json.dumps(prog,indent=2)+'\n')
    rows.append(dict(variant=label,LU=lu,LS=ls,spans=spans,
        P_R_banks_per_ring=2 if lu+2<=64 else 4,
        P_R_total_macro_area_um2=(4 if lu+2<=64 else 8)*177.768*81))
for row in rows:
    da = row['spans']['AR256']-rows[0]['spans']['AR256']
    dg = row['spans']['ARGMAX1']-rows[0]['spans']['ARGMAX1']
    added = 72*da+dg
    row.update(token_added_cycles=added,token_cycles=249577+added,
        added_cycles_percent=100*added/249577,
        throughput_loss_percent=100*added/(249577+added))
ledger = dict(schema='opentallas.safe_collective.regional_model.v1',
    status='MODEL_ONLY_NO_IMPLEMENTATION_OR_GATE_ADOPTION',rows=rows,
    landing_lane_widths=widths,total_bundle_bits=sum(widths),
    target_A_payload_state_bits=5*sum(widths),
    target_A_full_metadata_state='UNDEFINED UNTIL INDEPENDENT RTL/SAFETY QUALIFICATION; payload count is not total',
    concrete_B_FIRST1_state_upper_bits=sum(9*w+5*((w+15)//16)+68 for w in widths),
    concrete_B_FIRST0_state_upper_bits=sum(9*w+5*((w+15)//16)+66 for w in widths),
    concrete_B_ICG_latches_FIRST1=9*len(widths),
    concrete_B_local_SRAM_macro_area_um2=0,
    B_W180_measured_mapped_state_bits=1746,B_W180_measured_area_um2=616.2237,
    B_W180_measured_area_source='SAFE-QW-LAND 62708ac8f W180; ff0368257 reset fix rebench live; smaller widths unmeasured',
    B_added_P_R_macros=4,B_added_P_R_storage_bits=4*32*546,
    B_added_P_R_macro_area_um2=4*177.768*81,
    note='A targets four crossings x2 added edges; B models x3 final-capture increments. Neither is an observed integrated calendar; root phase, startup, first operation and steady workloads require proof.')
(BASE/'tradeoff.json').write_text(json.dumps(ledger,indent=2)+'\n')
print(json.dumps(ledger,indent=2))
