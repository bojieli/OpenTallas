#!/usr/bin/env python3
"""R-CAP (RULES-CAP-1, RULEBOOK 11-13): movable-cell budget per OpenROAD run, estimated BEFORE launch.

What the 400k "cell cap" measures (376 harvested kit runs, 11-03..11-13, tools/die_plan/testdata/cap_runs_1113.json):
it is not memory (peak RSS <= 43 GB for every run up to 4 mm2; RSS follows OUTLINE AREA, 110 GB at 10 mm2) and not
global placement (<= 3.4 h at 1.4 M cells).  It is the serial timing repair after placement: CTS takes 3-5 h above
550k movable cells and every such run failed the FF hold gate; GRT repair + detail route take 9-10 h at 290-380k and
none of those signed off; of 58 runs above 400k movable cells after place resize, none finished global route.  So the
cap is judged on MOVABLE cells (everything except TAPCELL/ENDCAP/FILLER/DECAP and macros) at the stage they exist:

  stage                     budget (movable std cells)
  synth (pre-floorplan)     280,000   design target only (median growth to resize is x1.41)
  place (after 3_4 resize)  400,000   HARD: projected here, measured by cell_census.tcl
  cts                       420,000   (+2.1 % median)
  grt (after repair)        460,000   (+5.8 % median)
  new types / split parts   250,000   after resize (sizing target; largest sign-off in the harvest is 134k)

Fixed cells do not count against the cap.  tap/endcap = free core area / (0.27 um row x 50 um staggered pitch)
+ 2 endcaps per row = 74k per mm2 (measured/model 0.994 on 90 macro-free types); they cost memory only.

Projection of the post-resize movable count from what a plan / kit knows before synthesis finishes:
  place = synth + pins + K_PIN * pins * hp/100 + K_MAC * macros * hp/100        hp = (W + H) / 2 in um
  (one port buffer per signal pin, measured 1.00; one repeater per ~250 um of half perimeter per pin; ~59 buffers per
  100 um of half perimeter per macro / hard core).  Hold-out error on 109 runs over 100k cells: median 10.1 %,
  p90 27.9 % of the measured count (BAND 25 %).  Verdicts:
    OVER    place > 400k                -> FAIL before launch, with the split
    NEAR    place * (1 + BAND) > 400k   -> launch, the place census trips the run if it measures > 400k
    TARGET  place > 250k                -> allowed for existing types; a new type or a split part must be below
    OK

    python3 tools/die_plan/cap_estimate.py --kit KIT [--synth N]         # one kit (budget.json + receipts)
    python3 tools/die_plan/cap_estimate.py --plan die_plan.json          # every type of a plan (cells.py estimates)
    python3 tools/die_plan/cap_estimate.py --validate RUNS.json          # predicted vs measured on harvested runs
"""
import argparse
import json
import math
import sys
from pathlib import Path

BUDGET = dict(synth=280_000, place=400_000, cts=420_000, grt=460_000)
TARGET = 250_000
BAND = 0.25
K_PIN = 0.395          # repeaters per signal pin per 100 um of half perimeter
K_MAC = 58.8           # buffers per macro / hard core per 100 um of half perimeter
CTS_GROWTH = 1.021
GRT_GROWTH = 1.058
ROW_UM = 0.27
TAP_PITCH_UM = 50.0    # ORFS asap7 tapcell -distance 25, alternate rows staggered
CORE_MARGIN_UM = 4.32
SPLIT_OVERHEAD = 1.03  # boundary registers + their buffers per part
AREA_WARN_MM2 = 6.5    # 6.1 mm2 passed GRT at 42 GB; 10.2 mm2 died at 110 GB
CORE_UTIL = (0.30, 0.50)   # hard core, movable area / free area after resize (signed cores: 0.24-0.50)


def tap_endcap(outline_um, blocked_um2=0.0):
    w, h = outline_um
    cw, ch = max(0.0, w - 2 * CORE_MARGIN_UM), max(0.0, h - 2 * CORE_MARGIN_UM)
    return int(round(max(0.0, cw * ch - blocked_um2) / (ROW_UM * TAP_PITCH_UM) + 2 * ch / ROW_UM))


def mem_gb(outline_um, instances):
    """ot-run --mem request: measured fit 4.4 + 3.4/mm2 + 0.034/k instances (100 runs), x1.5, at least 32."""
    a = outline_um[0] * outline_um[1] / 1e6
    return int(max(32, math.ceil(1.5 * (4.4 + 3.4 * a + 0.034 * instances / 1e3))))


