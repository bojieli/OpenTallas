#!/usr/bin/env python3
"""ASAP7 via-programmed NOR mask-ROM compiler, and the per-instance personalisation.

A ROM macro has two independent halves, exactly as a mask ROM is built:

* the **macro** (``compile``): bit array, row decoder and wordline drivers,
  column multiplexer, single-ended sense amplifiers, output latches.  Every
  cell carries its transistor; only the drain via differs.  LEF, Liberty and
  the behavioural model therefore do not depend on the content at all -- the
  Liberty is characterised with every via present (the heaviest bitline), so
  one set of views serves every personalisation;
* the **personalisation** (``personalise``): the per-instance via map (one bit
  per physical cell, ``1`` = via present = stored ``1``), optionally SECDED
  encoded, with its SHA-256 and the CRC-32 signature the ROM BIST must
  reproduce from the array.  For the V4.1 universal die this is the per-die
  content signature: the same macro views, a different via map and signature
  per die.

Views written under ``--out/<name>/``: ``<name>.lef``, ``<name>_{tt,ss,ff}.lib``,
``<name>.v`` (loads ``<dir>/<INSTANCE>.viamap.hex`` given ``+OT_ROM_DIR=<dir>``,
or the ``VIAMAP`` parameter), ``<name>_bb.v`` and ``<name>.json``.

    python3 tools/mem_compiler/rom_gen.py compile --config configs/memories/asap7_macros.json \\
        --out physical/asap7_memory_macros
    python3 tools/mem_compiler/rom_gen.py personalise --macro physical/asap7_memory_macros/X/X.json \\
        --image data.hex --data-bits 256 --ecc secded --instance-prefix wrom --out <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asap7  # noqa: E402
import behav  # noqa: E402
import ecc  # noqa: E402
from views import Pin, Timing, blackbox_verilog, macro_outline, write_lef, write_liberty  # noqa: E402

GENERATOR_VERSION = "1.0"
ROOT = asap7.ROOT


@dataclass
class RomSpec:
    name: str
    words: int
    bits: int
    mux: int = 8

    def validate(self) -> None:
        if self.mux not in (1, 2, 4, 8, 16, 32):
            raise ValueError(f"{self.name}: column mux must be a power of two up to 32")
        if self.words % self.mux or self.words // self.mux < 2:
            raise ValueError(f"{self.name}: words must be a multiple of mux with at least two rows")

    @property
    def rows(self) -> int:
        return self.words // self.mux

    @property
    def cols(self) -> int:
        return self.bits * self.mux

    @property
    def addr_bits(self) -> int:
        return behav._clog2(self.words)


ROM_ASSUMED = {
    "tap_band_um": {"value": 0.27, "grade": "assumed",
                    "note": "one standard-cell row of well/substrate taps every tap_every_rows rows; the IHP "
                            "130 nm ROM route found a minimum-pitch array illegal without them "
                            "(results/spice/ihp_sg13g2_rom_macro/REPORT.md)"},
    "tap_every_rows": {"value": 128, "grade": "assumed", "note": "tap band spacing"},
    "decoder_per_row_bit_um": {"value": 0.40, "grade": "assumed", "note": "predecode + NOR decode + WL driver"},
    "column_per_mux_bit_um": {"value": 0.45, "grade": "assumed", "note": "one more column-mux level"},
}


def pins_for(spec: RomSpec) -> list[Pin]:
    return [Pin("clk", 1, "input", "clock"), Pin("ce_in", 1, "input", "control"),
            Pin("addr_in", spec.addr_bits, "input", "control"), Pin("rd_out", spec.bits, "output", "data_out")]


def area_model(spec: RomSpec) -> dict[str, Any]:
    cell = asap7.bitcells()["rom_via"]
    g = asap7.ASSUMED["periphery_geometry_um"]["value"]
    array_w = spec.cols * cell["col_pitch_um"]
    taps = math.ceil(spec.rows / ROM_ASSUMED["tap_every_rows"]["value"])
    array_h = spec.rows * cell["row_pitch_um"] + taps * ROM_ASSUMED["tap_band_um"]["value"]
    dec_w = g["rom_decoder_fixed"] + ROM_ASSUMED["decoder_per_row_bit_um"]["value"] * math.log2(spec.rows)
    col_h = g["rom_column_fixed"] + ROM_ASSUMED["column_per_mux_bit_um"]["value"] * math.log2(spec.mux)
    return {
        "cell_area_um2": cell["area_um2"], "cell_col_pitch_um": cell["col_pitch_um"],
        "cell_row_pitch_um": cell["row_pitch_um"], "array_width_um": array_w, "array_height_um": array_h,
        "tap_bands": taps, "data_array_area_um2": spec.words * spec.bits * cell["area_um2"],
        "physical_array_area_um2": array_w * array_h, "decoder_width_um": dec_w, "column_height_um": col_h,
        "core_width_um": array_w + dec_w, "core_height_um": array_h + col_h,
    }


def timing_model(spec: RomSpec, area: dict[str, Any], cal: dict[str, Any], corner: str) -> Timing:
    c = cal["corners"][corner]
    tt = cal["corners"]["tt"]
    fo4 = c["fo4_ps"]
    k = asap7.ASSUMED["periphery_fo4_budget"]["value"]
    v = c["voltage_v"]
    cg_fin = asap7.gate_cap_per_fin_ff(cal)
    r_m2, c_m2 = asap7.SETRC["M2"]
    r_m1, c_m1 = asap7.SETRC["M1"]
    # wordline: every cell has its gate whatever it stores -> content-independent load
    wl_len = area["array_width_um"]
    c_wl = wl_len * c_m2 + spec.cols * cg_fin
    r_wl = wl_len * r_m2
    drive = min(8.0, max(1.0, c_wl / (16.0 * c["inv4_cin_ff"])))
    t_wl = c["inv4_r_kohm"] / drive * c_wl + 0.38 * r_wl * c_wl
    if spec.cols > 512:
        t_wl = c["inv4_r_kohm"] / drive * c_wl + 0.38 * r_wl * c_wl / 4.0  # centre-driven wordline
    # bitline: characterised with EVERY via present (the heaviest content), so the
    # timing view holds for any personalisation
    c_bl = spec.rows * (area["cell_row_pitch_um"] * c_m1 + asap7.ASSUMED["drain_cap_per_cell_ff"]["value"])
    i_cell = asap7.ASSUMED["rom_cell_read_current_ua"]["value"] * tt["fo4_ps"] / fo4
    dv = asap7.ASSUMED["rom_sense_swing_v"]["value"]
    t_bl = c_bl * dv / i_cell * 1000.0
    t_ctrl = k["clock_and_latch"] * fo4
    t_dec = (k["decoder_fixed"] + k["decoder_per_address_bit"] * math.log2(spec.rows)) * fo4
    t_mux = k["mux_per_level"] * math.log2(spec.mux) * fo4
    t_sa = k["sense"] * fo4
    t_out = k["output"] * fo4
    out_r = c["inv4_r_kohm"] / 2.0
    clk_q = t_ctrl + t_dec + t_wl + t_bl + t_mux + t_sa + t_out + out_r * 0.72
    t_pre = k["precharge"] * fo4 + 0.69 * (c["inv4_r_kohm"] / 2.0) * c_bl
    period = t_ctrl + t_dec + t_wl + t_bl + t_sa + t_pre
    e_wl = c_wl * v * v
    e_dec = 20.0 * cg_fin * v * v * math.log2(spec.rows)
    e_per = asap7.ASSUMED["periphery_energy_ff_per_bit"]["value"] * spec.bits * v * v
    e_bl_all = spec.cols * c_bl * v * dv            # every bitline of the row discharging (all vias)
    leak = asap7.tech_value("power.static_leakage_w_per_mm2.rom_array") * area["macro_area_um2"] * 1e3
    return Timing(
        corner=corner, voltage=v, temperature=c["temperature_c"], clk_to_q_ps=clk_q, out_r_kohm=out_r,
        out_slew_intrinsic_ps=1.5 * fo4, setup_ps=c["dff_setup_ps"] + fo4, hold_ps=c["dff_hold_ps"] + 0.5 * fo4,
        min_period_ps=period, min_pulse_ps=0.4 * period, read_energy_fj=e_wl + e_dec + e_bl_all + e_per,
        write_energy_fj=0.0, leakage_nw=leak, pin_cap_ff=c["inv1_cin_ff"], clk_cap_ff=4 * c["inv4_cin_ff"],
        breakdown={"control_ps": t_ctrl, "decode_ps": t_dec, "wordline_ps": t_wl, "bitline_ps": t_bl,
                   "column_mux_ps": t_mux, "sense_ps": t_sa, "output_ps": t_out, "precharge_ps": t_pre,
                   "wordline_cap_ff": c_wl, "bitline_cap_ff": c_bl, "cell_current_ua": i_cell, "fo4_ps": fo4,
                   "read_energy_fixed_fj": e_wl + e_dec + e_per,
                   "read_energy_per_discharging_bitline_fj": c_bl * v * dv})


def behavioural(spec: RomSpec, pins: list[Pin], header: str) -> str:
    params = {"WORDS": spec.words, "BITS": spec.bits, "MUX": spec.mux, "AW": spec.addr_bits,
              "ROWS": spec.rows, "NSR": 0, "NSC": 0, "PR": spec.rows, "PC": spec.cols,
              "RA": behav._clog2(spec.rows), "CB": behav._clog2(spec.bits)}
    body = [
        "    // The array IS the via mask: arr[row][col] = 1 where the drain via is present.",
        "    reg [PC-1:0] arr [0:PR-1];",
        "    reg [8*1024-1:0] rom_dir;",
        "    integer init_i;",
        "    initial begin",
        "        for (init_i = 0; init_i < PR; init_i = init_i + 1) arr[init_i] = {PC{1'b0}};",
        "        if ($value$plusargs(\"OT_ROM_DIR=%s\", rom_dir) && INSTANCE != \"\")",
        "            $readmemh({rom_dir, \"/\", INSTANCE, \".viamap.hex\"}, arr);",
        "        else if (VIAMAP != \"\")",
        "            $readmemh(VIAMAP, arr);",
        "    end",
        behav.FAULT_BLOCK, behav.HELPERS,
        "    always @(posedge clk)",
        "        if (ce_in) rd_out <= word_read(addr_in);",
    ]
    return behav.module_text(spec.name, pins, params, "\n".join(body) + "\n", header, 0, 0,
                             module_params='#(parameter string VIAMAP = "", parameter string INSTANCE = "") ')


def analytical_comparison(sheet: dict[str, Any]) -> dict[str, Any]:
    """The compiled macro against the analytical model's ROM constants (configs/hardware/technology.json)."""
    sys.path.insert(0, str(ROOT / "src"))
    from opentallas.roofline import Technology  # noqa: E402
    tech = Technology.load(asap7.TECH_JSON)
    out: dict[str, Any] = {}
    for node in ("N7",):
        bits_mm2 = tech.rom_bits_per_mm2(node).value
        bw = tech.rom_read_bytes_s_per_mm2(node).value
        sram_bits = tech.sram_bits_per_mm2(node).value
        macro_bits_mm2 = sheet["area"]["density_mb_per_mm2"] * 1e6
        macro_bw = sheet["read_bandwidth_bytes_s_tt"] / (sheet["area"]["macro_area_um2"] * 1e-6)
        out[node] = {
            "model_rom_bits_per_mm2": bits_mm2, "macro_rom_bits_per_mm2": macro_bits_mm2,
            "density_ratio_macro_over_model": macro_bits_mm2 / bits_mm2,
            "model_rom_read_bytes_s_per_mm2": bw, "macro_rom_read_bytes_s_per_mm2": macro_bw,
            "bandwidth_ratio_macro_over_model": macro_bw / bw,
            "model_sram_bits_per_mm2": sram_bits,
            "model_rom_cell_to_sram_cell_ratio": tech.graded("rom", "cell_to_sram_cell_area_ratio").value,
            "measured_asap7_rom_cell_to_sram_cell_ratio":
                asap7.bitcells()["rom_via"]["area_um2"] / asap7.bitcells()["sram_6t"]["area_um2"],
            "model_rom_array_efficiency": tech.graded("rom", "array_efficiency").value,
            "macro_array_efficiency": sheet["area"]["array_efficiency"],
        }
    return out


