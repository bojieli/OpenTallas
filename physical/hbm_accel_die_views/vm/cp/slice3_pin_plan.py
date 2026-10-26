#!/usr/bin/env python3
"""[vm8 FACE3 2026-10-13] vm_cp_slice3 floorplan + locked per-bit N-face pin plan + cut analysis (cx2).

MEASURED (vm_cp_slice3_cx-cx1-2c31a0533, ot-epyc4, congestion-30.rpt, 5,178 markers): every marker lies in x 90-160
(the 20.1 um centre channel 119.4-139.5 and the macro edges facing it), y 80-200; nets u_slice.q[1] 5,682, q[0] 3,347,
c_wd 3,175 marker hits.  3,549 horizontal markers sit at capacity 0 INSIDE the macro edges, 1,629 vertical in the channel.

LEF FACT (ot_sram_1r1w_128x256_m1_r2c2.lef, every signal pin on M4): edge A (LEF x = 0) carries rd_out[255:0] AND
wd_in[136:0] + clk / r_ce / r_addr / w_ce / w_addr (409 pins); edge B (x = 94.824) carries wd_in[255:137] (119) and the
tied-off w_mask / rr / cr.  So "wd on one edge, rd on the other" (the FACE2 note) is NOT the macro: mirroring the whole
right column would put 256 rd + 137 wd per macro into each margin (3 rows: 1,230 bits on ~1,090 tracks = 1.13).

cx1 FLOORPLAN: both columns R0 and the six instances placed in dictionary order, which pairs a bank-0 macro with a
bank-1 macro of the OTHER column and another row (m0: L row 1 + R row 2 ...).  Each rd bit is the mux of two macros'
q and each wd bit feeds two macros: with that pairing nothing is shared and the centre channel carries, at the top of
row 3, edge B of 3 left macros + edge A of 3 right macros = 1,584 bits on 976 tracks (1.62).

cx2 PLAN (pairs share one channel; the pair's rd mux and its wd trunk are local):
  pair 0 (banks[0|1].macros[0])  left column rows 1+2, R0: edge A -> LEFT margin  (rd 256 after the mux + wd 137 + ctl)
  pair 1 (banks[0|1].macros[1])  right column rows 1+2, MY: edge A -> RIGHT margin
  pair 2 (banks[0|1].macros[2])  row 3 (top, nearest the pins): left MY + right R0: edge A of both -> CENTRE channel
  edge B (119 wd bits, shared by a pair's two macros): pairs 0+1 -> centre, pair 2 -> one in each margin.
Outline 259.2 -> 280.8 um wide (SLOT_CHANGE_REQUEST): centre channel 20.1 -> 35.6 um, margins 22.5 -> 25.5 / 25.7 um.
N-face pins (M3, 3 tracks per pin) sit over the channel their bit descends in.
    python3 slice3_pin_plan.py   writes codex_specs/pins/vm_cp_slice3_cx_pins.tcl, prints the cut table + spec fields
"""
import json
from pathlib import Path

CP = Path(__file__).resolve().parent
W, H = 280.8, 216.0
MW, MH = 94.824, 41.064
XL, XR = 27.648, 158.112
ROWS = (23.76, 86.4, 149.04)
T3, T3O, T5 = 0.036, 0.009, 0.048
NA_WD, NB_WD = 137, 119                 # wd_in bits on edge A / edge B
CTL = 17                                # clk, r_ce, r_addr[7], w_ce, w_addr[7] on edge A
# (inst pattern, x, y, orient)
MACROS = [("*banks?0?.macros?0?.u_sram", XL, ROWS[0], "R0"), ("*banks?1?.macros?0?.u_sram", XL, ROWS[1], "R0"),
          ("*banks?0?.macros?1?.u_sram", XR, ROWS[0], "MY"), ("*banks?1?.macros?1?.u_sram", XR, ROWS[1], "MY"),
          ("*banks?0?.macros?2?.u_sram", XL, ROWS[2], "MY"), ("*banks?1?.macros?2?.u_sram", XR, ROWS[2], "R0")]


def tracks(w, m5_loss=0.15):
    """vertical tracks of a channel: M3 + M5 less the M5 PG stripes"""
    return w / T3 + w / T5 * (1 - m5_loss)


