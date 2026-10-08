"""Prepare/run a literal root hold-cell patch with fresh SS and FF signoff processes.

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
from w18.corner_sta import script as corner_script

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {f'HB{i}xp67_ASAP7_75t_R' for i in range(1, 5)}
AREA = {f'HB{i}xp67_ASAP7_75t_R': a for i, a in enumerate([.05832, .0729, .08748, .10206], 1)}
AOI = {'_130070_/A1', '_129371_/A1', '_130136_/A1'}
DFF = {'DFFHQNx1_ASAP7_75t_R', 'DFFHQNx2_ASAP7_75t_R'}
ENDPOINT = re.compile(r'u_root\.(?:(?:qm|flm)\[\d+\]\[\d+\]\$_DFFE_PP_|r2_w\[\d+\]\$_DFF_P_)/D')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(plan):
    if plan.get('schema') != 'opentallas.s81.root_selective_patch.v1':
        raise ValueError('Unknown patch schema')
    if plan.get('cycles_added') != 0:
        raise ValueError('Only zero-cycle physical delay patches permitted')
    seen = set()
    area = 0.
    for row in plan['patches']:
        endpoint = row['endpoint']
        if (not ENDPOINT.fullmatch(endpoint) and endpoint not in AOI) or endpoint in seen:
            raise ValueError('Duplicate or out-of-scope root pin')
        seen.add(endpoint)
        expected = {'AOI21x1_ASAP7_75t_R'} if endpoint in AOI else DFF
        if row.get('expected_master') not in expected:
            raise ValueError('Incorrect expected original master')
        if not row['cells'] or any(c not in ALLOWED for c in row['cells']):
            raise ValueError('Only literal non-inverting characterized hold cells permitted')
        if not math.isfinite(row['baseline_ss_ps']) or row['baseline_ss_ps'] < 15:
            raise ValueError('Cannot patch an already failing setup endpoint')
        area += sum(AREA[c] for c in row['cells'])
    if not seen:
        raise ValueError('Empty patch')
    targets = plan['timed_endpoints']
    if not targets or len(targets) != len(set(targets)) or any(not ENDPOINT.fullmatch(p) for p in targets):
        raise ValueError('Missing, duplicate or out-of-scope timed receiver')
    aoi_receivers = {'_130070_/A1': 13, '_129371_/A1': 42, '_130136_/A1': 7}
    for pin in seen:
        required = f'u_root.r2_w[{aoi_receivers[pin]}]$_DFF_P_/D' if pin in AOI else pin
        if required not in targets:
            raise ValueError('Patch receiver missing from timing requirements')
    if not math.isclose(plan.get('area_added_um2', -1), area, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError('Area must equal characterized inserted-cell inventory')


def prepare(base, out, plan):
    validate(plan)
    if out.exists():
        raise ValueError('Candidate directory already exists; evidence is immutable')
    for name in ['6_final.odb', '6_final.sdc', '6_final.spef']:
        if sha(base / name) != plan['original_sha256'][name]:
            raise ValueError('Original artifact hash mismatch: ' + name)
    if any(not re.fullmatch(r'[A-Za-z0-9_./-]+', str(p)) for p in (base, out)):
        raise ValueError('Unsupported Tcl path characters')
    out.mkdir(parents=True)
    shutil.copy2(base / '6_final.sdc', out / '6_final.sdc')
    (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    # Load the exact same SS libraries, parasitics and effective signoff constraints.
    prefix = corner_script('ss', str(base), [],
                           ['physical/s81_ph_views/common/signoff_unc60.sdc']).split('puts "OT_CORNER')[0]
    rows = []
    for row in plan['patches']:
        rows.append('  {' + row['endpoint'] + '} {' + row['expected_master'] + '} {' + ' '.join(row['cells']) + '}')
    actions = 'set patches {\n' + '\n'.join(rows) + '\n}\n'
    body = (ROOT / 'physical/s81_ph_views/gather/root_selective_patch.tcl').read_text()
    (out / 'patch.tcl').write_text(prefix + '\nset patch_out {' + str(out) + '}\n' + actions + body)
    for c in ['ss', 'ff']:
        # This file is consumed only by a NEW OpenROAD process after patching exits.
        check = 'max' if c == 'ss' else 'min'
        target_report = '\n'
        for endpoint in plan['timed_endpoints']:
            target_report += ('foreach p [get_pins -hierarchical */D] {\n'
                              '  if {[get_full_name $p] eq {' + endpoint + '}} {\n'
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
    if sha(out / '6_final.sdc') != plan['original_sha256']['6_final.sdc']:
        raise RuntimeError('Original constraints changed during patch')
    required = set(plan['timed_endpoints'])
    timing = {}
    for corner in ['ss', 'ff']:
        text = (out / f'sta_{corner}.log').read_text()
        matches = re.findall(r'^S81_TARGET endpoint=(\S+) slack=([-+0-9.eE]+)$', text, re.M)
        if len(matches) != len(required):
            raise RuntimeError('Missing or duplicate fresh timing endpoint')
        values = {name: float(value) for name, value in matches}
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
