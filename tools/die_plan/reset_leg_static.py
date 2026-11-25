#!/usr/bin/env python3
"""RESET-LEG-STATIC (S81-OWN-LEAF 11-25, COORD/Fable review 03:35 item 7): the reset-leg plan delta of reset_leg_plan.py
(RESET-RELAY-GEN-1530 forms F/L/R) for a type that has NO placed dump, from plan geometry.

A placed reference dump of a type built from the same RTL (same leaf slice, same lfN instance naming) supplies the
netlist; every cell is re-seated on the TARGET type's plan geometry, so reset_leg_plan.py runs unchanged on it:
  * hard macros            -> the target hard_cores origin (same core name), keeping the dump's row/site snap offset
  * plan-seated cells      -> the target plan relay_sites site (u_rr regions, crr relays, every seated relay flop)
  * lane pad stage flops   -> the target bits-weighted stage centroid of the bus (the kit is_place_alt site)
  * every other std cell   -> the same offset from its nearest reference macro, applied to that macro in the target
                              (mirrored when the core orientation differs), clamped into the core
  * macro reset/clock pins -> moved with their macro; die/core boxes from the target outline
The output is a geom.tsv in the AUTO-GEOM format.  Its result is only as good as the transplant: check it on types that
have a real dump, and run a place-only kit where the check fails.

CHECK 11-25 (c9s plan, leaf lf4 t25__cl55642d17 <-> t36, both placed c8s 3_place dumps): self-transplant reproduces the
real result (t36: 78 clone->sink legs, max 779 um, 7 > 405 um, same as the real dump).  Cross-transplant does NOT:
t36 from t25 gives 54 legs > 405 um on the real t36 placement (real-dump delta: 7), t25 from t36 gives 42 (real: 2).
The soft reset sinks (cst status flops, u_rr consumer flops) do not keep their macro-relative offsets between leaf
floorplans, so this static form cannot decide LPAD-RR for a leaf type; S81 leaf types take place-only kits instead.

    reset_leg_static.py PLAN REF_TYPE REF_GEOM TARGET_TYPE OUT_GEOM
"""
import json
import re
import sys


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", s)


def core_name(inst):
    return norm(re.sub(r"^u_lf\.", "", inst))


def dump_core(name):
    m = re.search(r"u_lf\d*_(.*)$", name)
    return norm(m.group(1) if m else name)


def site_key(nm):
    return re.sub(r"^u_bound[./]", "", re.sub(r"\$_[A-Za-z0-9_]*$", "", nm.replace("\\", "")))


def stage_sites(t, bus):
    """[xy] per packed lane pad stage of `bus`: bits-weighted centroid of the deepest station rows (kit_istations merge)"""
    es = [e for e in t.get("internal_stations", []) if e.get("conn") == "bus:" + bus]
    if not es:
        return []
    n = max(len(e["regs_um"]) for e in es)
    deep = [e for e in es if len(e["regs_um"]) == n]
    w = sum(int(e.get("bits", 1)) for e in deep)
    return [[sum(e["regs_um"][j][k] * int(e.get("bits", 1)) for e in deep) / w for k in (0, 1)] for j in range(n)]


FLIPX = {"R0": 0, "MX": 0, "MY": 1, "R180": 1}
FLIPY = {"R0": 0, "MX": 1, "MY": 0, "R180": 1}
LPAD = re.compile(r"^u_lpad_(\w+?)[./](?:r\[(\d+)\]|q)\[")


