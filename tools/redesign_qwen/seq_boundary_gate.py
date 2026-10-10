#!/usr/bin/env python3
"""Minimum emitted-master boundary gate; arithmetic/seq interiors are isolated.

Exercises the real pin pipeline with endpoint snapshots and internal per-layer
sequencer launch signals. It does not establish whole-token exactness or closure.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/redesign_qwen'))
import split_ctrl

def run(out):
    rtl = ROOT / 'rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_boundary.sv'
    old = ROOT / 'rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su.sv'
    assert split_ctrl.emit_seq_su() == old.read_text(), 'legacy emission changed'
    assert split_ctrl.emit_seq_su(boundary=True) == rtl.read_text(), 'successor stale'
    text = rtl.read_text()
    mutants = {
        'package_start': ('assign b_me_start_o = core_start;', 'assign b_me_start_o = q_h_start;'),
        'premature_count': ('assign b_su_acc_o = q_pi_su_acc;', "assign b_su_acc_o = {23'd0, b_po_su_go};"),
        'wrong_program': ('assign b_me_prog_base_o = prog_base;', "assign b_me_prog_base_o = 12'd0;"),
        'mixed_snapshot': ('assign b_su_rows_o = q_pi_su_progress_rows;', 'assign b_su_rows_o = q_pi_su_progress;'),
    }
    sm = (ROOT / 'rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv').read_text()
    start = sm.index('module ot_qfd_rst_stn')
    reset = sm[start:sm.index('endmodule',start)+len('endmodule')]
    records=[]
    with tempfile.TemporaryDirectory(prefix='qwen-seq-boundary-') as scratch:
        work=Path(scratch)
        (work/'rst.sv').write_text(reset)
        cases=[('baseline',i,o,text,True) for i,o in ((0,0),(1,1),(1,2),(2,1),(2,2))]
        for name,(before,after) in mutants.items():
            assert text.count(before)==1
            cases.append((name,1,1,text.replace(before,after),False))
        for name,i,o,source,expected in cases:
            (work/'dut.sv').write_text(source)
            cmd=['iverilog','-g2012','-i','-s','tb',f'-Ptb.IS={i}',f'-Ptb.OS={o}','-o',str(work/'tb'),
                 str(ROOT/'tests/rtl/qwen_seq_boundary/tb.sv'),str(work/'dut.sv'),
                 str(ROOT/'rtl/hdc/ot_hdc_delay.sv'),str(work/'rst.sv')]
            build=subprocess.run(cmd,text=True,capture_output=True)
            if build.returncode:
                raise RuntimeError(build.stderr)
            sim=subprocess.run(['vvp',str(work/'tb')],text=True,capture_output=True)
            passed=sim.returncode==0 and 'PASS boundary' in sim.stdout
            record=dict(case=name,IS=i,OS=o,expected_pass=expected,observed_pass=passed,
                        exit_code=sim.returncode,stdout=sim.stdout,stderr=sim.stderr,
                        source_sha256=hashlib.sha256(source.encode()).hexdigest())
            records.append(record)
            if passed != expected:
                raise RuntimeError(json.dumps(record))
    payload=dict(schema='opentallas.qwen-seq-boundary-gate.v1',verdict='PASS',
                 scope='actual emitted-top boundary pin stations; controller/arithmetic/sequencer interiors isolated by forced launch/issue wires and missing-module isolation',
                 unsupported_claims=['full-token exactness','SU endpoint counter correctness','physical closure'],
                 files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                        (rtl,old,ROOT/'tests/rtl/qwen_seq_boundary/tb.sv',ROOT/'rtl/hdc/ot_hdc_delay.sv')},cases=records)
    if out:
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(payload,indent=2)+'\n')
    print(f"PASS: {len(records)-len(mutants)} pipeline shapes; {len(mutants)} mutants detected; legacy emission byte-identical")

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path)
    run(ap.parse_args().out)
