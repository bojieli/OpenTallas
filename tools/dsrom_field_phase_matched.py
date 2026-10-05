#!/usr/bin/env python3
"""Matched admission control on retained full-region PQ hardware; no RTL build or adoption."""
import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def parse(text, expected, nops, serial):
    writes = {k: {} for k in ('W', 'VMW', 'VMS')}
    events = {k: [] for k in ('A', 'G', 'E', 'XR')}
    node, profile, passes, errors = [], [], [], []
    for line in text.splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] in writes:
            if len(t) != 4 or not re.fullmatch('[0-9a-f]{8}', t[3]):
                errors.append('malformed write'); continue
            cyc, address, value = int(t[1]), int(t[2]), int(t[3], 16)
            writes[t[0]].setdefault(address, []).append((cyc, value))
        elif t[0] in events:
            if len(t) != 3:
                errors.append('malformed event'); continue
            events[t[0]].append(tuple(map(int, t[1:])))
        elif t[0] == 'NODE':
            node.append({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', line)})
        elif t[0] == 'PROFILE':
            profile.append({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', line)})
        elif t[0] == 'PASS':
            passes.append(line)
        elif t[0] == 'FAIL':
            errors.append(line)
    for kind, words in writes.items():
        if set(words) != set(expected) or any(len(words.get(a, [])) != 1 or words[a][0][1] != v for a, v in expected.items()):
            errors.append(kind + ' exact values/counts mismatch')
    for a in expected:
        if all(len(writes[k].get(a, [])) == 1 for k in writes):
            w, commit, stored = (writes[k][a][0] for k in writes)
            if not (commit == stored and commit[0] == w[0] + 1):
                errors.append('commit calibration mismatch')
    if len(node) != 1 or node[0].get('fault') != 0:
        errors.append('node/fault')
    if len(profile) != 1 or profile[0].get('serial_offer') != int(serial):
        errors.append('profile/mode')
    if len(passes) != 1 or not re.fullmatch(r'PASS cycles=\d+', passes[0]) or not text.rstrip().endswith(passes[0]):
        errors.append('terminal')
    if [i for i, cyc in events['A']] != list(range(nops)):
        errors.append('accept count/order')
    for k in ('G', 'E'):
        if [tag for cyc, tag in events[k]] != [i % 4 for i in range(nops)]:
            errors.append(k + ' count/order')
    if len(profile) == 1:
        p = profile[0]
        if p.get('input_read_beats') != len(events['XR']) or p.get('input_bytes') != 256 * len(events['XR']):
            errors.append('read count')
        if len(node) == 1 and p.get('last_vm_commit', 10**9) > node[0].get('idle', -1):
            errors.append('retired before visibility')
    return dict(pass_=not errors, errors=errors[:20], rows=len(expected), node=node, profile=profile, events=events)


def one(task):
    import dsrom_recovery_field as F
    import numpy as np
    F.G.set_arith('chunk8')
    root, plan_dir, key, phases, region, rb, bfs, tb, retained = task
    rd = Path(root) / F.gname(key) / f'r{region:03d}'
    rd.mkdir(parents=True, exist_ok=False)
    img = rd / 'image'; img.mkdir()
    with np.load(Path(plan_dir) / 'x.npz') as z:
        xs = {p['phase']: z[p['phase']] for p in phases}
    ops, expect, metas = F.node_image(Path(plan_dir), phases, region, rb, bfs, xs, img)
    (rd / 'ops.txt').write_text(ops)
    (rd / 'expected.json').write_text(json.dumps(expect, sort_keys=True) + '\n')
    image_pins = {p.name: sha(p) for p in img.iterdir() if p.is_file()}
    (rd / 'image_sha256.json').write_text(json.dumps(image_pins, sort_keys=True) + '\n')
    results = {}
    for mode in ('overlap', 'serial'):
        command = [str(tb), str(img), str(rd / 'ops.txt')]
        if mode == 'serial': command.append('--serial-offer')
        start = time.monotonic()
        with (rd / (mode + '.log')).open('w') as log:
            p = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        r = parse((rd / (mode + '.log')).read_text(), expect, len(phases), mode == 'serial')
        r.update(returncode=p.returncode, seconds=time.monotonic()-start, log_sha256=sha(rd / (mode+'.log')))
        if p.returncode: r['pass_'] = False
        results[mode] = r
        if not r['pass_']: break
    old = Path(retained) / F.gname(key) / f'r{region:03d}' / 'result.json'
    calibration = False
    if old.exists() and results['overlap']['pass_']:
        historical = json.loads(old.read_text())
        calibration = results['overlap']['node'] == [historical['node']]
        for i, m in enumerate(historical['ops']):
            calibration &= results['overlap']['events']['A'][i][1] == m['accept']
            calibration &= results['overlap']['events']['G'][i][0] == m['go']
            calibration &= results['overlap']['events']['E'][i][0] == m['end']
    passed = calibration and len(results) == 2 and all(r['pass_'] for r in results.values())
    result = dict(group=F.gname(key), region=region, pass_=passed, calibration=calibration, metas=metas,
                  phases=len(phases), image_sha256=image_pins, results=results)
    (rd / 'result.json').write_text(json.dumps(result, indent=1)+'\n')
    # Retain images on any failure; successful images are reproducible from the pinned input NPZs.
    if passed:
        import shutil
        shutil.rmtree(img)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--tb', type=Path, required=True)
    p.add_argument('--retained-runs', type=Path, required=True)
    p.add_argument('--jobs', type=int, default=8)
    a = p.parse_args()
    import dsrom_recovery_field as F
    plan = json.loads((a.plan_dir/'plan.json').read_text())
    a.output.mkdir(parents=True, exist_ok=False)
    groups = {k:v for k,v in F.node_groups(plan, {'attn.wo_a','ffn.experts_gu','ffn.down'}).items() if k[0] == 20}
    tasks = []
    for key, phases in sorted(groups.items()):
        for region in sorted({r for ph in phases for r in ph['regions']}):
            tasks.append((str(a.output), str(a.plan_dir), key, [ph for ph in phases if region in ph['regions']],
                          region, plan['region_bounds'], set(plan['bf_sites']), a.tb, str(a.retained_runs)))
    results = []
    try:
        with cf.ProcessPoolExecutor(a.jobs) as pool:
            for r in pool.map(one, tasks):
                results.append(r)
                print(r['group'], r['region'], 'PASS' if r['pass_'] else 'FAIL', flush=True)
    finally:
        (a.output/'summary.json').write_text(json.dumps(dict(
            scope='Matched serial admission versus overlap on SAME retained PQ RTL; not historical bare-PQ0 or full-token/physical qualification',
            expected_cases=len(tasks), completed=len(results), passed=sum(r['pass_'] for r in results),
            results=results), indent=1)+'\n')
    return 0 if len(results)==len(tasks) and all(r['pass_'] for r in results) else 1

if __name__ == '__main__':
    raise SystemExit(main())
