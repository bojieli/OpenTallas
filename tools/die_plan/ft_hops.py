#!/usr/bin/env python3
"""Per-bit feedthrough hop table of a die_trial kit: the longest unregistered hop of every ft slot instance, from the
plan's own pins / station sites AND from the die GRT guides (die_trial.py kit + run_grt.sh), against the 405-um M4-M7
signal reach (owner decision 12 / ruling 9.3).  Read-only diagnostic (DIE-PROTO 2026-10-25).

    ft_hops.py PLAN.json KITDIR [--reach 405] [--out hops.json]

Model (as check.py geometry / ft_reach.py): a slot with S stations has S register-to-register legs inside the
partition (S-1 internal stages + the face flop); with explicit bit_sites_um the legs are pin -> site_1 -> .. ->
site_{S-1} -> pin (Manhattan), otherwise the in->out length / S.  'grt' uses the routed guide length of the bit's net
(sum of wire-box spans in the guide, gcell-quantised) / S, i.e. evenly spaced stations on the real route.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_rtl  # noqa: E402
import schema as S  # noqa: E402
from gen_phys import type_pins  # noqa: E402


def guide_lengths(path, dbu=1000.0):
    """{net: routed length um} from an OpenROAD route.guide (wire boxes: long side minus one gcell)."""
    out, net, acc, boxes = {}, None, 0.0, []
    for ln in open(path):
        s = ln.strip()
        if s == "(":
            boxes = []
        elif s == ")":
            if boxes:
                g = min(min(x1 - x0, y1 - y0) for x0, y0, x1, y1 in boxes)
                acc = sum(max(x1 - x0, y1 - y0) - g for x0, y0, x1, y1 in boxes)
                out[net] = acc / dbu
        elif s:
            f = s.split()
            if len(f) == 5:
                boxes.append(tuple(int(v) for v in f[:4]))
            elif len(f) == 1:
                net = s
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("kit")
    ap.add_argument("--reach", type=float, default=S.SIGNAL_REACH_UM if hasattr(S, "SIGNAL_REACH_UM") else 405.0)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    P = S.Plan(S.load(a.plan))
    gl = {}
    gp = Path(a.kit) / "grt" / "route.guide"
    if gp.is_file():
        gl = guide_lengths(gp)
    byinst = defaultdict(dict)
    for k, v in gl.items():
        if "[" in k:
            byinst[k.split("[")[0]][k] = v
    rows = []
    for tn, t in sorted(P.types.items()):
        slots = t.get("ft_slots") or []
        if not slots:
            continue
        pins = {(bus, bit): (x, y) for bus, bit, _, x, y, _ in type_pins(P, tn)}
        insts = [n for n, p in sorted(P.parts.items()) if p["type"] == tn]
        for sl in slots:
            st = int(sl.get("stations", 1))
            sites = sl.get("bit_sites_um")
            worst_plan, worst_bit, nb = 0.0, None, 0
            for bit in range(int(sl["width"]) + 1):
                a_ = pins.get((sl["name"] + "_i", bit))
                b_ = pins.get((sl["name"] + "_o", bit))
                if a_ is None or b_ is None:
                    continue
                nb += 1
                if sites:
                    pts = [a_] + [tuple(stg[bit]) for stg in sites] + [b_]
                    leg = max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))
                else:
                    leg = (abs(a_[0] - b_[0]) + abs(a_[1] - b_[1])) / st
                if leg > worst_plan:
                    worst_plan, worst_bit = leg, bit
            for n in insts:
                w = f"ft_{gen_rtl.sv_id(n)}__{gen_rtl.sv_id(sl['name'])}"
                L = sorted(v / st for k, v in byinst.get(w, {}).items())
                g = L[-1] if L else None
                p90 = L[int(0.9 * (len(L) - 1))] if L else None
                nover = sum(1 for v in L if v > a.reach)
                rows.append(dict(inst=n, type=tn, slot=sl["name"], width=int(sl["width"]), stations=st,
                                 bit_sites=bool(sites), bits=nb, plan_hop_um=round(worst_plan, 1), plan_bit=worst_bit,
                                 grt_hop_um=None if g is None else round(g, 1),
                                 grt_hop_p90_um=None if p90 is None else round(p90, 1), grt_bits_over=nover,
                                 detour_max=None if g is None or not worst_plan or sites else round(g / worst_plan, 2),
                                 over=(worst_plan > a.reach) or (g is not None and g > a.reach)))
    rows.sort(key=lambda r: -max(r["plan_hop_um"], r["grt_hop_um"] or 0))
    over = [r for r in rows if r["over"]]
    res = dict(plan=a.plan, kit=a.kit, reach_um=a.reach, slot_instances=len(rows), over=len(over),
               over_bits_plan=sum(r["bits"] for r in over if r["plan_hop_um"] > a.reach),
               over_bits_grt=sum(r.get("grt_bits_over") or 0 for r in rows),
               grt_bits=sum(len(v) for v in byinst.values()),
               over_types=sorted({(r["type"], r["slot"]) for r in over}), worst=rows[:40],
               over_rows=[dict((k, r[k]) for k in ("inst", "type", "slot", "width", "stations", "plan_hop_um", "grt_hop_um", "grt_hop_p90_um", "grt_bits_over")) for r in over])
    txt = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(txt + "\n")
    print(json.dumps(dict((k, v) for k, v in res.items() if k != "worst"), indent=1))
    for r in rows[:15]:
        print(r)


if __name__ == "__main__":
    main()
