#!/usr/bin/env python3
"""DIE-HBM-82 d44v part 46 (plan-owner approved DIE-HBM-82 11-06 15:0x): ot_hgi_sm_xload_cl2_ctlx clock pin back to the signed site.

Part 35 (510f347b9f) moved clk_cal in the ctlx pin table 194.52 -> 194.808 (y 194.4); the signed ctlx DB (die-hbm-63
eco/ctlx2 i2, re-signed ss29/resign/ctlx2_k on flow-20261104-k-hbm, routed LEC EQ) has clk_cal at 194.52 and so stopped
counting (release cache: design_unmatched 1/5782 pins, clk_cal).  As DIE-HBM-82-B128 did for lane_core_fr (part 44):
restore the ctlx table to its pre-p35 bytes (510f347b9f^, the signed kit's source), and set the part-45
clock_pin_sites_um of both ctlx clock entries to that table (clk 194.424, clk_cal 194.52) so --clock-pin-entry kits
keep matching it.  The 0.096-um clk / clk_cal pair is proven routable by the signed DB.  No pin cycles.
    mk_p46.py REPO   (needs the git history: reads the pre-p35 table with git show)"""
import gzip, hashlib, json, subprocess, sys
from pathlib import Path
R = Path(sys.argv[1])
D = R / "physical/die_plan/hbm/plan_of_record/d44v"
T = "cores/ot_hgi_sm_xload_cl2_ctlx__388.8x388.8__canon__c20g_391.392x416.448__centry.json.gz"
PRE = "456621d51445a1a6348f3bb2d37fddf998122284faba053b93e5a4d00bf94398"   # logical sha of the pre-p35 table
b = subprocess.run(["git", "-C", str(R), "show", f"510f347b9f^:physical/die_plan/hbm/plan_of_record/d44v/{T}"],
                   check=True, capture_output=True).stdout
assert hashlib.sha256(gzip.decompress(b)).hexdigest() == PRE
cur = {p["name"]: p for p in json.loads(gzip.decompress((D / T).read_bytes()))}
old = {p["name"]: p for p in json.loads(gzip.decompress(b))}
assert set(cur) == set(old) and [n for n in old if old[n] != cur[n]] == ["clk_cal"], "table differs beyond clk_cal"
assert cur["clk_cal"]["x"] == 194.808 and old["clk_cal"]["x"] == 194.52
(D / T).write_bytes(b)
CE = json.loads(gzip.decompress((D / "clock_entries.json.gz").read_bytes()))
want = {"clk": [old["clk"]["x"], old["clk"]["y"]], "clk_cal": [old["clk_cal"]["x"], old["clk_cal"]["y"]]}
n = 0
for blk in CE.values():
    for e in (blk.values() if isinstance(blk, dict) else []):
        if isinstance(e, dict) and e.get("module") == "ot_hgi_sm_xload_cl2_ctlx":
            assert e["clock_pin_sites_um"] == {"clk": [194.424, 194.4], "clk_cal": [194.808, 194.4]}, e.get("clock_pin_sites_um")
            e["clock_pin_sites_um"] = want; n += 1
assert n == 2, n
out = (json.dumps(CE) + "\n").encode()
with open(D / "clock_entries.json.gz", "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
    g.write(out)
print("P46 ctlx table restored to pre-p35 (clk_cal 194.808 -> 194.52); clock entries", n, json.dumps(want))
