#!/usr/bin/env python3
"""DIE-HBM-82-SPB d44v part 52 packaging: RR/new.json -> d44v die_plan.json.gz (gzip -n, mtime 0), part52_event.json,
part52_ft_uturn_ledger.json, README paragraph, SHA256SUMS rows.   fin_p52.py RR   (run from the repo root)"""
import gzip, hashlib, json, sys
from pathlib import Path
RR = Path(sys.argv[1]); D = Path("physical/die_plan/hbm/plan_of_record/d44v")
sha = lambda b: hashlib.sha256(b).hexdigest()
b = (RR / "new.json").read_bytes()
with open(D / "die_plan.json.gz", "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as g:
    g.write(b)
led = json.loads((RR / "ledger.json").read_text())
(D / "part52_ft_uturn_ledger.json").write_text(json.dumps(led, indent=1) + "\n")
ev = {"schema": "opentallas.hbm_plan_event.v1", "part": 52, "plan": "d44v", "lane": "DIE-HBM-82-SPB", "date": "2026-11-06",
      "approved": "plan-owner approved DIE-HBM-82 (q_spb2 RE-FORM brief: wiring safe form, fix-only; COORD 18:37 (1) types safe by construction)",
      "what": ["q_spb2 ft_slots L1278x3 (1483 b, 5 stations) and L1280x6 (746 b, 6 stations), both N->N turnarounds: internal stations "
               "moved from the N edge (regs y 1494.72, spiral clumps) to nested U corridors below the xcal hard-core row; explicit "
               "per-bit row-legal bit_sites_um (cell 1.404x0.27) at fraction j/k of each bit's own in->band->out Manhattan path; "
               "bands L1278x3 y 1065-1175 (M4+M6 track use 0.49), L1280x6 y 995-1055 (0.46); regs_um = in-window centre + one real "
               "bit site per station (ft_corridor convention)"],
      "why": "q_spb2 vA GRT never converged (3 rounds x 30 extra iterations, 9 h): congestion-25.rpt 20000 capped gcells all at "
             "x 430-953 / y 1279-1502, i.e. ~2230 turnaround bits E-W in the 34-um strip between u_xc_Q2 (OBS M1-M5) and the N edge",
      "evidence": {"grt_probe_before": "same kit/deck (geom_grt.tcl M2-M7 adj 0.25 50 it) on the old 3_place.odb: still in extra iterations",
                   "grt_probe_after": "event sites in the same kit, re-placed: GRT 0/0/0 congestion after 12 extra iterations, total usage 5.04%"},
      "hops_um": {s["slot"]: s["hops_um"] for s in led["slots"]},
      "check": "plan-time G0/G0C (check.py --completeness --plan-geom report) vs the d44v before this part: errors 971 = 971, NEW 0, GONE 0; "
               "one WARN value improves (q_spb2 geom_tap_sinks clk_t16 8239 -> 4394)",
      "unchanged": ["station counts / PIN CYCLES 0 / latency table", "windows, pins, cores, outlines", "every other slot and type",
                    "core_conns, core_macros, clock_entries, reset trees", "netlist (kit LEC proof reusable)"],
      "replay": "RR=<scratch> bash results/die_hbm_1106/spb2_uturn/run_p52.sh"}
(D / "part52_event.json").write_text(json.dumps(ev, indent=1) + "\n")
rd = D / "README.md"; t = rd.read_text()
para = ("\nEvent part 52 (DIE-HBM-82-SPB 11-06, plan-owner approved DIE-HBM-82): q_spb2 N->N turnaround ft slots L1278x3 / L1280x6 "
        "re-sited from the N-edge strip above u_xc_Q2 to nested U corridors below the xcal row with explicit per-bit station sites "
        "(bands y 1065-1175 / 995-1055, track use 0.49 / 0.46, hops <= 363 um); station counts unchanged, 0 pin cycles; plan-time "
        "G0/G0C NEW 0; GRT probe 0 overflow; part52_event.json, part52_ft_uturn_ledger.json; replay results/die_hbm_1106/spb2_uturn/run_p52.sh.\n")
if "Event part 52" not in t:
    rd.write_text(t.rstrip("\n") + "\n" + para)
cur = {"die_plan.json": sha(b), "part52_event.json": sha((D / "part52_event.json").read_bytes()),
       "part52_ft_uturn_ledger.json": sha((D / "part52_ft_uturn_ledger.json").read_bytes()), "README.md": sha(rd.read_bytes())}
S = D / "SHA256SUMS"
L = [l.split(None, 1) for l in S.read_text().splitlines() if l.strip()]
names = [n for _, n in L]
for i, (a, n) in enumerate(L):
    if n in cur:
        L[i] = [cur[n], n]
L += [[cur[n], n] for n in cur if n not in names]
S.write_text("".join(f"{a}  {n}\n" for a, n in L))
print("PART 52 written", {k: v[:12] for k, v in cur.items()})
