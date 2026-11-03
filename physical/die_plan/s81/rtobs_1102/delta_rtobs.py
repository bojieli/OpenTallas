"""DIE-S81-49 11-02: pin the frozen S81 reset relay obstacle model (metadata-only plan event; KV DIE-KV-61 rtobs class).

main 74080dbb8 (canonical placed obstacle union for reset relays) re-solves the reset relay graph of S81 soft types
the plan froze with the pre-11-02 model: on plan_h2_2249 the published landing collector_tree relays match the
re-solved graph on 58/194 types under "canonical" and 191/194 under "lef_origin" (rtobs_1102/census.json; the 3
remaining mismatch under both models, unchanged), and 13 grid+explicit types fail tap legality (radius > 200)
because re-sited relays fall outside their added tap.  Every non-hard S81 type gets reset.obstacle_model =
"lef_origin" (54c3c7c9f mechanism).  No geometry, pin, net or relay change.  Written in the repo plan format.

Step 2 (same event): col_h10_r0_p1__t1__cl574cc59d / __cl911743eb fail under ANY tools (also 39f754dda07): the ft_s2
per-bit station sinks at (1000-1012, 882-889) are 219.17 um from added tap clk_t28 and 219.27 from grid clk_t10.
tools/die_plan/added_tap_recentre.py moves clk_t28 (1126.44, 980.6) -> (1126.818, 954.666) (26.3 um, legal site)
in both types; the reset tree keeps its contract (taps/indices, depth, tap_depth, outs, core resets) and only the
relays re-site, so their collector_tree is republished in the plan and in h2_2249/landed_sidecar_h2.json:

    python3 physical/die_plan/s81/rtobs_1102/delta_rtobs.py
    python3 tools/die_plan/added_tap_recentre.py physical/die_plan/s81/plan_h2_2249.json --out physical/die_plan/s81/plan_h2_2249.json \
        --types col_h10_r0_p1__t1__cl574cc59d,col_h10_r0_p1__t1__cl911743eb --add \
        --sidecar physical/die_plan/s81/h2_2249/landed_sidecar_h2.json --sidecar-out physical/die_plan/s81/h2_2249/landed_sidecar_h2.json \
        --report physical/die_plan/s81/rtobs_1102/tapfix_report.json
    python3 physical/die_plan/s81/rtobs_1102/census.py . physical/die_plan/s81/plan_h2_2249.json   # 204/204 taps, 191/194 trees
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[4] / "tools" / "die_plan"))
import pin_template as PT  # noqa: E402
p = Path(sys.argv[1] if len(sys.argv) > 1 else HERE.parents[1] / "plan_h2_2249.json")
P = json.loads(p.read_text()); n = 0
for tn, t in P["partition_types"].items():
    if t.get("hard"):
        continue
    r = t.setdefault("reset", {})
    if r.get("obstacle_model") != "lef_origin":
        r["obstacle_model"] = "lef_origin"; n += 1
p.write_text(PT.dumps(P))
print("types pinned", n)
