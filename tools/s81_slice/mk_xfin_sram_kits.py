#!/usr/bin/env python3
"""ELEM-XFV/XFIN 10-21: physical kits for the 93-SRAM ot_s81dv_xfin (opt-in OT_S81DV_XFIN_SRAM, RTL 2e42dda2a).

Writes two spec.json (then `ref_tile.py gen`):
  s81dv_xfin_s2  MAIN: 5 finish columns x 2 macro tiers (abutted N-S stacks of <=10 ot_sram_1r1w_32x64_m1), one central
                 macro-free E-W band (ring stop, adders, broadcast flits), std-cell bands between every pair of columns.
  s81dv_xfin_s3  FALLBACK: 5 finish columns x 3 tiers (stacks <=7), two macro-free E-W bands, wider bands (lower density).
One column per finish instance (W->E: g_cp[0], g_cp[1], u_f (NORM), g_cp[2], g_cp[3]); each column holds exactly that
instance's banks, internal-role banks next to a band.  The macros block M1-M4 (cap M5), so every E-W wire (ring W<->E,
dl_* broadcast to the 5 finishes, e_* to the W face) runs in the macro-free bands; ring pins are centred on them.
Ports / faces identical to s81dv_xfin_e2 (slice binding = master swap + new outline).
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/ref_tile"))
import ref_tile as RT  # noqa: E402

VIEW = "physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1"
MW, MH = 31.968, 17.28          # LEF; pins only on the W / E faces (M4) -> N-S abutment is legal (abutted_stack)
HALO = 5.4
G = 2.16
CM = RT.CORE_MARGIN
FIN = ["g_cp[0].u_e", "g_cp[1].u_e", "u_f", "g_cp[2].u_e", "g_cp[3].u_e"]   # W -> E
NB = {"u_f": 17}
EXTRA_SRC = ["rtl/dsrom_sys/s81_dv/ot_s81dv_fp_n32.sv", "rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv",
             VIEW + "/ot_sram_1r1w_32x64_m1_bb.v"]


def snap(v, g=G):
    return math.ceil(v / g - 1e-9) * g


def tiers_of(fin: str, nt: int) -> list[list[int]]:
    """bank lists per tier, S -> N.  ENG 19 = 15 leaf (port p, residue r -> bank 5p+r) + 4 internal (15..18); NORM 17."""
    n = NB.get(fin, 19)
    leaf, internal = list(range(15)), list(range(15, n))
    if nt == 2:
        # S tier: port-2 leaves bottom-up then the internal banks at the top (next to the central band)
        # N tier: ports 0/1 bottom-up (bank 0 next to the central band)
        return [leaf[10:] + internal, leaf[:10]]
    # 3 tiers: S = port 2 (5) + 1-2 internal at top, M = port 1 + internal, N = port 0 (+ rest)
    s = leaf[10:15] + internal[:1]
    m = leaf[5:10] + internal[1:3]
    nn = leaf[0:5] + internal[3:]
    return [s, m, nn]


def ranges(face_len: float, groups: list[tuple[str, int]], lo: float, hi: float) -> dict:
    """consecutive per-port ranges in [lo, hi] proportional to width, scalars >= 2.16 um"""
    tot = sum(max(w, 1) for _, w in groups)
    span = hi - lo
    out, y = {}, lo
    fixed = sum(G for _, w in groups if w * span / tot < G)
    scale = (span - fixed) / sum(w for _, w in groups if w * span / tot >= G)
    for p, w in groups:
        d = G if w * span / tot < G else w * scale
        out[p] = [round(y, 3), round(y + d, 3)]
        y += d
    assert y <= hi + 1e-6 and lo >= 0 and hi <= face_len
    return out


def build(base: dict, name: str, nt: int, band_y: float, col_gap: float, edge_x: float, edge_y: float, km: int,
          std_est: float, purpose: str, why: str) -> dict:
    s = copy.deepcopy(base)
    s["name"] = name
    s["sources"] = list(base["sources"]) + EXTRA_SRC
    s["defines"] = ["OT_S81DV_XFIN_SRAM"]
    tier_banks = [tiers_of(f, nt) for f in FIN]
    tier_n = [max(len(tb[t]) for tb in tier_banks) for t in range(nt)]
    probe = {"kind": "macro", "view": VIEW, "orient": "R0", "_tm": None}
    # geometry
    x0 = snap(CM + edge_x)
    xs = [round(x0 + i * snap(MW + col_gap, RT.GRID_X * 5), 3) for i in range(5)]
    W = snap(xs[-1] + MW + edge_x + CM)
    ys0, y = [], snap(CM + edge_y)
    for t in range(nt):
        ys0.append(y)
        y = snap(y + tier_n[t] * MH + band_y)
    H = snap(ys0[-1] + tier_n[-1] * MH + edge_y + CM)
    # put every stack origin on the M4 track lattice (same shift for all: stack pitch 17.28 = 360 M4 tracks)
    _, oy, off = RT.on_track(probe, xs[0], ys0[0])
    dy = round(oy - ys0[0], 3)
    macros = []
    for c, fin in enumerate(FIN):
        for t in range(nt):
            for k, bank in enumerate(tier_banks[c][t]):
                macros.append({"view": VIEW, "count": 1, "inst": "*" + f"{fin}.u_values.g_bank[{bank}].u_m".replace("[", "?").replace("]", "?"),
                               "at": [xs[c], round(ys0[t] + dy + k * MH, 3)], "orient": "R0", "at_exact": True})
    assert len(macros) == 93, len(macros)
    s["macros"] = macros
    s["outline"] = {"w": round(W, 3), "h": round(H, 3)}
    # pins: same faces as e2; ring + e_* centred on the macro-free band(s)
    bands = [(ys0[t] + tier_n[t] * MH, ys0[t + 1]) for t in range(nt - 1)]
    bc = sum((a + b) / 2 for a, b in bands) / len(bands)
    wl = [("wi_v", 1), ("wi_h", 4), ("wi_b", 8), ("wi_d", 160), ("wo_v", 1), ("wo_h", 4), ("wo_b", 8), ("wo_d", 160)]
    el = [("ei_v", 1), ("ei_h", 4), ("ei_b", 8), ("ei_d", 160), ("eo_v", 1), ("eo_h", 4), ("eo_b", 8), ("eo_d", 160)]
    pr = {}
    pr.update(ranges(H, wl, bc - 95.0, bc + 25.0))                       # 346 pins / 120 um = 2.9 / um
    pr.update(ranges(H, [("e_v", 1), ("e_c", 2), ("e_hh", 32), ("e_kk", 32), ("e_dd", 32)], bc + 30.0, bc + 80.0))
    pr.update(ranges(H, el, bc - 60.0, bc + 60.0))                       # 346 / 120 = 2.9 / um
    s["pin_ranges"] = pr
    # E-face ranges share names with W ranges? no: per-port, the face comes from spec pins
    s["pre_cts_extra"] = ["physical/common_flow/clock_split_km.tcl"]
    s["orfs_vars"] = {"OT_CKKM_K": str(km)}
    s["std_area_um2"] = std_est
    s.pop("std_area_um2_est", None)
    s.pop("util", None)
    s["route"] = dict(base["route"], threads=16, peak_ram_gb=64)
    s["outline_note"] = why
    s["structural_change"] = (
        "ELEM-XFV/XFIN 10-21: SAFE item 5 storage fix -- the 12 ENG + 1 NORM golden-heap value stores (~65.7k payload "
        "flops) move to 93 ot_sram_1r1w_32x64_m1 macros (source 2e42dda2a opt-in OT_S81DV_XFIN_SRAM, model 18f13c8ce, "
        "macro registered read replaces the a_q/b_q capture edge; LM5/LA6 tail unchanged).  " + why)
    j = s["job"]
    j["owner"] = "Claude:S81-ELEM/XFIN"
    j["branch"] = "claude/s81-xfin-sram-phys-1021"
    j["tag"] = name.split("_")[-1]
    j["purpose"] = purpose
    j["extra_paths"] = sorted(set(j["extra_paths"] + [VIEW, "tools/s81_slice/xfin_sram_bench.sh",
                                                     "rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv",
                                                     "results/rtl/s81_xfin_sram_1021"]))
    j["benches"] = sram_benches()
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    return s


def sram_benches() -> list:
    w = "results/rtl/s81_xfin_sram_1021"
    return [
        {"name": "dv_xfin16_sram_exact", "cmd": "bash tools/s81_slice/xfin_sram_bench.sh norm {RUN}/bench base xfin",
         "expect": "pass", "pass_regex": "^PASS dvxfin16$", "threads": 8, "peak_ram_gb": 64},
        {"name": "dv_xfin16_sram_mutbase", "cmd": "bash tools/s81_slice/xfin_sram_bench.sh norm {RUN}/mutb mutbase xfin",
         "expect": "fail", "fail_regex": "NEGATIVE_CONTROL_FAILED_AS_EXPECTED", "fail_witness": f"{w}/norm_mutbase.log",
         "threads": 8, "peak_ram_gb": 64},
        {"name": "dv_xfin16_sram_mutleaf", "cmd": "bash tools/s81_slice/xfin_sram_bench.sh norm {RUN}/mutl mutleaf xfin",
         "expect": "fail", "fail_regex": "NEGATIVE_CONTROL_FAILED_AS_EXPECTED", "fail_witness": f"{w}/norm_mutleaf.log",
         "threads": 8, "peak_ram_gb": 64},
        {"name": "dv_xfin16e_sram_exact", "cmd": "bash tools/s81_slice/xfin_sram_bench.sh eng {RUN}/eng base 0 0 1",
         "expect": "pass", "pass_regex": "^PASS dvxfin16e ", "threads": 8, "peak_ram_gb": 48},
        {"name": "dv_xfin16e_sram_mutetag", "cmd": "bash tools/s81_slice/xfin_sram_bench.sh eng {RUN}/etag mutetag",
         "expect": "fail", "fail_regex": "NEGATIVE_CONTROL_FAILED_AS_EXPECTED", "fail_witness": f"{w}/eng_mutetag.log",
         "threads": 8, "peak_ram_gb": 48},
        {"name": "dv_xfin16e_sram_muteassoc", "cmd": "bash tools/s81_slice/xfin_sram_bench.sh eng {RUN}/eass muteassoc",
         "expect": "fail", "fail_regex": "NEGATIVE_CONTROL_FAILED_AS_EXPECTED", "fail_witness": f"{w}/eng_muteassoc.log",
         "threads": 8, "peak_ram_gb": 48},
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--std-um2", type=float, required=True, help="std-cell area (native synth of 2e42dda2a)")
    a = ap.parse_args()
    base = json.loads((ROOT / "physical/ref_tile/s81dv_xfin_e2/spec.json").read_text())
    std = a.std_um2
    out = {}
    for name, nt, band0, gap0, edge_x, edge_y, km, dens, purpose in (
            ("s81dv_xfin_s2", 2, 64.8, 21.6, 30.24, 25.92, 16, 0.55,
             "xfin 93-SRAM MAIN: 5 finish columns x 2 abutted tiers, 1 central E-W band"),
            ("s81dv_xfin_s3", 3, 43.2, 36.72, 34.56, 25.92, 20, 0.45,
             "xfin 93-SRAM FALLBACK: 5 finish columns x 3 abutted tiers, 2 E-W bands, lower density")):
        # width <= 399.6 so the W->E ring pass-through (pin flop -> xstop -> pin flop, one registered hop) stays
        # <= 405 um: the widest column gap that fits, then grow the macro-free E-W band(s) (enlarge, never squeeze)
        def dens_of(band, gap):
            s = build(base, name, nt, band, gap, edge_x, edge_y, km, std, purpose, "")
            W, H = s["outline"]["w"], s["outline"]["h"]
            core = (W - 2 * CM) * (H - 2 * CM)
            foot = len(s["macros"]) * (MW + 2 * HALO) * (MH + 2 * HALO)   # gate metric (ref_tile.util_metrics)
            return s, W, H, core, foot, std / (core - foot)
        band, gap = band0, gap0
        while True:
            s, W, H, core, foot, d = dens_of(band, gap)
            if d <= dens:
                break
            if dens_of(band, gap + 2.16)[1] <= 399.6:
                gap += 2.16          # widen the std-cell bands first (width <= 399.6: ring hop < 405 um)
            else:
                band += 2.16         # then grow the macro-free E-W band(s): enlarge, never squeeze
        why = (f"{nt} tiers x 5 finish columns, abutted R0 stacks (pins W/E only), column gap {gap:.2f} um "
               f"(std-cell band), {'central band' if nt == 2 else 'two bands'} {band:.2f} um macro-free for every E-W wire; "
               f"outline {W} x {H}; std {std:.0f} um2 / placeable {core - foot:.0f} = {d:.2f}; KM {km} regional clock roots.")
        s = build(base, name, nt, band, gap, edge_x, edge_y, km, std, purpose, why)
        out[name] = s
        p = ROOT / "physical/ref_tile" / name
        p.mkdir(parents=True, exist_ok=True)
        (p / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print(name, why)


if __name__ == "__main__":
    main()
