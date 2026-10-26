#!/usr/bin/env python3
"""Compare verilator diagnostics of the __q3sync lint vs the legacy lint of the
same core (gen line numbers shifted by the 2-line generated header; __q3sync
suffix and directories stripped). Prints a JSON summary per core."""
import re, sys, json, os
from collections import Counter
d = sys.argv[1]
out = {}
def diags(path, shift):
    c = Counter()
    for ln in open(path, errors="replace"):
        m = re.match(r"%(Error|Warning)(-\w+)?: (\S+?):(\d+):(\d+): (.*)", ln)
        if not m:
            continue
        f = os.path.basename(m.group(3)).replace("__q3sync", "")
        msg = m.group(6).replace("__q3sync", "")
        c[(m.group(1) + (m.group(2) or ""), f, int(m.group(4)) - shift, msg)] += 1
    return c
for core in ["body", "edge", "vm", "reduce", "ring_ag"]:
    g = os.path.join(d, core + "_gen.log"); l = os.path.join(d, core + "_legacy.log")
    G, L = diags(g, 2), diags(l, 0)
    rc = {}
    for m, p in (("gen", g), ("legacy", l)):
        t = open(p).read(); mm = re.search(r"# rc=(\d+)", t); rc[m] = int(mm.group(1)) if mm else None
    kinds = Counter()
    for k, v in G.items(): kinds[k[0]] += v
    out[core] = dict(rc_gen=rc["gen"], rc_legacy=rc["legacy"], diag_gen=sum(G.values()), diag_legacy=sum(L.values()),
                     by_kind_gen=dict(kinds), new_in_gen=sum((G - L).values()), missing_in_gen=sum((L - G).values()),
                     new_examples=[" ".join(map(str, k)) for k in list((G - L))[:5]])
if len(sys.argv) > 2:
    c = json.load(open(sys.argv[2]), object_pairs_hook=__import__("collections").OrderedDict)
    c["lint"] = dict(verilator="verilator 5.050 --lint-only -Wno-fatal -Werror-SELRANGE -Werror-WIDTH -Wno-TIMESCALEMOD --error-limit 1000000",
                     run="ot-run --hosts localhost(epyc1/tender-ray) --threads 2 (body --mem 32, others 4)",
                     logs="results/token_pass/path_hbm_1713/q3sync/lint/", per_core=out)
    ls = os.path.join(d, "lockstep_vm.log")
    if os.path.exists(ls):
        c["lockstep_vm"] = [l.strip() for l in open(ls) if l.startswith(("LOCKSTEP", "# build", "# sim", "MISMATCH"))]
    json.dump(c, open(sys.argv[2], "w"), indent=1)
print(json.dumps(out, indent=1))