def transplant(plan, ref_tn, ref_geom, tn, out):
    pt = plan["partition_types"]
    R, T = pt[ref_tn], pt[tn]
    rc = {core_name(h["inst"]): h for h in R.get("hard_cores", [])}
    tc = {core_name(h["inst"]): h for h in T.get("hard_cores", [])}
    W, H = T["outline_um"]
    lines = open(ref_geom).read().split("\n")
    masters = {l.split("\t")[1] for l in lines if l.startswith("O\t")}
    # pass 1: reference macros (dump bbox) and their target placement
    mac, mac_by_id = [], {}
    for l in lines:
        f = l.split("\t")
        if f[0] == "C" and f[3] in masters:
            n = dump_core(f[8])
            if n not in rc or n not in tc:
                raise SystemExit(f"RESET-LEG-STATIC {tn}: core {f[8]} not in both plans (ref {ref_tn}): floorplans differ")
            x0, y0, x1, y1 = map(float, f[4:8])
            r, t = rc[n], tc[n]
            fx = FLIPX.get(r.get("orient", "R0"), 0) ^ FLIPX.get(t.get("orient", "R0"), 0)
            fy = FLIPY.get(r.get("orient", "R0"), 0) ^ FLIPY.get(t.get("orient", "R0"), 0)
            tx0 = t["origin_um"][0] + (x0 - r["origin_um"][0]); ty0 = t["origin_um"][1] + (y0 - r["origin_um"][1])
            m = dict(id=f[1], box=(x0, y0, x1, y1), tbox=(tx0, ty0, tx0 + x1 - x0, ty0 + y1 - y0), fx=fx, fy=fy)
            mac.append(m); mac_by_id[f[1]] = m
    if len(mac) != len(tc):
        raise SystemExit(f"RESET-LEG-STATIC {tn}: {len(mac)} dump macros vs {len(tc)} target hard cores")

    def mapm(m, x, y):
        x0, y0, x1, y1 = m["box"]; tx0, ty0, tx1, ty1 = m["tbox"]
        dx = (x1 - x) if m["fx"] else (x - x0)
        dy = (y1 - y) if m["fy"] else (y - y0)
        return tx0 + dx, ty0 + dy

    def near(x, y):
        def d(m):
            x0, y0, x1, y1 = m["box"]
            return max(x0 - x, 0, x - x1) + max(y0 - y, 0, y - y1)
        return min(mac, key=d)

    seats = T.get("relay_sites", {})
    rseats = R.get("relay_sites", {})
    anchors = [(tuple(rseats[k]), tuple(seats[k])) for k in rseats if k in seats]
    pads = {b["name"]: stage_sites(T, b["name"]) for b in T.get("buses", [])}
    rpads = {b["name"]: stage_sites(R, b["name"]) for b in R.get("buses", [])}
    stats = dict(seated=0, pad=0, macro_rel=0, macros=len(mac))
    out_l = []
    cx0, cy0, cx1, cy1 = 4.32, 4.32, W - 4.32, H - 4.32
    for l in lines:
        f = l.split("\t")
        if f[0] == "D":
            f[1:5] = ["0.0000", "0.0000", f"{W:.4f}", f"{H:.4f}"]
        elif f[0] == "R":
            f[1:5] = [f"{cx0:.4f}", f"{cy0:.4f}", f"{cx1:.4f}", f"{cy1:.4f}"]
        elif f[0] == "C":
            x0, y0, x1, y1 = map(float, f[4:8]); w, h = x1 - x0, y1 - y0
            if f[1] in mac_by_id:
                nx0, ny0 = mac_by_id[f[1]]["tbox"][:2]
            else:
                k = site_key(f[8]); m = LPAD.match(k)
                if k in seats:
                    cx, cy = seats[k]; stats["seated"] += 1
                elif m and pads.get(m.group(1)):
                    st = pads[m.group(1)]; j = int(m.group(2)) if m.group(2) is not None else len(st) - 1
                    cx, cy = st[min(j, len(st) - 1)]; stats["pad"] += 1
                else:
                    px, py = (x0 + x1) / 2, (y0 + y1) / 2
                    m = near(px, py); bx0, by0, bx1, by1 = m["box"]
                    dm = max(bx0 - px, 0, px - bx1) + max(by0 - py, 0, py - by1)
                    a = min(anchors, key=lambda a: abs(a[0][0] - px) + abs(a[0][1] - py)) if anchors else None
                    da = abs(a[0][0] - px) + abs(a[0][1] - py) if a else 1e9
                    if da < dm:          # a plan-seated relay is the nearer known landmark: keep the offset from it
                        cx, cy = a[1][0] + px - a[0][0], a[1][1] + py - a[0][1]; stats["seat_rel"] = stats.get("seat_rel", 0) + 1
                    else:
                        cx, cy = mapm(m, px, py); stats["macro_rel"] += 1
                cx = min(max(cx, cx0 + w / 2), cx1 - w / 2); cy = min(max(cy, cy0 + h / 2), cy1 - h / 2)
                nx0, ny0 = cx - w / 2, cy - h / 2
            f[4:8] = [f"{nx0:.4f}", f"{ny0:.4f}", f"{nx0 + w:.4f}", f"{ny0 + h:.4f}"]
        elif f[0] in ("MR", "MC") and f[1] in mac_by_id:
            x, y = mapm(mac_by_id[f[1]], float(f[2]), float(f[3]))
            f[2:4] = [f"{x:.4f}", f"{y:.4f}"]
        out_l.append("\t".join(f))
    open(out, "w").write("\n".join(out_l))
    return stats


if __name__ == "__main__":
    if len(sys.argv) != 6:
        raise SystemExit(__doc__)
    P = json.load(open(sys.argv[1]))
    print("RESET-LEG-STATIC", sys.argv[4], json.dumps(transplant(P, sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])))
