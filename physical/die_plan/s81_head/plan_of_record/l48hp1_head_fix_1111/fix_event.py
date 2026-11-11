#!/usr/bin/env python3
"""HEAD-94 11-11 class fix for the l48uj HEAD kit FAILs (COORD fail-watch 12:0x).
 hd_host_e PDN-0006: the H2 child ot_s81hd_he_epc abstract has ONE blanket M6 and M7 OBS rect over 97% of the macro, so the
   die PDN M6/M7 straps cannot reach its M5 PG stripes (Class C of tools/die_plan/abstract_detail.py). Fix = the existing
   splice: M6/M7 OBS replaced by the exact shapes of the SAME routed ODB (write_abstract_lef -bloat_factor 1), nothing else
   changes (check_ok, pins/PG/lower OBS identical).  Plan: hard core lef -> tracked l48hp1_h2/views/ot_s81hd_he_epc.lef.
 hd_st_n4 OT_CLAND 'no legal nonoverlapping row/site in reserved band for u_cland_agg_5': lepB cropped hd_st_n4 1123.2 -> 993.6
   and scaled bands/stages/sites but NOT clock.landing_status_anchors; agg_5 x 1011.845 sits outside the 993.6 outline.
   Fix = scale the anchors' x by 993.6/1123.2 like every other nst4 item (collinearity kept).
 usage: fix_event.py REPO BASE_PLAN.json[.gz] OUT.json"""
import gzip, json, sys
from pathlib import Path
R = Path(sys.argv[1]); src = Path(sys.argv[2]); out = Path(sys.argv[3])
raw = gzip.open(src).read() if src.suffix == ".gz" else src.read_bytes()
P = json.loads(raw)
LEF = "physical/die_plan/s81_head/plan_of_record/l48hp1_h2/views/ot_s81hd_he_epc.lef"
assert (R / LEF).is_file()
for h in P["partition_types"]["hd_host_e"]["hard_cores"]:
    if h["module"] == "ot_s81hd_he_epc":
        print("epc lef", h["lef"], "->", LEF); h["lef"] = LEF
t = P["partition_types"]["hd_st_n4"]
W, _ = t["outline_um"]
OLDW = 1123.2
f = W / OLDW
an = t["clock"]["landing_status_anchors"]
for k, (x, y) in list(an.items()):
    if x > W - 1e-6 or True:
        an[k] = [round(x * f, 3), y]
        print("anchor", k, [x, y], "->", an[k])
out.write_text(json.dumps(P, indent=1) + "\n")
