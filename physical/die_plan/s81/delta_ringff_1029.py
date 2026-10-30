#!/usr/bin/env python3
"""DIE-S81-30/BAND 10-29 fix-only plan event (variant A of the COORD two-variant ruling DIE-S81-30):
slice_station canary PLACE (t8 ring:ft2_i, t43 ring:ft10_i) stops in 3_3 GPL with "OT_CLAND no legal nonoverlapping
row/site in reserved band": the full ring (flops + ~3.4 comb cells per flop) is placed FIRM in the band and needs
1.33-1.57 x the band area at the landing_placement.tcl reserve rule (measured on the mapped canary netlists:
ft2_i 5665 flops / 24685 cells -> 8012 um2 reserved vs 5601 um2 band).  The existing opt-in ring_place="ff"
(DIE-HEAD-13, landing_place.py tag '+ff', landing_placement.tcl cland_place_ff) places only the ring FLOPS FIRM,
bit-major, and leaves the ring logic to global placement: ft2_i flops 4130 um2 reserved vs 0.9 x 5601 = 5041 um2.

This delta sets ring_place="ff" on every ring band (non-monitor, with rect_um) of every slice_station type.  Band
rects, every other plan field and every other type stay byte-identical (text insertion of one line per band; the
result is checked to equal the json-level edit).

A2 (same event, after the A t43 canary 3_5 DPL "Overlap check failed (22)": timing-driven GPL upsized 22 FIRM ring
flops DFFHQNx1 -> x3 in place over TAPCELLs, the KV io_ft DPL-0033 class): it also sets the existing DIE-KV-34 opt-in
budgets.cland_fit_reserve = true (gen_phys exports OT_CLAND_FIT_RESERVE=1; landing_placement.tcl then requires the whole
reserved footprint free, so an in-place upsize cannot reach a tapcell).

usage: delta_ringff_1029.py PLAN_IN PLAN_OUT
"""
import json, re, sys


def targets(plan):
    out = set()
    for tn, t in plan["partition_types"].items():
        if not tn.startswith("slice_station__"):
            continue
        bands = ((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}
        for bus, b in bands.items():
            if not bus.startswith("monitor_") and b.get("rect_um"):
                out.add((tn, bus))
    return out


def apply(text, tg, fit=True):
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
    if fit:
        k = out.index(' "budgets": {')
        out.insert(k + 1, '  "cland_fit_reserve": true,')
    if done != tg:
        raise SystemExit(f"text edit missed {sorted(tg - done)[:5]} ({len(tg - done)})")
    return "\n".join(out), done


def main():
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src).read(); plan = json.loads(text); tg = targets(plan)
    new, done = apply(text, tg)
    want = json.loads(text)
    for tn, bus in tg:
        want["partition_types"][tn]["clock"]["landing_contract"]["bands"][bus]["ring_place"] = "ff"
    want["budgets"]["cland_fit_reserve"] = True
    if json.loads(new) != want:
        raise SystemExit("text edit != json edit")
    open(dst, "w").write(new)
    types = sorted({t for t, _ in done})
    print(f"OT_RINGFF {len(done)} ring bands set ring_place=ff in {len(types)} slice_station types; budgets.cland_fit_reserve=true; json-level check PASS")


if __name__ == "__main__":
    main()
