#!/usr/bin/env python3
"""KV-TYPES-5 11-08 usage (repo root): compose_onto.py BASE(48fdd735) TARGET(plan_r8fix) KVCLS(886ab8db) OUT.  kvcls_1108 on plan_r8fix: copy the kvcls fields (clock.ft_hop_lockup, every changed type's clock.landing_contract,
io_ft_v1.landing_status_reg) from the kvcls plan onto the r8fix plan; refuse if r8fix touched any of those fields."""
import json, sys, hashlib, re
from pathlib import Path
sys.path.insert(0, "tools/die_plan")
import ring_band_spread as R
import schema as S
base_p, r8_p, kc_p, out_p = sys.argv[1:5]
base, r8, kc = (json.load(open(p)) for p in (base_p, r8_p, kc_p))
r8text = open(r8_p).read()
out = json.loads(r8text); changed = []
assert base["clock"].get("ft_hop_lockup") == r8["clock"].get("ft_hop_lockup")
out["clock"]["ft_hop_lockup"] = kc["clock"]["ft_hop_lockup"]
for t, kt in kc["partition_types"].items():
    bt, rt = base["partition_types"][t], r8["partition_types"][t]
    if kt == bt: continue
    for f in set(bt) | set(kt):
        if bt.get(f) == kt.get(f): continue
        if f == "clock":
            for g in set(bt["clock"]) | set(kt["clock"]):
                if bt["clock"].get(g) != kt["clock"].get(g):
                    assert g == "landing_contract", (t, g)
                    assert rt["clock"].get(g) == bt["clock"].get(g), ("r8fix touched", t, g)
                    out["partition_types"][t]["clock"][g] = kt["clock"][g]
        else:
            assert f == "landing_status_reg", (t, f)
            assert rt.get(f) == bt.get(f), ("r8fix touched", t, f)
            out["partition_types"][t][f] = kt[f]
    changed.append(t)
for k in set(base) | set(kc):
    if k not in ("clock", "partition_types"): assert base.get(k) == kc.get(k), k
txt = json.dumps(out, indent=1) + "\n"
assert json.loads(txt) == out
S.Plan(json.loads(txt), Path(r8_p).resolve())
open(out_p, "w").write(txt)
print("types", len(changed), " ".join(changed)); print("md5", hashlib.md5(txt.encode()).hexdigest())
# control: r8fix bytes reproduce under the same dump
print("r8 dump-identical", json.dumps(r8, indent=1) + "\n" == r8text)
# byte-preserving form: r8fix text, top-level "clock" value text taken verbatim from the kvcls plan (r8fix clock == base
# clock, asserted), changed types spliced with the ring_band_spread splice (same indent rule)
assert r8["clock"] == base["clock"]
kctext = open(kc_p).read()
def seg(text, key):
    m = re.search(r'^ "' + re.escape(key) + r'": ', text, re.M)
    _, j = json.JSONDecoder().raw_decode(text, m.end())
    return m.end(), j
import re
a0, a1 = seg(r8text, "clock"); b0, b1 = seg(kctext, "clock")
t2 = r8text[:a0] + kctext[b0:b1] + r8text[a1:]
t2 = R.splice(t2, out, changed)
assert json.loads(t2) == out
open(out_p, "w").write(t2)
print("byte-preserving md5", hashlib.md5(t2.encode()).hexdigest())
