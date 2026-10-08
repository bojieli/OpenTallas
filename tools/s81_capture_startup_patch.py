"""Prepare/run a literal startup-cell patch with fresh SS and FF signoff processes.

No repair_timing calls or in-process STA verdicts. Original inputs are read-only;
a candidate directory is exclusive and each result retains full logs and hashes.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from w18.corner_sta import script as corner_script

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {f'HB{i}xp67_ASAP7_75t_R' for i in range(1, 5)} | {'BUFx2_ASAP7_75t_R'}
ENDPOINT = re.compile(r'(?:g_r\[\d+\]\.u_x|u_s)\.(?:w_st_r|r_st_w)\[[01]\]\$_DFF_P_/D')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(plan):
    if plan.get('schema') != 'opentallas.s81.capture_startup_patch.v1':
        raise ValueError('Unknown patch schema')
    seen = set()
    for row in plan['patches']:
        if not ENDPOINT.fullmatch(row['endpoint']) or row['endpoint'] in seen:
            raise ValueError('Duplicate or non-startup endpoint')
        seen.add(row['endpoint'])
        if not row['cells'] or any(c not in ALLOWED for c in row['cells']):
            raise ValueError('Only literal non-inverting characterized cells permitted')
        if row['baseline_ss_ps'] < 15:
            raise ValueError('Cannot patch an already failing setup endpoint')
    if not seen:
        raise ValueError('Empty patch')


def prepare(base, out, plan):
    validate(plan)
    if out.exists():
        raise ValueError('Candidate directory already exists; evidence is immutable')
    for name in ['6_final.odb', '6_final.sdc', '6_final.spef']:
        if sha(base / name) != plan['original_sha256'][name]:
            raise ValueError('Original artifact hash mismatch: ' + name)
    out.mkdir(parents=True)
    shutil.copy2(base / '6_final.sdc', out / '6_final.sdc')
    (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    # Load the exact same SS libraries, parasitics and effective signoff constraints.
    prefix = corner_script('ss', str(base), [],
                           ['physical/s81_ph_views/common/signoff_unc60.sdc']).split('puts "OT_CORNER')[0]
    rows = []
    for row in plan['patches']:
        rows.append('  {' + row['endpoint'] + '} {' + ' '.join(row['cells']) + '}')
    actions = 'set patches {\n' + '\n'.join(rows) + '\n}\n'
    body = (ROOT / 'physical/s81_ph_views/capture/startup_pin_patch.tcl').read_text()
    (out / 'patch.tcl').write_text(prefix + '\nset patch_out {' + str(out) + '}\n' + actions + body)
    for c in ['ss', 'ff']:
        # This file is consumed only by a NEW OpenROAD process after patching exits.
        check = 'max' if c == 'ss' else 'min'
        target_report = '\n'
        for row in plan['patches']:
            target_report += ('foreach p [get_pins -hierarchical */D] {\n'
                              '  if {[get_full_name $p] eq {' + row['endpoint'] + '}} {\n'
                              '    puts \"S81_TARGET endpoint=[get_full_name $p] slack=[get_property $p slack_' + check + ']\"\n'
                              '  }\n}\n')
        source = corner_script(c, str(out), [],
                               ['physical/s81_ph_views/common/signoff_unc60.sdc'])
        (out / f'sta_{c}.tcl').write_text(source.rsplit('exit', 1)[0] + target_report + 'exit\n')
    return out


def run(out, binary):
    receipts = []
    for stage in ['patch', 'sta_ss', 'sta_ff']:
        log = out / (stage + '.log')
        if log.exists():
            raise ValueError('Stage log exists; refusing replay: ' + stage)
        with log.open('x') as stream:
            result = subprocess.run([binary, '-exit', str(out / (stage + '.tcl'))],
                                    stdout=stream, stderr=subprocess.STDOUT)
        receipts.append(dict(stage=stage, rc=result.returncode, log_sha256=sha(log)))
        (out / 'execution.json').write_text(json.dumps(receipts, indent=2) + '\n')
        if result.returncode:
            raise RuntimeError('Candidate failed stage ' + stage)
    # The two fresh sessions are the only timing authority. Missing target rows
    # fail closed; full-design deficits remain visible even when this pin passes.
    plan = json.loads((out / 'plan.json').read_text())
    required = {row['endpoint'] for row in plan['patches']}
    timing = {}
    for corner in ['ss', 'ff']:
        text = (out / f'sta_{corner}.log').read_text()
        values = {name: float(value) for name, value in re.findall(
            r'^S81_TARGET endpoint=(\S+) slack=([-+0-9.eE]+)$', text, re.M)}
        worst = re.search(r'^OT_WS ([-+0-9.eE]+)$', text, re.M)
        if set(values) != required or not worst or '[ERROR' in text:
            raise RuntimeError('Missing or invalid fresh ' + corner + ' timing')
        full = float(worst[1]) * 1e12
        if not all(math.isfinite(v) for v in [full, *values.values()]):
            raise RuntimeError('Non-finite fresh timing')
        timing[corner] = dict(target_slack_ps=values, full_design_worst_slack_ps=full)
    drc_text = (out / 'drc.rpt').read_text()
    drc_count = 0 if not drc_text.strip() else len(re.findall(r'violation type:', drc_text, re.I)) or None
    result = dict(status='MEASURED_CANDIDATE_NOT_ADOPTED', stages=receipts,
                  timing=timing, drc_count=drc_count,
                  target_timing_pass=all(v >= 15 for row in timing.values() for v in row['target_slack_ps'].values()),
                  full_design_gates_pass=(drc_count == 0 and all(row['full_design_worst_slack_ps'] >= 15 for row in timing.values())),
                  outputs={n: sha(out / n) for n in ['6_final.odb', '6_final.sdc', '6_final.spef', '6_final.v']})
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--base', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--openroad', default='openroad')
    a = ap.parse_args()
    prepare(a.base, a.out, json.loads(a.plan.read_text()))
    if a.run:
        run(a.out, a.openroad)
