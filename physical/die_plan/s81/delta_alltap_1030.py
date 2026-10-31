#!/usr/bin/env python3
"""DIE-S81-40 die-wide clock tap delta (COORD 2026-10-30 23:51/23:53 (b): "the relaytap pattern (stations only) must be
applied to ALL S81 types; use plan_geom.py as the check, extend the tap delta die-wide (taps only, no moves), keep CA
related-pair <= 150").

plan_geom (AUTOBUILD-GATE-1, same AUTO-GEOM rules/limits) on plan 84fc22ab807d: 161/203 types FAIL, clock_reach on every
R4-grid type (ceil(w/400) x ceil(h/400) grid: cell half-diagonal 280-340 um Manhattan > 220) and tap load up to 11211
plan sinks on one grid tap (leaf ft columns).  The 46 slice_station types already carry the fix form (stform2 density
taps frozen as an explicit table + relay taps, delta_station_form_1030 / delta_station_relaytap_1030) and pass.

Fix = the SAME station form on every non-hard R4-grid type (tap_mode unset), plan data only:
  1. clock.tap_mode density with the station settings (target 600, cap 1500, radius 150 um), control_sinks, and the
     landing-contract control pins (non-clock) as sink_sites_um rows (delta_station_form_1030 (b)); the reset IN site
     joins the density sinks for the solve only;
  2. the density table is FROZEN as clock.tap_mode explicit (clk, clk_t1.. ; early core taps kept unchanged, first);
  3. relay-tap passes (delta_station_relaytap_1030 rule, extended to the full plan_geom sink inventory: reset relays /
     root / outs, landing collectors, landed out registers, ring-band read corners): every site farther than 150 um
     (Manhattan) from every clock entry becomes a sink_sites_um row with one light tap at it (schema.tap_clear strict),
     iterated with the reset tree recomputed on the new taps until none is left;
  4. explicit_taps re-validated (load <= cap, radius <= 150, no empty tap); forwarded out clocks re-take the nearest tap.
Asserted unchanged: hard types, station types, outlines, pins, buses, ft_slots, hard_cores, every plan key other than
partition_types; within a changed type only clock.{tap_mode, control_sinks, tap_target_sinks, tap_max_sinks,
tap_radius_um, taps (non-core), sink_sites_um} and landing_contract pins' source_clock_port.
usage (repo root): delta_alltap_1030.py PLAN_IN PLAN_OUT REPORT.json   (ALLTAP_ONLY=t1,t2 subset; ALLTAP_JOBS=n)"""
import copy
import json
import multiprocessing as mp
import os
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(ROOT))
import schema as S  # noqa: E402
import taps as TP  # noqa: E402
import plan_geom as PG  # noqa: E402
import reset_tree as RT  # noqa: E402
from gen_phys import clock_pins, tap_pins  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compact_plan as CP  # noqa: E402

CLOCK = dict(tap_mode="density", tap_target_sinks=600, tap_max_sinks=1500, tap_radius_um=150.0)
R = CLOCK["tap_radius_um"]
_P = None


def l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def face_point(x, y, w, h):
    return list(TP._inset(x, y, min((("W", x), ("E", w - x), ("S", y), ("N", h - y)), key=lambda q: q[1])[0], w, h))


def _density(tn):
    return [tuple(r[:3]) for r in TP.density_taps(_P, tn, control=False)]


def _sites(tn):
    """every plan clock sink of tn that AUTO-GEOM / plan_geom measures for clock_reach (kind, x, y)."""
    try:
        G = PG.type_sites(_P, tn)
        out = [(k, float(x), float(y)) for x, y, _, k in G["sinks"]]
        out += [(k, float(x), float(y)) for x, y, k in G["fwd"]]
        ent = [(x, y) for n, x, y in G["entries"]]
        return out, ent, None
    except Exception as ex:          # plan_geom cannot read this type: cover sink_sites + reset relays directly
        out = [("plan", x, y) for x, y, _ in TP.sink_sites(_P, tn)]
        T = RT.for_type(_P, tn)
        out += [("relay:" + r["name"], float(r["xy"][0]), float(r["xy"][1])) for r in T["relays"]]
        out.append(("reset_root", float(T["root"][0]), float(T["root"][1])))
        ent = [(x, y) for n, x, y in tap_pins(_P, tn) if n not in ("arst_n", "start_i")]
        return out, ent, f"{type(ex).__name__}: {str(ex)[:100]}"


