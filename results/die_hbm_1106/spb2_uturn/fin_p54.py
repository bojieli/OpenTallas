#!/usr/bin/env python3
"""DIE-HBM-82-SPB d44v part 54 packaging: RR/new.json -> d44v die_plan.json.gz (gzip -n, mtime 0), part54_event.json,
part54_l3012_window_ledger.json, README paragraph, SHA256SUMS rows.   fin_p54.py RR   (run from the repo root)"""
import gzip, hashlib, json, sys
from pathlib import Path
RR = Path(sys.argv[1]); D = Path("physical/die_plan/hbm/plan_of_record/d44v")
sha = lambda b: hashlib.sha256(b).hexdigest()
b = (RR / "new.json").read_bytes()
with open(D / "die_plan.json.gz", "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as g:
    g.write(b)
led = json.loads((RR / "ledger.json").read_text())
(D / "part54_l3012_window_ledger.json").write_text(json.dumps(led, indent=1) + "\n")
ev = {"schema": "opentallas.hbm_plan_event.v1", "part": 54, "plan": "d44v", "lane": "DIE-HBM-82-SPB", "date": "2026-11-06",
      "approved": "plan-owner approved DIE-HBM-82 (TYPE-SAFE-2 20:31 ASK (4), approved by DIE-HBM-82 21:2x)",
      "what": ["lane L3012 (27 b, NW_su21 -> su20 x1 -> b103 x2 -> b111 x3 -> b102 x4 -> spb2 x5 -> spu1 x6 -> b110 x7 -> NW_hub): "
               "all 16 pin windows (both faces of all 8 abutted ports) widened to max(old, 3.5) um about their own centre; "
               "12 were 1.75 um (u_window 0.56), 4 were 2.45-2.49 um (both faces of L3012_2 and L3012_3)"],
      "why": "28 pins in a 1.75-um window is u_window 0.56 > 0.5 on q_b102/q_b103/q_b110/q_spb2/q_spu1/q_su20 (TYPE-SAFE-2 track-use report)",
      "check": "plan-time G0/G0C (check.py --completeness --plan-geom report) vs d44v with part 52: errors 971 = 971, warnings 1314 = 1314, "
               "no new error; the pre-existing hops ERROR on NW_b103.L3012x2 (S0->S1 696 um > 405, regs_um[0]) now names bit 1 "
               "instead of bit 0, and one q_spu1 partial_face WARN value moves (W 4229 -> 4226 pins); min gap to the next window "
               "on the same face >= 1.125 um (ledger)",
      "unchanged": ["station counts, regs_um, PIN CYCLES 0, latency table", "window centres, faces, layers, order", "every other lane, slot and type",
                    "outlines, cores, clock, reset", "netlist"],
      "kit_local": "results/die_hbm_1106/spb2_uturn/kit_pin_patch.py rewrites only the L3012 rows of pins.json/io.tcl/plan_pins.json/"
                   "audit_pins.json + freeze.json of a generated kit, after proving the old plan regenerates those rows exactly",
      "replay": "RR=<scratch> bash results/die_hbm_1106/spb2_uturn/run_p54.sh"}
(D / "part54_event.json").write_text(json.dumps(ev, indent=1) + "\n")
rd = D / "README.md"; t = rd.read_text()
para = ("\nEvent part 54 (DIE-HBM-82-SPB 11-06, plan-owner approved DIE-HBM-82): lane L3012 (27 b, su21 -> x1..x7 -> hub) "
        "pin windows widened to max(old, 3.5) um about the same centre on both faces of all 8 abutted ports (16 windows); "
        "fix-only, 0 pin cycles; plan-time G0/G0C 971 = 971 errors, no new error; part54_event.json, "
        "part54_l3012_window_ledger.json; replay results/die_hbm_1106/spb2_uturn/run_p54.sh.\n")
if "Event part 54" not in t:
    rd.write_text(t.rstrip("\n") + "\n" + para)
cur = {"die_plan.json": sha(b), "part54_event.json": sha((D / "part54_event.json").read_bytes()),
       "part54_l3012_window_ledger.json": sha((D / "part54_l3012_window_ledger.json").read_bytes()), "README.md": sha(rd.read_bytes())}
S = D / "SHA256SUMS"
L = [l.split(None, 1) for l in S.read_text().splitlines() if l.strip()]
names = [n for _, n in L]
for i, (a, n) in enumerate(L):
    if n in cur:
        L[i] = [cur[n], n]
L += [[cur[n], n] for n in cur if n not in names]
S.write_text("".join(f"{a}  {n}\n" for a, n in L))
print("PART 54 written", {k: v[:12] for k, v in cur.items()})
