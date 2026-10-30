#!/usr/bin/env python3
"""DIE-S81-32/IQF 10-29 fix-only plan event (COORD ruling 20:5x, S81-KITS-B ASK 20:31): iqf__t1 landing bands -> ring_ff form.

iqf__t1 PLACE cannot pass 3_3 on plan_s13r2: its three landing bands carry the full ring FIRM (band_ring=all,
landing_placement.tcl reserves ceil(w/0.4/site) per ring cell) and need 1.36-1.58 x their band area (CHECKED by
S81-KITS-B on the iqf__t1 mapped netlist: ft1_i 30,520 ring cells 10,126 um2 vs 6,423; idx_i0/ql_i0 11,658 cells 3,866 vs
2,861/2,821).  The existing opt-in ring_place="ff" (DIE-HEAD-13; the same form as the slice_station A2 event
delta_ringff_1029.py) places only the ring FLOPS FIRM bit-major and leaves the ring logic to global placement.
budgets.cland_fit_reserve is already true on plan_s13r2 (A2), so the fit-reserve rule applies unchanged.

The delta adds ring_place="ff" to the three iqf__t1 landing_contract.bands rows (ft1_i, idx_i0, ql_i0) and nothing
else: band rects, outline, pins, neighbours, die datums, every other type and every other field stay byte-identical
(text insertion of one line per band, checked against the json-level edit).  It asserts the exact old band forms and
refuses a second run.

usage: delta_iqf_ringff_1029.py PLAN_IN PLAN_OUT
"""
import json, re, sys

TYPE = "iqf__t1"
# exact old forms on plan_s13r2 (origin/main ac0b29e7fa5): bus -> (rect_um, width, ring_width, area_reserve_um2, instance)
OLD = {
    "ft1_i": ([17.28, 1188.0, 314.66, 1209.6], 1368, 1408, 6275.232, "u_cland_ft1_i"),
    "idx_i0": ([598.272, 1183.68, 708.644, 1209.6], 513, 576, 2636.064, "u_cland_idx_i0"),
    "ql_i0": ([823.68, 1183.68, 932.516, 1209.6], 513, 576, 2636.064, "u_cland_ql_i0"),
}
OLD_KEYS = {"rect_um", "width", "ring_width", "live_data_storage_flops", "padded_data_storage_flops", "clock_roles",
            "max_pin_to_band_hop_um", "area_reserve_um2", "placement", "instance"}


def check_old(plan):
    if plan["budgets"].get("cland_fit_reserve") is not True:
        raise SystemExit("budgets.cland_fit_reserve is not true (A2 base expected)")
    t = plan["partition_types"][TYPE]
    if t["outline_um"] != [1442.88, 1226.88]:
        raise SystemExit(f"{TYPE} outline changed: {t['outline_um']}")
    bands = t["clock"]["landing_contract"]["bands"]
    if sorted(bands) != sorted(OLD):
        raise SystemExit(f"{TYPE} band set {sorted(bands)} != {sorted(OLD)}")
    for bus, (rect, w, rw, res, inst) in OLD.items():
        b = bands[bus]
        if "ring_place" in b:
            raise SystemExit(f"{TYPE}.{bus} already ring_place={b['ring_place']} (second run refused)")
        if set(b) != OLD_KEYS:
            raise SystemExit(f"{TYPE}.{bus} keys {sorted(b)} differ from the old form")
        if (b["rect_um"], b["width"], b["ring_width"], b["area_reserve_um2"], b["instance"]) != (rect, w, rw, res, inst):
            raise SystemExit(f"{TYPE}.{bus} old form mismatch: {b}")


def apply(text):
    lines = text.split("\n"); out = []; ty = None; bands_ind = None; done = set(); in_lc = False
    type_re = re.compile(r'^  "([A-Za-z0-9_]+)": \{$')
    for ln in lines:
        m = type_re.match(ln)
        if m:
            ty = m.group(1); bands_ind = None
        out.append(ln)
        if ty != TYPE:
            continue
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
            if mb and mb.group(1) in OLD:
                if mb.group(1) in done:
                    raise SystemExit(f"duplicate band {TYPE} {mb.group(1)}")
                out.append(" " * (ind + 1) + '"ring_place": "ff",'); done.add(mb.group(1))
    if done != set(OLD):
        raise SystemExit(f"text edit missed {sorted(set(OLD) - done)}")
    return "\n".join(out)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src).read(); plan = json.loads(text)
    check_old(plan)
    new = apply(text)
    want = json.loads(text)
    for bus in OLD:
        want["partition_types"][TYPE]["clock"]["landing_contract"]["bands"][bus]["ring_place"] = "ff"
    if json.loads(new) != want:
        raise SystemExit("text edit != json edit")
    open(dst, "w").write(new)
    print(f"OT_IQF_RINGFF {TYPE}: {len(OLD)} landing bands set ring_place=ff ({', '.join(sorted(OLD))}); band rects, "
          f"outline, pins and all other types unchanged; json-level check PASS")


if __name__ == "__main__":
    main()
