#!/usr/bin/env python3
"""DIE-S81-85 11-09 RCK2-1109: a SECOND io_pma_rck clock entry for the S81 serdes column types (serdes-only plan event).

COORD loopgap-155x-1109 (ii): "second io_pma_rck entry YES ... a plan event adding a second rck entry/tap on the serdes
slot, as a one-block change (serdes types only) with a plan check new-only 0".

Problem (serdes__t14 attempt_11, 3_place.odb / 4_1_cts.log): the one io_pma_rck pin (257.952, 1090.8) sits at the west
end of the PMA stack and drives 22,311 sinks.  They are two clusters: the decoder core (u_dec u_lpl/u_out/u_dly/
u_syn, u_rm, dchn/dmem/cmem; 21,445 sinks, bbox 863..1724 x 37..584) and the RX face band under the rxm (544
u_face_p_d capture flops at y 946 over x 260..2476, the first u_syn stage, am_ok at the NE corner; 866 sinks).  One
TritonCTS H-tree spans both (2504 x 1044 um): root wire 1752 um to the bbox centre, path depth 38-41 BUFx24,
37 delay buffers to balance the macros, about 2.6 ns insertion.

Form chosen: the PMA view has ONE recovered-clock pin (ot_s81_pma_rxm.lef PIN pma_rck, DIRECTION INPUT, USE CLOCK,
M5 x 13.428..13.452 at the line edge; the CDR clock is the type input pad io_pma_rck, delivered at that pin), so the
PMA cannot deliver the clock at a second point, and a second type port would be a die-top change.  The second entry
is therefore a PLAN-PLACED TRUNK inside the type (clock.pad_clock pins[].entries, pad_clock.py +
pad_clock_entry.tcl, PRE_CTS): from the pad pin, BUFx24 stations (hops <= 400 um, 12.1e) to an entry driver at the
decoder cluster; its output net io_pma_rck_e1 carries every sink below the face band plus the decoder macro clock
pins, the pad net keeps the face band, the rxm pin and the NE outliers.  TritonCTS then builds two local trees under
the one clock and its latency balancer equalises them; the 1-sink station nets are left as planned (CTS-0041).  Ports, RTL, SDC, die top unchanged.

Geometry per type (plan data only, deterministic):
  face band   y >= y_a = max(PHY region bottom - FACE_BAND_UM, decoder macro top + CLEAR)  -> pad pin (root tree)
  entry e1    region [0, 0, W, y_a]; sink_pins = dchn clk, dmem wclk/rclk, cmem clk (rxm pma_rck stays on the pin)
  driver      x = decoder macro bbox centre x; y = max((macro bottom + y_a) / 2, macro top + 2*CLEAR)
  trunk       pin -> s0 (pin x, region bottom - S0_DROP_UM, below the RX capture band) -> down the pin x -> east at the
              driver y -> driver; stations evenly spaced, ceil(L / 400) hops.
Only serdes types with an io_pma_rck pad clock are rewritten (the pins[] object in the plan's indent-1 style); every
other key and type is asserted unchanged.  Refuses a second run.

usage: delta_rck2_1109.py PLAN_IN PLAN_OUT [REPORT.json]"""
import copy
import json
import math
import re
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[3] / "tools" / "die_plan")]
from delta_romq_split_1106 import spans  # noqa: E402

EVENT = "RCK2-1109"
PORT = "io_pma_rck"
ENTRY = "io_pma_rck_e1"
CELL = "BUFx24_ASAP7_75t_R"          # the kit CTS root/sink buffer (4_1_cts.log CTS-0050/0051) and the cland_fwd cell
HOP_UM = 400.0                       # < pad_clock.ENTRY_HOP_UM 405 (12.1e)
FACE_BAND_UM = 350.0                 # face band depth under the PHY region (t14: u_face_p_d + u_syn stage 1 + am_ok)
CLEAR = 8.64                         # schema TAP_CLEAR_UM / kit macro channel
S0_DROP_UM = 12.0                    # s0 below the PHY region bottom: clear of the 4 RX capture band rows (+2 clear)
DEC_MACROS = (("ot_s81_kp4_dchn", ("clk",)), ("ot_sram_1r1w2c_64x546_m1", ("wclk", "rclk")),
              ("ot_sram_1r1w_32x546_m1", ("clk",)))
