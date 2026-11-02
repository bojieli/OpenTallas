#!/usr/bin/env python3
"""DIE-S81-47 11-01 (CLOSURE-LIST S81-007, OWNER 11-01 batch: one fix per class): G0C 'cuts' class (12 ERRORs on the
event plan 6daabfc70429; check.check_cuts reports only the worst partition per cut line, so fixing those exposes the
next partition on the same line -- this delta iterates the exact G0 cut model to a fixed point over ALL partitions).

Class: the G0 cut model gives each partition only ft_track_frac (default 0.25) of its M4/M6 (H) or M5/M7 (V) tracks
for feedthrough bits and fails a partition segment above budgets.cut_ratio_max 0.6, i.e. ft may use 15 % of the lower
tracks.  The listed types carry their S81 slot-ft bits (ft_slots, routed BY the partition kit itself, not by the die)
above that budget.  None of the first 10 has a routed kit yet (KIT-WAVE: WAIT-DEP child lib / svc landing band), so
there is no measured routing either way.

Fix (budget declaration, one key per type): partition_types.<t>.ft_track_frac = the share the plan's own ft bits need
so every segment of the type sits at <= TARGET (0.58) of its share: frac = ceil100(frac * (bits/tracks) / TARGET),
iterated with check.check_cuts until it reports no cut ERROR.  die_ft_bands (die-owned stripes the kit keeps its own
routing OFF) are NOT used: on S81 the ft bits are partition-routed, so a die-owned band would block the wires it is
meant to carry.  die_trial's die GRT model takes min(ft_track_frac) over all types (still 0.25), so the frozen die
GRT model is unchanged.  The measured gate stays each type's own kit GRT/DRT (12.28b: no stricter reading, measured
route decides); a kit route failure re-opens the type.
Nothing else changes (asserted).  usage (repo root): delta_cutfrac_1101.py PLAN_IN PLAN_OUT REPORT.json"""
import copy
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import compact_plan as CP  # noqa: E402
import schema as S  # noqa: E402
import check as CK  # noqa: E402

BASE, TARGET = CK.FT_TRACK_FRAC, 0.58
MSG = re.compile(r"cut at ([\d.]+): (\S+) segment carries (\d+) bits on ([\d.]+) tracks")


def cut_errors(raw):
    P = S.Plan(raw)
    R = CK.Report(False)
    geo = {lid: CK.lane_geometry(P, lid) for lid in P.lanes}
    CK.check_cuts(P, R, geo)
    return [e for e in R.errors() if e.get("check") == "cuts"] if hasattr(R, "errors") else []


def main():
    src, dst, rp = sys.argv[1:4]
    text = Path(src).read_text()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    parts = {p["name"]: p for p in raw["partitions"]}
    rows, history = {}, []
    for it in range(12):
        errs = cut_errors(raw)
        history.append([e["msg"] for e in errs])
        if not errs:
            break
        for e in errs:
            m = MSG.search(e["msg"])
            assert m, e    # a full-line (non-partition) cut ERROR is not this class
            tn = parts[m.group(2)]["type"]
            t = raw["partition_types"][tn]
            if tn not in rows:
                assert "ft_track_frac" not in orig["partition_types"][tn] and not t.get("die_ft_bands"), tn
                assert sum(1 for p in parts.values() if p["type"] == tn) == 1, tn
            cur = t.get("ft_track_frac", BASE)
            ratio = int(m.group(3)) / float(m.group(4))
            new = max(cur, math.ceil(cur * ratio / TARGET * 100) / 100)
            assert new < 1.0, (tn, new)
            t["ft_track_frac"] = new
            r = rows.setdefault(tn, dict(parts=sorted(n for n, p in parts.items() if p["type"] == tn), segments=[]))
            r["segments"].append(dict(iter=it, cut=m.group(1), part=m.group(2), bits=int(m.group(3)),
                                      tracks_at_prev_frac=float(m.group(4)), prev_frac=cur, ratio=round(ratio, 3)))
            r["ft_track_frac"] = new
    else:
        raise SystemExit("no fixed point")
    assert not cut_errors(raw)
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in raw["partition_types"]:
        a = dict(raw["partition_types"][tn])
        if tn in rows:
            a.pop("ft_track_frac")
        assert a == orig["partition_types"][tn], tn
    for tn in rows:
        mm = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, mm.end())
        text = text[:mm.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == raw
    Path(dst).write_text(text)
    rep = dict(rule="S81-007 cuts class: per-type ft_track_frac budget declaration (kit GRT/DRT = measured gate)",
               base_frac=BASE, cut_ratio_max=raw["budgets"]["cut_ratio_max"], target=TARGET, iterations=len(history),
               errors_per_iteration=[len(h) for h in history],
               types={tn: dict(ft_track_frac=r["ft_track_frac"], parts=r["parts"], segments=r["segments"])
                      for tn, r in sorted(rows.items())})
    Path(rp).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(errors_per_iteration=rep["errors_per_iteration"],
                          fracs={t: v["ft_track_frac"] for t, v in rep["types"].items()})))


if __name__ == "__main__":
    main()
