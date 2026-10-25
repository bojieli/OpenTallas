#!/usr/bin/env python3
"""TOK-SCHED 10-25 (b): QC MIF=1 price on the Qwen compute static schedule (analytical, not a token run).

Engine/recipe = Codex results/uarch/qwen_s8_crom_price_1025/price.py (composition engine 94cd97b7a + compiler sources
f0ef9ad67 + fixed-RTL s8exp_wf3 bound ages).  That recipe priced CROM alignment as "+3 on every SU-derived output/retire
age" (ssq_psum_out, add_psum_out, xs_out, silu_out, red_vm, d2d).  MIF=1 (qfd_dv_s8x_vmr / _btab / _prog, main
32620f9399) is the same mechanism at a smaller edge count: vmr q, bs_q and p_q each land exactly one edge later.
Codex tools/uarch_model.py qwen_sram_if_mif_model (codex/qc-mif-1309 c9cdec9e2) predicts 2 serial edges a SU command
(program fetch start +1, memory/head reply +1).  This prices the bound-current schedule with the SU-derived ages
shifted by +1 (memory reply only: lower bound) and +2 (fetch + reply: Codex model, charged) and, for reference, +3
(must reproduce Codex's CROM 288,025).

usage (on a fleet host, scratch dir): qc_mif_price.py <repo> <workdir>
"""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

REPO, D = Path(sys.argv[1]), Path(sys.argv[2])
REC = 'results/uarch/qwen_s8_crom_price_1025'
ENGINE, COMPILER = '94cd97b7a', 'f0ef9ad67'
D.mkdir(parents=True, exist_ok=True)
T, SRC = D / 'tree', D / 'sources'
SRC.mkdir(exist_ok=True)


def git(*a, **k):
    return subprocess.run(['git', '-C', str(REPO), *a], check=True, capture_output=True, **k).stdout


for f, rel in (('compose_tokfunc.py', 'tools/qwen_tokfunc/compose_tokfunc.py'),
               ('dv_lower.py', 'tools/qwen_layerbench/dv_lower.py'),
               ('dv_lower_vec.py', 'tools/qwen_layerbench/dv_lower_vec.py'),
               ('dv_lower_mat.py', 'tools/qwen_layerbench/dv_lower_mat.py')):
    (SRC / f).write_bytes(git('show', f'{COMPILER}:{rel}'))
src = (SRC / 'compose_tokfunc.py').read_text()
ns = {}
exec(re.search(r"^REC = .*$", src, re.M).group(0), ns)
exec(re.search(r"^BASE_PATHS = \[.*?\]", src, re.M | re.S).group(0), ns)
assert ns['BASE_PATHS'] and ns['BASE_PATHS'][0] == 'tools', ns['BASE_PATHS']
if T.exists():
    shutil.rmtree(T)
T.mkdir()
tar = git('archive', ENGINE, *ns['BASE_PATHS'])
subprocess.run(['tar', '-x', '-C', str(T)], input=tar, check=True)
for f in ('inputs_source.json',):
    (D / f).write_bytes(git('show', f'origin/main:{REC}/{f}'))
for k in ('slice', 'vec', 'stn'):
    (D / f'{k}_ages.json').write_bytes(git('show', f'origin/main:{REC}/ages/{k}_ages.json'))
pr = git('show', f'origin/main:{REC}/price.py').decode()
# Codex's recipe up to and including bound_current, then our shifts (same keys as its CROM +3 scenario)
head, tail = pr.split('def shift(x):', 1)
mif = '''
import copy as _c
base_inp = _c.deepcopy(inp)
s0 = json.loads((agesdir/'slice_ages.json').read_text()); v0 = json.loads((agesdir/'vec_ages.json').read_text())
def shiftn(x, n):
    if isinstance(x, list): return [shiftn(v, n) for v in x]
    if isinstance(x, dict): return {k: shiftn(v, n) for k, v in x.items()}
    return x + n
out = {}
for n in (1, 2, 3):
    s = _c.deepcopy(s0); v = _c.deepcopy(v0); i2 = _c.deepcopy(base_inp)
    s['ssq_psum_out'] = shiftn(s['ssq_psum_out'], n)
    for k in ('add_psum_out', 'xs_out', 'silu_out', 'red_vm', 'd2d'): v[k] = shiftn(v[k], n)
    for k, a in (('slice', s), ('vec', v)):
        (agesdir/f'{k}_mif{n}_ages.json').write_text(json.dumps(a, indent=1)); i2['dv']['ages'][k] = f'results/analytic_s8/{k}_mif{n}_ages.json'
    i2['release_source'] += f'; TOK-SCHED 10-25: SU-derived ages +{n} (MIF1 bracket)'
    out[n] = run(f'bound_su_plus{n}', i2)
'''
# the historical source reproduction needs the 10-19 stg ages that are not committed at their engine paths; the
# bound_current scenario (which must reproduce Codex's 286,726) is the base of this price
head = head.replace("run('source_reproduced', inp)\n", "", 1)
assert "run('source_reproduced'" not in head
code = head + mif
(D / 'price_mif_run.py').write_text(code)
p = subprocess.run([sys.executable, str(D / 'price_mif_run.py')], cwd=D, capture_output=True, text=True)
print(p.stdout[-4000:], p.stderr[-4000:])
if p.returncode:
    raise SystemExit(p.returncode)


def tok(name):
    d = json.loads((D / f'{name}.json').read_text())
    return d


summ = {}
for name in ('bound_current', 'bound_su_plus1', 'bound_su_plus2', 'bound_su_plus3'):
    d = tok(name)
    u = d['result']['1u']
    summ[name] = dict(cycles_per_token=u['cycles_per_token'], tok_s=u['tok_s'], chained=u['layer']['chained'],
                      l0_cold=u['layer']['l0_cold'], calendar_ok=u['layer']['calendar']['ok'],
                      calendar_clashes=len(u['layer']['calendar_clashes']))
(D / 'mif_summary_raw.json').write_text(json.dumps(summ, indent=1))
print(json.dumps(summ, indent=1)[:3000])
