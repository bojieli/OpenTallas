#!/usr/bin/env python3
"""Production Yosys/ASAP7 sequential mapping and copy-retention component gate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
RTL='rtl/physical/ot_qwen_die_dualfault_station_r22.sv'
LIB='results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib'
TOP='ot_qwen_die_dualfault_station_r22'
ATTR='(* keep = 1, dont_touch = 1 *) always @(posedge clk) '
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(out,yosys):
    out.mkdir(parents=True,exist_ok=False)
    cases=[]
    with tempfile.TemporaryDirectory(prefix='station-mapped-') as tmp:
        tmp=Path(tmp)
        for negative in [0,1]:
            src=(ROOT/RTL).read_text()
            if negative: src=src.replace(ATTR,'always @(posedge clk) ')
            (tmp/'dut.sv').write_text(src)
            for tap,split in ([(0,0),(1,0),(0,1),(1,1)] if not negative else [(1,0),(0,1),(1,1)]):
                key=f'n{negative}_t{tap}_s{split}'
                script=f'read_verilog -sv {tmp}/dut.sv; chparam -set ENABLE_FULLWIDTH 1 -set TAP {tap} -set SPLIT {split} {TOP}; synth -top {TOP}; dfflibmap -liberty {ROOT/LIB}; opt_clean; write_json {tmp}/net.json'
                proc=subprocess.run([yosys,'-Q','-T','-p',script],capture_output=True,text=True)
                (out/f'{key}.log').write_text(proc.stdout+proc.stderr)
                if proc.returncode: raise RuntimeError(proc.stderr)
                m=json.loads((tmp/'net.json').read_text())['modules'][TOP]
                ffs={n:c for n,c in m['cells'].items() if c['type'].startswith('DFF') and c['type'].endswith('_ASAP7_75t_R')}
                qdrivers={}
                for n,c in ffs.items():
                    for port in ['Q','QN']:
                        for bit in c['connections'].get(port,[]): qdrivers.setdefault(bit,[]).append(n)
                inv={c['connections']['Y'][0]:c['connections']['A'][0] for c in m['cells'].values() if c['type']=='$_NOT_'}
                def driver(bit):
                    # ASAP7 mapping may use inverted-Q plus an inverter.
                    seen=set()
                    while bit in inv and bit not in seen:
                        seen.add(bit);bit=inv[bit]
                    return qdrivers.get(bit,[])
                ports=['b_d']+(['t_d'] if tap else [])+(['c_d'] if split else [])
                ds=[driver(bit) for port in ports for bit in m['ports'][port]['bits']]
                good=all(len(x)==1 for x in ds) and len({x[0] for x in ds if len(x)==1})==508*len(ports)
                fault=['bf_q','bfn_q','af_q','afn_q']+(['tf_q','tfn_q'] if tap else [])+(['cf_q','cfn_q'] if split else [])
                fs={name:driver(m['netnames']['g_selected.'+name]['bits'][0]) for name in fault}
                fg=all(len(x)==1 for x in fs.values()) and len({x[0] for x in fs.values() if len(x)==1})==len(fault)
                cases.append(dict(case=key,expected_payload_retained=not negative,payload_retained=good,
                    expected_payload_FF=508*len(ports),mapped_distinct_payload_FF=len({x[0] for x in ds if len(x)==1}),
                    mapped_total_FF=len(ffs),fault_retained=fg,fault_drivers=fs,
                    sequential_netlist_sha256=sha(tmp/'net.json'),log_sha256=sha(out/f'{key}.log')))
    result=dict(schema='opentallas.qwen_station_dualfault_mapped_retention.v1',
        pass_all=all(c['expected_payload_retained']==c['payload_retained'] and c['fault_retained'] for c in cases),cases=cases,
        yosys_version=subprocess.check_output([yosys,'-V'],text=True).strip(),yosys_binary_sha256=sha(Path(yosys)),
        source_sha256={p:sha(ROOT/p) for p in [RTL,LIB,'tools/qwen_station_dualfault_mapped_retention.py']},
        scope='Actual ASAP7 SS sequential cell mapping and Q-driver tracing after optimization; no combinational-library mapping or P&R claimed',
        remaining=['Forward control/data integrity','Root publication guard','Die reset/clock distribution','Actual boundary loads and SS/FF','Final ORFS mapped and post-repair retention audit'],adoption=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(pass_all=result['pass_all'],cases=len(cases))))
    if not result['pass_all']: raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--yosys',required=True)
    args=p.parse_args();run(args.out,args.yosys)
