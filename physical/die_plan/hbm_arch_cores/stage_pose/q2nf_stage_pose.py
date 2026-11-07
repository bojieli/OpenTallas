#!/usr/bin/env python3
"""HBM-HARD-2-QOUT 11-07: even pose for the pin_d stations of ot_q2nf_qout (no netlist change).

Measured on vR1 (RTL pin_d +2): GPL wirelength does not care where a flop sits on a fanout-1 chain, so u_bmid0/u_bmid1 stayed
near dst_d: hop p50 16/9/91 um, mid1->bout max 595 um, 1498 bits over 230 um, 1360 of the 1494 TT slew pins on these hops.
This writes KIT/stage_pose.tsv: each station at L*j/3 on the line from the bit's slice column (S face pins, y SRC_Y) to its N pin,
on a legal-ish slot grid in the N half.  stage_pose_pre.tcl holds them FIRM through GPL, face_flops_release.tcl lets DPL legalise.
  q2nf_stage_pose.py KIT      (reads KIT/pins.json, writes KIT/stage_pose.tsv)
"""
import json
import statistics
import sys

NS, PWT = 9, 545
SRC_Y, Y_M0, Y_M1 = 35.0, 58.0, 82.0   # top of the mux cloud in vR1; stage rows; the out flops sit at the N face already
PITCH_X, PITCH_Y = 2.16, 0.54          # slot: flop + inverter + room; 0.29 local density when every slot is taken
Y_LO, Y_HI = 46.0, 100.0
X_LO, X_HI = 6.0, 778.0
DEST = [2, 3, 4, 5, 6, 7, 8, 9, 14]    # dests that reach pin_d, slices 0..15; slices 16, 17 have fewer (fcore assign list)
DEST_SHORT = [2, 3, 4, 5, 14]


def pin_d_slices():
    bit = 0
    for k in range(18):
        cw = 32 if k < 17 else 1
        for _ in DEST if k < 16 else DEST_SHORT:
            for _ in range(cw):
                yield bit, k
                bit += 1


def main(kit):
    pins = json.load(open(f"{kit}/pins.json"))
    cap = {p["bit"]: p for p in pins if p["bus"] == "captured"}
    out = {p["bit"]: p for p in pins if p["bus"] == "pin_d"}
    col = {}
    for k in range(18):
        cw = 32 if k < 17 else 1
        col[k] = statistics.median(cap[s * PWT + k * 32 + i]["x"] for s in range(NS) for i in range(cw))
    used, rows, hops = set(), [], []

    def slot(x, y):
        ci, ri = round((x - X_LO) / PITCH_X), round((y - Y_LO) / PITCH_Y)
        cmax, rmax = int((X_HI - X_LO) / PITCH_X), int((Y_HI - Y_LO) / PITCH_Y)
        for d in range(0, 400):
            for dc in range(-d, d + 1):
                dr = d - abs(dc)
                for r in {ri + dr, ri - dr}:
                    c = ci + dc
                    if 0 <= c <= cmax and 0 <= r <= rmax and (c, r) not in used:
                        used.add((c, r))
                        return X_LO + c * PITCH_X, Y_LO + r * PITCH_Y
        raise SystemExit(f"no slot near {x} {y}")

    n = 0
    for bit, k in pin_d_slices():
        n += 1
        px, py = out[bit]["x"], out[bit]["y"]
        sx = col[k]
        a = slot(sx + (px - sx) / 3, Y_M0)
        b = slot(sx + (px - sx) * 2 / 3, Y_M1)
        rows.append((f"u_bmid0_pin_d/q[{bit}]", *a, abs(px - sx) / 3))
        rows.append((f"u_bmid1_pin_d/q[{bit}]", *b, abs(px - sx) / 3))
        d = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
        hops += [d((sx, SRC_Y), a), d(a, b), d(b, (px, py - 6))]
    if n != len(out):
        raise SystemExit(f"bit map {n} != pin_d {len(out)}")
    with open(f"{kit}/stage_pose.tsv", "w") as f:
        f.write("# inst x_um y_um hop_um\n")
        for nm, x, y, h in rows:
            f.write(f"{nm}\t{x:.3f}\t{y:.3f}\t{h:.1f}\n")
    hops.sort()
    print(f"STAGE_POSE bits {n} stations {len(rows)} hop p50 {hops[len(hops)//2]:.0f} p90 {hops[int(len(hops)*.9)]:.0f} max {hops[-1]:.0f} over230 {sum(h>230 for h in hops)}")


if __name__ == "__main__":
    main(sys.argv[1])
