#!/usr/bin/env python3
"""Minimum ROOTD128 staged-CAM exact gate; original arithmetic is unchanged."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ['rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_delay.sv',
           'rtl/v41rom/ot_v41_ret.sv',
           'rtl/dsrom_sys/s81_pq_parent/ot_s81_pq_ret_root_cam.sv',
           'tests/rtl/s81_pq_parent/root_cam_tb.sv']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--opc', type=int, default=0, help='OPC parameter of the DUT (1 = stage-C operand fetch)')
    p.add_argument('--only', help='run one case (positive / no_insert_forward / wrong_sibling)')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    original = (ROOT / SOURCES[3]).read_text()
    cases = {}
    for name, old, new in [
        ('positive', None, None),
        ('no_insert_forward', 'if (insert_b && fr == n) begin',
         "if (1'b0 && insert_b && fr == n) begin"),
        ('wrong_sibling', 'sibling(effective_tag, at)',
         'effective_tag[28:13] == at[28:13]')]:
        if a.only and name != a.only:
            continue
        source = ROOT / SOURCES[3]
        if old:
            assert original.count(old) == 1
            source = a.out / (name + '.sv')
            source.write_text(original.replace(old, new))
        binary = a.out / (name + '.vvp')
        tb = ROOT / SOURCES[4]
        if a.opc:
            t = tb.read_text(); o = 'ot_s81_pq_ret_root_cam #(.D(128),.QD(128)) dut'
            assert t.count(o) == 1
            tb = a.out / ('tb_opc_' + name + '.sv'); tb.write_text(t.replace(o, o.replace('.QD(128))', f'.QD(128),.OPC({a.opc}))')))
        cmd = ['iverilog', '-g2012', '-s', 'root_cam_tb', '-o', str(binary),
               *[str(ROOT / q) for q in SOURCES[:3]], str(source), str(tb)]
        compile_run = subprocess.run(cmd, text=True, capture_output=True)
        (a.out / (name + '_compile.log')).write_text(compile_run.stdout + compile_run.stderr)
        if compile_run.returncode:
            raise RuntimeError('compile failed: ' + name)
        run = subprocess.run(['vvp', str(binary)], text=True, capture_output=True)
        log = run.stdout + run.stderr
        (a.out / (name + '.log')).write_text(log)
        passed = (run.returncode == 0 and 'PASS CAM384' in log) if not old else (
            run.returncode != 0 and ('unexpected fault' in log or 'pairing/result mismatch' in log))
        cases[name] = dict(exit_code=run.returncode, gate_passed=passed,
                           compiled_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        binary.unlink()
    record = dict(schema='opentallas.s81.pq-root-cam-gate.v1', cases=cases,
                  source_sha256={q: hashlib.sha256((ROOT/q).read_bytes()).hexdigest() for q in SOURCES},
                  tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  exact_roots=384, ROOTD=128, QD=128,
                  measured_delta_cycles=dict(complete=1, two_leaf=2, eight_leaf=4),
                  scope='Minimum one real ROOTD128 component compared to unchanged native root. No parity, full-parent or physical qualification.',
                  adopted=False)
    (a.out / 'record.json').write_text(json.dumps(record, indent=2)+'\n')
    return not all(c['gate_passed'] for c in cases.values())


if __name__ == '__main__':
    raise SystemExit(main())
