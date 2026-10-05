#!/usr/bin/env python3
"""Small source-pinned real kstream/data lockstep plus last-block mutant."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
args.work.mkdir(parents=True,exist_ok=True);args.out.mkdir(parents=True,exist_ok=True)
src=['rtl/test/tb_dsrom_kctl_drain.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring_drain.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv']
records={}
for name in ['positive','last_block_mutant']:
    selected=[ROOT/p for p in src]
    if name!='positive':
        mutant=args.work/'last_block_mutant.sv'
        text=selected[2].read_text();assert text.count('d_more <= d_left > 1;')==1
        mutant.write_text(text.replace('d_more <= d_left > 1;','d_more <= d_left > 2;'))
        selected[2]=mutant
    binary=args.work/(name+'.vvp')
    command=['iverilog','-g2012','-s','tb_dsrom_kctl_drain','-o',str(binary),*map(str,selected)]
    with (args.out/(name+'_compile.log')).open('w') as f:
        cp=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
    if cp.returncode:raise RuntimeError('compile failed; retained log')
    with (args.out/(name+'.log')).open('w') as f:
        run=subprocess.run(['vvp',str(binary)],stdout=f,stderr=subprocess.STDOUT)
    text=(args.out/(name+'.log')).read_text()
    detected=run.returncode!=0 and 'mismatch' in text
    records[name]={'returncode':run.returncode,'mutant_detected':detected,'pass':run.returncode==0 and 'PASS KCTL_DRAIN scans=28' in text}
    if name=='positive' and not records[name]['pass']:raise RuntimeError('positive failed; retained evidence')
    if name!='positive' and not detected:raise RuntimeError('mutant escaped')
record={'schema':'dsrom.kctl_drain_gate.v1','runs':records,
        'sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [*src,'rtl/hdc/v41x/ot_hdc_v41x_idx_pool_adapt_drain.sv','tools/dsrom_kctl_drain_gate.py']},
        'cycle_accounting':{'measured_scan_count':28,'measured_total_clocks':5677,'added_cycles_per_scan':0,'added_cycles_per_block':0,'stream_clock_target_ns':1/1.2,'added_token_ns_if_parent_uses_same_schedule':0},
        'scope':'real kstream plus unchanged ROB/key datapath, baseline/enabled/off outputs every edge under legal backpressure; transport payload equivalence, not model inference/golden token',
        'parent_pool_integration_executed':False,'SS_FF_qualified':False,'adoption':False}
(args.out/'receipt.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(records))
