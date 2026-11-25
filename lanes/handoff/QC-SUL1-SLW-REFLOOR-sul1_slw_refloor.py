#!/usr/bin/env python3
"""SUL1-SLW-CHAN (QC-SUL1-SLW-REFLOOR 11-25, C1p row on C1o v13 aa3a14fb7484).

Cause (census 07:3x): slw_su_l1 DRT floor ~8.5k, 93% of violations in x475-525 y200-300 on u_ist_x_su_c_i__* banks.
The three x_su_c_i core chains launch from the cl_x_su_c_i W face (x 527.08, y 188-278, 1770 bit wires) with per-bit
L routes (normal_first / along_first) that put every bit of a chain in ONE column (x 497.8 for lane4+5, x 527 for
lane6/lane7), so the 696-bit lane4+5 chain seats 6 x 697 flops in a 30 x 140 um column and the 1074 lane6/7 bits run
up the same column.  Fix (KIT-CHAN-1 form, istation_channel.py, kit-supported): leg_order "channel" with a per-chain
channel_um band across the free street x 440-520; every bit takes its own column, stations at per-bit arc length.
Station count, cycles, start sites and leaves unchanged; regs_um re-centred on the per-bit sites (stage centroids).

    python3 -I sul1_slw_refloor.py PLAN_IN PLAN_OUT REPORT.json --tools <tree>/tools/die_plan
"""
import argparse, hashlib, json, sys

TYPES = ("slw_su_l1__cla2a78701", "slw_su_l1__clcc9d0155")
# Fable review 08:2x: one common band (columns follow the bus bit index and the 3 chains share bits 0-501, so split bands
# only crowd each chain into part of its band); max ~33 wires/um.
BAND = (440.0, 524.0)
BANDS = {("bus:x_su_c_i", "u_lane4+u_lane5"): BAND, ("bus:x_su_c_i", "u_lane6"): BAND, ("bus:x_su_c_i", "u_lane7"): BAND}
# RANK-SEAT (kit_istations rs_rank_line): the cl_x_su_c_i landing pad delay (u_lpad_x_su_c_i r[0..4], q; 767 bits each) and
# the fan-out bin (u_bin_x_su_c_i q) were packed as compact blocks between the q pins (x 527.08) and stage 0: one line each,
# parallel to the face, 4.3 um apart, x 524.4 (first rank, next to the pins) .. 498.5, y 195.6 -> 330.
RANKS = ("u_lpad_x_su_c_i.r[0]", "u_lpad_x_su_c_i.r[1]", "u_lpad_x_su_c_i.r[2]", "u_lpad_x_su_c_i.r[3]",
         "u_lpad_x_su_c_i.r[4]", "u_lpad_x_su_c_i.q", "u_bin_x_su_c_i.q")
RANK_X = (524.4, 520.08, 515.76, 511.44, 507.12, 502.8, 498.48)
RANK_Y = (195.6, 330.0)
NOTE = " | SUL1-SLW-CHAN 11-25 (QC-SUL1-SLW-REFLOOR): leg_order channel %s (was %s; per-bit columns, DRT station pile fix)"


def core_key(e):
    c = e.get("core")
    return "+".join(c) if isinstance(c, list) else str(c)


