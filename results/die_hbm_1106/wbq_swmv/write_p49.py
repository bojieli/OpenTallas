#!/usr/bin/env python3
"""DIE-HBM-82-EP6 d44v part 49 writer: RR/new.json + RR/p/clock_entries.json + the new ot_wbq_sw pins table -> d44v (gzip -n),
part49_event.json, README paragraph, SHA256SUMS rows.  usage: write_p49.py RR"""
import gzip, hashlib, json, sys
from pathlib import Path
RR = Path(sys.argv[1]); D = Path("physical/die_plan/hbm/plan_of_record/d44v"); NEWF = "cores/ot_wbq_sw__155.52x544.32__d44v_split.json"
def gz(src, dst):
    b = Path(src).read_bytes()
    with open(dst, "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as g: g.write(b)
    return hashlib.sha256(b).hexdigest()
cur = {"die_plan.json": gz(RR / "new.json", D / "die_plan.json.gz"),
       "clock_entries.json": gz(RR / "p/clock_entries.json", D / "clock_entries.json.gz"),
       NEWF: gz(RR / "p" / NEWF, D / (NEWF + ".gz"))}
rs = json.loads((RR / "rs/station_resite_report.json").read_text())["types"]
ev = {"schema": "opentallas.hbm_plan_event.v1", "part": 49, "plan": "d44v", "lane": "DIE-HBM-82-EP6", "date": "2026-11-06",
      "approved": "plan-owner DIE-HBM-82 16:1x (grow the wbq_sw outline, estimate the q1 neighbour move) + 16:5x (redo with aqhi on the lattice, stations re-planned by the station tool; clean -> next PART)",
      "what": ["ot_wbq_sw (4 inst: q_hub_nw/ne u_wbk_Q__q{0,1}__sw) 86.4x544.32 -> 155.52x544.32, grown WEST (origin x -69.12); E/N/S/interior pins keep their absolute site (table x +69.12), W face (4101 pins) moves 69.12 west; new table " + NEWF,
               "clock_entries: the 4 sw entries x +69.12 in the sub frame (absolute site kept)",
               "aq_tree13 u_xl_Q_aqhi (q_hub_nw, q_hub_ne) origin x -51.84 (6 x 8.64) to keep the 8.64 gap to the grown q1 sw; contents follow",
               "internal stations: tools/die_plan/station_resite.py on q_hub_nw/ne, applied by hyb.py only to chains the move touched; same register counts (0 added cycles on the applied chains)",
               "ft_slots: tools/die_plan/ft_nudge.py (L7001x1 stage 4 off the grown q0 sw; ledger part49_ft_nudge_ledger.json)"],
      "why": "wbq_sw vA/vB (HG7) GRT-0116 at 86-95% total with 7352 pins on an 86.4-um strip; the root N1M form (part 48) does not change the sw pins",
      "resite_report": {t: {k: v for k, v in x.items() if not isinstance(v, (list, dict))} for t, x in rs.items()},
      "hyb": (RR / "hyb.log").read_text().strip().splitlines(),
      "check": "plan-time G0/G0C (check.py --completeness --plan-geom report) vs the d44v before this part: NEW 0, GONE 0",
      "unchanged": ["core_conns", "core_macros (wbq_sw has none)", "reset trees", "every other type", "register counts / PIN CYCLES 0"],
      "replay": "RR=<scratch> bash results/die_hbm_1106/wbq_swmv/run_p49.sh"}
(D / "part49_event.json").write_text(json.dumps(ev, indent=1) + "\n")
cur["part49_event.json"] = hashlib.sha256((D / "part49_event.json").read_bytes()).hexdigest()
cur["part49_ft_nudge_ledger.json"] = hashlib.sha256((D / "part49_ft_nudge_ledger.json").read_bytes()).hexdigest()
rd = D / "README.md"; t = rd.read_text()
para = ("\nEvent part 49 (DIE-HBM-82-EP6 11-06, plan-owner approved DIE-HBM-82): ot_wbq_sw (4 instances) 86.4 -> 155.52 x 544.32, grown west "
        "(W face moves 69.12 west, other pins keep their absolute site; table " + NEWF + "), aq_tree13 u_xl_Q_aqhi 51.84 west in q_hub_nw/ne, "
        "station chains touched by the move re-planned by station_resite.py (same counts) + ft_nudge.py; plan-time G0/G0C NEW 0; part49_event.json; "
        "replay results/die_hbm_1106/wbq_swmv/run_p49.sh.\n")
if "Event part 49" not in t: rd.write_text(t.rstrip("\n") + "\n" + para)
cur["README.md"] = hashlib.sha256(rd.read_bytes()).hexdigest()
L = [l.split(None, 1) for l in (D / "SHA256SUMS").read_text().splitlines() if l.strip()]
names = [n for _, n in L]
for i, (a, n) in enumerate(L):
    if n in cur: L[i] = [cur[n], n]
L += [[cur[n], n] for n in cur if n not in names]
(D / "SHA256SUMS").write_text("".join(f"{a}  {n}\n" for a, n in L)); print("PART 49 written", {k: v[:12] for k, v in cur.items()})
