#!/usr/bin/env python3
"""WIDE-FLOAT-1 11-12 plan event: wide face-bus station chains that trace a relay path along the type outline get
sites="float" (their stages keep the lane's cycle count but are placed by GPL toward the bus's data consumers).

  wide_chain_float_event.py PLAN_IN PLAN_OUT [--min-bits 256] [--types REGEX] [--all-wide]

A chain is marked when its conn is bus:X, X is at least --min-bits wide (or the entry's own "bits" is), and at least
one planned register site lies on the type outline (within 2 um); --all-wide marks every wide bus chain.  Positions
only in effect: no cycle, port, RTL, outline or core change.  Prints one line per marked chain.

Why: col_* frame buses (1167-1264 b) are padded whole (u_lpad_<bus>, ot_dp_dly W+1 x D) at the sites of a
TYPE-SAFE-2 relay chain aimed at a 1-bit u_bn*.rs capture, so the whole bus was pinned along the outline (col_h9_r2
clce45cab5 real GRT: 87 % of overflow gcells in the bottom 72-um edge row) while its data feeds soft u_lpl_* seams.
"""
import argparse, json, re, sys


def bus_width(t, name):
    for b in t.get("buses") or []:
        if isinstance(b, dict) and b.get("name") == name:
            return int(b.get("width") or 0)
    return 0


def on_outline(t, p, tol=2.0):
    W, H = t["outline_um"]
    return p[0] < tol or p[1] < tol or p[0] > W - tol or p[1] > H - tol


def mark(P, min_bits=256, types=None, all_wide=False):
    out = []
    for tn, t in sorted(P["partition_types"].items()):
        if types and not re.search(types, tn):
            continue
        for s in t.get("internal_stations") or []:
            cn = str(s.get("conn", ""))
            if not cn.startswith("bus:") or s.get("sites") == "float":
                continue
            if s.get("bit_route") or "bit_sites_um" in s or "face_bit_sites_um" in s:
                continue
            w = int(s.get("bits") or bus_width(t, cn[4:].split("|", 1)[0]))
            regs = s.get("regs_um") or []
            if w < min_bits or not regs:
                continue
            if not all_wide and not any(on_outline(t, r) for r in regs):
                continue
            s["sites"] = "float"
            s["note"] = (str(s.get("note", "")) + " | WIDE-FLOAT-1 11-12: %d-b chain, %d planned sites on the outline -> "
                         "sites=float (stages placed by GPL toward the data consumers; cycles unchanged)"
                         % (w, sum(on_outline(t, r) for r in regs))).strip(" |")
            out.append((tn, cn, w, len(regs)))
    # a bus chain is one chain in the kit: float all its entries together
    for tn, t in P["partition_types"].items():
        fl = {s["conn"] for s in t.get("internal_stations") or [] if s.get("sites") == "float"}
        for s in t.get("internal_stations") or []:
            if s.get("conn") in fl and s.get("sites") != "float":
                s["sites"] = "float"
                out.append((tn, s["conn"], 0, len(s.get("regs_um") or [])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in"); ap.add_argument("plan_out")
    ap.add_argument("--min-bits", type=int, default=256)
    ap.add_argument("--types")
    ap.add_argument("--all-wide", action="store_true")
    a = ap.parse_args()
    P = json.load(open(a.plan_in))
    rows = mark(P, a.min_bits, a.types, a.all_wide)
    for tn, cn, w, n in rows:
        print("WIDE-FLOAT", tn, cn, ("%d b" % w) if w else "(same chain)", "%d sites" % n)
    print("WIDE-FLOAT marked %d chain entries in %d types" % (len(rows), len({r[0] for r in rows})))
    json.dump(P, open(a.plan_out, "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
