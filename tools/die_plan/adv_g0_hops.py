"""adv_g0_hops.py -- PRECHECK ADV-G0-HOPS (COORD 11-24 00:5x; S81 c8 post-tail: INT/RTHOPS found 98 hop ERRORs on 98 lanes only at G0).

G0 (check.py) runs check_hops(P, R, geo) -- every lane's mandatory-slot-pin / ft-station hop against its reach (lane reach_um or
P.reach) -- as part of a long full G0; this advisory runs ONLY that function on the plan (lane_geometry + check_hops, ~30 s on S81 c8,
973 lanes) so the 98 land in PRE time, before the tail / bind.  Same messages as G0 ('lane L: hop i via mandatory slot pins is X um > reach
Y' / 'normal FT ... real input bit'), lane count and worst over-reach per type in the summary.  The sibling plan_gate_pre classes RSTREACH
and DERIVEDNAME (derived_drop.py: stale START raw pointers, the 28 reset-reach FAIL types on c8) already run in PRE, not here.
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.  Needs a tree whose tools/die_plan carries check.py.

BIT lines (S81-B1-RTHOPS 11-24, report only): check_hops measures station CENTRES.  A wide ft slot (1104 bits) can pass there
and still have bits whose real hop is over reach: S0 (the bit's in pin) -> its S1 bit site, Sj -> Sj+1 bit sites, last bit site
-> its out pin (die_hop_scan.station_site / pin_table, the same per-bit model ft_reach_fix uses; the seam beyond the out pin is
not added).  On c8 + RTHOPS-98 the centres were all <= 405 while 14 slots had bits up to 484 um.  Bounded by
OT_ADV_G0_HOPS_BIT_S seconds (default 120; 0 = off); a partial scan says so in its summary.
"""
import os
import time
import sys
from pathlib import Path

CHECK = "ADV-G0-HOPS"
MAX_LINES = 20


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def _findings(raw, plan_path, tree=None, **kw):
    d = Path(tree) / "tools" / "die_plan" if tree and (Path(tree) / "tools" / "die_plan" / "check.py").is_file() else Path(__file__).resolve().parent
    sys.path.insert(0, str(d))
    import check as C
    import schema as S
    R = C.Report(False)
    P = S.Plan(raw, Path(plan_path))
    geo = {lid: C.lane_geometry(P, lid) for lid in P.lanes}
    C.check_hops(P, R, geo)
    errs = [i for i in R.items if i.get("check") == "hops"]
    over = {}
    for i in errs:
        m = i["msg"]
        try:
            h = float(m.split(" um > reach ")[0].split()[-1])
            r = float(m.split(" um > reach ")[1].split()[0].rstrip(";,)"))
        except (ValueError, IndexError):
            continue
        over[i.get("lane")] = max(over.get(i.get("lane"), 0.0), h - r)
    out = [_w(i["msg"]) for i in sorted(errs, key=lambda i: -over.get(i.get("lane"), 0.0))[:MAX_LINES]]
    out.append(_w("summary", f"{len(over) or len(errs)} lane(s) with a hop over reach ({len(errs)} ERROR(s); worst +{max(over.values(), default=0.0):.0f} um) "
                             f"of {len(P.lanes)} lanes; same check as G0 hops, fix: add stations / re-seat the crossed ft slot"))
    try:
        bits = bit_lines(P, reach=float(getattr(P, "reach", 405.0) or 405.0))
    except Exception as e:  # noqa: BLE001
        bits = [_w("bit not checked", f"{type(e).__name__}: {str(e)[:120]}")]
    return out[:-1] + bits + out[-1:]   # the lane summary stays the last line


def slot_bit_worst(P, tn, slot, pins):
    """(worst per-bit hop um, bit, hop index) of one ft slot; hop index k-1 = last bit site -> out pin; -1 = in pin -> explicit S0."""
    import die_hop_scan as D
    sn, k = slot["name"], int(slot.get("stations", 1))
    pi, po = pins.get(sn + "_i", {}), pins.get(sn + "_o", {})
    nm = D.normal_slot(P, tn, sn)
    exp0 = bool(nm) and slot.get("explicit_stage0") is True   # unlanded explicit S0: in pin -> S0 is a placed hop
    best = (0.0, None, None)
    for b in set(pi) | set(po):
        a, z = pi.get(b) or po[b], po.get(b) or pi[b]
        st = [D.station_site(slot, j, b, a, z, normal=nm) for j in range(k)]
        if exp0 and b in pi:   # QC-STA-HOP: explicit stage 0 is a placed site, so in pin -> S0 is a real hop (index -1)
            st = [D.input_site(pi[b])] + st
        h = [D.md(x, y) for x, y in zip(st, st[1:])]
        if b in po:
            h.append(D.md(st[-1], D.input_site(po[b])))
        off = -1 if (exp0 and b in pi) else 0
        for i, v in enumerate(h):
            if v > best[0]:
                best = (v, b, i + off)
    return best


def bit_lines(P, reach=405.0):
    budget = float(os.environ.get("OT_ADV_G0_HOPS_BIT_S", "120"))
    if budget <= 0:
        return [_w("bit summary off (OT_ADV_G0_HOPS_BIT_S=0)")]
    import die_hop_scan as D
    t0, rows, done, total, partial = time.time(), [], 0, 0, False
    for tn, t in sorted((getattr(P, "types", None) or {}).items()):
        slots = [s for s in t.get("ft_slots") or [] if int(s.get("stations", 1)) >= 2]
        total += len(slots)
        if partial or not slots:
            continue
        if time.time() - t0 > budget:
            partial = True
            continue
        try:
            pins = D.pin_table(P, tn)
        except Exception:  # noqa: BLE001
            continue
        for s in slots:
            try:
                w, b, i = slot_bit_worst(P, tn, s, pins)
            except Exception:  # noqa: BLE001
                continue
            done += 1
            if w > reach + 1e-6:
                rows.append((w, tn, s["name"], b, i, int(s.get("stations", 1))))
    rows.sort(reverse=True)
    out = [_w("BIT", f"type {tn} slot {sn}: bit {b} hop {i}{' (last -> out pin)' if i == k - 1 else ' (in pin -> S0)' if i == -1 else ''} is {w:.0f} um > reach {reach:.0f}"
              " (station centres may pass; re-shape the bit group along the pin line or add a station)")
           for w, tn, sn, b, i, k in rows[:MAX_LINES]]
    out.append(_w("bit summary", f"{len(rows)} ft slot(s) with a per-bit hop over reach (worst {rows[0][0] if rows else 0:.0f} um) of {done} checked"
                  f" / {total} ft slots; report only{'; PARTIAL: budget %.0f s hit' % budget if partial else ''}"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import json
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
