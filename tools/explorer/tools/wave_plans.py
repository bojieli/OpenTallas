#!/usr/bin/env python3
"""plan_now on the plans the wave builds and the count counts (COORD / GEOM review 2026-11-14).

The sign-off count (release_tree_plan.py, COUNT-FRICTION-1) counts each die against the kit wave's plan
(cache: plans[*].plan_counted = {host, path, sha}), which may not be on origin/main yet.  This wrapper stages those plan
files into the plan repo checkout (physical/die_plan/_wave/<die>/<stem>_<sha12>.json, sha256 checked), then runs the
unchanged plan_now with its plan list pointing at them, so the explorer's partitions, type list and denominators are the
count's.  A die without plan_counted keeps the pinned plan of record.  Writes <state>/wave_plans.json (what was used).

    python3 -I wave_plans.py        # env as refresh.sh: FLEET_VIZ_STATE, FLEET_VIZ_REPO, OT_RELEASE_TREE_DIR, ...
"""
import hashlib, json, os, pathlib, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'fleet_viz'))
import plan_now   # noqa: E402

STATE = pathlib.Path(os.environ['FLEET_VIZ_STATE']); REPO = pathlib.Path(os.environ['FLEET_VIZ_REPO'])
OFF = set(os.environ.get('OFF_LIMITS_HOSTS', 'epyc4,epyc5,epyc6').split(','))


def stage():
    c = json.loads((STATE / 'release_tree_plan_cache.json').read_text()); out = {}
    for key, v in (c.get('plans') or {}).items():
        die = v.get('die') or key.split('/')[0]; pc = v.get('plan_counted')
        rec = dict(pinned='physical/die_plan/' + key if not key.startswith('physical/') else key, pinned_src=v.get('plan_src'), types=v.get('types'), wave_plan_sha=v.get('wave_plan_sha'), drift=v.get('drift'))
        if pc and pc.get('host') and pc['host'] not in OFF:
            stem = pathlib.PurePosixPath(pc['path']).name.replace('.json.gz', '').replace('.json', '')
            rel = 'physical/die_plan/_wave/%s/%s_%s.json' % (die, stem, pc['sha']); dst = REPO / rel
            try:
                if not dst.is_file():
                    dst.parent.mkdir(parents=True, exist_ok=True); tmp = dst.with_suffix('.part')
                    r = subprocess.run(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ControlPath=none', '%s:%s' % (pc['host'], pc['path']), str(tmp)], capture_output=True, text=True, timeout=300)
                    if r.returncode: raise RuntimeError('scp: ' + r.stderr.strip()[-160:])
                    got = hashlib.sha256(tmp.read_bytes()).hexdigest()
                    if not got.startswith(pc['sha']): tmp.unlink(); raise RuntimeError('sha256 %s is not the counted %s (the wave plan changed since the count)' % (got[:12], pc['sha']))
                    os.replace(tmp, dst)
                rec.update(rel=rel, sha=pc['sha'], host=pc['host'], path=pc['path'], staged=dst.stat().st_mtime, source='count cache plan_counted (kit wave plan)')
            except Exception as e:
                rec['error'] = '%s: %s' % (type(e).__name__, e)
        out[die] = rec
    (STATE / 'wave_plans.json').write_text(json.dumps(dict(generated=time.time(), count_generated=c.get('generated'), dies=out), indent=1))
    return out


ARGS = sys.argv[1:]


def main():
    W = stage()
    orig = plan_now.plans_of_record

    def plans():
        base, src = orig()
        return [(d, (W.get(d) or {}).get('rel') or rel) for d, rel in base], src + ' + wave plans counted (tools/explorer/tools/wave_plans.py)'
    plan_now.plans_of_record = plans
    sys.argv = [sys.argv[0]]
    plan_now.main()
    # the staged plans are not in git: give them the facts the pages show (sha, staging time, where the wave reads them)
    f = STATE / 'plan_now.json'; d = json.loads(f.read_text())
    for row in d.get('dies') or []:
        w = W.get(row['die']) or {}
        if w.get('rel') == row.get('plan_path'):
            row.update(plan_commit=None, plan_sha256=w['sha'], plan_date=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(w['staged'])),
                       plan_subject='kit wave plan %s:%s (sha %s), the plan the sign-off count counts; not on origin/main yet (pinned plan of record: %s)' % (w['host'], w['path'], w['sha'], w.get('pinned_src') or w.get('pinned')),
                       wave=dict(sha=w['sha'], host=w['host'], path=w['path'], pinned=w.get('pinned_src') or w.get('pinned'), count_types=w.get('types')))
    tmp = f.with_suffix('.tmp2'); tmp.write_text(json.dumps(d, separators=(',', ':'))); os.replace(tmp, f)
    print(json.dumps({k: (v.get('rel') or 'pinned: ' + str(v.get('error') or 'no plan_counted')) for k, v in W.items()}))
    if '--plan-only' in ARGS: return
    r = subprocess.run([sys.executable, '-I', str(HERE.parents[1] / 'fleet_viz' / 'design_index.py')], timeout=900)
    if r.returncode: sys.exit(r.returncode)
    overlay(W)


