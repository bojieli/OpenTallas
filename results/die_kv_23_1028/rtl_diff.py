# DIE-KV-23: structural "equivalence modulo declared values" check of the bound KV RTL, bind6 (record) vs bind7 (event).
# Each bound .sv (type modules + top) is normalised: numeric parameter values inside #( ... ) and sized constants
# (N'dV / N'bV / N'hV) -> placeholders, type-module names -> base names (count-strap class suffix __clXXXX dropped).
# Equal normalised text => the files differ only in parameter values / tied constants (K, DEPTH, PAD, EDGE_FALL, delay
# depths, strap ties).  Remaining differences are listed (instances added/removed, connectivity) for manual review.
# Not a formal LEC: the claim is "same netlist structure, only declared values changed" (+ listed residue).
import re, sys, json, difflib
from pathlib import Path
from collections import Counter
A, B = Path(sys.argv[1]), Path(sys.argv[2])
CL = re.compile(r"__cl[0-9a-f]{8}")
PAR = re.compile(r"\.(\w+)\((\d+)\)")
def base(n): return CL.sub("", n.replace("_part", ""))
def norm(t):
    t = CL.sub("__clX", t)
    t = re.sub(r"(kv3_\w+?)(_part)?\b", lambda m: m.group(1), t)
    t = re.sub(r"\d+'[dbh][0-9a-fA-F_xz]+", "C", t)
    t = re.sub(r"#\((.*?)\)\s", lambda m: "#(" + re.sub(r"\((\d+)\)", "(N)", m.group(1)) + ") ", t, flags=re.S)
    return t
fa = {base(p.stem): p for p in A.glob("*.sv")}; fb = {base(p.stem): p for p in B.glob("*.sv")}
grp = lambda d: {k: sorted(v for v in d if base(v.stem) == k) for k in d}
fa2, fb2 = {}, {}
for p in A.glob("*.sv"): fa2.setdefault(base(p.stem), []).append(p)
for p in B.glob("*.sv"): fb2.setdefault(base(p.stem), []).append(p)
rep = dict(only_old=sorted(set(fa2) - set(fb2)), only_new=sorted(set(fb2) - set(fa2)), files={}, residue={})
for k in sorted(set(fa2) & set(fb2)):
    na = {norm(p.read_text()) for p in fa2[k]}; nb = {norm(p.read_text()) for p in fb2[k]}
    ta = fa2[k][0].read_text(); tb = fb2[k][0].read_text()
    pc = Counter()
    if ta != tb or len(fa2[k]) != len(fb2[k]):
        for p in fb2[k]:
            tt = p.read_text(); q = fa2[k][0].read_text()
            for x, y in zip(re.findall(r"#\(.*?\)\s", q, re.S), re.findall(r"#\(.*?\)\s", tt, re.S)):
                for (n1, v1), (n2, v2) in zip(PAR.findall(x), PAR.findall(y)):
                    if n1 == n2 and v1 != v2: pc[n1] += 1
    same = na == nb
    rep["files"][k] = dict(old=len(fa2[k]), new=len(fb2[k]), identical=ta == tb and len(fa2[k]) == len(fb2[k]),
                           equal_modulo_values=same, param_value_changes=dict(pc))
    if not same:
        a = sorted(na)[0].splitlines(); b = sorted(nb)[0].splitlines()
        d = [l for l in difflib.unified_diff(a, b, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        rep["residue"][k] = dict(lines=len(d), sample=d[:12])
json.dump(rep, open(sys.argv[3], "w"), indent=1)
print("only_old", rep["only_old"], "only_new", rep["only_new"])
print("identical", sum(v["identical"] for v in rep["files"].values()), "equal_modulo_values", sum(v["equal_modulo_values"] and not v["identical"] for v in rep["files"].values()),
      "residue", {k: v["lines"] for k, v in rep["residue"].items()})
tot = Counter()
for v in rep["files"].values(): tot.update(v["param_value_changes"])
print("param value changes", dict(tot))
