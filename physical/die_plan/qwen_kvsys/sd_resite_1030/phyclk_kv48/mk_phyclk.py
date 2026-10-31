#!/usr/bin/env python3
"""DIE-KV-48-CLK 2026-10-30: restore the SD PHY clock pin clk_clk_phy on kv3_sys_SD / kv3_sys_SD_v1 (plan_c).

The bind of record exposes clk_clk_phy (hub_C pll.pll_phy -> serdes .clk_phy) as a bound-only SD pin, but plan_c
(773deac7e121, post sd re-site) never declared it, so the kit's pre-floorplan port_bind gate FAILs (extra 1).
This adds exactly the DIE-KV-35 KV-022 edge clock (COORD 10-29 14:37; claude/die-kv-35-1029@7756db575c
results/die_kv_35_1029/kv022/die_plan_sd35_delta.json) to the two SD types and nothing else (fail-closed).
usage: mk_phyclk.py plan_c.json   (rewrites in place, indent=1 as mk_sd47.py)"""
import copy, hashlib, json, sys

EC = {"port": "clk_clk_phy", "tap_um": [1898.656, 354.0], "period_mult": 1,
      "source": "hub_C pll.pll_phy (asbuilt sources: pll_phy -> domain clk_phy; bound-top spine clk_clk_phy)",
      "note": "KV-022 COORD 10-29 14:37 (DIE-KV-35): x6 PHY clock -> serdes .clk_phy (u_fdi_cdc phy side 5259 FF + macro clk pin (1866.24,354.0)); E-rim interior M7 pin at the macro clk pin row; kit clock at the die period (PLL model 1043 ps: 833 is tighter, not relaxed), synchronous with clk per schema (QC clk_serdes form)"}
TYPES = ("kv3_sys_SD", "kv3_sys_SD_v1")
p = sys.argv[1]
raw = open(p, "rb").read()
assert hashlib.sha256(raw).hexdigest().startswith("773deac7e121"), "unexpected base plan_c"
P = json.loads(raw)
old = copy.deepcopy(P)
for tn in TYPES:
    ck = P["partition_types"][tn]["clock"]
    ecs = ck.setdefault("edge_clocks", [])
    assert all(e["port"] != "clk_clk_phy" for e in ecs)
    w, h = P["partition_types"][tn]["outline_um"]
    assert 0 <= EC["tap_um"][0] <= w and 0 <= EC["tap_um"][1] <= h
    ecs.append(copy.deepcopy(EC))
# nothing else changed
for tn in TYPES:
    old["partition_types"][tn]["clock"]["edge_clocks"].append(copy.deepcopy(EC))
assert old == P
out = json.dumps(P, indent=1) + "\n"
open(p, "w").write(out)
print("PHYCLK_DELTA", {t: [e["port"] for e in P["partition_types"][t]["clock"]["edge_clocks"]] for t in TYPES},
      "sha256", hashlib.sha256(out.encode()).hexdigest()[:12])