def main():
    global _P
    src, dst, rp = sys.argv[1:4]
    raw = json.load(open(src))
    orig = copy.deepcopy(raw)
    types = sorted(tn for tn, t in raw["partition_types"].items()
                   if not t.get("hard") and not t.get("clock", {}).get("tap_mode"))
    if os.environ.get("ALLTAP_ONLY"):
        types = [tn for tn in types if tn in os.environ["ALLTAP_ONLY"].split(",")]
    jobs = min(len(types), int(os.environ.get("ALLTAP_JOBS", "32")))
    rep = {tn: dict(light=[]) for tn in types}
    arst = {}
    for tn in types:
        t = raw["partition_types"][tn]
        ck = t["clock"]
        w, h = t["outline_um"]
        ck.update(CLOCK)
        ss = [face_point(p["xy_um"][0], p["xy_um"][1], w, h) + [1]
              for p in ck.get("landing_contract", {}).get("pins", []) if p.get("kind") != "clock"]
        ss = [[round(v, 4) for v in r] for r in ss]
        if ss:
            ck["sink_sites_um"] = list(ck.get("sink_sites_um", [])) + ss
        a = (raw.get("reset", {}).get("in_sites") or {}).get(tn)
        if a:
            arst[tn] = [float(v) for v in a] + [1]
            ck.setdefault("sink_sites_um", []).append(arst[tn])
    _P = S.Plan(raw)
    with mp.get_context("fork").Pool(jobs) as pool:
        got = dict(zip(types, pool.map(_density, types)))
    for tn in types:
        ck = raw["partition_types"][tn]["clock"]
        if tn in arst:
            ck["sink_sites_um"].pop()
            if not ck["sink_sites_um"]:
                ck.pop("sink_sites_um")
        ck["tap_mode"] = "explicit"
        ck["control_sinks"] = True
        order = sorted(got[tn], key=lambda r: 0 if r[0] == "clk" else int(r[0][5:]))
        assert [r[0] for r in order] == ["clk"] + [f"clk_t{i}" for i in range(1, len(order))], order
        core = [p for p in ck.get("taps", []) if p.get("kind") == "core"]
        ck["taps"] = core + [dict(name=n, xy=[round(x, 4), round(y, 4)]) for n, x, y in order]
        rep[tn]["density_taps"] = len(order)
        print("density", tn, len(order), flush=True)
    for it in range(10):
        _P = S.Plan(raw)
        with mp.get_context("fork").Pool(jobs) as pool:
            sites = dict(zip(types, pool.map(_sites, types)))
        added = 0
        for tn in types:
            t = raw["partition_types"][tn]
            ck = t["clock"]
            w, h = t["outline_um"]
            out, ent, err = sites[tn]
            if err:
                rep[tn]["plan_geom_error"] = err
            ent = list(ent)
            txy = [tuple(p["xy"]) for p in ck["taps"] if p.get("kind") != "core"]
            for kind, x, y in out:
                if ent and min(l1((x, y), q) for q in ent) <= R:
                    continue
                q = S.tap_clear(t, min(max(x, TP.TAP_MARGIN_UM), w - TP.TAP_MARGIN_UM),
                                min(max(y, TP.TAP_MARGIN_UM), h - TP.TAP_MARGIN_UM), txy, strict=True)
                q = (round(q[0], 4), round(q[1], 4))
                assert l1((x, y), q) <= R, (tn, kind, x, y, q)
                ck.setdefault("sink_sites_um", []).append([round(x, 4), round(y, 4), 1])
                ck["taps"].append(dict(name=f"clk_t{len(txy)}", xy=list(q)))
                txy.append(q)
                ent.append(q)
                added += 1
                rep[tn]["light"].append(dict(iter=it, site=kind, xy=[round(x, 4), round(y, 4)], tap=list(q)))
        print("relay-tap pass", it, "added", added, flush=True)
        if not added:
            break
    else:
        raise SystemExit("relay taps did not converge")
    _P = S.Plan(raw)
    for tn in types:
        t = raw["partition_types"][tn]
        fin = TP.explicit_taps(_P, tn)
        roots = clock_pins(_P, tn)
        moved = []
        for p in t["clock"].get("landing_contract", {}).get("pins", []):
            if p.get("kind") == "clock" and p.get("dir") == "out" and "source_clock_port" in p:
                tap = min(roots, key=lambda r: abs(r[1] - p["xy_um"][0]) + abs(r[2] - p["xy_um"][1]))[0]
                if tap != p["source_clock_port"]:
                    moved.append(f"{p['name']}:{p['source_clock_port']}->{tap}")
                p["source_clock_port"] = tap
        rep[tn].update(taps=len(fin), tap_load_max=max(q[3] for q in fin), tap_radius_max=max(q[4] for q in fin),
                       source_retap=moved)
        print("taps", tn, len(fin), "load", rep[tn]["tap_load_max"], "radius", rep[tn]["tap_radius_max"], flush=True)
    # nothing but the clock tap data changed
    for tn in raw["partition_types"]:
        if tn not in types:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    CK = set(CLOCK) | {"control_sinks", "taps", "sink_sites_um"}
    for tn in types:
        a, b = copy.deepcopy(raw["partition_types"][tn]), copy.deepcopy(orig["partition_types"][tn])
        assert [p for p in a["clock"].get("taps", []) if p.get("kind") == "core"] == \
            [p for p in b["clock"].get("taps", []) if p.get("kind") == "core"], tn
        for x in (a, b):
            for k in CK:
                x["clock"].pop(k, None)
            for p in x["clock"].get("landing_contract", {}).get("pins", []):
                p.pop("source_clock_port", None)
        assert a == b, tn
    text = open(src).read()
    for tn in types:
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == raw
    open(dst, "w").write(text)
    summ = dict(types=len(types), taps_total=sum(rep[tn]["taps"] for tn in types),
                light_taps=sum(len(rep[tn]["light"]) for tn in types),
                tap_load_max=max(rep[tn]["tap_load_max"] for tn in types),
                tap_radius_max=max(rep[tn]["tap_radius_max"] for tn in types))
    rep["_summary"] = summ
    json.dump(rep, open(rp, "w"), indent=1)
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
