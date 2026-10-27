# for every module in every changed file: A = orig(read_slang) vs fix(read_verilog -sv, flow frontend); B = orig(read_slang) vs fix(read_slang)
import re, sys, json, os, subprocess
from pathlib import Path
from collections import defaultdict
root = Path(sys.argv[1]); out = Path(sys.argv[2]); orig = Path(sys.argv[3]); bb = sys.argv[4]
rel = json.load(open(sys.argv[5])); changed = sys.argv[6:]
relfiles = sorted({f for v in rel.values() for f in v['files']} | set(changed))
strip = lambda s: re.sub(r'//[^\n]*|/\*.*?\*/', ' ', s, flags=re.S)
defs = defaultdict(list); uses = {}
for f in relfiles:
    t = strip((root / f).read_text(errors='replace'))
    for m in re.finditer(r'^\s*module\s+([A-Za-z_]\w*)', t, re.M): defs[m.group(1)].append(f)
    uses[f] = set(re.findall(r'^\s*([A-Za-z_]\w*)\s*(?:#\s*\(|[A-Za-z_]\w*\s*\()', t, re.M))
def pick(m, near):
    c = defs[m]; same = [x for x in c if os.path.dirname(x) == os.path.dirname(near)]
    return (same or c)[0]
bbs = ' '.join(str(p) for p in Path(bb).glob('*.v'))
Y = '/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys'
sh = []; n = 0
for hf in changed:
    t = strip((root / hf).read_text(errors='replace'))
    mods = re.findall(r'^\s*module\s+([A-Za-z_]\w*)', t, re.M)
    files, todo, seen = [hf], list(uses[hf]), set(mods)
    while todo:
        m = todo.pop()
        if m in seen or m not in defs: continue
        seen.add(m); f = pick(m, hf)
        if f not in files: files.append(f); todo.extend(uses[f])
    fix = ' '.join(str(root / f) for f in files)
    org = ' '.join(str((orig if f in changed else root) / f) for f in files)
    for m in mods:
        for mode in ('A', 'B'):
            gate_rd = (f"read_verilog -sv -defer {fix}; read_verilog -sv -lib {bbs}; hierarchy -top {m}" if mode == 'A'
                       else f"read_slang {fix} {bbs} --top {m} --compat=vcs --ignore-assertions -DSYNTHESIS; hierarchy -top {m}")
            s = (f"read_slang {org} {bbs} --top {m} --compat=vcs --ignore-assertions -DSYNTHESIS; hierarchy -top {m}; prep -flatten -top {m}; memory_map; async2sync; rename {m} gold; design -stash g; "
                 f"{gate_rd}; prep -flatten -top {m}; memory_map; async2sync; rename {m} gate; design -stash t; "
                 "design -copy-from g -as gold gold; design -copy-from t -as gate gate; equiv_make -blacklist /dev/null gold gate eq; hierarchy -top eq; equiv_simple -seq 2; equiv_induct -seq 2; equiv_status -assert")
            log = out / f'{n:03d}_{mode}_{m}.log'; n += 1
            sh.append(f"timeout 1500 {Y} -q -l {log} -p '{s}' >/dev/null 2>&1; rc=$?; "
                      f"if [ $rc = 0 ]; then v=EQ; elif grep -q 'unproven' {log}; then v=NEQ; elif [ $rc = 124 ]; then v=TIMEOUT; else v=ERR; fi; "
                      f"echo \"$v\t{mode}\t{hf}\t{m}\t$(grep -o 'Found [0-9]* unproven[^.]*' {log} | tail -1)$(grep -m1 ERROR {log} | cut -c1-120)\"")
(out / 'jobs.sh').write_text('\n'.join(sh) + '\n'); print(n, 'jobs')
