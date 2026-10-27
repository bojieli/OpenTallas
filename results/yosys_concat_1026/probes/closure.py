import re, sys, gzip, json, os
from pathlib import Path
from collections import defaultdict
root = Path(sys.argv[1]); out = sys.argv[2]
defs = defaultdict(set); body = {}
KW = set('module endmodule input output inout wire reg logic assign always always_ff always_comb initial begin end if else case endcase for generate endgenerate genvar parameter localparam function endfunction task endtask integer int bit typedef struct enum return default posedge negedge or and not buf assert property'.split())
for p in root.rglob('*'):
    if p.suffix not in ('.sv', '.v', '.svh', '.vh') or not p.is_file(): continue
    rel = str(p.relative_to(root))
    if '/test/' in rel or rel.startswith('rtl/test/') or os.path.basename(rel).startswith('tb_'): continue
    try: t = p.read_text(errors='replace')
    except Exception: continue
    if p.stat().st_size > 3_000_000: continue   # generated flat netlists
    t = re.sub(r'//[^\n]*|/\*.*?\*/', ' ', t, flags=re.S)
    for m in re.finditer(r'^\s*module\s+(?:automatic\s+)?([A-Za-z_]\w*)', t, re.M): defs[m.group(1)].add(rel)
    body[rel] = set(re.findall(r'^\s*([A-Za-z_]\w*)\s*(?:#\s*\(|[A-Za-z_]\w*\s*(?:\[[^\]]*\]\s*)?\()', t, re.M)) - KW
def tops_from(path):
    op = gzip.open if str(path).endswith('.gz') else open
    t = op(path, 'rt', errors='replace').read()
    return set(re.findall(r'^\s*([A-Za-z_]\w*)\s+(?:#\s*\(.*?\)\s*)?[A-Za-z_][\w$]*\s*\(', t, re.M | re.S)) - KW
dp = root / 'physical/die_plan'
seeds = {'s81': tops_from(dp/'s81/bind/inputs/die_b178.v'), 'qwen_compute': tops_from(dp/'qwen_compute/bind/inputs/die_r56.v.gz'),
         'qwen_kvsys': tops_from(dp/'qwen_kvsys/bind/inputs/die_rtl6.v.gz'), 'hbm': tops_from(dp/'hbm/bind/inputs/die_r18h5.v.gz')}
try:
    hp = json.load(open(dp/'s81_head/die_plan.json'))
    seeds['s81_head'] = {pt.get('module') or k for k, pt in (hp.get('partition_types') or {}).items()} if isinstance(hp.get('partition_types'), dict) else {pt.get('module') for pt in hp.get('partition_types')}
except Exception as e: print('head', e); seeds['s81_head'] = set()
res = {}
for die, s in seeds.items():
    seen, files, todo, missing = set(), set(), [m for m in s], set()
    while todo:
        m = todo.pop()
        if m in seen: continue
        seen.add(m)
        if m not in defs: missing.add(m); continue
        for f in defs[m]:
            if f not in files:
                files.add(f); todo.extend(x for x in body[f] if x in defs)
    res[die] = dict(seeds=len(s), modules=len(seen - missing), files=sorted(files), missing_defs=sorted(missing)[:40], n_missing=len(missing))
    print(die, 'seeds', len(s), 'modules', len(seen - missing), 'files', len(files), 'undefined', len(missing))
json.dump(res, open(out, 'w'), indent=1)
