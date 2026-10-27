# per hit file: for each module defined there, read_verilog -sv vs read_slang (default params), deps by module-name closure
import re, sys, json, os, subprocess
from pathlib import Path
from collections import defaultdict
root = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(exist_ok=True)
rel = json.load(open(sys.argv[3])); hits = [l.split('\t')[1].rsplit(':', 1)[0] for l in open(sys.argv[4]) if not l.startswith('die\t')]
relfiles = sorted({f for v in rel.values() for f in v['files']})
defs = defaultdict(list); uses = {}
for f in relfiles:
    t = re.sub(r'//[^\n]*|/\*.*?\*/', ' ', (root / f).read_text(errors='replace'), flags=re.S)
    for m in re.finditer(r'^\s*module\s+([A-Za-z_]\w*)', t, re.M): defs[m.group(1)].append(f)
    uses[f] = set(re.findall(r'^\s*([A-Za-z_]\w*)\s*(?:#\s*\(|[A-Za-z_]\w*\s*\()', t, re.M))
def pick(m, near):
    c = defs[m]; same = [x for x in c if os.path.dirname(x) == os.path.dirname(near)]
    return (same or c)[0]
jobs = []
for hf in sorted(set(hits)):
    t = re.sub(r'//[^\n]*|/\*.*?\*/', ' ', (root / hf).read_text(errors='replace'), flags=re.S)
    mods = re.findall(r'^\s*module\s+([A-Za-z_]\w*)', t, re.M)
    files, todo, seen = [hf], list(uses[hf]), set(mods)
    while todo:
        m = todo.pop()
        if m in seen or m not in defs: continue
        seen.add(m); f = pick(m, hf)
        if f not in files: files.append(f); todo.extend(uses[f])
    for m in mods:
        jobs.append((hf, m, files))
Y = '/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys'
sh = []
for i, (hf, m, files) in enumerate(jobs):
    fl = ' '.join(str(root / f) for f in files)
    log = out / f'{i:03d}_{m}.log'
    s = (f"read_verilog -sv -defer {fl}; hierarchy -top {m}; prep -flatten -top {m}; async2sync; rename {m} gold; design -stash g; "
         f"read_slang {fl} --top {m} --compat=vcs --ignore-assertions -DSYNTHESIS; hierarchy -top {m}; prep -flatten -top {m}; async2sync; rename {m} gate; design -stash t; "
         "design -copy-from g -as gold gold; design -copy-from t -as gate gate; equiv_make gold gate eq; hierarchy -top eq; equiv_simple -seq 2; equiv_induct -seq 2; equiv_status -assert")
    sh.append(f"timeout 1500 {Y} -q -l {log} -p '{s}' >/dev/null 2>&1; rc=$?; "
              f"if [ $rc = 0 ]; then v=EQ; elif grep -q 'unproven' {log}; then v=NEQ; elif [ $rc = 124 ]; then v=TIMEOUT; else v=ERR; fi; "
              f"echo \"$v\t{hf}\t{m}\t$(grep -o 'Found [0-9]* unproven[^.]*' {log} | tail -1)$(grep -m1 ERROR {log} | cut -c1-120)\"")
(out / 'jobs.sh').write_text('\n'.join(sh) + '\n')
print(len(jobs), 'jobs')
