"""adv_placed_hop_ratio.py -- PRECHECK ADV-PLACED-HOP-RATIO (S81-STAGE-SEAT 11-25, COORD; report only, never a gate).

A placed kit's placed_scan.json (tools/autopilot/placed_scan.py: groups with the plan row `ROW=n/hopum` and the placed mean hop)
is compared with the plan: a group whose placed mean hop exceeds RATIO x the plan hop (default 1.2) is a stage chain the placer did
not hold at its plan seats (unseated, or drifted).  FP-CONVERGE-S81 11-25: 354 slice groups over 405 um, 311 unseated, 43 drifted.

Input: placed_scan.json path / directory (searched to depth 3) via kw placed_scan, env OT_ADV_PLACED_SCAN (os.pathsep list), or
`placed_scan.json` files under the tree's kit dirs (kw tree).  Absent = one INFO line, no warning.  RATIO: env OT_ADV_PLACED_HOP_RATIO.
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import json
import os
import re
from pathlib import Path

CHECK = "ADV-PLACED-HOP-RATIO"
RATIO = 1.2
MAX_EX = 3


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def over_ratio(groups, ratio=RATIO):
    """-> [(group, placed_mean_um, plan_hop_um, x)] with placed mean > ratio x the plan hop of its row, worst first"""
    out = []
    for g in groups or []:
        m = re.match(r"^\d+/(\d+)um$", str(g.get("row", "")))
        if not m:
            continue
        hop = float(m.group(1))
        mean = float(g.get("mean_um") or 0)
        if hop > 0 and mean > ratio * hop:
            out.append((g, mean, hop, mean / hop))
    return sorted(out, key=lambda x: -x[3])


def _files(spec):
    for p in str(spec).split(os.pathsep):
        if not p:
            continue
        p = Path(p)
        if p.is_file():
            yield p
        elif p.is_dir():
            base = len(p.parts)
            for f in p.rglob("placed_scan.json"):
                if len(f.parts) - base <= 5:
                    yield f


def findings(raw, plan_path, tree=None, **kw):
    try:
        ratio = float(kw.get("ratio") or os.environ.get("OT_ADV_PLACED_HOP_RATIO") or RATIO)
        spec = kw.get("placed_scan") or os.environ.get("OT_ADV_PLACED_SCAN") or ""
        files = list(_files(spec))
        if not files:
            return [f"# {CHECK}: no placed_scan.json (kw placed_scan / OT_ADV_PLACED_SCAN); nothing to compare"]
        out, ng, nb = [], 0, 0
        for f in files:
            d = json.load(open(f))
            bad = over_ratio(d.get("groups"), ratio)
            if not bad:
                continue
            ng += len(bad)
            nb += sum(int(g.get("bits") or 0) for g, _, _, _ in bad)
            out.append(_w(d.get("type") or f.parent.name, f"{len(bad)} group(s) with placed mean hop > {ratio:g} x plan hop:",
                          "; ".join(f"{g['src']}->{g['end']} placed {m:.0f} um plan {h:.0f} um x{x:.1f} {g.get('bits', 0)}b"
                                    for g, m, h, x in bad[:MAX_EX]) + (" ..." if len(bad) > MAX_EX else "")))
        return out + [_w(f"summary {ng} groups / {nb} bits over {ratio:g} x plan hop in {len(files)} placed_scan.json (report only)")]
    except Exception as e:  # noqa: BLE001 an advisory never breaks the gate
        return [_w(f"not checked: {type(e).__name__}: {str(e)[:200]}")]
