#!/usr/bin/env python3
"""Data-flow link records for the CURRENT plans of record (one `plan_<die>` record per die).

    python3 -I refresh_data.py [--die s81,...] [--out <EXPLORER_STATE>/dataflow] [--force]

For every die of the design index: plan geometry from the plan file (plan_now.plan_geometry: partitions, hard cores,
aggregated plan ports), then tools/fleet_viz/dataflow_links.py `explorer` -> <out>/plan_<die>.links.json.gz and
<out>/index.json.  A record is rebuilt only when its plan (path + commit) changed.  The explorer server calls
refresh() in a background thread whenever the design index changes, so no extra timer is needed; the CLI is for a
timer or a manual run.  Token records are NOT refreshed here: they are exports of the token simulator
(tools/token_path_export.py) and need its measured inputs; see README.md.
"""
import argparse, gzip, hashlib, json, os, pathlib, subprocess, sys, threading, time

HERE = pathlib.Path(__file__).resolve().parent
FV = HERE.parent / 'fleet_viz'
sys.path.insert(0, str(FV))
DESIGN = dict(s81='ds_rom', s81_head='ds_rom', qwen_compute='qwen_rom', qwen_kvsys='qwen_rom', hbm='hbm')
TOKENS = dict(s81=['ds_rom'], s81_head=['ds_rom'], qwen_compute=['qwen_rom'], qwen_kvsys=['qwen_rom'], hbm=['hbm_gen_qwen', 'hbm_gen_ds'])
_LOCK = threading.Lock()


def refresh(idx, out, dies=None, force=False, log=lambda *a: None):
    """-> {die: 'built' | 'current' | 'failed: ...'}"""
    import plan_now, design_index   # the engines (plan file loader + geometry)
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    res = {}
    with _LOCK:
        stamp_f = out / 'stamps.json'
        try: stamps = json.loads(stamp_f.read_text())
        except (OSError, ValueError): stamps = {}
        for die in dies or idx['dies']:
            n = idx['nodes'].get(die)
            if not n: continue
            p = n['plan']; key = '%s@%s' % (p['path'], p.get('commit'))
            rid = 'plan_' + die
            if not force and stamps.get(die) == key and (out / (rid + '.links.json.gz')).is_file(): res[die] = 'current'; continue
            try:
                t0 = time.time()
                g = plan_now.plan_geometry(die, p['path'], p.get('commit') or '', design_index.load_plan(p['path']))
                gf = out / (rid + '.geom.json.gz'); gf.write_bytes(gzip.compress(json.dumps(g, separators=(',', ':')).encode(), 5))
                stem = pathlib.PurePosixPath(p['path']).name.replace('.json.gz', '').replace('.json', '')
                cmd = [sys.executable, '-I', str(FV / 'dataflow_links.py'), 'explorer', '--id', rid, '--out', str(out),
                       '--label', '%s · plan of record %s (%s)' % (n['label'], stem, str(p.get('date') or '')[:10]), '--design', DESIGN.get(die, die),
                       '--token-designs', ','.join(TOKENS.get(die, [])), '--revision', '%s @ %s' % (p['path'], (p.get('commit') or '')[:10]), '--role', 'canonical',
                       '--reach', str(p.get('reach_um') or 405.0), '--reach-source', 'die plan reach_um', '--geom', str(gf), '--geom-path', str(gf)]
                if p.get('commit'): cmd += ['--source-commit', p['commit']]
                r = subprocess.run(['nice', '-n', '15'] + cmd, capture_output=True, text=True, timeout=1800)
                if r.returncode: raise RuntimeError((r.stderr or r.stdout)[-300:])
                stamps[die] = key; res[die] = 'built'; log(die, (r.stdout.strip().splitlines() or [''])[-1], '%.1fs' % (time.time() - t0))
            except Exception as e:   # one die must not stop the others
                res[die] = 'failed: %s: %s' % (type(e).__name__, str(e)[:200]); log(die, res[die])
        tmp = stamp_f.with_suffix('.tmp'); tmp.write_text(json.dumps(stamps)); os.replace(tmp, stamp_f)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    state = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
    ap.add_argument('--die'); ap.add_argument('--force', action='store_true')
    ap.add_argument('--out', default=str(pathlib.Path(os.environ.get('EXPLORER_STATE', state / 'explorer_v1')) / 'dataflow'))
    a = ap.parse_args()
    idx = json.loads(pathlib.Path(os.environ.get('DESIGN_INDEX', state / 'design_index.json')).read_text())
    res = refresh(idx, a.out, a.die.split(',') if a.die else None, a.force, log=lambda *x: print(*x, flush=True))
    print(json.dumps(res))
    sys.exit(1 if any(v.startswith('failed') for v in res.values()) else 0)


if __name__ == '__main__':
    main()
