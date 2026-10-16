#!/usr/bin/env python3
"""Q-TILE-REPACK (2026-10-15, owner 20:35): ref_tile cluster specs for the re-packed 64-lane compute tile qfd_tile_nk_rp1.

The closed rpair leaf boxes 2 ROM macros (121.824 x 62.91) in 311.04 x 129.6 um; five of them cap the tile near 38 %
fill.  qfd_tile_nk_rp1 (RTL RPH 1) places the 10 ROM macros directly in the tile with one RAW clock entry each
(ck_rom0..9) and the soft bank-row logic on five local CTS roots (ck_rp0..4).  Geometry (all channels >= 20 um, macro /
child to any pin face >= 20 um, macro rows abutted N-S where neither touching face carries a pin):

  * lane block: 8 x qfd_tile_lsl_fp1 (99.792 x 140.4, every pin on its E face) in 3 columns x 3 rows, all MY (pins W),
    so every channel carries one column's pins; the 9th slot (top right) is left to the face glue (tap / E face).
  * node leaf (47.52 x 432) at the W face, beside lane column 0; the die tree pins n_a / n_b / t_out / n_y sit on the
    node's own pin rows (straight through the pin registers).
  * macro block above the lanes: rows of 3 or 2 macros, alternating R0 / MX so two rows face their (bottom-edge) pins
    at a shared line; rows abutted at pitch 62.934 (= H + 0.024, ref_tile abutted stack); each bank's two macros
    adjacent.  The width 449.28 holds at most 3 macros per row (3 x 121.824 + 4 x ~21 um).

Floor (P1, every channel at the 20.088 minimum): lanes 3 x 140.4 + 2 x 20.088 = 461.4, macros 4 rows x 62.934 =
251.7, 3 channels / edges -> 773.4 -> outline 449.28 x 775.44.  A 735 um tile cannot hold the 8 lane leaves + 10
macros with >= 20 um channels at this width (lane block alone 461 + macro block 252 + 3 x 20).

    python3 tools/qwen_tp8/make_tile_nk_rp1_specs.py        # writes tools/ref_tile/specs_q_tile_repack/*.json
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "tools/ref_tile/specs_q_compute_native/qfd_tile_nk_native.json"
OUT = ROOT / "tools/ref_tile/specs_q_tile_repack"
LSL = "physical/ref_tile/qfd_tile_lsl_fp1/views/ot_qwen_tile_lsl_fp1"
NODE = "physical/ref_tile/ot_qwen_tile_node/views/ot_qwen_tile_node"
ROM = "physical/asap7_memory_macros/ot_rom_4096x266_m8"
LW, LH = 99.792, 140.4
NW_, NH = 47.52, 432.0
MW, MH = 121.824, 62.91
MPITCH = round(MH + 0.024, 3)       # abutted N-S stack
CL = 0.216
E = 22.464                           # >= 20 um from the CORE edge (core margin 2.16) on every face                           # child lattice (as qfd_tile_nk_native)
INST_LSL = "u_tile.u_tile.u_logic.u_me.g_hier.g_sl[{k}].g_hd.u_lh"
INST_NODE = "u_tile.u_tile.u_logic.genblk4.g_ndh.u_node"
INST_ROM = "u_tile.u_tile.g_col[{p}].g_bank[{b}].u_rom"


def row_y(y_min, orient):
    """lowest origin >= y_min that puts ot_rom_4096x266_m8's M4 pins on track: R0 at y = 0 (mod 0.048), MX at
    y = 0.042 (mod 0.048) (measured with check_macro_track_alignment); consecutive rows abut with a 0.012-0.024 um gap"""
    import math
    off = 0.0 if orient == "R0" else 0.042
    k = math.ceil(round((y_min - off) / 0.048, 6))
    return round(off + k * 0.048, 3)


def macro_xs(W, n):
    """n macros per row on the 0.432 macro lattice, >= 20.088 apart and >= E from the die edge, spread evenly"""
    g = (W - 2 * E - n * MW) / (n - 1)
    assert g >= 20.088, (W, n, g)
    xs = [up(E + i * (MW + g), 0.432) for i in range(n)]
    assert xs[-1] + MW <= W - E + 1e-6 and all(b - a - MW >= 20.0 for a, b in zip(xs, xs[1:])), xs
    return xs


def up(v, g):
    import math
    return round(math.ceil(round(v / g, 6)) * g, 4)


def plan(name, tag, W, ncol, rows, gl, gm, e_bot, e_top, purpose):
    """rows: bank layout per macro row, bottom (next to the lanes) first: list of (p, b) tuples"""
    s = copy.deepcopy(json.loads(BASE.read_text()))
    s["name"] = name
    s["top"] = "qfd_tile_nk_rp1"
    xs = [up(E + NW_ + 20.088, CL)]                            # lane column 0 (pins W -> node channel)
    for _ in range(ncol - 1):
        xs.append(up(xs[-1] + LW + 20.088, CL))
    assert xs[-1] + LW <= W - E + 1e-6, (W, xs)
    nrow = 3 if ncol == 3 else 4
    ya = up(e_bot, CL)
    yr = [ya]
    for _ in range(nrow - 1):
        yr.append(up(yr[-1] + LH + gl, CL))
    lanes_top = yr[-1] + LH
    ym = up(lanes_top + gm, 2.16)
    ny = up(ya + (lanes_top - ya - NH) / 2, CL)
    if ncol == 3:   # column 0 = lsl 0..2 (top..bottom), column 1 = 3..5, column 2 = 6, 7 (bottom); top-right slot = glue
        slots = {0: (0, 2), 1: (0, 1), 2: (0, 0), 3: (1, 2), 4: (1, 1), 5: (1, 0), 6: (2, 1), 7: (2, 0)}
    else:           # 2 x 4 as qfd_tile_nk_native: column 0 = lsl 0..3, column 1 = 4..7 (top..bottom); E strip = glue
        slots = {k: (k // 4, 3 - k % 4) for k in range(8)}
    children = [{"view": LSL, "count": 1, "inst": INST_LSL.format(k=k), "at": [xs[c], yr[r]], "orient": "MY"}
                for k, (c, r) in sorted(slots.items())]
    children.insert(0, {"view": NODE, "count": 1, "inst": INST_NODE, "at": [E, ny], "orient": "R0"})
    macros = []
    y = ym
    for r, row in enumerate(rows):
        xr = macro_xs(W, len(row))
        orient = "R0" if r % 2 == 0 else "MX"
        y = row_y(y if r == 0 else y + MH, orient)
        for (p, b), x in zip(row, xr):
            k = p * 5 + b
            macros.append({"view": ROM, "count": 1, "inst": INST_ROM.format(p=p, b=b), "at": [x, y], "at_exact": True,
                           "orient": orient,
                           "clock_entry": {"port": f"ck_rom{k}", "pin": "clk", "reference": "raw_liberty_clock_pin"}})
    H = up(y + MH + e_top, 2.16)
    assert sorted((m["inst"]) for m in macros) == sorted(INST_ROM.format(p=p, b=b) for p in (0, 1) for b in range(5))
    roots = ["ck"] + [f"ck_rp{b}" for b in range(5)]
    entries_child = [f"ck_lsl{k}" for k in range(8)] + ["ck_node"]
    s["clock_ports"] = roots + [f"ck_rom{k}" for k in range(10)] + entries_child
    s["clock_port"] = "ck"
    s["clock_cts_roots"] = roots
    hc = s["required_hybrid_roots"]["hard_child_entry"]
    s["required_hybrid_roots"] = {"standard_cell_cts": roots,
                                  "hard_child_entry": {k: v for k, v in hc.items() if not k.startswith("ck_rp")}}
    s["sources"] = [f for f in s["sources"] if f not in ("rtl/physical/bb/ot_qwen_tile_rpair_bb.v",
                                                        "rtl/physical/qfd_tile_nk_slot.sv")] + ["rtl/physical/qfd_tile_nk_rp1.sv"]
    s["children"] = children
    s["macros"] = macros
    s["outline"] = {"w": W, "h": H, "exact": True}
    # faces: die tree on W at the node's pin rows; issue tap + strap on E beside the glue slot (top right lane slot);
    # every clock on N (the macro block / soft roots); the die re-derives the column pins from this plan.
    tap_lo = yr[-1] + 30.0
    s["pins"] = {"W": ["n_a", "n_b", "t_out", "n_y"],
                 "E": ["tie_lo", "tie_hi", "tile_id", "rst_n", "tap"],
                 "N": s["clock_ports"]}
    s["pin_ranges"] = {
        "n_a": [round(ny + 10.9, 3), round(ny + 110.2, 3)],
        "n_b": [round(ny + 111.5, 3), round(ny + 210.8, 3)],
        "t_out": [round(ny + 212.0, 3), round(ny + 311.3, 3)],
        "n_y": [round(ny + 312.5, 3), round(ny + 411.8, 3)],
        "tie_lo": [round(tap_lo - 8.0, 3), round(tap_lo - 7.0, 3)],    # pin regions need HIGH > LOW
        "tie_hi": [round(tap_lo - 6.5, 3), round(tap_lo - 5.5, 3)],
        "tile_id": [round(tap_lo - 5.0, 3), round(tap_lo - 2.0, 3)],
        "rst_n": [round(tap_lo - 1.5, 3), round(tap_lo - 0.5, 3)],
        "tap": [round(tap_lo, 3), round(tap_lo + 48.672, 3)],
        "ck": [round(W / 2 - 0.5, 3), round(W / 2 + 0.5, 3)],
    }
    s.pop("io_tcl", None)
    s["structural_change"] = (
        "Q-TILE-REPACK: ROM macros placed directly in the tile (RPH 1, soft bank rows on local CTS roots ck_rp0..4, "
        "10 raw macro clock entries ck_rom0..9) instead of 5 closed rpair leaves (311 x 130 um each); lanes 3 x 3 grid, "
        "macro block abutted rows; same die ports/values/edges as qfd_tile_nk; die adopts under the name qfd_tile_nk.")
    s["slot_change_request"] = (f"qfd_tile_nk outline 449.28 x 1442.88 -> {W} x {H} (Q-TILE-REPACK {tag}); clock pins "
                                "ck_rp0..4 become CTS roots, +ck_rom0..9 raw macro entries; W tree pins move to the node rows")
    job = s["job"]
    job.update({"owner": "Claude:q_tile_repack", "branch": "claude/qtile-repack-1015", "tag": tag, "purpose": purpose,
                "views_to": f"physical/ref_tile/{name}/views", "record_to": f"results/rtl/ref_tile/{name}"})
    job.pop("benches_from", None)
    job["extra_paths"] = ["rtl/test/tb_qfd_tile_nk_rp1.sv", "tools/rtl_qwen_me_partition_gate_w12.py",
                          "tools/qwen_blocks/ot_hdc_matvec_0e8df511.sv"]
    r5 = json.loads((ROOT / "tools/ref_tile/specs_qtile_r5/qfd_tile_nk_r5_benches.json").read_text())["benches"]
    keep = {"r5_rom_pipe_exact", "r5_rom_pipe_tmut3", "r5_rpair_seam_tmut5"}
    face = "rtl/test/tb_qfd_tile_nk_rp1.sv rtl/physical/qfd_tile_nk_rp1.sv rtl/physical/ot_qwen_rom_tile_nk.sv"
    job["benches"] = [
        {"name": "rp1_face_exact",
         "cmd": "mkdir -p {RUN}/bench && iverilog -g2012 -s tb_qfd_tile_nk_rp1 -o {RUN}/bench/rp1_exact " + face
                + " && vvp -n {RUN}/bench/rp1_exact",
         "expect": "pass", "threads": 1, "peak_ram_gb": 1, "needs": ["iverilog"],
         "pass_regex": "^PASS qfd_tile_nk_rp1 checks=4000"},
        {"name": "rp1_face_mutant",
         "cmd": "mkdir -p {RUN}/bench && iverilog -g2012 -DOT_QFD_TILE_NK_RP1_MUT -s tb_qfd_tile_nk_rp1 -o "
                "{RUN}/bench/rp1_mutant " + face + " && vvp -n {RUN}/bench/rp1_mutant",
         "expect": "fail", "threads": 1, "peak_ram_gb": 1, "needs": ["iverilog"],
         "fail_regex": "^FAIL qfd_tile_nk_rp1 checks=4000"},
    ] + [b for b in r5 if b["name"] in keep]
    return s, H


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    b = lambda p, *bs: [(p, x) for x in bs]
    # P1 (minimum): rows of 3, 3, 2, 2 macros; each bank's two macros side by side, bank 1 split over rows 0 / 1 (same x)
    r3322 = [[(0, 0), (1, 0), (0, 1)], [(0, 2), (1, 2), (1, 1)], [(0, 3), (1, 3)], [(0, 4), (1, 4)]]
    r22222 = [[(0, k), (1, k)] for k in range(5)]
    plans = [
        # A: 3 lane columns + node need 452.1 um and a row of 3 macros 449.8 um (>= 20 um channels, 22.16 um from the
        # die edge) -> both exceed today's 449.28 column pitch; 457.92 is the next 8.64 um cluster lattice width.
        ("qfd_tile_nk_rp1_a1", "a1", 457.92, 3, r3322, 20.088, 20.088, E, E,
         "Re-pack minimum (die column +8.64 um): 3x3 lane grid, every channel at 20 um, 4 abutted macro rows (3,3,2,2)"),
        ("qfd_tile_nk_rp1_a2", "a2", 457.92, 3, r3322, 30.24, 34.56, 25.92, 25.92,
         "Re-pack middle (die column +8.64 um): 30-35 um channels for the soft bank rows, 4 abutted macro rows (3,3,2,2)"),
        # B: today's width: 2 lane columns x 4 rows + node, 2 macros per row (5 abutted rows, one bank each)
        ("qfd_tile_nk_rp1_b1", "b1", 449.28, 2, r22222, 20.088, 20.088, E, E,
         "Re-pack at today's 449.28 column: 2x4 lane grid + E glue strip, 5 abutted macro rows (one bank each)"),
    ]
    for name, tag, W, ncol, rows, gl, gm, eb, et, purpose in plans:
        s, H = plan(name, tag, W, ncol, rows, gl, gm, eb, et, purpose)
        (OUT / f"{name}.json").write_text(json.dumps(s, indent=1) + "\n")
        print(f"{name}: {W} x {H} um = {W * H / 1e3:.1f}k um2; real-area fill at 173.0k = {173.0e3 / (W * H) * 100:.1f} %")


if __name__ == "__main__":
    main()
