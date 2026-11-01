#!/usr/bin/env python3
"""DIE-S81-47 11-01 (COORD 08:2x batch class (c)): one-block site fix (METHODOLOGY 12.20) for iqf__t1 KIT-WAVE
FAIL PLAN @place [ERROR DPL-0033] (kit-wave s81/e8cbe5f6c70 iqf__t1 attempt_2; fill exception standing).

Root cause (CHECKED on that run's run_place.log + landing_placement.tcl): the one DPL overlap is the FIRM collector
relay cell u_cland_collect_rst_n_t21/_4_ (site 1423.44..1427.76 x 611.352..615.672 = near(relay u_rrl_109 xy
(1425.6, 613.512)) +/-2.16) against ring flop u_cland_idx_i0/u_ring.dch[0].u_dsel/y[59] of the FIRM band idx_i0
[1399.68, 598.272, 1425.6, 708.644].  The relay sits exactly on the band's east edge column (x = 1425.6), so its
reserved site straddles the band edge by 2.16 um.

Fix (variant v2, structural): relay u_rrl_109 moves one site east, x 1425.6 -> 1427.76 (same y, inside the 1442.88
outline); its collector / raw-copy sites then clear the band (abut it at 1425.6).  Hop change +/-2.16 um.
Fallback (variant v1, --v1): landing_contract.group_rects_um override of u_cland_collect_rst_n_t21 only.
Nothing else changes (asserted): every other key of iqf__t1 and every other type.
usage (repo root): delta_iqfsite_1101.py PLAN_IN PLAN_OUT REPORT.json [--v1]"""
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S  # noqa: E402
import landing_place as LP  # noqa: E402
import compact_plan as CP  # noqa: E402

TN = "iqf__t1"
BAND = [1399.68, 598.272, 1425.6, 708.644]
OLD, NEW = [1425.6, 613.512], [1427.76, 613.512]
SITE = "u_cland_collect_rst_n_t21"


def groups(raw):
    tcl = LP.tcl(S.Plan(raw), TN)
    return [(m.group(1), list(map(float, m.group(2).split())), m.group(3))
            for m in re.finditer(r"\{(\S+) \{([\d. ]+)\} (\S+)\}", tcl)]


def straddle(r, b):
    ov = r[0] < b[2] - 1e-6 and r[2] > b[0] + 1e-6 and r[1] < b[3] - 1e-6 and r[3] > b[1] + 1e-6
    inside = r[0] >= b[0] - 1e-6 and r[2] <= b[2] + 1e-6 and r[1] >= b[1] - 1e-6 and r[3] <= b[3] + 1e-6
    return ov and not inside


def main():
    src, dst, rp = sys.argv[1:4]
    v1 = "--v1" in sys.argv[4:]
    text = Path(src).read_text()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    t = raw["partition_types"][TN]
    c = t["clock"]["landing_contract"]
    assert c["bands"]["idx_i0"]["rect_um"] == BAND
    rel = [r for r in c["collector_tree"]["relays"] if r["q"] == "rst_n_t21"]
    assert len(rel) == 1 and rel[0]["name"] == "u_rrl_109" and rel[0]["xy"] == OLD, rel
    before = [(n, r, g) for n, r, g in groups(orig) if n.endswith(("rst_n_t21", "rst_idx_i0"))]
    if v1:
        c.setdefault("group_rects_um", {})[SITE] = [BAND[2], OLD[1] - 2.16, BAND[2] + 4.32, OLD[1] + 2.16]
    else:
        rel[0]["xy"] = NEW
        rel[0]["note"] = ("DIE-S81-47 11-01 iqf__t1 DPL-0033 one-block fix: relay one site east of the idx_i0 band "
                          "edge column (1425.6 -> 1427.76) so its collector/raw-copy sites clear the FIRM ring band")
    assert 0 <= NEW[0] + 2.16 <= t["outline_um"][0]
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in raw["partition_types"]:
        if tn != TN:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
    after = [(n, r, g) for n, r, g in groups(raw) if n.endswith(("rst_n_t21", "rst_idx_i0"))]
    left = [(n, g) for n, r, g in after if straddle(r, BAND) and (not v1 or n == SITE)]   # v1 moves the FIRM site only
    assert not left, left
    mm = re.search(r'^  "' + re.escape(TN) + r'": ', text, re.M)
    _, j = json.JSONDecoder().raw_decode(text, mm.end())
    text = text[:mm.end()] + CP._d(raw["partition_types"][TN], 2) + text[j:]
    assert json.loads(text) == raw
    Path(dst).write_text(text)
    rep = dict(type=TN, variant="v1 group_rects_um override" if v1 else "v2 relay u_rrl_109 one site east",
               band_idx_i0=BAND, sites_before=before, sites_after=after, straddling_after=left)
    Path(rp).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep)[:1500])


if __name__ == "__main__":
    main()