def split_parts(place):
    n = 2
    while place * SPLIT_OVERHEAD / n > TARGET:
        n += 1
    return n


def project(synth, pins, outline_um, macros=0, blocked_um2=0.0):
    """Stage projection for one run.  synth = movable std cells of the synthesized top (or its estimate)."""
    w, h = outline_um
    hp = (w + h) / 200.0
    port = int(pins)
    wire = int(round(K_PIN * pins * hp + K_MAC * macros * hp))
    place = int(synth) + port + wire
    cts = int(round(place * CTS_GROWTH))
    grt = int(round(cts * GRT_GROWTH))
    fixed = tap_endcap(outline_um, blocked_um2)
    free = max(1.0, (w - 2 * CORE_MARGIN_UM) * (h - 2 * CORE_MARGIN_UM) - blocked_um2)
    if synth > BUDGET["place"] or place > BUDGET["place"]:
        verdict = "OVER"
    elif place * (1 + BAND) > BUDGET["place"]:
        verdict = "NEAR"
    elif place > TARGET:
        verdict = "TARGET"
    else:
        verdict = "OK"
    out = dict(schema="opentallas.cap_estimate.v1", rule="R-CAP", synth=int(synth), pins=int(pins), macros=int(macros),
               outline_um=[w, h], port_buffers=port, wire_buffers=wire, place=place, cts=cts, grt=grt,
               tap_endcap=fixed, instances_place=place + fixed, band=BAND, budget=dict(BUDGET, target=TARGET),
               util_place=round(place * 0.129 / free, 4), area_mm2=round(w * h / 1e6, 3),
               mem_gb=mem_gb(outline_um, grt + fixed), verdict=verdict)
    if verdict == "OVER":
        n = split_parts(place)
        out["split_parts"] = n
        out["split"] = (f"split into {n} parts of <= {TARGET} movable cells after resize (about "
                        f"{int(place * SPLIT_OVERHEAD / n)} each): cut at lane-group boundaries, each cut bus registered "
                        "at the boundary (a station on the cut links, +1 cycle on the cut lanes); logic with no lane "
                        f"groups is hardened into cores of <= {TARGET} cells at {CORE_UTIL[0]:.2f}-{CORE_UTIL[1]:.2f} "
                        "utilization so that only glue stays movable in the parent")
    return out


def message(name, e):
    s = (f"{name}: R-CAP {e['verdict']} projected movable cells after resize {e['place']} (synth {e['synth']} + "
         f"{e['port_buffers']} port buffers + {e['wire_buffers']} wire buffers; +-{int(BAND * 100)} %) against "
         f"{BUDGET['place']}; cts {e['cts']}, grt {e['grt']}; fixed tap/endcap {e['tap_endcap']} not counted; "
         f"mem {e['mem_gb']} GB")
    if e["verdict"] == "OVER":
        s += "; " + e["split"]
    elif e["verdict"] == "NEAR":
        s += f"; inside the error band: the place census stops the run above {BUDGET['place']}"
    if e["area_mm2"] > AREA_WARN_MM2:
        s += f"; outline {e['area_mm2']} mm2 > {AREA_WARN_MM2} mm2 (GRT memory, 110 GB measured at 10.2 mm2)"
    return s


# ---- kit (preflight) -------------------------------------------------------------------------------------------
# Measured std-cell counts of the kit's synthesized top (macro / hard-core instances are physical blocks, never
# cells), best first: the pre-floorplan receipt native_cell_cap.tcl writes, its projection receipt, and the ORFS synth
# metrics of a run inside the kit.  A measured count always beats a plan estimate (KV-RCAP-MEAS 11-13: kv3_pc_v1
# measured 227,619 std cells + 12 macros at synth; the plan's flat cells.py row, 850,612, counts the qkd_kvs_pcc/pcf
# hard cores' contents).
MEASURED = (("native_cell_count.json", "stdcells", "macros"),
            ("cap_projection.json", "synth", "macros"),
            ("run/logs/*/*/*/1_synth.json", "synth__design__instance__count__stdcell",
             "synth__design__instance__count__macros"))


def measured_synth(kit):
    """(stdcells, macros, basis) measured on the kit's synthesized top, or None when the kit has no measurement."""
    kit = Path(kit)
    for pattern, key, mkey in MEASURED:
        for f in sorted(kit.glob(pattern)):
            try:
                doc = json.loads(f.read_text())
                n = int(doc[key])
            except (OSError, ValueError, KeyError, TypeError):
                continue
            try:
                m = int(doc.get(mkey) or 0)
            except (ValueError, TypeError):
                m = 0
            return n, m, f"measured synth ({f.relative_to(kit)} {key})"
    return None


