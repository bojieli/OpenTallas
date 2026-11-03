#!/usr/bin/env python3
"""differential verdict for astk_strap_direct_lec: an eq case PASSes when its unproven key points are a subset of the
gold-vs-gold baseline's (same yosys method on two identical copies of the ORIGINAL module = method limitation, not a
difference); a mutant must leave key points unproven beyond the baseline.  usage: DIR BASE_ZN_LOG BASE_CTL_LOG"""
import json, re, sys
from pathlib import Path
d = Path(sys.argv[1]); base = {"qkd_astk_zn": sys.argv[2], "qkd_astk_ctl_s_g0": sys.argv[3]}
rx = re.compile(r"Unproven \$equiv \S+: \\(\S+)_gold \[(\d+)\] \\\S+_gate")
rx1 = re.compile(r"Unproven \$equiv \S+: \\(\S+)_gold \\\S+_gate")
def unp(p):
    t = Path(p).read_text(errors="replace")
    if "equiv_status -assert" not in t and "Found a total of" not in t and "End of script" not in t:
        return None
    s = {f"{m.group(1)}[{m.group(2)}]" for m in rx.finditer(t)} | {m.group(1) for m in rx1.finditer(t)}
    return s
bs = {k: unp(v) for k, v in base.items()}
res, ok = [], True
for c in sorted(d.iterdir()):
    if not (c / "lec.log").is_file():
        continue
    mod = "qkd_astk_ctl_s_g0" if c.name.startswith("qkd_astk_ctl_s_g0") else "qkd_astk_zn"
    u = unp(c / "lec.log")
    mut = c.name.endswith("_mutant")
    if u is None or bs[mod] is None:
        v = "INCOMPLETE"
    elif mut:
        v = "PASS" if (u - bs[mod]) else "FAIL"
    else:
        v = "PASS" if u <= bs[mod] else "FAIL"
    ok &= v == "PASS"
    res.append(dict(case=c.name, unproven=len(u or ()), beyond_baseline=sorted((u or set()) - (bs[mod] or set()))[:10], verdict=v))
    print(c.name, v, len(u or ()), "beyond", len((u or set()) - (bs[mod] or set())))
out = dict(schema="opentallas.astk_strap_direct_lec_diff.v1", baseline={k: sorted(v or ()) for k, v in bs.items()},
           cases=res, verdict="PASS" if ok and len(res) == 20 else "FAIL")
(d / "strap_direct_lec_diff.json").write_text(json.dumps(out, indent=1) + "\n")
print("STRAP_DIRECT_LEC_DIFF", out["verdict"], len(res))
