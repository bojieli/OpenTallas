#!/usr/bin/env python3
"""Produce a separate opt-in coherent-gather quarter; never edit pinned C1.

Only result captures, result banks, and result-face bits change clock mapping.
The old numeric lane, broadcast and all input clocks remain byte-identical.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from uarch_model_hfd_hc_gather import model


def build(source, plan, mutant=False):
    assert plan['chains'] == 2 and plan['lanes'] == 88
    assert plan['WO'] == 1024 and plan['face_stages'] == {'f_sfu': 1, 't_sfu': 2}
    assert 'module hfd_hc (' in source
    source = source.replace('module hfd_hc (',
        'module hfd_hc #(parameter integer ENABLE_GATHER_COHERENCE = 0) (', 1)
    changed = {'lane_capture': 0, 'accumulate': 0, 'face_output': 0}

    def clock(old, half):
        return f'(ENABLE_GATHER_COHERENCE ? clk{2 if half == 0 else 6} : {old})'

    def capture(m):
        j, old = int(m[1]), m[2]
        changed['lane_capture'] += 1
        return f'always @(posedge {clock(old, j // 44)}) lq_{j} <= lo_{j};'

    source = re.sub(r'always @\(posedge (clk\d+)\) lq_(\d+) <= lo_\2;',
        lambda m: capture((m[0], m[2], m[1])), source)

    def acc(m):
        old, k, g = m[1], int(m[2]), int(m[3])
        changed['accumulate'] += 1
        rhs = f'nx_{k}_{g}'
        if mutant and (k, g) == (0, 7):
            rhs = f'(ENABLE_GATHER_COHERENCE ? 512\'b0 : {rhs})'
        return f'always @(posedge {clock(old, k)}) acc_{k}_{g} <= {rhs};'

    source = re.sub(r'always @\(posedge (clk\d+)\) acc_(\d+)_(\d+) <= nx_\2_\3;', acc, source)

    def face(m):
        old, stage, rhs = m[1], m[2], m[3]
        changed['face_output'] += 1
        return '\n'.join(
            f'always @(posedge {clock(old, k)}) t_sfu_o{stage}[{511+512*k}:{512*k}] <= {rhs}[{511+512*k}:{512*k}];'
            for k in range(2))

    source = re.sub(r'always @\(posedge (clk\d+)\) t_sfu_o(\d+) <= (heads\[1023:0\]|t_sfu_o\d+);',
        lambda m: face((m[0], m[1], m[2], 'heads' if m[3].startswith('heads') else m[3])), source)
    assert changed == {'lane_capture': 88, 'accumulate': 22, 'face_output': 2}, changed
    return ('// Codex independent gather-clock experiment: PHYSICAL ENVELOPE ONLY.\n'
            '// Source/arithmetic clocks unchanged; static opt-in, zero added logical cycles.\n' + source)


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--source-dir', type=Path, required=True)
    a.add_argument('--out', type=Path, required=True)
    p = a.parse_args()
    plan = json.loads((p.source_dir / 'plan.json').read_text())
    fp = json.loads((p.source_dir / 'floorplan.json').read_text())
    sizing = model(plan, fp)
    source = (p.source_dir / 'hfd_hc.sv').read_text()
    p.out.mkdir(parents=True, exist_ok=True)
    (p.out / 'model.json').write_text(json.dumps(sizing, indent=2) + '\n')
    (p.out / 'hfd_hc.sv').write_text(build(source, plan))
    (p.out / 'hfd_hc_neg.sv').write_text(build(source, plan, mutant=True))
    for name in ['macro_place.tcl', 'face_stages.tcl', 'floorplan.json',
                 'ot_dsrom_su_hcpost_lane_pr_simstub.sv', 'tb_in.mem', 'tb_out.mem']:
        (p.out / name).write_bytes((p.source_dir / name).read_bytes())
    (p.out / 'source.json').write_text(json.dumps({'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'default_enable': 0, 'mutation': 'freeze gather bank acc_0_7 to zero while enabled',
        'scope': 'clock/routing envelope only; original numeric lane not modified'}, indent=2) + '\n')


if __name__ == '__main__':
    main()