def compile_macro(spec: RomSpec, out_dir: Path | None = None) -> dict[str, Any]:
    spec.validate()
    cal = asap7.calibration()
    pins = pins_for(spec)
    area = area_model(spec)
    w, h, info = macro_outline(area["core_width_um"], area["core_height_um"], pins)
    area.update({"macro_width_um": w, "macro_height_um": h, "macro_area_um2": w * h, "outline": info})
    bits_total = spec.words * spec.bits
    area["array_efficiency"] = area["data_array_area_um2"] / area["macro_area_um2"]
    area["density_mb_per_mm2"] = bits_total / area["macro_area_um2"]
    corners = {c: timing_model(spec, area, cal, c) for c in asap7.CORNERS}
    tt = corners["tt"]
    header = (f"{spec.name}: ASAP7 via-programmed NOR mask ROM {spec.words} x {spec.bits}, mux {spec.mux}; "
              f"layout and timing content-independent; OpenTallas tools/mem_compiler/rom_gen.py v{GENERATOR_VERSION}")
    sheet: dict[str, Any] = {
        "schema": "opentallas.mem-compiler.rom.v1",
        "generator": f"tools/mem_compiler/rom_gen.py v{GENERATOR_VERSION}",
        "kind": "rom",
        "spec": asdict(spec),
        "physical": {"rows": spec.rows, "columns": spec.cols,
                     "column_interleave": "data bit b, column select s -> physical column b*mux + s",
                     "via_polarity": "via present = stored 1"},
        "area": area,
        "capacity_bits": bits_total,
        "timing": {c: asdict(t) for c, t in corners.items()},
        "fmax_mhz": {c: 1e6 / t.min_period_ps for c, t in corners.items()},
        "read_bandwidth_bytes_s_tt": spec.bits / 8.0 * 1e12 / tt.min_period_ps,
        "content_independence": {
            "lef": "no content in the abstract: every cell has its transistor, only the drain via differs",
            "liberty": "characterised with every via present (heaviest bitline and largest read energy)",
            "read_energy_depends_on_content": "only through the discharging bitlines: fixed part "
                                              f"{tt.breakdown['read_energy_fixed_fj']:.1f} fJ + "
                                              f"{tt.breakdown['read_energy_per_discharging_bitline_fj']:.3f} fJ "
                                              "per programmed cell on the accessed row (TT)",
        },
        "calibration": {"bitcells": asap7.bitcells(), "assumed": {**asap7.ASSUMED, **ROM_ASSUMED},
                        "stdcell": {"image_id": cal.get("image_id"),
                                    "file": "tools/mem_compiler/asap7_calibration.json"}},
        "claim_boundary": "abstract views from an analytical model on the measured DRC-clean ASAP7 ROM bitcell "
                          "and ASAP7 standard-cell FO4; periphery dimensions and cell current are assumed; "
                          "no transistor layout or SPICE of the macro; not silicon",
    }
    sheet["analytical_model_comparison"] = analytical_comparison(sheet)
    if out_dir is not None:
        d = out_dir / spec.name
        d.mkdir(parents=True, exist_ok=True)
        props = {"width": spec.bits, "depth": spec.words, "banks": 1}
        (d / f"{spec.name}.lef").write_text(write_lef(spec.name, w, h, pins, props))
        mem = {"type": "rom", "address_width": spec.addr_bits, "word_width": spec.bits}
        for c, t in corners.items():
            (d / f"{spec.name}_{c}.lib").write_text(write_liberty(spec.name, t, pins, w * h, mem, header))
        (d / f"{spec.name}.v").write_text(behavioural(spec, pins, "// " + header))
        (d / f"{spec.name}_bb.v").write_text(blackbox_verilog(spec.name, pins, header))
        files = sorted(p.name for p in d.iterdir() if p.name != f"{spec.name}.json")
        sheet["views"] = {f: asap7.sha256_file(d / f) for f in files}
        (d / f"{spec.name}.json").write_text(json.dumps(sheet, indent=2, sort_keys=True) + "\n")
    return sheet


