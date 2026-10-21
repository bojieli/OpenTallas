#!/usr/bin/env python3
"""Actual Yosys/ABC checks for native-cell gold; run on the fleet, not pytest stubs."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

PORTS = '(clk,rst_n,a,b,q,c); input clk,rst_n,a,b; output q,c;'
GOOD = """wire qn;
DFFASRHQNx1_ASAP7_75t_R f(.CLK(clk),.D(a),.QN(qn),.RESETN(rst_n),.SETN(1'b1));
INVx1_ASAP7_75t_R oq(.A(qn),.Y(q));
INVx1_ASAP7_75t_R oc(.A(a),.Y(c));
"""


ENCODED_GATE = """wire x,n0,n1,s0,s1;
XOR2xp5_ASAP7_75t_R xi(.A(a),.B(b),.Y(x));
DFFASRHQNx1_ASAP7_75t_R f0(.CLK(clk),.D(x),.QN(n0),.RESETN(rst_n),.SETN(1'b1));
DFFASRHQNx1_ASAP7_75t_R f1(.CLK(clk),.D(b),.QN(n1),.RESETN(rst_n),.SETN(1'b1));
INVx1_ASAP7_75t_R i0(.A(n0),.Y(s0));
INVx1_ASAP7_75t_R i1(.A(n1),.Y(s1));
XOR2xp5_ASAP7_75t_R oq(.A(s0),.B(s1),.Y(q));
INVx1_ASAP7_75t_R oc(.A(a),.Y(c));
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    a = ap.parse_args()
    work = Path(a.work).resolve(); work.mkdir(parents=True, exist_ok=True)
    tool = Path(__file__).resolve().with_name('kv_leaf_lec.py')
    records = {}
    for name in ['native_equal', 'wrong_input_port', 'wrong_cell_function', 'unknown_gold_cell', 'rtl_equal']:
        root = work / name; root.mkdir(exist_ok=True)
        gold = GOOD
        if name == 'unknown_gold_cell':
            gold = GOOD.replace('INVx1_ASAP7_75t_R oq', 'UNMODELED_NATIVE_CELL oq')
        if name == 'rtl_equal':
            gold = "reg v; always @(posedge clk or negedge rst_n) if(!rst_n) v<=0; else v<=a; assign q=v; assign c=~a;\n"
        (root / 'gold.sv').write_text('module native_gold'+PORTS+'\n'+gold+'endmodule\n')
        gate = ENCODED_GATE
        if name == 'wrong_input_port':
            gate = gate.replace('.A(a),.B(b)', '.A(b),.B(b)')
        if name == 'wrong_cell_function':
            gate = gate.replace('XOR2xp5_ASAP7_75t_R oq', 'XNOR2xp5_ASAP7_75t_R oq')
        if name.startswith('wrong_'):
            assert gate != ENCODED_GATE, 'causal mutation did not change the gate'
        (root / 'gate.v').write_text('module native_gate'+PORTS+'\n'+gate+'endmodule\n')
        expect = 'fail' if name.startswith('wrong_') else 'pass'
        cmd = [sys.executable, str(tool), '--src', str(root), '--top', 'native_gold', '--params', '{}',
               '--source', 'gold.sv', '--gate', str(root/'gate.v'), '--gate-top', 'native_gate',
               '--work', str(root/'lec'), '--out', str(root/'result.json'), '--expect', expect]
        with (root / 'driver.log').open('w') as log:
            proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
        result = json.loads((root/'result.json').read_text())
        target = 'ERROR' if name == 'unknown_gold_cell' else ('NOT_EQUIVALENT' if expect == 'fail' else 'EQUIVALENT')
        assert result['verdict'] == target, (name, result)
        assert bool(result['library_models']['liberty'])
        assert result['library_models']['gold_and_gate_same_models'] is True
        if target == 'ERROR':
            assert proc.returncode != 0 and 'gold elaboration failed' in result['error']
            assert 'UNMODELED_NATIVE_CELL' in result['error']
        else:
            assert proc.returncode == 0 and result['ok']
            if expect == 'fail':
                assert result.get('cex_frame') is not None, 'negative needs actual counterexample'
        records[name] = {'verdict': result['verdict'], 'rc': proc.returncode,
                         'models': result['library_models']}
        print(name, result['verdict'], flush=True)
    (work/'SUMMARY.json').write_text(json.dumps(records, indent=2)+'\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