def cut():
    core = 2.16
    ch = {"left": XL - core, "centre": XR - (XL + MW), "right": (W - core) - (XR + MW)}
    # bits through each channel mouth at the top of row 3 (every signal of the tile leaves north)
    rd, a, b = 256, NA_WD, NB_WD
    dem = {"left": rd + a + 2 * CTL + b,            # pair 0 edge A (shared) + pair 2 left macro edge B
           "right": rd + a + 2 * CTL + b,           # pair 1 edge A + pair 2 right macro edge B
           "centre": rd + a + 2 * CTL + 2 * b}      # pair 2 edge A (shared) + edge B of pairs 0 and 1
    rows = {}
    for k in ch:
        rows[k] = dict(width_um=round(ch[k], 3), bits=dem[k], tracks=round(tracks(ch[k])),
                       cut=round(dem[k] / tracks(ch[k]), 3), cut_no_pg_loss=round(dem[k] / tracks(ch[k], 0), 3))
    old = dict(width_um=20.088, bits=3 * (NB_WD + 256 + NA_WD + CTL), tracks=round(tracks(20.088, 0)))
    old["cut"] = round(old["bits"] / old["tracks"], 3)
    return rows, old


def pins():
    """-> {name: M3 track}; groups over the channel each bit descends in"""
    out = {}
    def run(names, t0, step=3):
        for i, n in enumerate(names):
            out[n] = t0 + step * i
        return t0 + step * len(names)
    def mix(m, a_lo, a_hi):
        """rd[m*256 +: 256] and wd[m*256 + a_lo .. a_hi) interleaved (2 rd : 1 wd)"""
        rdl = [f"rd[{m * 256 + i}]" for i in range(256)]
        wdl = [f"wd[{m * 256 + i}]" for i in range(a_lo, a_hi)]
        res = []
        while rdl or wdl:
            res += rdl[:2]; rdl = rdl[2:]
            res += wdl[:1]; wdl = wdl[1:]
        return res
    tr = lambda x: round((x - T3O) / T3)
    # left margin: pair 0 edge A
    e = run(mix(0, 0, NA_WD), tr(2.7))
    # pair 2 edge B (one macro in each margin): next to the left group, crosses the top strip to the right margin
    e = run([f"wd[{512 + i}]" for i in range(NA_WD, 256)], e + 12)
    e = run([f"cmd[{i}]" for i in range(10)] + ["rst"], e + 12)
    out["ck"] = e + 40
    # centre channel: pair 2 edge A, then edge B of pairs 0 and 1, centred on the channel
    cen = mix(2, 0, NA_WD) + [f"wd[{i}]" for i in range(NA_WD, 256)] + [f"wd[{256 + i}]" for i in range(NA_WD, 256)]
    cmid = (XL + MW + XR) / 2
    c0 = tr(cmid) - 3 * len(cen) // 2
    assert c0 > out["ck"] + 20, (c0, out["ck"])
    e = run(cen, c0)
    out["rv"] = e + 12
    # right margin: pair 1 edge A, ending 2.7 um off the corner
    rg = mix(1, 0, NA_WD)
    r0 = tr(W - 2.7) - 3 * (len(rg) - 1)
    assert r0 > out["rv"] + 20
    run(rg, r0)
    assert len(out) == 768 * 2 + 10 + 3 and len(set(out.values())) == len(out)
    return out


def main():
    p = pins()
    L = ["# generated by physical/hbm_accel_die_views/vm/cp/slice3_pin_plan.py (vm_cp_slice3_cx cx2) -- do not edit",
         "# locked per-bit N-face pin plan: every pin sits over the channel its bit descends in (M3, 3 tracks per pin)"]
    for n, t in sorted(p.items(), key=lambda kv: kv[1]):
        L.append(f"place_pin -pin_name {{{n}}} -layer M3 -location {{{t * T3 + T3O:.4f} {H:.4f}}} -force_to_die_boundary")
    (CP / "codex_specs" / "pins").mkdir(exist_ok=True)
    (CP / "codex_specs" / "pins" / "vm_cp_slice3_cx_pins.tcl").write_text("\n".join(L) + "\n")
    rows, old = cut()
    rng = {}
    for n, t in p.items():
        b = n.split("[")[0]; x = round(t * T3 + T3O, 3)
        lo, hi = rng.get(b, (x, x)); rng[b] = (min(lo, x), max(hi, x))
    # top strip: pins outside their mouth cross it horizontally; worst vertical line
    strip_h = (H - 2.16) - (ROWS[2] + MH)
    htr = strip_h / 0.048 + strip_h / 0.036
    res = dict(outline=[W, H], macros=[dict(inst=m[0], at=[m[1], m[2]], orient=m[3]) for m in MACROS], cut=rows,
               cx1_centre_channel=old, top_strip=dict(height_um=round(strip_h, 2), h_tracks_M2_M4=round(htr)),
               pin_ranges={k: [v[0], v[1]] for k, v in sorted(rng.items())})
    print(json.dumps(res, indent=1))
    return 0 if max(r["cut"] for r in rows.values()) <= 0.60 else 1


if __name__ == "__main__":
    raise SystemExit(main())
