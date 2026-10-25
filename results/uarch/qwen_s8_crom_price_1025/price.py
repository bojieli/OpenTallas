import copy, importlib.util, json, os, re, shutil, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve().parent
T = R / 'tree'
SRC = R / 'sources'

def run(name, inp):
    (T / f'inputs_{name}.json').write_text(json.dumps(inp, indent=1))
    p = subprocess.run([sys.executable, '-I', 'tools/qwen_layerbench/toksim_compose.py', '--inputs', f'inputs_{name}.json', '--out', str(R / f'{name}.json')], cwd=T, capture_output=True, text=True)
    (R / f'{name}.log').write_text(p.stdout + p.stderr)
    if p.returncode: raise RuntimeError(f'{name} compose failed rc{p.returncode}: {p.stderr[-1500:]}')
    print(name, p.stdout.strip().splitlines()[-1], flush=True)
    return json.loads((R / f'{name}.json').read_text())

inp = json.loads((R / 'inputs_source.json').read_text())
os.environ.pop('DV2_S8DIE', None)
# Reproduce the historical compose: attnret98 measured +18 priced successor delta.
(T/'results/analytic_source_attn.json').write_text(json.dumps({'measured_span_edges':116}))
p = T/'tools/qwen_layerbench/dv_layer.py'
p.write_text(re.sub(r"^ATTNRET_REC = '[^']*'", "ATTNRET_REC = 'results/analytic_source_attn.json'", p.read_text(), flags=re.M))
run('source_reproduced', inp)
spec = importlib.util.spec_from_file_location('compose_helper', SRC / 'compose_tokfunc.py')
C = importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
meta = C.s8die_tree(T)
for fn in ('dv_lower.py', 'dv_lower_vec.py', 'dv_lower_mat.py'):
    shutil.copy(SRC / fn, T / 'tools/qwen_layerbench' / fn)
p = T / 'tools/qwen_layerbench/dv_lower_vec.py'
p.write_text(p.read_text().replace('e + 2 * abs(m - s)', 'e + D.ST_HOP * abs(m - s)'))
# The old98-edge attn-return measurement is on slice2. Use the compiler's current bound span, retaining its GAP qualification.
p = T / 'tools/qwen_layerbench/dv_layer.py'
p.write_text(re.sub(r"^ATTNRET_REC = '[^']*'", "ATTNRET_REC = 'results/analytic_bound_attn_unmeasured.json'", p.read_text(), flags=re.M))
agesdir = T / 'results/analytic_s8'
agesdir.mkdir(parents=True, exist_ok=True)
for k in ('slice','vec','stn'):
    shutil.copy(R / f'{k}_ages.json', agesdir / f'{k}_ages.json')
inp['dv'].pop('base_ages', None)
inp['dv']['ages'] = {k:f'results/analytic_s8/{k}_ages.json' for k in ('slice','vec','stn')}
inp['dv']['grade'] = 'PRICED'
inp['release_source'] = 'PREDICTED ONLY: bound S8 current ages + SC4/ST4 + actual L9 owners; no full-token qualification'
run('bound_current', inp)
# Invalid historical occupancy is a counterfactual only: the RTL hop is four.
p = T/'tools/qwen_layerbench/dv_lower_vec.py'
good = p.read_text()
try:
    p.write_text(good.replace('e + D.ST_HOP * abs(m - s)', 'e + 2 * abs(m - s)'))
    run('bound_bad_occupancy_s8', inp)
finally:
    p.write_text(good)

def shift(x):
    if isinstance(x,list): return [shift(v) for v in x]
    if isinstance(x,dict): return {k:shift(v) for k,v in x.items()}
    return x + 3
s = json.loads((agesdir/'slice_ages.json').read_text());s['ssq_psum_out']=shift(s['ssq_psum_out'])
v = json.loads((agesdir/'vec_ages.json').read_text())
for k in ('add_psum_out','xs_out','silu_out','red_vm','d2d'): v[k]=shift(v[k])
for k,a in (('slice',s),('vec',v)):
    (agesdir/f'{k}_aligned_ages.json').write_text(json.dumps(a,indent=1));inp['dv']['ages'][k]=f'results/analytic_s8/{k}_aligned_ages.json'
inp['release_source'] += '; hypothetical optin head/CROM align +3 per SU op/output/retire (c1c42f554)'
run('bound_aligned', inp)
(R/'s8_engine_overlay.json').write_text(json.dumps(meta,indent=1))
