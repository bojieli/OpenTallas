#!/usr/bin/env python3
"""Collect generic synthesis retention evidence; not a technology-mapped gate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
RTL='rtl/physical/ot_qwen_die_dualfault_station_r22.sv'
TOP='ot_qwen_die_dualfault_station_r22'

def run(out):
    out.mkdir(parents=True,exist_ok=False)
    rows=[]
    with tempfile.TemporaryDirectory(prefix='qwen-station-retention-') as tmp:
        for tap,split in [(0,0),(1,0),(0,1),(1,1)]:
            key=f't{tap}_s{split}'
            net=Path(tmp)/f'{key}.json'
            script=f'read_verilog -sv {ROOT/RTL}; chparam -set ENABLE_FULLWIDTH 1 -set TAP {tap} -set SPLIT {split} {TOP}; hierarchy -top {TOP}; synth -top {TOP}; write_json {net}'
            (out/f'{key}.ys').write_text(script+'\n')
            proc=subprocess.run(['yosys','-Q','-T','-p',script],capture_output=True,text=True)
            log=proc.stdout+proc.stderr
            (out/f'{key}.log').write_text(log)
            if proc.returncode: raise RuntimeError(log)
            m=json.loads(net.read_text())['modules'][TOP]
            rails=['bf_q','bfn_q','af_q','afn_q']
            if tap: rails+=['tf_q','tfn_q']
            if split: rails+=['cf_q','cfn_q']
            drivers={}
            for rail in rails:
                bits=m['netnames']['g_selected.'+rail]['bits']
                drivers[rail]=[name for name,c in m['cells'].items() if c['type'].startswith('$_DFF') and c['connections'].get('Q')==bits]
            active=['b_d']+(['t_d'] if tap else [])+(['c_d'] if split else [])
            payload_bits=[bit for port in active for bit in m['ports'][port]['bits']]
            fault_distinct=all(len(ds)==1 for ds in drivers.values()) and len({ds[0] for ds in drivers.values()})==len(rails)
            rows.append(dict(case=key,active_fault_state_bits=len(rails),fault_drivers=drivers,fault_drivers_distinct=fault_distinct,
                modeled_payload_FF=508*len(active),observed_distinct_payload_outputs=len(set(payload_bits)),
                payload_copies_distinct=len(set(payload_bits))==len(payload_bits),
                log_sha256=hashlib.sha256(log.encode()).hexdigest(),netlist_sha256=hashlib.sha256(net.read_bytes()).hexdigest()))
    result=dict(schema='opentallas.qwen_station_dualfault_retention.v1',cases=rows,
        fault_generic_retention_pass=all(row['fault_drivers_distinct'] for row in rows),
        payload_generic_retention_pass=all(row['payload_copies_distinct'] for row in rows),
        route_eligible=False,adoption=False,
        blocker='Yosys synth merges equivalent payload register copies despite wire keep attributes. Physical independent output drivers need a retained-cell synthesis policy or structural implementation; cell-library mapping and die loads remain unqualified.',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [RTL,'tools/qwen_station_dualfault_retention.py']},
        yosys_version=subprocess.check_output(['yosys','-V'],text=True).strip())
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['fault_generic_retention_pass','payload_generic_retention_pass','route_eligible']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path)
    run(p.parse_args().out)
