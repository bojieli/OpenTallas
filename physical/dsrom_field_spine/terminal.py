#!/usr/bin/env python3
"""Terminal verdict of one v9 spine screen (phys.sh): corner STA (SS 60 / FF 25), signal integrity, DRC, antenna and the
kept replica instances in the routed netlist.  Usage: terminal.py <out dir> <tag>"""
import json
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
           g_sel=r"u_sp\.g_reg\[\d+\]\.g_sel\[\d+\]\.u_s", u_rsfm=r"u_sp\.g_reg\[\d+\]\.u_rsfm", u_cc=r"u_sp\.u_cc",
           g_aqi=r"u_sp\.g_aqi\[\d+\]\.u_c", g_qwe=r"u_sp\.g_qwe\[\d+\]\.u_we", g_bwb=r"u_sp\.g_bwb\[\d+\]\.u_bwb",
           u_aoh=r"u_sp\.u_aoh\d", g_grp=r"u_sp\.g_grp\[\d+\]\.u_rep",
           **{f"u_oh{i}": rf"u_sp\.g_reg\[\d+\]\.u_oh{i}" for i in range(5)})
exp = dict(g_ixb=32, g_ixq=8, g_sel=4 * R, u_rsfm=R, u_cc=1, g_aqi=9, g_qwe=8, g_bwb=16, u_aoh=2, g_grp=(R + 7) // 8,
           **{f"u_oh{i}": R for i in range(5)})
act = {k: sum(bool(re.fullmatch(p, n)) for n in names) for k, p in pat.items()}
# v10 / v11 kept copies: g_ixc (stage-3 BF16 read sub-index, ot_v41_kreg) and the quantisers' s11 exponent copies
# (ot_dsrom_aq12f g_s11c, inside the kept quantiser hierarchy: named u_sp.g_aq[k].u_aq/g_s11c[j].u_c/...)
names2 = {"/".join(n.split("/")[:2]) for n in re.findall(r"^\s*DFF\w+\s+\\?(\S+)", net, re.M) if n.count("/") >= 2}
pat2 = dict(g_ixc=r"u_sp\.g_ixc\[\d+\]\.u_ix", g_s11c=r"u_sp\.g_aq\[\d+\]\.u_aq/g_s11c\[\d+\]\.u_c",
            g_selg=r"u_sp\.g_reg\[\d+\]\.g_sel\[\d+\]\.u_g")
exp.update(g_ixc=32, g_s11c=8, g_selg=4 * R)   # v12: per-lane kept {row_ge, select outcomes} copies
act.update({k: sum(bool(re.fullmatch(p, n)) for n in (names | names2)) for k, p in pat2.items()})
si = phy.get("signal_integrity_violations", {})
d.update(SS_ps=sta["setup_ss"]["worst_slack_ps"], SS_pins=sta["setup_ss"]["violating_d_pins"],
         FF_ps=sta["hold_ff"]["worst_slack_ps"], FF_pins=sta["hold_ff"]["violating_d_pins"], SI=si,
         drc=phy.get("drc"), antenna=phy.get("antenna"), area_um2=phy.get("area_um2"),
         replicas=dict(expected=exp, actual=act, passed=act == exp))
clean = all(si.get(k) == 0 for k in ("max_slew_violations", "max_cap_violations", "max_fanout_violations")) \
    and d["drc"] == 0 and d["antenna"] == 0
d["verdict"] = "PASS" if sta.get("closes_signoff") and clean and act == exp else "FAIL"
(out / f"{tag}_terminal.json").write_text(json.dumps(d, indent=1) + "\n")
print(json.dumps({k: d[k] for k in ("tag", "verdict", "SS_ps", "FF_ps", "SI", "drc")}))
sys.exit(0 if d["verdict"] == "PASS" else 1)
