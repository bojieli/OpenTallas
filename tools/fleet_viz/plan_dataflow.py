#!/usr/bin/env python3
"""WEBVIEW-1 2026-11-03: data-flow link records (explorer/dataflow) for the current plans of record.

For every Chip Explorer die of kind 'plan' (explorer_dies.json, kept current by plan_now.py) whose geometry cache
changed, run dataflow_links.py explorer -> explorer/dataflow/data/plan_<die>.links.json.gz (role canonical).  Records
of other ids are kept in index.json as role 'previous' with their token designs moved to legacy_token_designs, so the
data-flow and token pages open the current plan by default."""
import gzip, hashlib, json, os, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
STATE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
OUT = HERE / 'explorer' / 'dataflow' / 'data'
TOK = dict(s81=['ds_rom'], s81_head=['ds_rom'], qwen_compute=['qwen_rom'], qwen_kvsys=['qwen_rom'], hbm=['hbm_gen_qwen', 'hbm_gen_ds'])
DESIGN = dict(s81='ds_rom', s81_head='ds_rom', qwen_compute='qwen_rom', qwen_kvsys='qwen_rom', hbm='hbm')


def main():
    dies = [d for d in json.loads((HERE / 'explorer_dies.json').read_text())['dies'] if d.get('kind') == 'plan']
    idx_p = OUT / 'index.json'
    idx = json.loads(idx_p.read_text())
    have = {r['id']: r for r in idx['records']}
    ids = set()
    for d in dies:
        g = STATE / 'explorer' / 'geom' / (d['id'] + '.json.gz')
        if not g.exists(): print('no geometry yet:', d['id']); continue
        ids.add(d['id'])
        sha = hashlib.sha256(g.read_bytes()).hexdigest()
        r = have.get(d['id'])
        if r and any(i.get('sha256') == sha for i in r.get('inputs') or []): continue
        rec = json.loads(gzip.decompress(g.read_bytes()))
        die = d['plan_die']
        cmd = [sys.executable, str(HERE / 'dataflow_links.py'), 'explorer', '--id', d['id'], '--out', str(OUT),
               '--label', '%s · plan of record %s (%s)' % (d['label'].split(' (plan')[0], pathlib.PurePosixPath(d['plan_path']).name, (rec.get('plan_date') or '')[:10]),
               '--design', DESIGN.get(die, die), '--token-designs', ','.join(TOK.get(die, [])),
               '--revision', '%s @ %s sha256 %s' % (d['plan_path'], rec['commit'][:10], rec.get('plan_sha256')), '--role', 'canonical',
               '--reach', str(d.get('reach_um') or 405.0), '--reach-source', 'die plan reach_um',
               '--source-commit', rec['commit'], '--geom', str(g), '--geom-path', str(g)]
        p = subprocess.run(['nice', '-n', '15'] + cmd, capture_output=True, text=True, timeout=1800)
        print(p.stdout.strip() or p.stderr[-400:])
    idx = json.loads(idx_p.read_text())
    ch = False
    for r in idx['records']:
        if r['id'] in ids: continue
        if r.get('token_designs') or r.get('role') == 'canonical':
            r['legacy_token_designs'] = r.get('legacy_token_designs') or r.get('token_designs') or []
            r['token_designs'] = []; r['legacy_role'] = r.get('legacy_role') or r.get('role'); r['role'] = 'previous'; ch = True
    if ch:
        idx_p.write_text(json.dumps(idx, indent=1) + '\n'); print('index: older records demoted to previous')


if __name__ == '__main__':
    main()
