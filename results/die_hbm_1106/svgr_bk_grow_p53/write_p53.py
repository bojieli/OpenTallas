#!/usr/bin/env python3
"""DIE-HBM-82-SVGR d44v part 53 writer: RR/new.json + RR/p/core_macros.json + the new ot_svgr_bk pins table -> d44v (gzip -n),
part53_event.json, README paragraph, SHA256SUMS rows.  usage: write_p53.py RR   (run from the repo root)"""
import gzip, hashlib, json, sys
from pathlib import Path
RR = Path(sys.argv[1]); D = Path("physical/die_plan/hbm/plan_of_record/d44v"); NEWF = "cores/ot_svgr_bk__302.4x207.36__d44v_p53.json"
def gz(src, dst):
    b = Path(src).read_bytes()
    with open(dst, "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as g: g.write(b)
    return hashlib.sha256(b).hexdigest()
cur = {"die_plan.json": gz(RR / "new.json", D / "die_plan.json.gz"), NEWF: gz(RR / "p" / NEWF, D / (NEWF + ".gz"))}
(D / "core_macros.json").write_bytes((RR / "p/core_macros.json").read_bytes())
cur["core_macros.json"] = hashlib.sha256((D / "core_macros.json").read_bytes()).hexdigest()
CL = "corelat/cycles_svgr_own_rf3_1106.tsv"
(D / CL).write_bytes(Path("results/die_hbm_1106/svgr_bk_grow_p53/cycles_svgr_own_rf3_1106.tsv").read_bytes())
cur[CL] = hashlib.sha256((D / CL).read_bytes()).hexdigest()
rs = json.loads((RR / "rs/station_resite_report.json").read_text())["types"]
mk = json.loads((RR / "p/part53_mk.json").read_text())
ev = {"schema": "opentallas.hbm_plan_event.v1", "part": 53, "plan": "d44v", "lane": "DIE-HBM-82-SVGR", "date": "2026-11-06",
      "approved": "plan-owner DIE-HBM-82 (A): grow ot_svgr_bk 43.2 on its E (FIFO) face if all 16 sites have room; plan-time check first, stations by the station tool, G0/G0C NEW 0 -> next free d44v PART",
      "what": ["ot_svgr_bk (16 inst: q_hub_nw/ne u_svg_Q{0..3}__b{0,1}) 259.2x207.36 -> 302.4x207.36, +43.2 on the core-local E face; macros + W/N/S/interior pins keep their core-frame site, the 1148 E-face pins (in_data, in_v, cr) move +43.2; new table " + NEWF + " (= GRT probe-W table, pins sha cf83c518e5c3)",
               "placement: core-local W face 25.92 out (street to ot_svgr_top 43.2 -> 17.28), core-local E face 17.28 out (street to ot_svgr_own 34.56 -> 17.28); MX origin x -25.92, MY origin x -17.28 (8.64 lattice); no neighbour moves",
               "clock taps: the 16 core taps follow their core-frame entry (MX x -25.92, MY x +25.92); clock_entries.json (core frame) unchanged",
               "core_macros.json: ot_svgr_bk outline only (same 4 SRAMs, same rects)",
               "internal stations: tools/die_plan/station_resite.py on q_hub_nw/ne, applied by results/die_hbm_1106/wbq_swmv/hyb.py only to chains the grow touched",
               "ft_slots: tools/die_plan/ft_nudge.py (ledger part53_ft_nudge_ledger.json)"],
      "why": "ot_svgr_bk vC..vO (DIE-HBM-82-SVGR): GRT vertical overflow over the SRAM column; the CDC FIFO storage (~6000 um2) does not fit the 43.2 east strip (guide-box capacity 0.97 on vN/vO); FIFO strip grown",
      "instances": mk["instances"], "taps": mk["taps"],
      "resite_report": {t: {k: v for k, v in x.items() if not isinstance(v, (list, dict))} for t, x in rs.items()},
      "hyb": (RR / "hyb.log").read_text().strip().splitlines(),
      "check": "plan-time G0/G0C (check.py --completeness --plan-geom report) + plan_geom.py vs the d44v before this part: " + "G0 ERROR set (paths normalised): NEW 0 substantive (only q_hub_nw core_faces count text 93 -> 90 ports facing away), GONE 3 (complete [internal_station] bus:L40_i hop > 405 x3); plan_geom FAIL 232 -> 232, NEW 0 GONE 0 WORSE 0",
      "pin_cycles": "corelat/cycles_svgr_own_rf3_1106.tsv: ot_svgr_own bk_in_v,bk_in_data +1 hbm_clk (RF3, recipe ot_svgr_own__rf3); svgr_bk grow itself adds 0",
      "unchanged": ["core_conns", "clock_entries", "reset trees", "every other module / type", "register counts on applied chains"],
      "replay": "RR=<scratch> bash results/die_hbm_1106/svgr_bk_grow_p53/run_p53.sh"}
(D / "part53_event.json").write_text(json.dumps(ev, indent=1) + "\n")
for n in ("part53_event.json", "part53_ft_nudge_ledger.json"): cur[n] = hashlib.sha256((D / n).read_bytes()).hexdigest()
rd = D / "README.md"; t = rd.read_text()
para = ("\nEvent part 53 (DIE-HBM-82-SVGR 11-06, plan-owner approved DIE-HBM-82 (A)): ot_svgr_bk (16 instances) 259.2 -> 302.4 x 207.36, "
        "+43.2 on the core-local E (FIFO) face (E-face pins +43.2, other pins and macros keep their core-frame site; table " + NEWF + "), "
        "streets to ot_svgr_top / ot_svgr_own 17.28, no neighbour moves; station chains touched re-planned (station_resite.py + ft_nudge.py); "
        "plan-time G0/G0C NEW 0; part53_event.json; replay results/die_hbm_1106/svgr_bk_grow_p53/run_p53.sh.\n")
if "Event part 53" not in t: rd.write_text(t.rstrip("\n") + "\n" + para)
cur["README.md"] = hashlib.sha256(rd.read_bytes()).hexdigest()
L = [l.split(None, 1) for l in (D / "SHA256SUMS").read_text().splitlines() if l.strip()]
names = [n for _, n in L]
for i, (a, n) in enumerate(L):
    if n in cur: L[i] = [cur[n], n]
L += [[cur[n], n] for n in cur if n not in names]
(D / "SHA256SUMS").write_text("".join(f"{a}  {n}\n" for a, n in L)); print("PART 53 written", {k: v[:12] for k, v in cur.items()})
