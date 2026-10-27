#!/usr/bin/env python3
"""INFRA-FIRST-QC-R11 (3): data hold-buffer (HB4xp67) count from the r10 legal hold_demand_fragment.json.

Kit rule (gen_phys.input_hold_min, plan_demand): each type input bus gets set_input_delay -min = sender guarantee
(12.5 ps) - D, ONE value per type port = the minimum over its instances (type hardened once). repair_timing -hold pads
until FF hold meets lib hold (12.28) + hold uncertainty share (0.5 x 25):  pad = D + 12.28 ps (hold_demand.seam_rows).
cells/bit = ceil(pad / (46.90 x 0.95)) (HB4xp67 FF min with flat 0.95 data early derate). Scalars (width 1) keep the
fallback contract (gen_phys) and are counted separately at the fallback pad (40 ps window) for completeness.
Fit: HB4 area vs each partition's non-hard-core area at the plan's est. std-cell fill (note 'fill X at util 0.6').
Usage: r11_hb_count.py PLAN FRAGMENT OUT.json
"""
import json
import math
import re
import sys
from collections import defaultdict

HB4_AREA, HB4_FF, EARLY = 0.1021, 46.90, 0.95
HB4_TT_LATE = 75.20 * 1.05 * 1.0511
LIB_HOLD, UNC_SHARE, GUAR = 12.28, 12.5, 12.5
UTIL = 0.6


def main(plan, frag, out):
    P = json.load(open(plan))
    hd = json.load(open(frag))["clock"]["hold_demand"]
    pairs, dflt = hd["pairs"], hd.get("default_ps")
    parts = {p["name"]: p for p in P["partitions"]}
    T = P["partition_types"]
    d_ff = HB4_FF * EARLY

    def D(s, t):
        k = "|".join(sorted((s, t)))
        return pairs.get(k, dflt), (k in pairs)
    # type-port demand = max D over every instance's senders
    tport = defaultdict(float)
    rows, used_default, scal = [], 0, 0
    for pr in P["ports"]:
        s, t = pr["src"]["part"], pr["dst"]["part"]
        if s == t or s not in parts or t not in parts:
            continue
        w = int(pr.get("width", 1))
        if w <= 1:
            scal += 1
            continue
        d, hit = D(s, t)
        used_default += (not hit)
        key = (parts[t]["type"], pr["dst"]["bus"])
        tport[key] = max(tport[key], d)
        rows.append((pr["id"], s, t, key, w, d))
    per_part = defaultdict(lambda: dict(cells=0, bits=0, cells_inst_d=0))
    total = inst_total = bits = 0
    cpb_hist = defaultdict(int)
    for pid, s, t, key, w, d in rows:
        n_t = math.ceil((tport[key] + LIB_HOLD) / d_ff - 1e-9)       # type value (what the kit actually pads)
        n_i = math.ceil((d + LIB_HOLD) / d_ff - 1e-9)                # per-instance lower bound (INFO)
        per_part[t]["cells"] += w * n_t
        per_part[t]["cells_inst_d"] += w * n_i
        per_part[t]["bits"] += w
        total += w * n_t
        inst_total += w * n_i
        bits += w
        cpb_hist[n_t] += w
    fit = []
    for name, v in per_part.items():
        ty = T[parts[name]["type"]]
        ow, oh = ty["outline_um"]
        hc = sum(c["outline_um"][0] * c["outline_um"][1] for c in ty.get("hard_cores", []))
        free = ow * oh - hc
        m = re.search(r"fill ([0-9.]+) at util", ty.get("note", ""))
        fill = float(m.group(1)) if m else None
        a = v["cells"] * HB4_AREA
        # headroom at util 0.6: std-cell area capacity = free x 0.6; est. used = fill x capacity (plan note)
        head = free * UTIL * (1 - fill) if fill is not None else None
        fit.append(dict(part=name, type=parts[name]["type"], bits_in=v["bits"], hb4=v["cells"], hb4_area_um2=round(a, 1),
                        free_um2=round(free, 1), hb4_frac_of_free=round(a / free, 5) if free > 0 else None,
                        est_fill=fill, headroom_um2=(round(head, 1) if head is not None else None),
                        hb4_frac_of_headroom=(round(a / head, 4) if head else None),
                        cells_before=ty.get("cells"), cells_after=(ty.get("cells") or 0) + v["cells"]))
    fit.sort(key=lambda r: -(r["hb4_frac_of_headroom"] or r["hb4_frac_of_free"] or 0))
    die_area = P["die"]["outline_um"][0] * P["die"]["outline_um"][1]
    worst_cpb = max(cpb_hist)
    rec = dict(
        schema="opentallas.r11_hb_count.v1", label="UNCHECKED plan estimate (HB4 from the r10 legal demand fragment)",
        plan=plan, fragment=frag, fragment_pairs=len(pairs), default_ps=dflt, ports_on_default=used_default,
        rule=dict(pad_ps="D + 12.28 (lib hold) ; sender guarantee 12.5 cancels uncertainty share 12.5",
                  cell="HB4xp67", d_ff_ps=round(d_ff, 3), area_um2=HB4_AREA, type_port="max D over instances"),
        vector_ports=len(rows), scalar_ports_fallback=scal, bits=bits,
        hb4_cells=total, hb4_area_mm2=round(total * HB4_AREA / 1e6, 6), hb4_area_frac_die=round(total * HB4_AREA / die_area, 6),
        hb4_cells_per_instance_D_info=inst_total, cells_per_bit_hist={str(k): v for k, v in sorted(cpb_hist.items())},
        tt_setup_cost_ps_worst=round(worst_cpb * HB4_TT_LATE, 2),
        demand_ps=[min(pairs.values()), max(pairs.values())],
        partitions=len(fit),
        fit_worst=fit[:12],
        fit_over_headroom=[r["part"] for r in fit if r["hb4_frac_of_headroom"] and r["hb4_frac_of_headroom"] > 1.0],
        fit_no_fill_note=sum(1 for r in fit if r["est_fill"] is None),
        fit_max_frac_of_free=max(r["hb4_frac_of_free"] for r in fit if r["hb4_frac_of_free"] is not None),
        per_partition=fit)
    json.dump(rec, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in rec.items() if k not in ("per_partition", "fit_worst")}, indent=1))
    print(json.dumps(rec["fit_worst"][:5], indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
