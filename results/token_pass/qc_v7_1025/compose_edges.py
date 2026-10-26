"""TOK-QK-QCL 10-25: compose the 1u token from S8 ages with the price engine of results/uarch/qwen_s8_crom_price_1025
(engine tree = git archive 94cd97b7a BASE_PATHS; compiler overlay = dv_lower*.py of the named main commit; same steps as
price.py 'bound_*' scenarios).  python3 compose_edges.py ROOT NAME SLICE VEC STN VFLAGS [EXTRA_EDGES_JSON]
TOK-QK-QCV7 10-25: EXTRA_EDGES_JSON = list of ledger die_edges appended to the sched ledger (bind-derived lane deltas)."""
import importlib.util, json, os, re, shutil, subprocess, sys
from pathlib import Path
R = Path(sys.argv[1]); name = sys.argv[2]; ages = dict(slice=sys.argv[3], vec=sys.argv[4], stn=sys.argv[5])
os.environ['DV_LOWER_VFLAGS'] = sys.argv[6]
S = R / 'src'; T = R / f'tree_{name}'
if T.exists(): shutil.rmtree(T)
shutil.copytree(R / 'tree', T, symlinks=True)
os.environ.pop('DV2_S8DIE', None)
spec = importlib.util.spec_from_file_location('ct', S / 'tools/qwen_tokfunc/compose_tokfunc.py')
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
meta = C.s8die_tree(T)
for fn in ('dv_lower.py', 'dv_lower_vec.py', 'dv_lower_mat.py'):
    shutil.copy(S / 'tools/qwen_layerbench' / fn, T / 'tools/qwen_layerbench' / fn)
p = T / 'tools/qwen_layerbench/dv_lower_vec.py'
p.write_text(p.read_text().replace('e + 2 * abs(m - s)', 'e + D.ST_HOP * abs(m - s)'))
p = T / 'tools/qwen_layerbench/dv_layer.py'
p.write_text(re.sub(r"^ATTNRET_REC = '[^']*'", "ATTNRET_REC = 'results/analytic_bound_attn_unmeasured.json'", p.read_text(), flags=re.M))
if len(sys.argv) > 7:
    lp = T / 'results/token_pass/measured_qwen_1019/sched/ledger.json'
    lg = json.loads(lp.read_text())
    if lp.is_symlink(): lp.unlink()
    lg['die_edges'] += json.loads(Path(sys.argv[7]).read_text()); lp.write_text(json.dumps(lg, indent=1))
ad = T / 'results/analytic_s8'; ad.mkdir(parents=True, exist_ok=True)
for k, f in ages.items(): shutil.copy(f, ad / f'{k}_ages.json')
inp = json.loads((S / 'results/uarch/qwen_s8_crom_price_1025/inputs_source.json').read_text())
inp['dv'].pop('base_ages', None)
inp['dv']['ages'] = {k: f'results/analytic_s8/{k}_ages.json' for k in ages}
inp['dv']['grade'] = 'PRICED'
inp['release_source'] = f'TOK-QK-QCL {name}: S8 ages {ages}'
(T / f'inputs_{name}.json').write_text(json.dumps(inp, indent=1))
r = subprocess.run([sys.executable, '-I', 'tools/qwen_layerbench/toksim_compose.py', '--inputs', f'inputs_{name}.json',
                    '--out', str(R / f'{name}.json')], cwd=T, capture_output=True, text=True)
(R / f'{name}.log').write_text(r.stdout + r.stderr)
if r.returncode: raise SystemExit(f'{name} compose failed rc{r.returncode}: {r.stderr[-2000:]}')
d = json.loads((R / f'{name}.json').read_text())['result']['1u']
print(name, d['cycles_per_token'], d['tok_s'], d['layer']['chained'], d['layer']['l0_cold'])
shutil.rmtree(T)
