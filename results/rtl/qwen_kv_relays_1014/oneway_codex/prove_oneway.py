import ast, hashlib, json, re, sys
from pathlib import Path
sys.path.insert(0, 'src/tools/qwen_kv_die')
import kv_relays as R
import die_port_bind_kv as P

# Execute the committed direction helpers without importing the full die generator.
text = Path('die_top_lint.py').read_text()
nodes = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name in ('flow', 'dirs_qwen')]
env = {'re': re}
exec(compile(ast.Module(body=nodes, type_ignores=[]), 'die_top_lint.py', 'exec'), env)
rel = R.parse('stubs.sv')
before, checked = R.crosscheck(rel, 'die.v')
assert len(before) == 7 and checked == 256, (before, checked)
_, insts = P.parse_die('die.v')
fix = {33: 'kc_', 513: 'gr_', 182: 'hc_', 93: 'tk_'}
changed = []
for width, bus in fix.items():
    master = f'qkd_rly_{width}'
    uses = [i for m, i, _ in insts if m == master]
    assert uses and all(i.startswith('rly_' + bus) for i in uses), (master, uses)
    rule = env['dirs_qwen'](bus[:-1], 'kv_oneway', width, [], 0, 'a')
    assert rule == [(0, width, 'out')], rule
    rel[master]['fwd'] = set(range(width)); rel[master]['rev'] = set()
    changed.append({'master': master, 'instances': uses, 'direction_rule': rule})
after, n = R.crosscheck(rel, 'die.v')
assert not after and n == checked, (after, n)
Path('oneway-proof.json').write_text(json.dumps({'old_conflicts': before, 'real_ends_checked': n,
    'new_conflicts': after, 'changed': changed, 'direction_helper_sha256': hashlib.sha256(text.encode()).hexdigest(),
    'method': 'original case and relay metadata, one-way bus rules applied after asserting every affected instance family; fresh die generation still required'}, indent=2)+'\n')
Path('tb_rly.sv').write_text(R.bench(rel))
for mutant in (0, 1, 2): Path(f'rly_m{mutant}.sv').write_text(R.emit(rel, mutant))
print(json.dumps({'old_conflicts': len(before), 'new_conflicts': len(after), 'real_ends_checked': n}))
