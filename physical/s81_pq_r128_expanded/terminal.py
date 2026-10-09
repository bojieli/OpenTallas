#!/usr/bin/env python3
"""Terminal verdict of one v9 spine screen (phys.sh): corner STA (TT setup / FF hold, 60 / 25 ps uncertainty), signal integrity, DRC, antenna and the
kept replica instances in the routed netlist.  Usage: terminal.py <out dir> <tag>"""
import json
import math
import re
import sys
from pathlib import Path

out, tag = Path(sys.argv[1]), sys.argv[2]
R = int(tag.split("_")[0].split("r")[1])
d = dict(tag=tag, verdict="FAIL_FLOW")
try:
    sta = json.loads((out / f"{tag}_corner_sta.json").read_text())
    phy = json.loads((out / f"{tag}.json").read_text())["design"]
    net = next((out / f"work_{tag}/orfs/results/asap7").glob("*/base/6_final.v")).read_text()
except Exception as e:  # noqa: BLE001
    d["error"] = repr(e)
    (out / f"{tag}_terminal.json").write_text(json.dumps(d, indent=1) + "\n"); print(json.dumps(d)); sys.exit(1)
names = {n.split("/")[0] for n in re.findall(r"^\s*DFF\w+\s+\\?(\S+)", net, re.M)}
pat = dict(g_ixb=r"u_sp\.g_ixb\[\d+\]\.u_ix", g_ixq=r"u_sp\.g_ixq\[\d+\]\.u_ix",
           g_sel=r"u_sp\.g_reg\[\d+\]\.g_sel\[\d+\]\.u_s", u_rsfm=r"u_sp\.g_reg\[\d+\]\.u_rsfm", u_cc=r"u_sp\.g_cc\[\d+\]\.u_cc",
           g_aqi=r"u_sp\.g_aqi\[\d+\]\.u_c", g_qwe=r"u_sp\.g_qwe\[\d+\]\.u_we", g_bwb=r"u_sp\.g_bwb\[\d+\]\.u_bwb",
           u_aoh=r"u_sp\.u_aoh\d", g_grp=r"u_sp\.g_grp\[\d+\]\.u_rep",
           **{f"u_oh{i}": rf"u_sp\.g_reg\[\d+\]\.u_oh{i}" for i in range(5)})
exp = dict(g_ixb=32, g_ixq=8, g_sel=4 * R, u_rsfm=R, u_cc=3, g_aqi=9, g_qwe=8, g_bwb=16, u_aoh=2, g_grp=(R + 7) // 8,
           **{f"u_oh{i}": R for i in range(5)})
act = {k: sum(bool(re.fullmatch(p, n)) for n in names) for k, p in pat.items()}
# v10 / v11 kept copies: g_ixc (stage-3 BF16 read sub-index, ot_v41_kreg) and the quantisers' s11 exponent copies
# (ot_dsrom_aq12f g_s11c, inside the kept quantiser hierarchy: named u_sp.g_aq[k].u_aq/g_s11c[j].u_c/...)
names2 = {"/".join(n.split("/")[:2]) for n in re.findall(r"^\s*DFF\w+\s+\\?(\S+)", net, re.M) if n.count("/") >= 2}
pat2 = dict(g_ixc=r"u_sp\.g_ixc\[\d+\]\.u_ix", g_s11c=r"u_sp\.g_aq\[\d+\]\.u_aq/g_s11c\[\d+\]\.u_c",
            g_selg=r"u_sp\.g_reg\[\d+\]\.g_sel\[\d+\]\.u_g")
exp.update(g_ixc=64, g_s11c=16, g_selg=4 * R)   # v12: per-lane select copies; v13: 64 g_ixc, 8 s11 copies per aq12m
act.update({k: sum(bool(re.fullmatch(p, n)) for n in (names | names2)) for k, p in pat2.items()})
si = phy.get("signal_integrity_violations", {})
tt = sta.get("setup_tt") or {}
ff = sta["hold_ff"]
d.update(setup_corner="tt", TT_ps=tt.get("worst_slack_ps"), TT_pins=tt.get("violating_d_pins"),
         SS_ps=sta["setup_ss"]["worst_slack_ps"], SS_pins=sta["setup_ss"]["violating_d_pins"],
         SS_sensitivity_ps=sta["setup_ss"]["worst_slack_ps"],
         FF_ps=sta["hold_ff"]["worst_slack_ps"], FF_pins=sta["hold_ff"]["violating_d_pins"], SI=si,
         drc=phy.get("drc"), antenna=phy.get("antenna"), area_um2=phy.get("area_um2"),
         replicas=dict(expected=exp, actual=act, passed=act == exp))
clean = all(si.get(k) == 0 for k in ("max_slew_violations", "max_cap_violations", "max_fanout_violations")) \
    and d["drc"] == 0 and d["antenna"] == 0
# Owner Option B: require measured TT setup and FF hold at zero; retain SS as sensitivity.
# A legacy closes_signoff flag may still include SS, so judge the actual corner receipts.
def finite_nonnegative(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0

errors = list(tt.get("errors") or []) + list(ff.get("errors") or [])
if tt.get("error") or ff.get("error"):
    errors.append(tt.get("error") or ff.get("error"))
d["timing_errors"] = errors
timing_ok = finite_nonnegative(d["TT_ps"]) and finite_nonnegative(d["FF_ps"]) and not errors
d["verdict"] = "PASS" if timing_ok and clean and act == exp else "FAIL"
import os  # noqa: E402
if os.environ.get("OT_FS_MARGIN") == "1":
    d["margin"] = dict(setup_corner="tt", tt_min_ps=0, ff_min_ps=0, post_sdc=sta.get("post_sdc"))
(out / f"{tag}_terminal.json").write_text(json.dumps(d, indent=1) + "\n")
print(json.dumps({k: d[k] for k in ("tag", "verdict", "setup_corner", "TT_ps", "SS_ps", "FF_ps", "SI", "drc", "SS_pins", "FF_pins")}))
sys.exit(0 if d["verdict"] == "PASS" else 1)