# ---------------------------------------------------------------------------
# personalisation
# ---------------------------------------------------------------------------

def via_map(spec: RomSpec, words: list[int]) -> list[int]:
    """Physical rows (column c is bit c) of the via mask for ``words`` codewords."""
    if len(words) > spec.words:
        raise ValueError(f"{len(words)} words do not fit {spec.name} ({spec.words})")
    rows = [0] * spec.rows
    for a, w in enumerate(words):
        r, s = divmod(a, spec.mux)
        acc = rows[r]
        b = 0
        while w:
            if w & 1:
                acc |= 1 << (b * spec.mux + s)
            w >>= 1
            b += 1
        rows[r] = acc
    return rows


def read_back(spec: RomSpec, rows: list[int]) -> list[int]:
    out = []
    for a in range(spec.words):
        r, s = divmod(a, spec.mux)
        row = rows[r] >> s
        w = 0
        for b in range(spec.bits):
            if (row >> (b * spec.mux)) & 1:
                w |= 1 << b
        out.append(w)
    return out


def personalise_instance(spec: RomSpec, words: list[int], instance: str, out_dir: Path) -> dict[str, Any]:
    rows = via_map(spec, words)
    digits = (spec.cols + 3) // 4
    text = "".join(f"{r:0{digits}x}\n" for r in rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{instance}.viamap.hex"
    path.write_text(text)
    full = list(words) + [0] * (spec.words - len(words))
    vias = sum(bin(r).count("1") for r in rows)
    rec = {
        "instance": instance, "macro": spec.name, "viamap": path.name,
        "viamap_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "signature_crc32": f"{ecc.signature_fast(full, spec.bits):08x}",
        "signature_definition": "tools/mem_compiler/ecc.py: CRC-32 0x04C11DB7, init 0xFFFFFFFF, every word of "
                                "the macro in address order, LSB first",
        "words_programmed": len(words), "vias_present": vias,
        "via_density": vias / (spec.rows * spec.cols),
    }
    return rec


def die_signature(records: list[dict[str, Any]]) -> str:
    """The per-die content signature: CRC-32 over every instance signature, in instance-name order.

    On the V4.1 universal die every die carries the same macros and a different
    via mask; the die signature is what the ROM BIST results must fold to for
    that die, and the SHA-256 of the sorted via-map hashes pins the mask set.
    """
    words = [int(r["signature_crc32"], 16) for r in sorted(records, key=lambda r: r["instance"])]
    return f"{ecc.signature(words, 32):08x}"


def read_hex(path: Path) -> list[int]:
    return [int(line.split("//")[0], 16) for line in path.read_text().split() if line.strip()]


def tile_image(image: list[int], data_bits: int, spec: RomSpec, tile_data_bits: int,
               ecc_kind: str) -> dict[tuple[int, int], list[int]]:
    """Split a logical image (``data_bits`` per word) into macro tiles of ``tile_data_bits``.

    Tile (row, col) holds words [row*spec.words, ...) and data bits
    [col*tile_data_bits, ...).  With SECDED each tile word is encoded, and the
    macro must be ``codeword_bits(tile_data_bits)`` wide.
    """
    if data_bits % tile_data_bits:
        raise ValueError("data width must be a multiple of the tile data width")
    want = ecc.codeword_bits(tile_data_bits) if ecc_kind == "secded" else tile_data_bits
    if spec.bits != want:
        raise ValueError(f"macro {spec.name} is {spec.bits} bits, the tile needs {want}")
    ncol = data_bits // tile_data_bits
    nrow = max(1, math.ceil(len(image) / spec.words))
    mask = (1 << tile_data_bits) - 1
    tiles: dict[tuple[int, int], list[int]] = {}
    for r in range(nrow):
        chunk = image[r * spec.words:(r + 1) * spec.words]
        for c in range(ncol):
            ws = [(w >> (c * tile_data_bits)) & mask for w in chunk]
            if ecc_kind == "secded":
                ws = [ecc.encode(w, tile_data_bits) for w in ws]
            tiles[(r, c)] = ws
    return tiles


def spec_from_sheet(path: Path) -> RomSpec:
    return RomSpec(**json.loads(path.read_text())["spec"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("--config", type=Path)
    c.add_argument("--name")
    c.add_argument("--words", type=int)
    c.add_argument("--bits", type=int)
    c.add_argument("--mux", type=int, default=8)
    c.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("personalise")
    p.add_argument("--macro", type=Path, required=True, help="the macro's datasheet JSON")
    p.add_argument("--image", type=Path, required=True, help="logical image, one hex word per line")
    p.add_argument("--data-bits", type=int, required=True)
    p.add_argument("--tile-data-bits", type=int, default=None)
    p.add_argument("--ecc", choices=("none", "secded"), default="none")
    p.add_argument("--instance-prefix", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "compile":
        specs = []
        if args.config:
            specs = [RomSpec(**s) for s in json.loads(args.config.read_text()).get("rom", [])]
        if args.name:
            specs.append(RomSpec(args.name, args.words, args.bits, args.mux))
        for spec in specs:
            s = compile_macro(spec, args.out)
            a, t = s["area"], s["timing"]
            cmp_ = s["analytical_model_comparison"]["N7"]
            print(f"{spec.name}: {a['macro_width_um']:.2f} x {a['macro_height_um']:.2f} um, "
                  f"{a['density_mb_per_mm2']:.1f} Mb/mm2 (model {cmp_['model_rom_bits_per_mm2'] / 1e6:.1f}), "
                  f"eff {a['array_efficiency']:.3f}, clk->q {t['tt']['clk_to_q_ps']:.0f} ps, "
                  f"fmax tt {s['fmax_mhz']['tt']:.0f} MHz, "
                  f"BW ratio to model {cmp_['bandwidth_ratio_macro_over_model']:.3f}")
        return 0
    spec = spec_from_sheet(args.macro)
    image = read_hex(args.image)
    tile_bits = args.tile_data_bits or args.data_bits
    tiles = tile_image(image, args.data_bits, spec, tile_bits, args.ecc)
    recs = [personalise_instance(spec, ws, f"{args.instance_prefix}_r{r}_c{c}", args.out)
            for (r, c), ws in sorted(tiles.items())]
    manifest = {"schema": "opentallas.rom-personalisation.v1", "macro": spec.name, "ecc": args.ecc,
                "image": str(args.image), "image_sha256": asap7.sha256_file(args.image),
                "data_bits": args.data_bits, "tile_data_bits": tile_bits, "instances": recs,
                "content_signature": die_signature(recs),
                "viamap_set_sha256": hashlib.sha256("".join(
                    r["viamap_sha256"] for r in sorted(recs, key=lambda r: r["instance"])).encode()).hexdigest()}
    (args.out / f"{args.instance_prefix}.personalisation.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"{len(recs)} instance(s) of {spec.name} personalised under {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
