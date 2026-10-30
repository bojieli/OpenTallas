#!/usr/bin/env python3
"""DIE-S81-33 10-29 fix-only plan event: every remaining S81 landing ring band -> ring_place="ff" (DIE-HEAD-13 form).

Why (measured): every S81 ring band measured so far overfills under the default full-ring FIRM reserve (band_ring=all,
landing_placement.tcl reserves the ring flops AND its logic, ~2x the flop-only footprint) and fits flop-only:
  slice_station t8/t43 1.33-1.57x -> ff fits (DIE-S81-30, delta_ringff_1029.py, all slice_station bands already ff);
  iqf__t1 3 bands 1.36-1.58x -> 0.68-0.79x (DIE-S81-32/IQF, CHECKED on its synth netlist, already ff);
  the 4 LP types, 15 bands 1.14-1.46x -> ff 0.57-0.74x (S81-KITS-C 21:14 FINDING, CHECKED,
  intel2 s81-kits-c/evidence/lp_ring_vs_band.txt).
19/19 measured bands overfill; the flop-only reserve is always <= the full-ring reserve, so a band that fits today
still fits.  No S81 type kit is placed on the old form (S81 type counts placed 0 / signed off 0 on 10-29), so no
signed-off result changes.  S81-KITS-B ASK 20:31 default: "every S81 type whose landing ring exceeds its band".
--scope lp limits the edit to the 4 measured LP types (the COORD fallback variant).

The delta adds ring_place="ff" to each target band in plan_s13r2.json (die_plan.json carries no landing_contract)
and nothing else: band rects, outlines, pins, every other field stay byte-identical (one inserted line per band,
checked against the json-level edit).  Monitor bands and bands without rect_um are not ring bands and stay.
budgets.cland_fit_reserve must already be true (A2).  A second run finds no targets and refuses.

usage: delta_ringff_all_1029.py PLAN_IN PLAN_OUT [--scope all|lp]
"""
import json, re, sys

LP = {"dsdv_slice_lepw_mus_LP__t2", "dsdv_slice_lepw_mu_LP__t2", "dsdv_slice_lepe_mu_LP__t2",
      "dsdv_slice_lepe_nh_mus_LP__t1"}


def targets(plan, scope):
    out = set()
    for tn, t in plan["partition_types"].items():
        if scope == "lp" and tn not in LP:
            continue
        bands = ((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}
        for bus, b in bands.items():
            if not bus.startswith("monitor_") and b.get("rect_um") and "ring_place" not in b:
                out.add((tn, bus))
    return out


def apply(text, tg):
    lines = text.split("\n"); out = []; ty = None; bands_ind = None; done = set()
    type_re = re.compile(r'^  "([A-Za-z0-9_]+)": \{$')
    for ln in lines:
        m = type_re.match(ln)
        if m:
            ty = m.group(1); bands_ind = None
        out.append(ln)
        s = ln.lstrip(" "); ind = len(ln) - len(s)
        if bands_ind is None:
            if s == '"bands": {':
                bands_ind = ind
            continue
        if ind <= bands_ind:
            bands_ind = None
            continue
        if ind == bands_ind + 1:
            mb = re.match(r'^"([^"]+)": \{$', s)
            if mb and (ty, mb.group(1)) in tg:
                if (ty, mb.group(1)) in done:
                    raise SystemExit(f"duplicate band {ty} {mb.group(1)}")
                out.append(" " * (ind + 1) + '"ring_place": "ff",'); done.add((ty, mb.group(1)))
    if done != tg:
        raise SystemExit(f"text edit missed {sorted(tg - done)[:5]} ({len(tg - done)})")
    return "\n".join(out), done


def main():
    a = sys.argv[1:]
    scope = "all"
    if "--scope" in a:
        k = a.index("--scope"); scope = a[k + 1]; del a[k:k + 2]
    assert scope in ("all", "lp"), scope
    src, dst = a
    text = open(src).read(); plan = json.loads(text)
    if plan["budgets"].get("cland_fit_reserve") is not True:
        raise SystemExit("budgets.cland_fit_reserve is not true (A2 base expected)")
    tg = targets(plan, scope)
    if not tg:
        raise SystemExit("no target bands (already applied?) - second run refused")
    if scope == "lp" and {t for t, _ in tg} != LP:
        raise SystemExit(f"LP type set mismatch {sorted({t for t, _ in tg})}")
    new, done = apply(text, tg)
    want = json.loads(text)
    for tn, bus in tg:
        want["partition_types"][tn]["clock"]["landing_contract"]["bands"][bus]["ring_place"] = "ff"
    if json.loads(new) != want:
        raise SystemExit("text edit != json edit")
    open(dst, "w").write(new)
    types = sorted({t for t, _ in done})
    print(f"OT_RINGFF_S81 scope={scope}: {len(done)} ring bands set ring_place=ff in {len(types)} types "
          f"(LP {sum(1 for t, _ in done if t in LP)} bands); band rects/outlines/pins unchanged; json-level check PASS")


if __name__ == "__main__":
    main()
