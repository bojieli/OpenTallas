#!/usr/bin/env python3
"""WAVE-OPS-1 11-10 (COORD URGENT (a), HBM-CORES-B 20:22): does each die's wave src match its declared commit + approved
overlays?  ADVISORY (OWNER 11-03 targets, not gates).  Per die and gen host: manifest of the live src (inode cache),
then on epyc8 `wave_src_remote.py check` against src_sha (declared) and the composed tree of the last nightly run
(main + approved overlays + the die branch).  Writes runs/srccheck-<stamp>/<die>.json here and the hub file
intel2:/srv/opentallas-scratch2/claude/wave-ops-1/srccheck/<die>.json that kit_wave's FLAGS WAVE-SRC-DRIFT line reads.
usage: wave_src_check.py [compose_run_date]     (prints one summary line per die/host)"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nightly_wave_src as N

HUB_DIR = N.LANE + '/srccheck'


def main(argv):
    ref_run = argv[1] if len(argv) > 1 else '20261110dry'
    stamp = time.strftime('%Y%m%d-%H%M')
    out_dir = os.path.join(N.HERE, 'runs', 'srccheck-' + stamp)
    os.makedirs(out_dir, exist_ok=True)
    cfg = N.hub_cfg()
    dies = N.die_inputs(cfg)
    N.HOSTS[:] = sorted({h for d in dies.values() for h in d['gen_hosts']})
    N.push_tools()
    comp = json.loads(N.ssh(N.CHOST, 'cat %s/runs/%s/compose.json' % (N.LANE, ref_run)))
    mdir = '%s/runs/srccheck-%s' % (N.LANE, stamp)
    lines = []
    for die, d in dies.items():
        new = (comp.get('dies', {}).get(die) or {}).get('sha') or d['src_sha']
        per = {}
        for h in d['gen_hosts']:
            try:
                N.ssh(h, 'mkdir -p %s/cache %s' % (N.LANE, mdir), 60)
                N.remote(h, 'manifest %s %s/live_%s_%s.tsv --cache %s/cache/manifest.tsv' % (d['src'], mdir, die, h, N.LANE))
                if h != N.CHOST:
                    N.ssh(N.CHOST, 'mkdir -p %s && timeout 1200 scp -q -o BatchMode=yes %s:%s/live_%s_%s.tsv %s/' % (
                        mdir, h, mdir, die, h, mdir), 1300)
                N.ssh(N.CHOST, 'git -C %s cat-file -e %s^{commit} || git -C %s fetch -q origin %s' % (
                    N.REPO, d['src_sha'], N.REPO, d['src_sha']), 600, check=False)
                o = N.remote(N.CHOST, 'check %s %s/live_%s_%s.tsv %s %s %s/check_%s_%s.json' % (
                    N.REPO, mdir, die, h, d['src_sha'], new, mdir, die, h), 7200)
                r = json.loads(N.ssh(N.CHOST, 'cat %s/check_%s_%s.json' % (mdir, die, h), 120))
                per[h] = r
                lines.append('%s %s: mismatch %d (stale old git copies %d, modified not in git %d); live-only %d, '
                             'absent vs declared %d' % (die, h, len(r['stale']) + len(r['modified']), len(r['stale']),
                                                        len(r['modified']), len(r['live_only']), r['missing']))
            except Exception as e:
                per[h] = dict(error=str(e)[-300:])
                lines.append('%s %s: check ERROR %s' % (die, h, str(e)[-160:]))
        ok = {h: r for h, r in per.items() if 'error' not in r}
        worst = max(ok, key=lambda h: len(ok[h]['stale']) + len(ok[h]['modified'])) if ok else None
        rec = dict(src=d['src'], declared=d['src_sha'], composed=new, at=time.strftime('%Y-%m-%d %H:%M %Z'),
                   host=worst, hosts={h: (dict(stale=len(r['stale']), modified=len(r['modified']),
                                                live_only=len(r['live_only']), missing=r['missing'])
                                           if 'error' not in r else r) for h, r in per.items()})
        if worst:
            w = ok[worst]
            rec.update(mismatch=len(w['stale']) + len(w['modified']), stale=len(w['stale']),
                       undeclared=len(w['modified']), sample_stale=w['stale'][:30], sample_modified=w['modified'][:30])
        json.dump(dict(rec, per_host=per), open(os.path.join(out_dir, die + '.json'), 'w'), indent=1)
        N.ssh(N.HUB, 'mkdir -p %s && cat > %s/%s.json.tmp && mv %s/%s.json.tmp %s/%s.json' % (
            HUB_DIR, HUB_DIR, die, HUB_DIR, die, HUB_DIR, die), 120, input=json.dumps(rec))
    open(os.path.join(out_dir, 'SUMMARY.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('OUT ' + out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
