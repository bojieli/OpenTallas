#!/usr/bin/env python3
"""DIE-HBM-82 d44v part 46 packaging (after mk_p46.py): event record, README line, SHA256SUMS.   fin_p46.py REPO"""
import gzip, hashlib, json, sys
from pathlib import Path
D = Path(sys.argv[1]) / "physical/die_plan/hbm/plan_of_record/d44v"
T = "cores/ot_hgi_sm_xload_cl2_ctlx__388.8x388.8__canon__c20g_391.392x416.448__centry.json"
sha = lambda b: hashlib.sha256(b).hexdigest()
ev = {"schema": "opentallas.hbm_plan_event.part46", "by": "DIE-HBM-82 11-06 (plan-owner approved DIE-HBM-82; ctlx clock pin back to the signed site)",
      "core": "ot_hgi_sm_xload_cl2_ctlx", "instances": 4,
      "change": "pin table restored byte for byte to pre-p35 (510f347b9f^): clk_cal M5 x 194.808 -> 194.52 (y 194.4), clk 194.424 unchanged, "
                "every other pin unchanged; clock_entries clock_pin_sites_um of both ctlx entries = that table (clk 194.424, clk_cal 194.52)",
      "why": "the signed ctlx DB has clk_cal at 194.52 and missed the p35 table only by that pin (release cache design_unmatched 1/5782)",
      "tables": {"ot_hgi_sm_xload_cl2_ctlx": {"pins_file": T, "sha256": sha(gzip.decompress((D / (T + ".gz")).read_bytes()))}},
      "signed_db": "epyc2 /srv/opentallas-scratch2/claude/die-hbm-63/eco/ctlx2/run/i2 (re-signed ss29/resign/ctlx2_k, flow-20261104-k-hbm, routed LEC EQ)",
      "pin_cycles": "none", "replay": "results/die_hbm_1106/ctlx_clkpin_p46/replay_p46.sh"}
(D / "part46_event.json").write_text(json.dumps(ev, indent=1) + "\n")
rd = D / "README.md"
rd.write_text(rd.read_text().rstrip("\n") + "\n\nEvent part 46 (DIE-HBM-82 11-06, plan-owner approved): ot_hgi_sm_xload_cl2_ctlx pin table back to "
              "pre-p35 (clk_cal 194.808 -> 194.52, the signed DB's site, as part 44 did for fr); its part-45 clock_pin_sites_um follow "
              "(clk 194.424, clk_cal 194.52); no pin cycles; part46_event.json; replay results/die_hbm_1106/ctlx_clkpin_p46.\n")
S = D / "SHA256SUMS"
L = [l.split(None, 1) for l in S.read_text().splitlines() if l.strip()]
new = {"clock_entries.json": sha(gzip.decompress((D / "clock_entries.json.gz").read_bytes())),
       T: sha(gzip.decompress((D / (T + ".gz")).read_bytes())), "part46_event.json": sha((D / "part46_event.json").read_bytes())}
ch = []
for i, (a, n) in enumerate(L):
    if n in new and new[n] != a:
        L[i] = [new[n], n]; ch.append(n)
if "part46_event.json" not in {n for _, n in L}:
    L.append([new["part46_event.json"], "part46_event.json"])
S.write_text("".join(f"{a}  {n}\n" for a, n in L))
print("SHA256SUMS changed", ch)