def cored_estimate(type_doc, basis):
    """True when a plan estimate of a type built from hard cores is not the type's own movable logic: only plan
    type.cells is (cells.py "plan"); a flat module / partition / by_type table counts the cores' contents too, and a
    hard core's contents are never movable cells of the parent run."""
    return bool((type_doc or {}).get("hard_cores")) and not str(basis).startswith("plan")


def kit_inputs(kit, synth=None):
    """(synth, basis, pins, outline, macros) of a generated kit, or None when the kit has no budget.json."""
    kit = Path(kit)
    try:
        bud = json.loads((kit / "budget.json").read_text())
        outline, pins = bud["outline_um"], int(bud["pins"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    basis = "given"
    measured = measured_synth(kit)
    if synth is None:
        if measured is not None:
            synth, basis = measured[0], measured[2]
        else:
            try:
                synth, basis = int(json.loads((kit / "cap_budget.json").read_text())["cells"]), \
                    "plan estimate (cap_budget.json)"
            except (OSError, ValueError, KeyError, TypeError):
                pass
    macros = 0
    mk = kit / "macros"
    if mk.is_dir():
        macros = len({p.stem for p in mk.glob("*.lef")})
    if measured is not None:
        macros = max(macros, measured[1])
    try:
        macros = max(macros, int(json.loads((kit / "cap_budget.json").read_text()).get("macros", 0)))
    except (OSError, ValueError, TypeError):
        pass
    return synth, basis, pins, outline, macros


def check_kit(kit, synth=None):
    """kit_preflight check: [] or one error line (OVER only).  No estimate -> no error (the pre-floorplan
    projection in native_cell_cap.tcl judges the synthesized count)."""
    got = kit_inputs(kit, synth)
    if got is None or got[0] is None:
        return [], None
    s, basis, pins, outline, macros = got
    e = project(s, pins, outline, macros)
    e["synth_basis"] = basis
    return ([message(Path(kit).name, e)] if e["verdict"] == "OVER" else []), e


# ---- plan (G0) -------------------------------------------------------------------------------------------------
def plan_pins(P, tn):
    """signal pins of a type: bus bits of its first instance (both ends of an internal lane count once each)."""
    inst = next((n for n, p in P.parts.items() if p["type"] == tn), None)
    if inst is None:
        return 0
    n = 0
    for pr in P.ports.values():
        for side in ("src", "dst"):
            if pr[side]["part"] == inst:
                n += int(pr.get("width", 0))
    return n


def plan_rows(P, est):
    """[(type, projection, basis)] for every type with a cell estimate.  A type built from hard cores whose estimate
    is not its own type.cells (a flat module / partition table counts the cores' cells too: KV kv3_pv 7.0 M flat,
    0.28-0.44 M measured) is not judged from the plan (verdict CORED): its kit preflight and the pre-floorplan
    projection judge the netlist the run really places."""
    rows = []
    for tn, t in P.types.items():
        nc, basis = est.get(tn, (None, None))
        if nc is None or nc <= 0:
            continue
        cores = t.get("hard_cores") or []
        macros = len(cores) + sum(1 for c in t.get("contents") or [] if isinstance(c, dict) and c.get("lef"))
        blocked = sum(c["outline_um"][0] * c["outline_um"][1] for c in cores if c.get("outline_um"))
        e = project(nc, plan_pins(P, tn), t["outline_um"], macros, blocked)
        e["synth_basis"] = basis
        if cored_estimate(t, basis):
            e["verdict"] = "CORED"
        rows.append((tn, e, basis))
    return rows


def check_plan(P, R, est):
    """G0: ERROR cell_budget for an OVER type, WARN for NEAR; returns the summary block."""
    out = dict(over=[], near=[], target=[], cored_unjudged=[], rows={})
    for tn, e, basis in plan_rows(P, est):
        out["rows"][tn] = dict(place=e["place"], synth=e["synth"], verdict=e["verdict"], tap_endcap=e["tap_endcap"],
                               mem_gb=e["mem_gb"], basis=basis)
        if e["verdict"] == "OVER":
            out["over"].append(tn)
            R.err("cell_budget", "type " + message(tn, e) + f" [estimate basis: {basis}]", type=tn)
        elif e["verdict"] == "NEAR":
            out["near"].append(tn)
            R.warn("cell_budget", "type " + message(tn, e) + f" [estimate basis: {basis}]", type=tn)
        elif e["verdict"] == "TARGET":
            out["target"].append(tn)
        elif e["verdict"] == "CORED":
            out["cored_unjudged"].append(tn)
    return out


# ---- validation ------------------------------------------------------------------------------------------------
def validate(runs, min_cells=0):
    """runs: [{die,type,outline,pins,mac,fp,tap,mov,...}] -> rows with predicted and measured post-resize counts."""
    rows = []
    for x in runs:
        if not x.get("mov") or not x.get("outline") or x.get("pins") is None or x["mov"] < min_cells:
            continue
        e = project(x["fp"], x["pins"], x["outline"], x.get("mac", 0))
        rows.append(dict(die=x.get("die"), type=x.get("type"), synth=x["fp"], pred=e["place"], meas=x["mov"],
                         err=round((e["place"] - x["mov"]) / x["mov"], 4), verdict=e["verdict"],
                         meas_over=x["mov"] > BUDGET["place"], tap_pred=e["tap_endcap"] if not x.get("mac") else None,
                         tap=x.get("tap"), last=x.get("last")))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", type=Path)
    ap.add_argument("--synth", type=int, help="synthesized movable std cells (overrides the kit receipts)")
    ap.add_argument("--plan", type=Path)
    ap.add_argument("--evidence", action="append", default=[])
    ap.add_argument("--validate", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    rc, doc = 0, None
    if a.kit:
        errs, e = check_kit(a.kit, a.synth)
        doc = e
        if e is None:
            print(f"CAP_ESTIMATE {a.kit.name}: no budget.json / no cell estimate, not judged")
        else:
            print("CAP_ESTIMATE " + message(a.kit.name, e) + f" [synth basis: {e['synth_basis']}]")
        rc = int(bool(errs))
    elif a.plan:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import cells as CE
        import schema as S
        raw = json.loads(a.plan.read_text())
        P = S.Plan(raw)
        est, _ = CE.estimate(raw, a.plan.parent, a.evidence)
        rows = plan_rows(P, est)
        doc = {tn: e for tn, e, _ in rows}
        for tn, e, basis in sorted(rows, key=lambda r: -r[1]["place"]):
            if e["verdict"] in ("OVER", "NEAR"):
                print("CAP_ESTIMATE " + message(tn, e) + f" [basis: {basis}]")
        n = {v: sum(1 for _, e, _ in rows if e["verdict"] == v) for v in ("OVER", "NEAR", "TARGET", "CORED", "OK")}
        print(f"CAP_ESTIMATE {a.plan}: {len(rows)} of {len(P.types)} types estimated: {n}")
        rc = int(n["OVER"] > 0)
    elif a.validate:
        rows = validate(json.loads(a.validate.read_text()))
        doc = rows
        big = sorted(abs(r["err"]) for r in rows if r["meas"] >= 100_000)
        for r in sorted(rows, key=lambda r: -r["meas"]):
            print(f"{str(r['die'])[:12]:12} {str(r['type'])[:36]:36} synth {r['synth']:8} pred {r['pred']:8} "
                  f"meas {r['meas']:8} err {100 * r['err']:+6.1f} % {r['verdict']:6} meas_over={int(r['meas_over'])}")
        if big:
            print(f"CAP_ESTIMATE validate: {len(rows)} runs; >=100k cells n={len(big)} median |err| "
                  f"{100 * big[len(big) // 2]:.1f} % p90 {100 * big[int(len(big) * 0.9)]:.1f} %")
        miss = [r for r in rows if r["meas_over"] and r["verdict"] not in ("OVER", "NEAR")]
        false = [r for r in rows if r["verdict"] == "OVER" and not r["meas_over"]]
        print(f"CAP_ESTIMATE validate: measured over {sum(r['meas_over'] for r in rows)}, of them predicted OVER "
              f"{sum(1 for r in rows if r['meas_over'] and r['verdict'] == 'OVER')} / NEAR "
              f"{sum(1 for r in rows if r['meas_over'] and r['verdict'] == 'NEAR')} / missed {len(miss)}; "
              f"predicted OVER but measured under: {len(false)}")
    else:
        ap.error("one of --kit, --plan, --validate")
    if a.json and doc is not None:
        a.json.write_text(json.dumps(doc, indent=1) + "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
