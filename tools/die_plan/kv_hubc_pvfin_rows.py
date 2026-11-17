#!/usr/bin/env python3
"""KV-HUBC-SPLIT: pvfin pair rows for kv3_hub_C.  Replaces the soft pvfin content (qkd_pv_fin_s, ~266k cells) by two
signed hard cores qkd_pv_fin_s8_pin (NL 8, IN_STAGE 1 = +1 declared cycle, 207.36 x 194.4 um, signoff_s8pin2b) nested in
the bound pair leaf u_bound.u_pvfin.u_pair.g_sl[0/1].u_sl (the kv101_rst2_form convention, KV-101/PVFIN).

usage: kv_hubc_pvfin_rows.py PLAN OUT_PLAN --type kv3_hub_C --core-pins PINS.json
Placement: both cores abut side by side (lo, hi) on the 8.64 um grid, as close as possible to the ahub hard core (the
rz / reciprocal source), clear of every hard core halo.  NO_SITE is a failure, never a guess."""
import argparse, copy, json, sys

LEAF = "qkd_pv_fin_s8_pin"
PAIR = "qkd_pv_fin_s2x8_pin_i1_rst2"
ROOT = "u_bound.u_pvfin.u_pair"
PROFILE = {"ADD_LAT": 7, "MUL_LAT": 6, "SKEW": 1, "MUT": 0, "NL": 8, "IN_STAGE": 1}


def hit(r, o):
    return r[0] < o[2] and r[2] > o[0] and r[1] < o[3] and r[3] > o[1]


def place(t, size, grid=8.64, margin=8.64, gap=4.32):
    W, H = t["outline_um"]; cw, ch = size
    obs = []
    anchor = None
    for h in t["hard_cores"]:
        x, y = h["origin_um"]; w, hh = h["outline_um"]; hl = h.get("halo_um") or 4.32
        obs.append((x - hl, y - hl, x + w + hl, y + hh + hl))
        if h["inst"] == "ahub":
            anchor = (x + w / 2, y + hh / 2)
    anchor = anchor or (W / 2, H / 2)
    best = None
    for i in range(int(W / grid) + 1):
        for j in range(int(H / grid) + 1):
            ox, oy = i * grid, j * grid
            lo = (ox, oy, ox + cw, oy + ch); hi = (ox + cw + gap, oy, ox + 2 * cw + gap, oy + ch)
            if lo[0] < margin or lo[1] < margin or hi[2] > W - margin or hi[3] > H - margin:
                continue
            d = abs(ox + cw + gap / 2 - anchor[0]) + abs(oy + ch / 2 - anchor[1])
            if best and d >= best[0]:
                continue
            if any(hit(lo, o) or hit(hi, o) for o in obs):
                continue
            best = (d, ox, oy)
    return best


def rows(plan, tn, pins, pins_file="cores/kv_pvfin/qkd_pv_fin_s8_pin_pins.json"):
    p = copy.deepcopy(plan); t = p["partition_types"][tn]
    c = [x for x in t["contents"] if x["inst"] == "pvfin"]
    if len(c) != 1:
        raise ValueError("expected one pvfin content")
    if any(h["inst"] in ("pvfin_lo", "pvfin_hi") for h in t["hard_cores"]):
        raise ValueError("pvfin cores already present")
    size = pins["outline_um"]
    b = place(t, size)
    if b is None:
        raise ValueError("NO_SITE for the pvfin pair")
    _, ox, oy = b
    for k, nm in enumerate(("pvfin_lo", "pvfin_hi")):
        t["hard_cores"].append(dict(
            inst=nm, module=LEAF, origin_um=[round(ox + k * (size[0] + 4.32), 3), round(oy, 3)], outline_um=list(size), orient="R0",
            pins_file=pins_file, physical_inst=f"{ROOT}.g_sl[{k}].u_sl", physical_master=LEAF,
            sub_core_parent="pvfin", sub_core_leaf_pin="rst_n", cells=0,
            note="KV-HUBC-SPLIT: pvfin lane slice %d, hard core %s (signed s8pin2b, IN_STAGE 1 +1 declared cycle); pair %s" % (k, LEAF, PAIR)))
    c[0]["module"] = PAIR
    c[0]["note"] = (c[0].get("note") or "") + " | KV-HUBC-SPLIT: pair of two %s hard cores (profile %s)" % (LEAF, json.dumps(PROFILE))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("--type", default="kv3_hub_C"); ap.add_argument("--core-pins", required=True)
    a = ap.parse_args()
    p = rows(json.load(open(a.plan)), a.type, json.load(open(a.core_pins)))
    json.dump(p, open(a.out, "w"), indent=1)
    print("pvfin pair rows written", [h["origin_um"] for h in p["partition_types"][a.type]["hard_cores"][-2:]])


if __name__ == "__main__":
    sys.exit(main())
