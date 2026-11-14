#!/usr/bin/env python3
"""QC-S28-BIND tap identity check + guarded re-point of forwarded clock sources (DIE-QC-100 11-12).
Derived taps (schema.tap_grid: density / grid+sinks ...) are renumbered from the plan geometry, so a core-zone or
stage move can rename taps: a landing_contract source_clock_port clk_tNN can dangle (EMIT: "not a planned physical tap
input") or, worse, silently name a tap at another place.  Identity is the tap LOCATION in the reference plan.
  For every used soft type with forwarded clock outputs (landing_contract pins kind clock, dir out,
  source_clock_port != clk):
    ref_xy = REF tap_grid[source]; final taps = FINAL tap_grid.
    kept      the same name sits at ref_xy (|d| <= EPS) in FINAL
    re-point  else -> the FINAL tap nearest ref_xy; if none within the type's tap_radius_um (merged away), the FINAL
              tap nearest the pin.  Fail closed (exit 3) if the move ref_xy -> new xy > one tap pitch
              (budgets.tap_pitch_um, 400), or the landing hop pin -> tap crosses HOP (405 um), or a pre-existing > HOP
              hop grows by > GROW (5 um).  Same name at a moved xy: reported, no edit.
  FINAL-first (11-13): a source naming a FINAL tap within HOP of its pin is kept as is (never re-pointed by REF
  identity: a reach rule may already have re-sourced it on the FINAL grid).  Every hop check is on FINAL coordinates.
  A pin whose source differs from its REF source (re-sourced later, e.g. a landing re-source, or a plan that already
  went through this step) was written against the FINAL numbering: it must exist in FINAL (fail closed), never re-pointed.
  Report: per type every tap NAME whose xy differs REF vs FINAL (renumbering), dangling names, re-points; EQ row per
  re-point (0 cycles: same clock family, a different tap of it).
  tap_ident.py REF_PLAN FINAL_PLAN --out PLAN_OUT --report R.json --eq EQ.tsv   (tree root; plans in the plan folder)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "tools/die_plan")
import schema  # noqa: E402

EPS, HOP, GROW = 1e-3, 405.0, 5.0
STRICT = __import__("os").environ.get("TI_STRICT") == "1"


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def fwd(t):
    return [q for q in ((t.get("clock") or {}).get("landing_contract") or {}).get("pins", [])
            if q.get("kind") == "clock" and q.get("dir") == "out" and q.get("source_clock_port") not in (None, "clk")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref")
    ap.add_argument("final")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--eq", required=True)
    a = ap.parse_args()
    R = json.loads(Path(a.ref).read_text())
    F = json.loads(Path(a.final).read_text())
    PR = schema.Plan(json.loads(json.dumps(R)), a.ref)
    PF = schema.Plan(json.loads(json.dumps(F)), a.final)
    pitch = float((F.get("budgets") or {}).get("tap_pitch_um", 400.0))
    used = sorted({p["type"] for p in F["partitions"]})
    rep, eq, fail, longhop = dict(pitch_um=pitch, types={}), [], [], []
    n_types = n_src = 0
    n_resrc = [0]
    for tn in used:
        t = F["partition_types"][tn]
        pins = fwd(t)
        if t.get("hard") or not pins:
            continue
        n_types += 1
        if tn not in R["partition_types"]:
            fail.append(f"{tn}: not in the reference plan")
            continue
        gr = {n: (x, y) for n, x, y in schema.tap_grid(PR, tn)}
        gf = {n: (x, y) for n, x, y in schema.tap_grid(PF, tn)}
        radius = float((t.get("clock") or {}).get("tap_radius_um", 200.0))
        drift = sorted(n for n in gr if n in gf and man(gr[n], gf[n]) > EPS)
        row = dict(ref_taps=len(gr), final_taps=len(gf), renamed_or_moved=drift,
                   gone=sorted(set(gr) - set(gf)), new=sorted(set(gf) - set(gr)), sources=[])
        rsrc = {q["name"]: q.get("source_clock_port", "clk")
                for q in ((R["partition_types"][tn].get("clock") or {}).get("landing_contract") or {}).get("pins", [])
                if q.get("kind") == "clock" and q.get("dir") == "out"}
        for q in pins:
            n_src += 1
            s = q["source_clock_port"]
            pin = q["xy_um"]
            # FINAL-first (DIE-QC-100 11-13, s29 R-REACH-4): a source that names a FINAL tap within HOP of its pin is
            # already a valid landing on the grid it will be built on -> kept as FINAL, never re-pointed by REF identity.
            if s in gf and man(gf[s], pin) <= HOP:
                row["sources"].append(dict(pin=q["name"], source=s, action="kept (final tap within hop)",
                                           hop_um=round(man(gf[s], pin), 1)))
                continue
            if rsrc.get(q["name"]) != s:
                # re-sourced after REF (or a new pin): authored against the FINAL numbering -> must exist, never re-pointed
                if s not in gf:
                    fail.append(f"{tn}.{q['name']}: re-sourced to {s}, which is not a FINAL tap (dangling)")
                    continue
                h1 = man(gf[s], pin)
                r0 = rsrc.get(q["name"])
                h0 = man(gf[r0], pin) if r0 in gf else None          # the hop of its REF source, on FINAL coordinates
                row["sources"].append(dict(pin=q["name"], source=s, action="re-sourced after REF (final numbering), kept",
                                           ref_source=r0, new_xy=gf[s], hop_um=round(h1, 1),
                                           ref_hop_um=None if h0 is None else round(h0, 1)))
                n_resrc[0] += 1
                # hard landing rule: a re-sourced pin must sit <= HOP from its FINAL source tap.  Only a hop that was
                # already > HOP in REF and did not grow (> GROW) is reported instead (pre-existing, owner QC-S28-RESID);
                # TI_STRICT=1 fails those too.
                if h1 > HOP:
                    pre = h0 is not None and h0 > HOP and h1 <= h0 + GROW and not STRICT
                    (longhop if pre else fail).append(
                        f"{tn}.{q['name']}: re-sourced {s} hop {h1:.1f} um > {HOP}"
                        + (f" (pre-existing, REF {r0} {h0:.1f} um)" if pre else
                           f" (REF {r0} {'-' if h0 is None else f'{h0:.1f}'} um)"))
                continue
            if s not in gr:
                fail.append(f"{tn}.{q['name']}: source {s} is not a tap of the REFERENCE plan either")
                continue
            rx = gr[s]
            # every hop below is measured on FINAL coordinates: h0 = the pin's hop to its source as named now (None when
            # that name dangles in FINAL), h1 = the hop after the re-point.  Reaching here, h0 is None or > HOP.
            h0 = man(gf[s], pin) if s in gf else None
            if s in gf and man(gf[s], rx) <= EPS:
                row["sources"].append(dict(pin=q["name"], source=s, action="kept", hop_um=round(h0, 1)))
                pre = not STRICT
                (longhop if pre else fail).append(f"{tn}.{q['name']}: {s} {h0:.1f} um (pre-existing > {HOP}, tap unmoved)")
                continue
            near = min(gf, key=lambda n: (man(gf[n], rx), n))
            how = "nearest ref tap xy"
            if man(gf[near], rx) > radius:
                near = min(gf, key=lambda n: (man(gf[n], pin), n))
                how = "ref tap merged away: nearest the pin"
            mv, h1 = man(gf[near], rx), man(gf[near], pin)
            x = dict(pin=q["name"], source=s, action="re-point", to=near, how=how, ref_xy=rx, new_xy=gf[near],
                     dangling=s not in gf, move_um=round(mv, 2), hop_um=[None if h0 is None else round(h0, 1), round(h1, 1)])
            row["sources"].append(x)
            if mv > pitch:
                fail.append(f"{tn}.{q['name']}: {s} -> {near} moves the source {mv:.1f} um > pitch {pitch}")
            if h1 > HOP:
                # FINAL hop over HOP fails closed, except a pre-existing FINAL long hop of a still-existing source
                # that does not grow (> GROW) (owner QC-S28-RESID; TI_STRICT=1 fails those too)
                pre = h0 is not None and h1 <= h0 + GROW and not STRICT
                (longhop if pre else fail).append(
                    f"{tn}.{q['name']}: {s} -> {near} FINAL hop {'-' if h0 is None else f'{h0:.1f}'} -> {h1:.1f} um > {HOP}"
                    + (" (pre-existing)" if pre else ""))
            if near == s:
                x["action"] = "moved (same name, no edit)"
                continue
            eq.append([tn, f"landing_contract.{q['name']}.source_clock_port", f"{s}@{rx[0]:.3f},{rx[1]:.3f}",
                       f"{near}@{gf[near][0]:.3f},{gf[near][1]:.3f}", "0",
                       f"{'dangling' if s not in gf else 'renumbered'}; {how}; move {mv:.1f} um; hop {'-' if h0 is None else f'{h0:.1f}'}->{h1:.1f} um (FINAL)"])
            q["source_clock_port"] = near
        if drift or row["gone"] or row["new"] or any(not x["action"].startswith("kept") for x in row["sources"]):
            rep["types"][tn] = row
    moved = sum(1 for r in rep["types"].values() for x in r["sources"] if x["action"].startswith("moved"))
    rep.update(types_checked=n_types, sources=n_src, repoints=len(eq), moved_same_name=moved, resourced_after_ref=n_resrc[0], long_hops=longhop, fail=fail)
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    with open(a.eq, "w") as f:
        f.write("type\tkind\tbefore\tafter\treset_release_cycles\tnote\n")
        for e in eq:
            f.write("\t".join(e) + "\n")
    drifted = {tn: len(r["renamed_or_moved"]) for tn, r in rep["types"].items() if r["renamed_or_moved"]}
    print("TAP_IDENT types", n_types, "sources", n_src, "repoints", len(eq), "moved same name", moved, "re-sourced after REF", n_resrc[0],
          "pre-existing long hops", len(longhop), "types with renamed/moved taps",
          len(drifted), drifted, "fail", len(fail))
    if fail:
        for x in fail:
            print("TAP_IDENT FAIL", x)
        sys.exit(3)
    Path(a.out).write_text(json.dumps(F, indent=1) + "\n")


if __name__ == "__main__":
    main()