EVIDENCE = ("serdes__t14 attempt_11 (kw26 e9eda32d41c) 3_place.odb: 22,311 io_pma_rck sinks; decoder cluster 21,445 "
            "(bbox 863..1724 x 37..584), face band 866 (y >= 600, x 222..2726, am_ok 2726,1047); 4_1_cts.log one "
            "H-tree over 2504 x 1044 um, avg sink wire 1752 um, depth 38-41, 37 delay buffers; COORD loopgap-155x-1109")


def serdes_types(raw):
    out = []
    for tn, t in sorted(raw["partition_types"].items()):
        pc = t.get("clock", {}).get("pad_clock")
        if tn.startswith("serdes") and pc and any(p["name"] == PORT for p in pc["pins"]):
            out.append(tn)
    return out


def boxes(t):
    """{master: [x0, y0, x1, y1]} of the placed decoder macros, plus every placed macro box (for clearance)."""
    allb, dec = [], {}
    for c in t.get("contents", []):
        for q in c.get("physical_parts", []):
            (x, y), (w, h) = q["origin_um"], q["outline_um"]
            allb.append((q["physical_master"], [x, y, x + w, y + h]))
    for c in t.get("hard_cores", []):
        (x, y), (w, h) = c["origin_um"], c["outline_um"]
        allb.append((c["module"], [x, y, x + w, y + h]))
    for m, b in allb:
        if m in dict(DEC_MACROS):
            assert m not in dec, (m, "twice")
            dec[m] = b
    return dec, allb


def l_points(a, corner, b, n):
    """n points evenly spaced along the L path a -> corner -> b (the last is b)."""
    legs = [(a, corner), (corner, b)]
    lens = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in legs]
    total = sum(lens)
    out = []
    for k in range(1, n + 1):
        s = total * k / n
        for (p, q), ln in zip(legs, lens):
            if s <= ln + 1e-9 and ln > 0:
                f = s / ln
                out.append([round(p[0] + (q[0] - p[0]) * f, 3), round(p[1] + (q[1] - p[1]) * f, 3)])
                break
            s -= ln
    return out


def entry(P, tn, t, pin):
    import gen_phys as GP
    W, H = t["outline_um"]
    dec, allb = boxes(t)
    if set(dec) != set(dict(DEC_MACROS)):
        raise SystemExit(f"{tn}: decoder macros {sorted(dec)} != {sorted(dict(DEC_MACROS))}")
    rxm = next(q["physical_inst"] for c in t["contents"] for q in c.get("physical_parts", [])
               if q["physical_master"] == "ot_s81_pma_rxm")
    doms = [d for d in GP.phy_pg_domains(P, tn) if rxm in d[4]]
    if len(doms) != 1:
        raise SystemExit(f"{tn}: rxm {rxm} must sit in exactly one PHY PG domain")
    reg = doms[0][3]
    mx0 = min(b[0] for b in dec.values()); my0 = min(b[1] for b in dec.values())
    mx1 = max(b[2] for b in dec.values()); my1 = max(b[3] for b in dec.values())
    y_a = round(max(reg[1] - FACE_BAND_UM, my1 + CLEAR), 3)
    ex, ey = round((mx0 + mx1) / 2, 3), round(max((my0 + y_a) / 2, my1 + 2 * CLEAR), 3)
    px, py = pin["xy_um"]
    s0 = [round(px, 3), round(reg[1] - S0_DROP_UM, 3)]
    L = abs(s0[1] - ey) + abs(ex - s0[0])
    n = max(1, math.ceil(L / HOP_UM))
    pts = [s0] + l_points(s0, [s0[0], ey], [ex, ey], n)
    for x, y in pts:                      # every trunk cell clear of every macro and of the PHY region
        for m, b in allb:
            if b[0] - CLEAR < x < b[2] + CLEAR and b[1] - CLEAR < y < b[3] + CLEAR:
                raise SystemExit(f"{tn}: trunk point ({x}, {y}) within {CLEAR} um of macro {m} {b}")
        if reg[0] <= x <= reg[2] and reg[1] <= y <= reg[3]:
            raise SystemExit(f"{tn}: trunk point ({x}, {y}) inside the PHY region {reg}")
    sinks = [dict(module=m, pin=p) for m, ps in DEC_MACROS for p in ps]
    e = dict(name=ENTRY, xy_um=pts[-1], stations_um=pts[:-1], cell=CELL, region_um=[[0.0, 0.0, float(W), y_a]],
             sink_pins=sinks,
             evidence=f"{EVENT} (DIE-S81-85, COORD loopgap-155x-1109): PMA view has one pma_rck pin, so the 2nd entry is "
                      f"a plan-placed {CELL} trunk; face band y >= {y_a:g} (PHY region bottom {reg[1]:g} - "
                      f"{FACE_BAND_UM:g}, decoder macro top {my1:g} + {CLEAR:g}) stays on the pad pin. Basis: {EVIDENCE}")
    hops = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip([pin["xy_um"]] + pts, pts)]
    rep = dict(type=tn, pin=pin["xy_um"], phy_region=reg, face_band_y=y_a, decoder_bbox=[mx0, my0, mx1, my1],
               entry_xy=pts[-1], stations=pts[:-1], trunk_um=round(sum(hops), 1), hops_um=[round(h, 1) for h in hops],
               root_keeps=["ot_s81_pma_rxm/pma_rck", f"std-cell sinks y >= {y_a:g}"],
               entry_takes=[f"{s['module']}/{s['pin']}" for s in sinks] + [f"std-cell sinks y < {y_a:g}"])
    return e, rep


