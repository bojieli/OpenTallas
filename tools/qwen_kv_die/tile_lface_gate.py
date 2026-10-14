#!/usr/bin/env python3
"""r5 tile lface gate: registered admission/credit faces + live streamed identity, positives and observed mutants.

Run inside a workdir staged by tools/qwen_kv_die/xcache_query40_prepare.py (src/ + provenance.json) with the three
lface sources added under src/.  ot-run only (Verilator builds of the real GT3072 control + CLOSED children).
"""
import concurrent.futures, json, os, pathlib, subprocess, sys

out = pathlib.Path.cwd()
m = json.loads((out / 'provenance.json').read_text())
src = out / 'src'
vlt = os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
LFACE = ['rtl/physical/ot_qwen_live_face.sv', 'rtl/physical/ot_qwen_tile_ctl_lface.sv',
         'rtl/test/qwen_kv_die/tb_qwen_tile_lface.sv']
sources = [s for s in m['sources'] if not s.endswith('tb_qwen_xcache_query40.sv')] + LFACE
# name, params, expected failure text (None = must PASS)
cases = [
    ('pos_lat2_d5_stall', dict(LAT=2, DEPTH=5, STALL=1), None),
    ('pos_lat6_d9_stall', dict(LAT=6, DEPTH=9, STALL=1), None),
    ('rate_lat2_d5', dict(LAT=2, DEPTH=5, STALL=0), None),
    ('rate_lat6_d9', dict(LAT=6, DEPTH=9, STALL=0), None),
    ('mut_margin', dict(LAT=2, DEPTH=5, STALL=1, QMUT=1), 'live queue overflow fault'),
    ('mut_heldlevel', dict(LAT=2, DEPTH=5, STALL=1, QMUT=2), 'live '),
    ('mut_accept_unaligned', dict(LAT=2, DEPTH=5, STALL=1, MUT=2), 'production accepted context mismatch'),
]
only = set(sys.argv[1:])


def run(case):
    name, params, expected = case
    obj = out / ('obj_' + name)
    cmd = [vlt, '--binary', '--timing', '-j', '4', '-Wno-fatal', '-Wno-lint', '-Wno-style', '--top-module',
           'tb_qwen_tile_lface', '--Mdir', str(obj), '-DXCACHE_TP8'] + [f'-G{k}={v}' for k, v in params.items()] + sources
    with (out / (name + '_build.log')).open('w') as log:
        subprocess.run(cmd, cwd=src, stdout=log, stderr=subprocess.STDOUT, check=True)
    r = subprocess.run([str(obj / 'Vtb_qwen_tile_lface')], cwd=src, capture_output=True, text=True)
    text = r.stdout + r.stderr
    (out / (name + '.log')).write_text(text)
    rec = dict(case=name, params=params, rc=r.returncode, expected_failure=expected,
               lines=[ln for ln in text.splitlines() if ln.startswith(('LFACE', 'PASS', '%Error', '[')) or 'fatal' in ln.lower()][:8])
    if expected:
        rec['verdict'] = 'MUTANT_FAILS' if (r.returncode != 0 and expected in text) else 'MUTANT_ESCAPED'
    else:
        rec['verdict'] = 'PASS' if (r.returncode == 0 and 'PASS lface registered faces' in text) else 'FAIL'
    shutil_rm(obj)
    return rec


def shutil_rm(p):
    import shutil
    shutil.rmtree(p, ignore_errors=True)


todo = [c for c in cases if not only or c[0] in only]
with concurrent.futures.ThreadPoolExecutor(max_workers=len(todo)) as p:
    res = list(p.map(run, todo))
(out / 'lface_gate.json').write_text(json.dumps(dict(sources=sources, cases=res), indent=1) + '\n')
for r in res:
    print(r['verdict'], r['case'], ' | '.join(r['lines'][:3]), flush=True)
ok = all(r['verdict'] in ('PASS', 'MUTANT_FAILS') for r in res)
print('GATE', 'PASS' if ok else 'FAIL', flush=True)
sys.exit(0 if ok else 1)
