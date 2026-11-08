"""DIE-HBM-90-OPSA count dry run (COUNT-AUDIT-2 method): the coord counter's own plan_designs / fetch-format / credit_designs
on the base and the event plan, overlays laid as release_tree_plan.py does (d35a, d35b, d35c, d44v; *.gz gunzipped)."""
import gzip, json, os, shutil, subprocess, sys, types
RTP, REPO, BASED, NEWD, OUT = sys.argv[1:6]
src = open(RTP).read()
m = types.ModuleType('rtp'); m.__file__ = RTP
exec(compile(src.replace("if __name__ == '__main__':", "if False:"), RTP, 'exec'), m.__dict__)
POR = REPO + '/physical/die_plan/hbm/plan_of_record/'
def lay(dst, d44v):
    if os.path.exists(dst): shutil.rmtree(dst)
    os.makedirs(dst)
    for ov in ('d35a', 'd35b', 'd35c', d44v):
        base = ov if os.path.isabs(ov) else POR + ov
        for root, _, fs in os.walk(base):
            for f in fs:
                rel = os.path.relpath(os.path.join(root, f), base)
                if rel in ('die_plan.json', 'die_plan.json.gz'): continue
                o = os.path.join(dst, rel[:-3] if rel.endswith('.gz') else rel); os.makedirs(os.path.dirname(o), exist_ok=True)
                if rel.endswith('.gz'): open(o, 'wb').write(gzip.open(os.path.join(root, f)).read())
                else: shutil.copy(os.path.join(root, f), o)
    return json.load(gzip.open(os.path.join(base, 'die_plan.json.gz')))
# record pins exactly as fetch_rec_pins: REC_PINS_PY on the record host, canon_pin_rows
key = '/srv/opentallas-scratch2/claude/hbm-hard-2/resign/opsaC2_du/signoff/signoff.json'
r = subprocess.run(['ssh', '-n', '-o', 'ControlPath=none', '-o', 'BatchMode=yes', 'intel1', 'python3 -c %s' % m.shlex_quote(m.REC_PINS_PY) + ' < /dev/stdin'],
                   capture_output=True, text=True) if False else None
inp = json.dumps([[key, key]])
r = subprocess.run(['ssh', '-o', 'ControlPath=none', '-o', 'BatchMode=yes', 'intel1', 'python3 -c %s' % m.shlex_quote(m.REC_PINS_PY)],
                   input=inp, capture_output=True, text=True, timeout=600)
x = json.loads(r.stdout.strip().splitlines()[-1])[key]
da = x['die_area']
got = dict(rows=m.canon_pin_rows(x['doc']), outline_nm=(m._nm(da[2] - da[0]), m._nm(da[3] - da[1])), read='intel1:' + x['read'], source=x['source'])
if x.get('shapes'): got['shapes'] = {k: [tuple(v) for v in vv] for k, vv in x['shapes'].items()}
rec = dict(scan_host='intel1', pins_path=key, path=key)
res = {}
for tag, d in (('base', BASED), ('new', NEWD)):
    pd = os.path.join(OUT, 'por_' + tag)
    P = lay(pd, d)
    open(os.path.join(pd, 'die_plan.json'), 'w').write(json.dumps(P))
    designs, rows = m.plan_designs(P, pd)
    signed, unmatched = m.credit_designs(designs, rows, {'ot_hgi_sfu_opsa_rest': [('opsaC2_du', rec)]}, {('intel1', key): got})
    res[tag] = (designs, rows, signed, unmatched)
    print(tag, 'designs', len(designs), 'opsa_rest designs', [k for k, g in designs.items() if g['module'] == 'ot_hgi_sfu_opsa_rest'],
          'signed', signed, 'unmatched', {k: [u[:300] for u in v] for k, v in unmatched.items()})
b, n = res['base'], res['new']
ch = sorted(k for k in set(b[0]) | set(n[0]) if b[1].get(k) != n[1].get(k) or {kk: vv for kk, vv in (b[0].get(k) or {}).items() if kk not in ('entries',)} != {kk: vv for kk, vv in (n[0].get(k) or {}).items() if kk not in ('entries',)})
print('design ids base', len(b[0]), 'new', len(n[0]), 'only base', sorted(set(b[0]) - set(n[0])), 'only new', sorted(set(n[0]) - set(b[0])))
print('designs whose pins/outline/instances differ:', ch)
for k in ch:
    for t, z in (('base', b), ('new', n)):
        g = z[0].get(k)
        if g: print('  ', t, k, {kk: g[kk] for kk in ('module', 'outline_um', 'pins_files', 'instances', 'types', 'orients') if kk in g})
