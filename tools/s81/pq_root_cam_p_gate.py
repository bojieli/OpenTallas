#!/usr/bin/env python3
"""Exact gate for the pipelined ROOTD128 CAM ot_s81_pq_ret_root_cam_p (claude/pq-rootcam-20261008).

Reuses tests/rtl/s81_pq_parent/root_cam_tb.sv (384 roots, full128 buffer, same-edge insert forward, queue
bypass, overflow/queue-pressure faults, reset) comparing every published root bit for bit against the unchanged
native ot_v41_ret_root.  Negative mutants of the NEW structure must fail (any $fatal / no PASS line).
PAR 1 additionally runs the face-parity and buffer-upset fault cases.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ['rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/v41rom/ot_v41_ret.sv',
           'rtl/dsrom_sys/s81_pq_parent/ot_s81_pq_ret_root_cam_p.sv', 'tests/rtl/s81_pq_parent/root_cam_tb.sv']
MUTANTS = [
    # B's same-edge insert is not forwarded to A: the next candidate misses its just-inserted sibling
    ('no_insert_forward', '| (in_mask & {D{sib_new}})', ''),
    # sibling compare (stored entries AND the forwarded insert) reduced to the row: non-siblings pair
    ('wrong_sibling', 'sibling(bt[n], at);\n    wire        sib_new = sibling(ct, at);',
     "bt[n][28:13] == at[28:13];\n    wire        sib_new = ct[28:13] == at[28:13];"),
    # B's removal does not free the entry: the slot stays valid (and stays matchable)
    ('no_free_on_remove', 'wire [D-1:0] bv_next = (bv & ~rm_mask) | in_mask;', 'wire [D-1:0] bv_next = bv | in_mask;'),
    # parent tag computed from the candidate without clearing lo bit k
    ('wrong_parent_lo', 'at[12:8] & ~a_kb, at[7:5]', 'at[12:8], at[7:5]'),
    # C reads the entry one-hot one cycle late (stale index): wrong operand
    ('stale_entry_read', "sel_d = sel_d | ({32{c_oh[n]}} & bd[n]);", "sel_d = sel_d | ({32{hit_oh[n]}} & bd[n]);"),
]


def run_case(out, name, dut_src, par, defs):
    tb = (ROOT / SOURCES[4]).read_text()
    o = 'ot_s81_pq_ret_root_cam #(.D(128),.QD(128)) dut'
    assert tb.count(o) == 1
    tbp = out / f'tb_{name}.sv'
    tbp.write_text(tb.replace(o, f'ot_s81_pq_ret_root_cam_p #(.D(128),.QD(128),.PAR({par})) dut'))
    binary = out / f'{name}.vvp'
    cmd = ['iverilog', '-g2012', *defs, '-s', 'root_cam_tb', '-o', str(binary),
           *[str(ROOT / q) for q in SOURCES[:3]], str(dut_src), str(tbp)]
    c = subprocess.run(cmd, text=True, capture_output=True)
    (out / f'{name}_compile.log').write_text(c.stdout + c.stderr)
    if c.returncode:
        raise RuntimeError('compile failed: ' + name + '\n' + c.stderr)
    r = subprocess.run(['vvp', str(binary)], text=True, capture_output=True)
    log = r.stdout + r.stderr
    (out / f'{name}.log').write_text(log)
    binary.unlink()
    return r.returncode, log


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--par', type=int, default=0)
    p.add_argument('--only', help='positive / a mutant name / par_flip / buf_flip')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    original = (ROOT / SOURCES[3]).read_text()
    cases = {}
    plan = [('positive', None, None, [])] + [(n, o, w, []) for n, o, w in MUTANTS]
    if a.par:
        plan += [('par_flip', None, None, ['-DROOT_PAR_FLIP']), ('buf_flip', None, None, ['-DROOT_BUF_FLIP'])]
    for name, old, new, defs in plan:
        if a.only and name != a.only:
            continue
        src = ROOT / SOURCES[3]
        if old is not None:
            assert original.count(old) == 1, name
            src = a.out / f'{name}.sv'
            src.write_text(original.replace(old, new))
        rc, log = run_case(a.out, name, src, a.par, defs)
        if name == 'positive':
            ok = rc == 0 and 'PASS CAM384' in log
        elif defs:   # fault-injection cases: PAR 1 must fail closed
            ok = rc != 0 and 'unexpected fault' in log
        else:        # mutants must be caught
            ok = rc != 0 and 'PASS CAM384' not in log
        lat = re.search(r'LATENCY isolated complete delta(-?\d+) sibling delta(-?\d+) eightleaf delta(-?\d+)', log)
        fatal = re.search(r'FATAL[^\n]*\n?[^\n]*', log)
        cases[name] = dict(exit_code=rc, gate_passed=ok,
                           caught_by=(fatal.group(0).strip()[:160] if fatal else None),
                           latency_delta_vs_native=(dict(complete=int(lat[1]), two_leaf=int(lat[2]), eight_leaf=int(lat[3]))
                                                    if lat else None),
                           compiled_source_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
        print(name, 'PASS' if ok else 'FAIL', 'rc', rc, cases[name]['latency_delta_vs_native'] or cases[name]['caught_by'])
    record = dict(schema='opentallas.s81.pq-root-cam-p-gate.v1', dut='ot_s81_pq_ret_root_cam_p', PAR=a.par,
                  cases=cases, source_sha256={q: hashlib.sha256((ROOT / q).read_bytes()).hexdigest() for q in SOURCES},
                  tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), exact_roots=384, ROOTD=128, QD=128,
                  all_passed=all(c['gate_passed'] for c in cases.values()), adopted=False)
    (a.out / 'record.json').write_text(json.dumps(record, indent=2) + '\n')
    print('ROOTCAM_P_GATE', 'PASS' if record['all_passed'] else 'FAIL')
    return 0 if record['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