def overlay(W):
    """The sign-off count is the authority on what is signed: every type / core the count credits (signed_types, signed_cores,
    dedup credits) is signed in the index, with the record the count used.  A design the count credits on the R-MINIMAL gates
    while its own signoff.json verdict is not SIGNED is labelled "signed off (R-MINIMAL)"."""
    f = pathlib.Path(os.environ.get('DESIGN_INDEX', STATE / 'design_index.json')); idx = json.loads(f.read_text())
    c = json.loads((STATE / 'release_tree_plan_cache.json').read_text()); N = idx['nodes']; fixed = {}
    for v in (c.get('plans') or {}).values():
        die = v.get('die')
        if die not in N: continue
        for level, key, mk in (('type', 'signed_types', '%s.t.%s'), ('core', 'signed_cores', '%s.c.%s')):
            src = v.get(key) or {}
            for name in (src if isinstance(src, (dict, list)) else []):
                n = N.get(mk % (die, name))
                if not n: continue
                st = n.setdefault('status', {}); via = src[name] if isinstance(src, dict) else None
                if st.get('state') != 'signed':
                    st.update(was=dict(state=st.get('state'), label=st.get('label')), state='signed', label='signed off'); fixed[die] = fixed.get(die, 0) + 1
                st['counted'] = True
                if via: st['count_record'] = (via[0] if isinstance(via, list) and via else str(via))[:400]
        ded = v.get('dedup_credited') or {}
        for name in (ded if isinstance(ded, (dict, list)) else []):
            n = N.get('%s.t.%s' % (die, name))
            if n and n['status'].get('state') != 'signed': n['status'].update(was=dict(state=n['status'].get('state')), state='signed', label='signed off (dedup credit)', counted=True); fixed[die] = fixed.get(die, 0) + 1
        dn = N[die]; dn['count'] = dict(types=v.get('types'), signed_types=len(v.get('signed_types') or []), signed_cores=len(v.get('signed_cores') or []), plan_sha=(W.get(die) or {}).get('sha') or v.get('plan_sha'), generated=c.get('generated'))
        w = W.get(die) or {}
        if w.get('rel'): dn['plan']['wave'] = dict(sha=w['sha'], host=w['host'], path=w['path'], pinned=w.get('pinned_src') or w.get('pinned'))
    for n in N.values():
        st = n.get('status') or {}
        if n['level'] != 'die' and st.get('state') == 'signed':
            verdict = str((st.get('metrics') or {}).get('verdict') or '')
            if verdict and not verdict.startswith(('SIGNED', 'LOCAL_PASS')): st['basis'] = 'R-MINIMAL'; st['label'] = 'signed off (R-MINIMAL)'
    for die in idx['dies']:   # the per-state counts follow
        dn = N.get(die)
        if not dn: continue
        hip = set(dn.get('hard_ip') or [])
        for level in ('type', 'core'):
            cnt = {s: 0 for s in idx['states']}
            for n in N.values():
                if n['die'] == die and n['level'] == level: cnt['hard ip' if n['id'] in hip else n['status'].get('state', 'not built')] = cnt.get('hard ip' if n['id'] in hip else n['status'].get('state', 'not built'), 0) + 1
            dn['counts'][level] = cnt
    idx['count_overlay'] = dict(fixed=fixed, count_generated=c.get('generated'))
    tmp = f.with_suffix('.tmp3'); tmp.write_text(json.dumps(idx, separators=(',', ':'))); os.replace(tmp, f)
    print('count overlay: set signed', fixed)


if __name__ == '__main__':
    main()
