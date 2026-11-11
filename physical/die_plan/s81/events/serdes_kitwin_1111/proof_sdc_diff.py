#!/usr/bin/env python3
"""SERDES-KITWIN-1111 proof: generate the kit SDC of EVERY plan type from the plan before and after the event.
Types outside the written serdes types must be byte-identical; the written types may differ only in the tap-window
comment, the set_clock_latency -source -early lines and the IO shift lines (set_input_delay -max / set_output_delay -min).
usage: proof_sdc_diff.py PLAN_BEFORE PLAN_AFTER OUT_JSON"""
import difflib, json, re, sys, time
from pathlib import Path
here = Path(__file__).resolve()
for up in here.parents:
    if (up / "tools" / "die_plan" / "gen_phys.py").exists():
        sys.path.insert(0, str(up / "tools" / "die_plan")); break
import gen_phys, schema

A, B, out = sys.argv[1:4]
PA, PB = (schema.Plan(json.load(open(f))) for f in (A, B))
names = sorted(PA.types) if hasattr(PA, "types") else sorted(json.load(open(A))["partition_types"])
ALLOWED = re.compile(r"^(# tap window: |set_clock_latency -source -early -clock |set_input_delay -max |set_output_delay -min )")
res = dict(identical=0, differing=[], bad=[], errors=[], n=len(names))
t0 = time.time()
for t in names:
    try:
        a = gen_phys.sdc(PA, t, gen_phys.type_pins(PA, t))
        b = gen_phys.sdc(PB, t, gen_phys.type_pins(PB, t))
    except Exception as e:                                   # types the generator cannot render alone
        res["errors"].append([t, f"{type(e).__name__}: {e}"[:160]]); continue
    if a == b:
        res["identical"] += 1; continue
    ch = [l[1:] for l in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
          if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    res["differing"].append(t)
    if not t.startswith("serdes__") or any(not ALLOWED.match(l) for l in ch):
        res["bad"].append([t, [l for l in ch if not ALLOWED.match(l)][:3]])
res["seconds"] = round(time.time() - t0)
Path(out).write_text(json.dumps(res, indent=1) + "\n")
print({k: (len(v) if isinstance(v, list) else v) for k, v in res.items()})