def old_sites(px, py, lx, ly, order, n):
    if order == "along_first":
        pts = [(px, py), (px, ly), (lx, ly)]
    else:
        pts = [(px, py), (lx, py), (lx, ly)]
    L = sum(abs(a[0] - c[0]) + abs(a[1] - c[1]) for a, c in zip(pts, pts[1:]))
    out = []
    for k in range(n):
        t = L * (k + 1) / (n + 1)
        for a, c in zip(pts, pts[1:]):
            d = abs(a[0] - c[0]) + abs(a[1] - c[1])
            if t <= d:
                f = 0.0 if d == 0 else t / d
                out.append((a[0] + f * (c[0] - a[0]), a[1] + f * (c[1] - a[1]))); break
            t -= d
        else:
            out.append(pts[-1])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in"); ap.add_argument("plan_out"); ap.add_argument("report")
    ap.add_argument("--tools", required=True)
    a = ap.parse_args()
    sys.path.insert(0, a.tools)
    import istation_channel as IC
    base_bytes = open(a.plan_in, "rb").read()
    raw = json.loads(base_bytes)
    if json.dumps(raw, indent=1).encode() != base_bytes:
        raise SystemExit("base plan does not round-trip json.dumps(indent=1); refusing to rewrite")
    rep = {"row": "SUL1-SLW-CHAN", "base_sha12": hashlib.sha256(base_bytes).hexdigest()[:12], "types": {}}
    for tn in TYPES:
        t = raw["partition_types"][tn]
        buses = {b["name"]: b for b in t["buses"]}
        rows = []
        for e in t["internal_stations"]:
            key = (e["conn"], core_key(e))
            if key not in BANDS:
                continue
            lo, hi = BANDS[key]
            b = buses[e["conn"][4:]]
            su = e["start_um"]; W = len(su) - 1
            bits = sorted({int(x) for x in e["core_bits"]} | {W})
            lx, ly = map(float, e["leaf_um"]); n = len(e["regs_um"])
            was = e.get("leg_order", "normal_first")
            if was == "channel":                                   # idempotent only on the same band
                if [float(v) for v in e.get("channel_um", [])] != [lo, hi]:
                    raise SystemExit(f"{tn} {e['conn']} {core_key(e)}: already channel {e.get('channel_um')} != {[lo, hi]}")
                rows.append(dict(conn=e["conn"], core=core_key(e), skipped="already channel")); continue
            new = [[0.0, 0.0] for _ in range(n)]; oldc = [[0.0, 0.0] for _ in range(n)]
            worst = 0.0; old_sites_all = []; new_sites_all = []
            for bit in bits:
                px, py = map(float, su[bit])
                s = IC.sites(px, py, lx, ly, b["face"], b["dir"], lo, hi, bit, W + 1, n)   # kit: (b+0.5)/(W+1)
                o = old_sites(px, py, lx, ly, was, n)
                worst = max(worst, IC.worst_hop(px, py, lx, ly, b["face"], b["dir"], lo, hi, bit, W + 1, n))
                for k in range(n):
                    new[k][0] += s[k][0]; new[k][1] += s[k][1]; oldc[k][0] += o[k][0]; oldc[k][1] += o[k][1]
                new_sites_all += s; old_sites_all += o
            new = [[round(x / len(bits), 3), round(y / len(bits), 3)] for x, y in new]
            rows.append(dict(conn=e["conn"], core=core_key(e), bits=len(bits), stations=n, was=was, channel_um=[lo, hi],
                             regs_before=e["regs_um"], regs_after=new, worst_bit_hop_um=round(worst, 1),
                             old_sites=[[round(x, 2), round(y, 2)] for x, y in old_sites_all],
                             new_sites=[[round(x, 2), round(y, 2)] for x, y in new_sites_all]))
            e["leg_order"] = "channel"; e["channel_um"] = [lo, hi]; e["regs_um"] = new
            e["note"] = e.get("note", "") + NOTE % ([lo, hi], was)
        rk = t.setdefault("relay_rank_sites", {})
        for name, x in zip(RANKS, RANK_X):
            want = {"line_um": [[x, RANK_Y[0]], [x, RANK_Y[1]]], "order": "asc",
                    "note": "SUL1-SLW-CHAN 11-25 RANK-SEAT: cl_x_su_c_i landing rank on a line parallel to its q face"}
            if name in rk and rk[name] != want:
                raise SystemExit(f"{tn} relay_rank_sites[{name}] exists and differs: {rk[name]}")
            rk[name] = want
        # wires per um across the band: vertical-leg columns of all 3 chains, 5 um bins
        cols = {}
        for e in t["internal_stations"]:
            if (e["conn"], core_key(e)) in BANDS:
                lo, hi = e["channel_um"]; W = len(e["start_um"]) - 1
                for bit in {int(x) for x in e["core_bits"]} | {W}:
                    c = IC.column(lo, hi, bit, W + 1); cols[int(c // 5) * 5] = cols.get(int(c // 5) * 5, 0) + 1
        rows.append(dict(wires_per_um_5um_bins={k: round(v / 5.0, 1) for k, v in sorted(cols.items())},
                         max_wires_per_um=round(max(cols.values()) / 5.0, 1)))
        rep["types"][tn] = rows
    s = json.dumps(raw, indent=1)
    open(a.plan_out, "w").write(s)
    rep["out_sha12"] = hashlib.sha256(s.encode()).hexdigest()[:12]
    json.dump(rep, open(a.report, "w"))
    for tn, rows in rep["types"].items():
        for r in rows:
            if "max_wires_per_um" in r:
                print(tn, "band wires/um (5 um bins)", r["wires_per_um_5um_bins"], "max", r["max_wires_per_um"]); continue
            print(tn, r["conn"], r["core"], r.get("bits"), r.get("was"), r.get("channel_um"), "hop", r.get("worst_bit_hop_um"),
                  "regs", r.get("regs_after"), r.get("skipped", ""))
    print("base", rep["base_sha12"], "out", rep["out_sha12"])


if __name__ == "__main__":
    main()