def main():
    pin_p, pout = sys.argv[1:3]
    rep_p = sys.argv[3] if len(sys.argv) > 3 else None
    import schema as S
    text = open(pin_p).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    P = S.Plan(json.loads(text), pin_p)
    types = serdes_types(raw)
    if not types:
        raise SystemExit("no serdes type with an io_pma_rck pad clock")
    rows, edits = [], []
    sp = spans(text)
    for tn in types:
        t = raw["partition_types"][tn]
        pins = t["clock"]["pad_clock"]["pins"]
        k = next(i for i, p in enumerate(pins) if p["name"] == PORT)
        pin = pins[k]
        if "entries" in pin:
            raise SystemExit(f"{tn}: {PORT} entries already present (second run refused)")
        have = {(s["module"], s["pin"]) for s in pin.get("sink_pins", [])}
        need = {(m, p) for m, ps in DEC_MACROS for p in ps}
        if not need <= have:
            raise SystemExit(f"{tn}: {PORT} sink_pins lack the decoder macro pins {sorted(need - have)}")
        e, r = entry(P, tn, t, pin)
        pin["entries"] = [e]
        rows.append(r)
        a, b = sp[("partition_types", tn, "clock", "pad_clock", "pins", k)]
        line0 = text.rfind("\n", 0, a) + 1
        ind = re.match(r" *", text[line0:]).group(0)
        old = text[a:b]
        if "\n" in old:
            new = json.dumps(pin, indent=1).replace("\n", "\n" + ind)
            assert json.dumps(orig["partition_types"][tn]["clock"]["pad_clock"]["pins"][k], indent=1).replace(
                "\n", "\n" + ind) == old, f"{tn}: pins[{k}] is not in the plan's indent-1 style"
        else:
            new = json.dumps(pin, separators=(",", ":"))
        edits.append((a, b, new))
    for a, b, new in sorted(edits, reverse=True):
        text = text[:a] + new + text[b:]
    assert json.loads(text) == raw
    for kk in raw:
        if kk != "partition_types":
            assert raw[kk] == orig[kk], kk
    for tn in raw["partition_types"]:
        if tn not in types:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
        else:
            a, b = copy.deepcopy(raw["partition_types"][tn]), copy.deepcopy(orig["partition_types"][tn])
            for p in a["clock"]["pad_clock"]["pins"]:
                p.pop("entries", None)
            assert a == b, tn
    # the edited plan must pass the pad clock contract (pad_clock.check_entries) on every rewritten type
    import pad_clock as PC
    P2 = S.Plan(json.loads(text), pout)
    for tn in types:
        assert len(PC.entries(P2, tn)) == 1, tn
    open(pout, "w").write(text)
    if rep_p:
        open(rep_p, "w").write(json.dumps(dict(event=EVENT, cell=CELL, hop_um=HOP_UM, face_band_um=FACE_BAND_UM,
                                               types=rows), indent=1) + "\n")
    for r in rows:
        print(json.dumps({k: r[k] for k in ("type", "face_band_y", "entry_xy", "trunk_um", "hops_um")}))


if __name__ == "__main__":
    main()
