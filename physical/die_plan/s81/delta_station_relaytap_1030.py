#!/usr/bin/env python3
"""DIE-S81-39 station clock-reach fix (COORD 22:2x, 12.20 one plan-wide pattern, default 'add taps, do not move relays').

KIT-WAVE-2 AUTO-GEOM on the stform2 plan (GEOM-83/84 21:47-22:19): every slice_station kit FAILs clock_reach 366-676 um.
The far sinks are (1) reset relay hops of the station reset tree (reset_tree.for_type: u_rrl_* / collect_rst_rl_*, kind
'wire'/'pad' with no tap) on the long arst_n legs, and (2) on t29 the last-station out-face registers at the NE corner.
Neither is in the planned sink inventory (taps.sink_sites), so the stform2 density/explicit taps never saw them.

Fix (plan data only, every slice_station type):
  * every reset-tree relay site, every ft_slots stage register site (regs_um) and every slot face register column
    (in/out window ends + centre on its face) that lies more than tap_radius_um
    (150, Manhattan) from every explicit tap becomes a plan sink row (clock.sink_sites_um [x, y, 1]) and gets one light
    tap at the site, legalised by schema.tap_clear(strict) -- the stform2 control-tap rule (delta_station_form_1030.py);
  * iterated with the reset tree recomputed on the new taps (relays are sited FROM taps) until no site is uncovered;
  * explicit_taps re-validated (load <= cap, radius <= 150, no empty tap); forwarded clock out pins re-take the nearest
    tap (stform2 rule).  Relays are not moved by this script; the collector refresh (delta_station_coll_1030.py, run
    next) recomputes the trees with reset_tree.for_type exactly as for stform2.
Nothing else changes (asserted): non-station types, outlines, buses, ft_slots, latency.
usage (repo root): delta_station_relaytap_1030.py PLAN_IN PLAN_OUT REPORT.json"""
import copy
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(ROOT))
import schema as S  # noqa: E402
import reset_tree as RT  # noqa: E402
import taps as TP  # noqa: E402
from gen_phys import clock_pins  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compact_plan as CP  # noqa: E402

PREFIX = "slice_station"


def l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def sites(P, raw, tn):
    t = raw["partition_types"][tn]
    w, h = t["outline_um"]
    T = RT.for_type(P, tn)
    out = [("relay:" + r["name"], (float(r["xy"][0]), float(r["xy"][1]))) for r in T["relays"]]
    for s in t.get("ft_slots", []):
        # the face register columns of every slot (in-face first stage, out-face last stage): window ends + centre
        for side in ("in", "out"):
            face, win = s.get(side + "_face"), s.get(side + "_window_um")
            if not face or not win:
                continue
            for k, v in enumerate((win[0], (win[0] + win[1]) / 2, win[1])):
                xy = {"N": (v, h), "S": (v, 0.0), "E": (w, v), "W": (0.0, v)}[face]
                out.append((f"face:{s['name']}:{side}:{k}", (float(xy[0]), float(xy[1]))))
        for k, xy in enumerate(s.get("regs_um", []) or []):
            out.append((f"ft:{s['name']}:{k}", (min(max(float(xy[0]), 0.0), w), min(max(float(xy[1]), 0.0), h))))
    return out


def main():
    src, dst, rp = sys.argv[1:4]
    raw = json.load(open(src))
    orig = copy.deepcopy(raw)
    types = sorted(tn for tn in raw["partition_types"] if tn.startswith(PREFIX))
    if os.environ.get("RT_ONLY"):
        types = [tn for tn in types if tn in os.environ["RT_ONLY"].split(",")]
    rep = {tn: dict(taps0=len(raw["partition_types"][tn]["clock"]["taps"]), added=[]) for tn in types}
    for it in range(8):
        P = S.Plan(raw)
        added = 0
        for tn in types:
            t = raw["partition_types"][tn]
            ck = t["clock"]
            R = float(ck.get("tap_radius_um", 150.0))
            w, h = t["outline_um"]
            txy = [tuple(p["xy"]) for p in ck["taps"] if p.get("kind") != "core"]
            for name, xy in sites(P, raw, tn):
                if min(l1(xy, q) for q in txy) <= R:
                    continue
                q = S.tap_clear(t, min(max(xy[0], TP.TAP_MARGIN_UM), w - TP.TAP_MARGIN_UM),
                                min(max(xy[1], TP.TAP_MARGIN_UM), h - TP.TAP_MARGIN_UM), txy, strict=True)
                q = (round(q[0], 4), round(q[1], 4))
                assert l1(xy, q) <= R, (tn, name, xy, q)
                ck.setdefault("sink_sites_um", []).append([round(xy[0], 4), round(xy[1], 4), 1])
                ck["taps"].append(dict(name=f"clk_t{len(ck['taps'])}", xy=list(q)))
                txy.append(q)
                added += 1
                rep[tn]["added"].append(dict(iter=it, site=name, xy=[round(xy[0], 4), round(xy[1], 4)], tap=list(q)))
        print("relay-tap pass", it, "added", added, flush=True)
        if not added:
            break
    else:
        raise SystemExit("relay taps did not converge")
    P = S.Plan(raw)
    for tn in types:
        t = raw["partition_types"][tn]
        fin = TP.explicit_taps(P, tn)
        roots = clock_pins(P, tn)
        moved = []
        for p in t["clock"].get("landing_contract", {}).get("pins", []):
            if p.get("kind") == "clock" and p.get("dir") == "out" and "source_clock_port" in p:
                tap = min(roots, key=lambda r: abs(r[1] - p["xy_um"][0]) + abs(r[2] - p["xy_um"][1]))[0]
                if tap != p["source_clock_port"]:
                    moved.append(f"{p['name']}:{p['source_clock_port']}->{tap}")
                p["source_clock_port"] = tap
        far = max(min(l1(xy, tuple(q["xy"])) for q in t["clock"]["taps"]) for _, xy in sites(P, raw, tn))
        rep[tn].update(taps=len(fin), tap_load_max=max(q[3] for q in fin), tap_radius_max=max(q[4] for q in fin),
                       site_reach_max=round(far, 2), source_retap=moved)
        print("taps", tn, rep[tn]["taps0"], "->", len(fin), "load", rep[tn]["tap_load_max"], "radius",
              rep[tn]["tap_radius_max"], "site reach", rep[tn]["site_reach_max"], flush=True)
    for tn in raw["partition_types"]:
        if tn not in types:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in types:
        a, b = copy.deepcopy(raw["partition_types"][tn]), copy.deepcopy(orig["partition_types"][tn])
        for x in (a, b):
            x["clock"].pop("taps")
            x["clock"].pop("sink_sites_um", None)
            for p in x["clock"].get("landing_contract", {}).get("pins", []):
                p.pop("source_clock_port", None)
        assert a == b, tn
    text = open(src).read()
    for tn in types:
        if not rep[tn]["added"] and not rep[tn]["source_retap"]:
            continue
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == raw
    open(dst, "w").write(text)
    summ = dict(types=len(types), types_changed=sum(1 for tn in types if rep[tn]["added"]),
                taps_added=sum(len(rep[tn]["added"]) for tn in types),
                tap_load_max=max(rep[tn]["tap_load_max"] for tn in types),
                site_reach_max=max(rep[tn]["site_reach_max"] for tn in types))
    rep["_summary"] = summ
    json.dump(rep, open(rp, "w"), indent=1)
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
