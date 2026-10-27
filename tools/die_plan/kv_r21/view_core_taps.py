#!/usr/bin/env python3
"""CLOCK-KV-R21 (b): plan core taps for hard cores from the core's OWN signed real view (RULING CLOCK-KV-R20 (b)).

The R18 method (kv_r18/slice_core_taps.py: one plan clock.taps[] leaf, kind 'core', on the core's native die-clock pin)
could not tap the head eighths: their pin views carry 6 per-tile '__clk' face pins and no slice entry.  For a module
with a signed view (--core-view MODULE=VIEWDIR, the same dirs the shared die_sta_related gate reads) the native pin is
NOT guessed: it is the single 'clock : true' pin of the view's own ETM (VIEWDIR/<MODULE>_tt.lib; die_sta_related.parse_etm
already refuses a view whose boundary arcs relate to any other clock).  A tap is placed only when the instance's plan
pin view IS the signed view:
  every pin common to the view LEF and the plan pins_file has the same layer and centre (0 geometry diffs), the only
  LEF-only pins are PG (VDD/VSS) and the only plan-only pins are ID straps (strap_*: tied at the parent, OWNER 10-25);
any other instance of the module (e.g. a re-pinned orientation variant such as kv3_head_eighth_e5_pins_fMX.json, data
pins mirrored) is listed untapped with the geometry diff count -- it is a different physical core without a signed view.
The tap is NOT early (clock.core_taps unchanged, insertion_ps = the plan common latency, die_clock.plan_taps unchanged ->
no die clock routing change): R19 found every hold negative has a declared-budget endpoint and both-real >= 0, so the
v5.0 early tap is not needed; the view's measured clock tree path is recorded in the note for a later early-tap decision.
usage: view_core_taps.py PLAN.json OUT_PLAN.json OUT_REPORT.json --core-view MODULE=DIR [...]"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import die_sta_related as R

PG = {"VDD", "VSS"}


def lef_pins(path):
    """{pin: (layer, cx, cy)} first RECT of each PIN (core frame, um)."""
    out, cur, lay = {}, None, None
    for ln in Path(path).read_text().splitlines():
        m = re.match(r"\s*PIN (\S+)", ln)
        if m:
            cur = m.group(1)
            continue
        if cur and re.match(r"\s*END " + re.escape(cur) + r"\s*$", ln):
            cur = None
            continue
        m = re.match(r"\s*LAYER (\S+)", ln)
        if m:
            lay = m.group(1)
        m = re.match(r"\s*RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", ln)
        if m and cur and cur not in out:
            a = [float(v) for v in m.groups()]
            out[cur] = (lay, round((a[0] + a[2]) / 2, 3), round((a[1] + a[3]) / 2, 3))
    return out


def plan_pins(path):
    d = json.loads(Path(path).read_text())
    p = d.get("pins", []) if isinstance(d, dict) else d
    out = {}
    for x in p:
        xy = x.get("xy") or [x.get("x"), x.get("y")]
        out[x["name"]] = (x.get("layer"), round(float(xy[0]), 3), round(float(xy[1]), 3))
    return out


def view_match(lef, pp):
    """(ok, detail): plan pin view == signed view geometry (PG only in LEF, strap_* only in the plan)."""
    common = set(lef) & set(pp)
    diff = sorted(n for n in common if lef[n] != pp[n])
    only_lef = sorted(set(lef) - set(pp) - PG)
    only_plan = sorted(n for n in set(pp) - set(lef) if not n.startswith("strap_"))
    ok = not diff and not only_lef and not only_plan
    return ok, dict(common=len(common), geom_diff=len(diff), geom_diff_eg=diff[:3], only_lef=only_lef[:5],
                    only_plan=only_plan[:5], plan_straps=sorted(n for n in set(pp) - set(lef) if n.startswith("strap_")))


def place(h, xy):
    w, hh = h["outline_um"]
    ox, oy = h["origin_um"]
    tx, ty = (h.get("track_offset_um") or [0.0, 0.0])
    x, y = {"R0": (xy[0], xy[1]), "MX": (xy[0], hh - xy[1]), "MY": (w - xy[0], xy[1]),
            "R180": (w - xy[0], hh - xy[1])}[h.get("orient", "R0")]
    return [round(ox + tx + x, 4), round(oy + ty + y, 4)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("out_plan"); ap.add_argument("out_report")
    ap.add_argument("--core-view", action="append", default=[], help="MODULE=VIEWDIR (signed view)")
    a = ap.parse_args(argv)
    src = Path(a.plan)
    raw = src.read_bytes()
    P = json.loads(raw)
    common = float(P["clock"]["insertion_ps"])
    views = {}
    for kv in a.core_view:
        m, d = kv.split("=", 1)
        vd = Path(d)
        prov = json.loads((vd / "provenance.json").read_text()) if (vd / "provenance.json").exists() else {}
        if "SIGNED" not in str(prov.get("verdict", "")):
            raise SystemExit(f"{m}: view {vd} is not signed off ({prov.get('verdict')})")
        etm = {c: R.parse_etm(vd / f"{m}_{c.lower()}.lib", 6.0) for c in ("TT", "FF")}
        views[m] = dict(dir=str(vd), lef=lef_pins(vd / f"{m}.lef"), clock_pin=etm["TT"]["clock_pin"],
                        ctp={c: etm[c]["clock_tree_path_ps"] for c in etm}, verdict=prov.get("verdict"),
                        lib_sha256={c: hashlib.sha256((vd / f"{m}_{c.lower()}.lib").read_bytes()).hexdigest()
                                    for c in ("tt", "ff")})
        if etm["FF"]["clock_pin"] != views[m]["clock_pin"]:
            raise SystemExit(f"{m}: TT/FF ETM clock pins differ")
    cnt = {}
    for p in P["partitions"]:
        cnt[p["type"]] = cnt.get(p["type"], 0) + 1
    rep = dict(lane="CLOCK-KV-R21", plan=str(src), plan_sha256=hashlib.sha256(raw).hexdigest(), rule=__doc__,
               views={m: {k: v for k, v in d.items() if k != "lef"} for m, d in views.items()},
               tapped=[], untapped=[], types={})
    pcache = {}
    for tn, t in P["partition_types"].items():
        new = []
        for h in t.get("hard_cores") or []:
            m = h.get("module")
            if m not in views:
                continue
            V = views[m]
            row = dict(type=tn, inst=h["inst"], module=m, pins_file=h.get("pins_file"), orient=h.get("orient", "R0"),
                       die_instances=cnt.get(tn, 0))
            ck = t.setdefault("clock", {})
            if any(tp.get("kind") == "core" and tp["name"].startswith(h["inst"] + ".") for tp in ck.get("taps", []) or []):
                raise SystemExit(f"{tn}.{h['inst']}: already has a core tap (refusing to overwrite)")
            if not h.get("pins_file"):
                rep["untapped"].append(dict(row, reason="no pins_file")); continue
            pf = src.parent / h["pins_file"]
            if pf not in pcache:
                pcache[pf] = plan_pins(pf)
            ok, det = view_match(V["lef"], pcache[pf])
            row["view_match"] = det
            if not ok:
                rep["untapped"].append(dict(row, reason=f"plan pin view is not the signed view ({det['geom_diff']} "
                                                        f"geometry diffs): different physical core, no signed view"))
                continue
            pin = V["clock_pin"]
            if pin not in pcache[pf]:
                rep["untapped"].append(dict(row, reason=f"ETM clock pin {pin} not in plan pins")); continue
            xy = place(h, pcache[pf][pin][1:])
            c = V["ctp"]
            new.append(dict(name=f"{h['inst']}.{pin}", kind="core", xy=xy, insertion_ps=common, budget_owner=m,
                            note=(f"CLOCK-KV-R21: tap on the signed view's ETM clock pin {pin} (view {V['verdict']}); "
                                  f"pin view == signed LEF; not early: measured clock tree path TT "
                                  f"{c['TT']['min_clock_tree_path']:.2f}-{c['TT']['max_clock_tree_path']:.2f} / FF "
                                  f"{c['FF']['min_clock_tree_path']:.2f}-{c['FF']['max_clock_tree_path']:.2f} ps")))
            rep["tapped"].append(dict(row, pin=pin, xy=xy))
        if new:
            ck = t.setdefault("clock", {})
            ck["taps"] = list(ck.get("taps", []) or []) + new
            rep["types"][tn] = dict(taps=len(new), instances=cnt.get(tn, 0))
    out = json.dumps(P, indent=1)
    Path(a.out_plan).write_text(out)
    rep["out_plan_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    di = lambda rows: sum(r["die_instances"] for r in rows)
    rep["summary"] = dict(rows_tapped=len(rep["tapped"]), rows_untapped=len(rep["untapped"]),
                          die_instances_tapped=di(rep["tapped"]), die_instances_untapped=di(rep["untapped"]),
                          by_module={m: dict(tapped=di([r for r in rep["tapped"] if r["module"] == m]),
                                             untapped=di([r for r in rep["untapped"] if r["module"] == m]))
                                     for m in views})
    Path(a.out_report).write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep["summary"]), rep["out_plan_sha256"][:8])


if __name__ == "__main__":
    sys.exit(main())
