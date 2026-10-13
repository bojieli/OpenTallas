#!/usr/bin/env python3
"""qfd_sp_res_ser cluster floorplan (Qwen ROM TP8 contract v4b slot 777.6 x 518.4), generated top-down.

  res_ser_cluster_fp.py [--tile-lef LEF] [--out-spec SPEC.json] [--out-io IO.tcl] [--out-json FP.json]

Floorplan (um).  Eight hard slot tiles ot_qfd_res_slot_tile (kit qfd_res_slot_rt, 216 x 129.6: chain in + out on E, the
i word on S, clk / strobes / strap on N, W pin-free) on a 3 x 3 grid with channels on every pin face; the ninth cell
(column 2, row 1) is the serialiser head (ot_qfd_res_tiles_ctl + the o / ok / cr / fault pin flops); a 62.6-um strip
under the N face holds the two input stages (A at the pins, B per tile).

  x: 23.76 | col 0 216 | 34.56 | col 1 216 | 34.56 | col 2 216 | 36.72        (E channels carry the chain)
  y: 23.76 | row 0 129.6 | 21.6 | row 1 129.6 | 21.6 | row 2 129.6 | 62.64   (row gaps carry the i words' last um)

Ring (slot g = ring position g): (2,2) (1,2) (0,2) (0,1) (0,0) (1,0) (1,1) (2,0), head at (2,1).

The script writes the ref_tile spec (children at exact origins), the exact pin plan (i word g on the N face above its
tile's own S pins, o / ok / cr / fault on E beside the head, ck / rst_n / me_en at the contract offsets) and the
analysis the die spec asks for before RTL is hardened: every registered hop's length (<= 500 um) and bits per cut
against routing tracks (<= 0.60)."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W, H = 777.6, 518.4
TW, TH = 216.0, 129.6
COLX = [23.76, 274.32, 524.88]
ROWY = [23.76, 174.96, 326.16]
RING = [(2, 2), (1, 2), (0, 2), (0, 1), (0, 0), (1, 0), (1, 1), (2, 0)]      # slot g -> (col, row)
HEAD = (2, 1)
NSTRIP_Y0 = ROWY[2] + TH                                                    # 455.76
P45, P67 = 0.048, 0.064                                                     # M4/M5 and M6/M7 track pitch
T0 = 0.012                                                                  # M4 / M5 track centre offset
KIT = "physical/ref_tile/qfd_res_slot_rt"
VIEW = KIT + "/views/ot_qfd_res_slot_tile"
CONTRACT = "results/arch/hier_contract_1012/qwen_rom_tp8.json"
CK_X, RST_X, ME_X = 388.788, 392.0, 396.0                                   # contract v4b offsets (N face)


def lef_pins(path):
    t = Path(path).read_text()
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t)
    w, h = float(m.group(1)), float(m.group(2))
    pins = {}
    for m in re.finditer(r"PIN (\S+)\n(.*?)END \1", t, re.S):
        if "USE SIGNAL" not in m.group(2):
            continue
        lay, r = re.search(r"LAYER (\S+) ;\s*RECT ([\d.\- ]+);", m.group(2)).groups()
        x0, y0, x1, y1 = map(float, r.split())
        face = "W" if x0 < 1e-6 else "E" if abs(x1 - w) < 1e-6 else "S" if y0 < 1e-6 else "N"
        pins[m.group(1)] = (face, lay, (x0 + x1) / 2, (y0 + y1) / 2)
    return w, h, pins


def snap(v, pitch=P45, off=T0):
    return round(round((v - off) / pitch) * pitch + off, 3)


def word_bits(g):
    """die bit of i for every S pin of tile g: tile pin name -> index in i[4424:0] (None = decoded in the parent)"""
    out = {}
    for b in range(512):
        out[f"i_data[{b}]"] = 329 + g * 512 + b
    for b in range(16):
        out[f"i_mask[{b}]"] = 201 + g * 16 + b
    for b in range(24):
        out[f"i_addr[{b}]"] = 9 + g * 24 + b
    out["i_we"] = 1 + g
    return out


def plan(tile_lef):
    tw, th, tp = lef_pins(tile_lef)
    assert abs(tw - TW) < 1e-6 and abs(th - TH) < 1e-6, (tw, th)
    faces = {}
    for n, (f, lay, x, y) in tp.items():
        faces.setdefault(f, []).append(n)
    assert "W" not in faces, "tile W face must be pin-free"
    pins = []                    # (name, layer, x, y, face)
    hops = []                    # (what, bits, um)
    # ---- N face: i word g above its tile's S pins.  Per column, the three tiles' pins are merged in x order onto
    # distinct M5 tracks (>= 2 tracks apart); the control pins sit at the contract offsets.
    keep = [(CK_X, "ck"), (RST_X, "rst_n"), (ME_X, "me_en")]
    ctl_bits = [(380.0 + 0.48 * k, f"i[{k}]") for k in range(9)]              # i_ov, i_we[7:0] beside the clock
    used = set()
    for x, n in keep + ctl_bits:
        xs = snap(x)
        while xs in used:
            xs = round(xs + P45, 3)
        used.add(xs)
        pins.append((n, "M5", xs, H, "N"))
    ipin = {}
    for c in range(3):
        want = []
        for g, (cc, r) in enumerate(RING):
            if cc != c:
                continue
            wb = word_bits(g)
            for n in faces["S"]:
                if n in wb and n != "i_we":
                    want.append((COLX[c] + tp[n][2], r, f"i[{wb[n]}]", g, n))
        want.sort()
        lo = COLX[c] - 8.0
        last = lo
        for xw, r, dn, g, tn in want:
            xs = max(snap(xw), round(last + 2 * P45, 3))
            while any(abs(xs - u) < 2 * P45 - 1e-9 for u in used if abs(u - xs) < 1.0):
                xs = round(xs + P45, 3)
            used.add(xs)
            last = xs
            pins.append((dn, "M5", xs, H, "N"))
            ipin[dn] = (xs, g, tn)
    # ---- E face: o beside the head (4-track pitch), then ok, cr, fault
    y0 = ROWY[1] + 12.0
    for b in range(551):
        pins.append((f"o[{b}]", "M4", W, snap(y0 + b * 4 * P45), "E"))
    ye = snap(y0 + 551 * 4 * P45 + 1.0)
    for k, n in enumerate(("ok", "cr", "fault")):
        pins.append((n, "M4", W, round(ye + k * 20 * P45, 3), "E"))
    # ---- hops
    ya, yb = H - 10.0, NSTRIP_Y0 + 12.0          # A band under the pins, B band at the bottom of the N strip
    worst = {}

    def hop(k, bits, um):
        a = worst.setdefault(k, [bits, 0.0, 0])
        a[1] = max(a[1], um)
        a[2] += 1

    for dn, (xs, g, tn) in ipin.items():
        c, r = RING[g]
        px, py = COLX[c] + tp[tn][2], ROWY[r]
        hop("pin -> A", 4425, H - ya)
        hop("A -> B", 4425, (ya - yb) + 2.0)
        if r == 0:
            yc = ROWY[1] - 10.8
            hop("B -> C (row 0 words)", 3 * 555, (yb - yc) + abs(xs - px))
            hop("C -> tile S pin (row 0)", 3 * 555, yc - py + 2.0)
        else:
            hop(f"B -> tile S pin (row {r})", 555, (yb - py) + abs(xs - px))
    # strobes / we / last / empty: A at the centre pins, B copies at each column's strip, C for row 0
    for g, (c, r) in enumerate(RING):
        npx = COLX[c] + max(tp[n][2] for n in faces["N"])
        hop("A (centre strobes) -> B copy", 8 * 5, abs(385.0 - (COLX[c] + TW / 2)) + (ya - yb))
        top = ROWY[r] + TH
        if r == 0:
            hop("B -> C (row 0 strobes)", 6, (yb - (ROWY[1] - 10.8)) + abs(COLX[c] + TW / 2 - npx))
            hop("C -> tile N pin (row 0)", 6, abs(ROWY[1] - 10.8 - top) + 4.0)
        else:
            hop(f"B -> tile N pin (row {r})", 2, (yb - top) + abs(COLX[c] + TW / 2 - npx))
    hx, hy = COLX[2] + TW / 2, ROWY[1] + TH / 2
    hop("A (centre strobes) -> head B copy", 2, abs(385.0 - hx) + (ya - hy))
    # chain: tile E pins.  Centre of the rq/rd (in) and rqf/od (out) pin groups
    ein = [n for n in faces["E"] if re.match(r"(rd|rq_|rv)", n)]
    eout = [n for n in faces["E"] if re.match(r"(od|rqf_|ov|fault)", n)]
    cy = lambda ns: sum(tp[n][3] for n in ns) / len(ns)
    sp = lambda ns: max(tp[n][3] for n in ns) - min(tp[n][3] for n in ns)
    pos_in = [(COLX[c] + TW, ROWY[r] + cy(ein)) for c, r in RING]
    pos_out = [(COLX[c] + TW, ROWY[r] + cy(eout)) for c, r in RING]
    head_e = (COLX[2] + TW + 18.0, ROWY[1] + 12.0 + 551 * 4 * P45 / 2)       # head output flops at the o pins
    head_w = (COLX[2] + 20.0, hy)
    chain = []
    for g in range(8):
        src = head_w if g == 0 else pos_out[g - 1]
        d = abs(src[0] - pos_in[g][0]) + abs(src[1] - pos_in[g][1]) + (sp(ein) + sp(eout)) / 4
        over = None
        if g and RING[g - 1][0] != RING[g][0] and RING[g][0] < RING[g - 1][0]:
            over = RING[g - 1]              # leaving a tile's E channel westward = over that tile on M6
        if g and RING[g][0] > RING[g - 1][0]:
            over = RING[g]                  # eastward = over the destination tile
        chain.append({"hop": f"{'head' if g == 0 else 'slot %d' % (g - 1)} -> slot {g}", "bits": 10 if g == 0 else 563,
                      "um": round(d, 1), "over_tile": over})
    d = abs(pos_out[7][0] - head_e[0]) + abs(pos_out[7][1] - head_e[1])
    chain.append({"hop": "slot 7 -> head (rd capture)", "bits": 552, "um": round(d, 1), "over_tile": None})
    chain.append({"hop": "head rd capture -> o pin flops", "bits": 551, "um": round(abs(head_e[1] - (ROWY[0] + TH)) + 20.0, 1),
                  "over_tile": None})
    # ---- cuts
    cuts = []
    PG7, PG6 = 0.85, 0.90                    # track share left by the M7 PG stripes / M6 child straps (estimate)
    for r in (2, 1, 0):
        for c in range(3):
            if (c, r) == HEAD:
                continue
            below = sum(555 for (cc, rr) in RING if cc == c and rr <= r)
            pitchw = COLX[c + 1] - COLX[c] if c < 2 else W - COLX[c]
            m7 = TW / P67 * PG7
            ch = (pitchw - TW) * (1 / 0.036 + 1 / P45 + 1 / P67) * 0.8
            cuts.append({"cut": f"y = top of ({c},{r}): i words going down column {c}", "bits": below,
                         "tracks": int(m7 + ch), "ratio": round(below / (m7 + ch), 3),
                         "basis": f"M7 over the tile {int(m7)} + channel M3/M5/M7 {int(ch)}"})
    for h in chain:
        if h["over_tile"]:
            c, r = h["over_tile"]
            m6 = TH / P67 * PG6
            cuts.append({"cut": f"x through tile ({c},{r}): {h['hop']} on M6 over the tile", "bits": h["bits"],
                         "tracks": int(m6), "ratio": round(h["bits"] / m6, 3), "basis": f"M6 over one tile row {int(m6)}"})
    for c in range(3):
        gw = (COLX[c + 1] - COLX[c] - TW) if c < 2 else (W - COLX[c] - TW)
        tr = gw * (1 / 0.036 + 1 / P45) * 0.8
        cuts.append({"cut": f"y through the E channel of column {c} ({gw:.2f} um): one chain hop", "bits": 563,
                     "tracks": int(tr), "ratio": round(563 / tr, 3), "basis": "M3 + M5 in the channel, 80 % usable"})
    nface = {}
    for n, lay, x, y, f in pins:
        if f == "N":
            nface.setdefault(int(x // 100), 0)
            nface[int(x // 100)] += 1
    dens = {"N_M5_max_b_per_um_100um": max(nface.values()) / 100.0,
            "E_M4_b_per_um": round(554 / (551 * 4 * P45 + 3.0), 2)}
    return {"schema": "opentallas.qwen.res_ser_cluster_fp.v1", "outline_um": [W, H], "tile_um": [TW, TH],
            "col_x": COLX, "row_y": ROWY, "ring": RING, "head_cell": HEAD,
            "ninth_cell": "column 2 row 1 = serialiser head (ot_qfd_res_tiles_ctl, o / ok / cr / fault pin flops)",
            "tile_pins": {f: len(v) for f, v in faces.items()},
            "hops_um": {k: {"bits": v[0], "max_um": round(v[1], 1)} for k, v in worst.items()},
            "chain_hops": chain, "cuts": cuts, "pin_density": dens,
            "max_hop_um": round(max([v[1] for v in worst.values()] + [h["um"] for h in chain]), 1),
            "max_cut": max(c["ratio"] for c in cuts)}, pins


def spec():
    ch = [{"view": VIEW, "count": 1, "inst": f"g_slot[{g}].u_t", "at": [COLX[c], ROWY[r]], "orient": "R0"}
          for g, (c, r) in enumerate(RING)]
    bench = "bash physical/res_ser/bench.sh {RUN}/bench/"
    return {
        "name": "qfd_sp_res_ser", "top": "qfd_sp_res_ser", "kind": "cluster",
        "sources": ["rtl/qwen_sys/vm_me_20261008/qfd_sp_res_ser.sv", "rtl/qwen_sys/vm_me_20261008/ot_qfd_res_tiles.sv",
                    "rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv", "rtl/lib/ot_rst_relay.sv",
                    "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v"],
        "params": {}, "defines": ["OT_HARD_CHILDREN"], "hard_define": "OT_HARD_CHILDREN",
        "clock_port": "ck", "reset_ports": ["rst_n"],
        "contract": {"file": CONTRACT, "slot": "sp_res_ser_0"},
        "child_lattice_um": 2.16,
        "children": ch,
        "pins": {"N": ["i", "me_en", "rst_n", "ck"], "E": ["o", "ok", "cr", "fault"]},
        "io_tcl": "physical/res_ser/qfd_sp_res_ser_pins.tcl",
        "route": {"pd": 0.45, "threads": 16, "peak_ram_gb": 48, "hold_margin_ns": 0.03},
        "slot_change_request": (
            "el1013-qwen-elements-r6 10-13: outline, faces, layers, clock entry (ck N x 388.788) and the rst_n / me_en "
            "offsets as contract v4b. PIN SPANS re-planned (the v4b spans put 4,425 i pins at every M5 track over 212 um "
            "= 20.8 b/um and 551 o pins over 26 um, above the 12 b/um/layer limit): i[4424:0] on N M5 over x 16..750, "
            "each slot word above its tile column (<= 7 b/um); o[550:0], ok, cr, fault on E M4 over y 187..297 beside "
            "the head cell. SUB-LAYOUT changed inside the unchanged slot: 8 tiles of 216 x 129.6 (kit qfd_res_slot_rt) "
            "on a 3 x 3 grid WITH channels (the 259.2 x 172.8 rs tiles cannot abut: W/E stubs short or corner-touch), "
            "head in cell (2,1). Packing: i = {i_data 4096, i_mask 128, i_addr 192, i_we 8, i_ov} (i_ov = i[0]); "
            "o = {o_v, o_end, o_nul, o_row 20, o_mask 16, o_data 512} (o_v = o[550]). +2 capture cycles (RS + 2 inside); "
            "reset release 4 ck edges after the pin."),
        "job": {
            "owner": "Claude:el1013-qwen-elements-r6", "branch": "claude/el1013-qwen-elements-r6", "tag": "c1",
            "purpose": ("Qwen ROM TP8 contract v4b slot cell qfd_sp_res_ser (3 instances sp_res_ser_0..2, 777.6 x 518.4): "
                        "hardened cluster under the die master name. 8 hard slot tiles (qfd_res_slot_rt) + the serialiser "
                        "head in the ninth cell; parent = registers at the pins (A), one per-tile stage (B), one more for "
                        "row 0 (C), reset relay, wires. Clock: balanced spine with each tile's routed insertion as its "
                        "leaf target; every seam registered on both sides."),
            "extra_paths": ["physical/res_ser", "rtl/test/res_ser", "rtl/test/res_tiles", "physical/res_tiles",
                            "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2", "tools/qwen_vm_me"],
            "benches": [
                {"name": "res_ser_exact", "cmd": bench + "pos", "expect": "pass", "pass_regex": "^PASS res_ser",
                 "min_count_regex": "beats=(\\d+)", "threads": 8, "peak_ram_gb": 4, "needs": ["verilator"],
                 "note": "the assembled cluster (8 tiles USE_MACRO=1 + head + A/B/C stages + reset relay) through the die "
                         "ports: 360 bursts / 1,465 beats exact, conveyor latency 19, 42-edge stopping debt, coverage floors"},
                {"name": "res_ser_mutant_tile", "cmd": bench + "neg1 1", "expect": "fail",
                 "fail_regex": "^FAIL res_ser mutant detected", "threads": 8, "peak_ram_gb": 4, "needs": ["verilator"],
                 "note": "MUT 1: one data bit of slot 1 inverted inside the tile"},
                {"name": "res_ser_mutant_seam", "cmd": bench + "neg2 2", "expect": "fail",
                 "fail_regex": "^FAIL res_ser mutant detected", "threads": 8, "peak_ram_gb": 4, "needs": ["verilator"],
                 "note": "MUT 2: the row-0 tiles' strobes bypass the C stage (word one cycle behind its strobe)"},
                {"name": "res_ser_coverage_refusal", "cmd": bench + "cov 0 0 40", "expect": "fail",
                 "fail_regex": "^COVERAGE_REFUSED", "threads": 8, "peak_ram_gb": 4, "needs": ["verilator"],
                 "note": "40-burst control: every beat exact but the floors are not reached, the bench must refuse"}]}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tile-lef", default=str(ROOT / VIEW / "ot_qfd_res_slot_tile.lef"))
    ap.add_argument("--out-spec", default=str(ROOT / "tools/ref_tile/specs_qsp/qfd_sp_res_ser.json"))
    ap.add_argument("--out-io", default=str(ROOT / "physical/res_ser/qfd_sp_res_ser_pins.tcl"))
    ap.add_argument("--out-json", default=str(ROOT / "physical/res_ser/qfd_sp_res_ser_fp.json"))
    a = ap.parse_args(argv)
    fp, pins = plan(a.tile_lef)
    Path(a.out_json).write_text(json.dumps(fp, indent=1) + "\n")
    Path(a.out_spec).write_text(json.dumps(spec(), indent=1) + "\n")
    L = ["# qfd_sp_res_ser exact pin plan, generated by tools/qwen_vm_me/res_ser_cluster_fp.py -- do not edit",
         "# i word g on N above its tile's S pins (M5), control at the contract offsets, o / ok / cr / fault on E (M4)"]
    seen = set()
    for n, lay, x, y, f in pins:
        assert n not in seen, n
        seen.add(n)
        nm = n if "[" in n else n
        if f == "N":
            L.append(f"place_pin -pin_name {{{nm}}} -layer {lay} -location {{{x:.3f} {y:.3f}}} -pin_size {{0.024 0.192}} -force_to_die_boundary")
        else:
            L.append(f"place_pin -pin_name {{{nm}}} -layer {lay} -location {{{x:.3f} {y:.3f}}} -pin_size {{0.192 0.024}} -force_to_die_boundary")
    need = {f"i[{b}]" for b in range(4425)} | {f"o[{b}]" for b in range(551)} | {"ck", "rst_n", "me_en", "ok", "cr", "fault"}
    assert seen == need, (len(seen), len(need), sorted(need - seen)[:5], sorted(seen - need)[:5])
    Path(a.out_io).write_text("\n".join(L) + "\n")
    print(f"res_ser cluster fp: {len(pins)} pins, max hop {fp['max_hop_um']} um, max cut {fp['max_cut']}, "
          f"N pin density {fp['pin_density']['N_M5_max_b_per_um_100um']} b/um")
    for k, v in fp["hops_um"].items():
        print(f"  hop {k}: {v['bits']} b, <= {v['max_um']} um")
    for h in fp["chain_hops"]:
        print(f"  chain {h['hop']}: {h['bits']} b, {h['um']} um" + (f", over tile {h['over_tile']}" if h["over_tile"] else ""))
    for c in fp["cuts"]:
        print(f"  cut {c['cut']}: {c['bits']} / {c['tracks']} = {c['ratio']}")
    return 0 if fp["max_hop_um"] <= 500.0 and fp["max_cut"] <= 0.60 else 1


if __name__ == "__main__":
    sys.exit(main())
