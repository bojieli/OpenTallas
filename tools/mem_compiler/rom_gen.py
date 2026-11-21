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
    python3 tools/mem_compiler/rom_gen.py weights --spec spec.json --snapshot <safetensors dir> --out <dir>
    python3 tools/mem_compiler/rom_gen.py verify-weights --manifest <dir>/weights.manifest.json --snapshot <dir>

``weights`` / ``verify-weights`` (ROM-WEIGHTS-1119) carry released checkpoint bytes into the ROMs and read them back
from the physical via maps against the checkpoint (see the section "real checkpoint weights").
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
ROM_MODULE_PARAMS = '#(parameter string VIAMAP = "", parameter string INSTANCE = "") '
# The physical blackbox carries metadata only. Classic Yosys read_verilog accepts
# untyped string-valued parameters; typed string parameters require read_slang.
ROM_BLACKBOX_PARAMS = '#(parameter VIAMAP = "", parameter INSTANCE = "") '

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
                             module_params=ROM_MODULE_PARAMS)


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
        (d / f"{spec.name}_bb.v").write_text(blackbox_verilog(spec.name, pins, header, module_params=ROM_BLACKBOX_PARAMS))
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


def verify_personalisation(manifest_path: Path, image_path: Path | None = None,
                           macro_sheet: Path | None = None) -> dict[str, Any]:
    """Functional / LEC check of one content against its macro: the via maps ARE the content.

    For every instance of a personalisation manifest: the via-map file hashes to the recorded SHA-256, its read-back
    (the behavioural model's exact read path: physical row a // mux, column b * mux + a % mux) equals the tile of
    the logical image (SECDED-encoded when the manifest says so, and every codeword decodes clean), and the CRC-32
    BIST signature of the read-back equals the recorded one.  The content signature over all instances is
    recomputed.  This is equivalence of the generated ROM (macro + via layer) against the weight file, word by word.
    """
    man = json.loads(manifest_path.read_text())
    image_path = image_path or Path(man["image"])
    if asap7.sha256_file(image_path) != man["image_sha256"]:
        return {"verdict": "FAIL", "error": f"image {image_path} does not hash to the manifest image_sha256"}
    base = manifest_path.parent
    macro_json = macro_sheet if macro_sheet and Path(macro_sheet).exists() else None
    for cand in () if macro_json else (ROOT / "physical" / "asap7_memory_macros_v2" / man["macro"] / f"{man['macro']}.json",
                 ROOT / "physical" / "asap7_memory_macros" / man["macro"] / f"{man['macro']}.json"):
        if cand.exists():
            macro_json = cand
            break
    if macro_json is None:
        return {"verdict": "FAIL", "error": f"no datasheet for {man['macro']}"}
    spec = spec_from_sheet(macro_json)
    tiles = tile_image(read_hex(image_path), man["data_bits"], spec, man["tile_data_bits"], man["ecc"])
    prefix = manifest_path.name[:-len(".personalisation.json")]
    by_name = {f"{prefix}_r{r}_c{c}": ws for (r, c), ws in tiles.items()}
    bad, words_checked = [], 0
    for rec in man["instances"]:
        vm = base / rec["viamap"]
        text = vm.read_text()
        if hashlib.sha256(text.encode()).hexdigest() != rec["viamap_sha256"]:
            bad.append(f"{rec['instance']}: via map hash differs from the manifest")
            continue
        got = read_back(spec, [int(x, 16) for x in text.split()])
        want = by_name.get(rec["instance"])
        if want is None:
            bad.append(f"{rec['instance']}: no tile of the image maps to this instance")
            continue
        want = list(want) + [0] * (spec.words - len(want))
        diff = [a for a in range(spec.words) if got[a] != want[a]]
        if diff:
            bad.append(f"{rec['instance']}: {len(diff)} words differ from the image (first address {diff[0]})")
        if man["ecc"] == "secded":
            unclean = [a for a in range(rec["words_programmed"])
                       if ecc.decode(got[a], man["tile_data_bits"])[1] != "ok"]
            if unclean:
                bad.append(f"{rec['instance']}: {len(unclean)} codewords do not decode clean")
        if f"{ecc.signature_fast(got, spec.bits):08x}" != rec["signature_crc32"]:
            bad.append(f"{rec['instance']}: BIST signature differs")
        words_checked += spec.words
    sig = die_signature(man["instances"])
    if sig != man["content_signature"]:
        bad.append("content signature differs")
    return {"verdict": "FAIL" if bad else "PASS", "macro": man["macro"], "instances": len(man["instances"]),
            "words_checked": words_checked, "content_signature": sig, "errors": bad[:20]}


def spec_from_sheet(path: Path) -> RomSpec:
    return RomSpec(**json.loads(path.read_text())["spec"])


# ---------------------------------------------------------------------------
# real checkpoint weights (OWNER 11-19, ROM-WEIGHTS-1119: "ROMs must carry real qwen and deepseek weights")
# ---------------------------------------------------------------------------
#
# ``weights`` turns a weight spec (which released tensor slices go into which ROM instance, in which word order) into
# per-instance via maps, a logical image and a sha256 manifest.  Payload bytes are copied from the safetensors file
# unchanged (no arithmetic, no requantisation); a family whose contract quantises (Qwen W8) emits its own codes and
# hands them in as a ``codes`` tensor file of the same safetensors layout.  ``verify-weights`` is the independent
# read-back bench: for a deterministic sample of (instance, address, lane) it decodes the PHYSICAL via map the way the
# macro model reads it and compares the lane bytes with bytes read again from the checkpoint at the element's own file
# offset (it never uses the packer's stream).  Tails beyond the payload must read zero.
#
# Spec (JSON, schema opentallas.rom-weights-spec.v1):
#   {"macro": "<datasheet name or path>", "lane_bits": 16,
#    "checkpoint": {"repo": "...", "revision": "...", "index_sha256": "..."},     (optional pins, checked when given)
#    "roms": [{"instances": ["u_x_0", "u_x_1"],          ping-pong: physical word p lives in instance p % len, addr p // len
#              "skew": 0, "skew_mod": 8,                  physical word p, lane j = logical word (p - skew*(j % skew_mod)) mod N
#              "segments": [{"tensor": "head.weight", "row0": 0, "rows": 32, "col0": 0, "cols": 4096,
#                            "row_order": [optional list of row offsets, default 0..rows-1]}]}]}
# The logical stream is the segments' elements in row-major order, packed lane_bits per lane, lanes = data bits /
# lane_bits per word, padded with zero words to N = len(instances) * macro words.

SAFETENSORS_ITEM_BYTES = {"BF16": 2, "F16": 2, "F32": 4, "F64": 8, "I8": 1, "U8": 1, "I16": 2, "U16": 2, "I32": 4,
                          "U32": 4, "I64": 8, "F8_E4M3": 1, "F8_E5M2": 1, "F8_E8M0": 1}
WEIGHTS_SPEC_SCHEMA = "opentallas.rom-weights-spec.v1"
WEIGHTS_MANIFEST_SCHEMA = "opentallas.rom-weights.v1"


class Checkpoint:
    """A safetensors snapshot read without torch: index -> shard -> header -> raw element bytes at their file offset."""

    def __init__(self, snapshot: Path):
        self.dir = Path(snapshot)
        idx = self.dir / "model.safetensors.index.json"
        if idx.is_file():
            self.index_sha256 = asap7.sha256_file(idx)
            self.weight_map = json.loads(idx.read_text())["weight_map"]
        else:                                     # single-file checkpoint
            self.index_sha256 = None
            self.weight_map = None
        self._headers: dict[str, tuple[dict[str, Any], int, str]] = {}

    def _header(self, shard: str) -> tuple[dict[str, Any], int, str]:
        if shard not in self._headers:
            with (self.dir / shard).open("rb") as f:
                n = int.from_bytes(f.read(8), "little")
                raw = f.read(n)
            self._headers[shard] = (json.loads(raw), 8 + n, hashlib.sha256(raw).hexdigest())
        return self._headers[shard]

    def tensor(self, key: str) -> dict[str, Any]:
        shard = self.weight_map[key] if self.weight_map is not None else "model.safetensors"
        hdr, start, hsha = self._header(shard)
        rec = hdr[key]
        item = SAFETENSORS_ITEM_BYTES[rec["dtype"]]
        shape = list(rec["shape"])
        cols = shape[-1] if shape else 1
        rows = (math.prod(shape[:-1]) if len(shape) > 1 else 1)
        lo, hi = rec["data_offsets"]
        if (hi - lo) != rows * cols * item:
            raise ValueError(f"{key}: data_offsets disagree with shape {shape} x {item} B")
        return {"key": key, "shard": shard, "header_sha256": hsha, "dtype": rec["dtype"], "shape": shape,
                "rows": rows, "cols": cols, "item": item, "offset": start + lo}

    def read(self, t: dict[str, Any], row: int, col0: int, ncols: int) -> bytes:
        if not (0 <= row < t["rows"] and 0 <= col0 and col0 + ncols <= t["cols"]):
            raise ValueError(f"{t['key']}: slice row {row} cols {col0}+{ncols} outside {t['shape']}")
        with (self.dir / t["shard"]).open("rb") as f:
            f.seek(t["offset"] + (row * t["cols"] + col0) * t["item"])
            data = f.read(ncols * t["item"])
        if len(data) != ncols * t["item"]:
            raise ValueError(f"{t['key']}: truncated shard {t['shard']}")
        return data


def _weights_macro(spec_json: dict[str, Any], spec_path: Path) -> tuple[RomSpec, Path]:
    m = Path(spec_json["macro"])
    for cand in (m, spec_path.parent / m, ROOT / "physical/asap7_memory_macros_v2" / m.name / f"{m.name}.json"):
        if cand.suffix == ".json" and cand.is_file():
            return spec_from_sheet(cand), cand
    raise ValueError(f"no ROM datasheet for {spec_json['macro']}")


def _segment_rows(seg: dict[str, Any]) -> list[int | None]:
    """Row offsets in stream order; ``None`` is a zero (padding) row, e.g. an invalid row inside a permuted block."""
    order = seg.get("row_order")
    rows = list(range(seg["rows"])) if order is None else [None if r is None else int(r) for r in order]
    real = [r for r in rows if r is not None]
    if sorted(real) != list(range(seg["rows"])):
        raise ValueError("row_order must hold each of 0..rows-1 exactly once (None = zero row)")
    return rows


def weights_streams(ck: Checkpoint, rom: dict[str, Any], spec: RomSpec, lane_bits: int,
                    payload_bits: int) -> tuple[list[int], list[dict[str, Any]]]:
    """The logical word stream of one ROM entry (all its ping-pong instances), packed from raw checkpoint bytes."""
    usable = payload_bits // 8                              # data bytes a word carries (bits above stay 0)
    buf = bytearray()
    segs = []
    for seg in rom["segments"]:
        t = ck.tensor(seg["tensor"])
        if (t["item"] * 8) > lane_bits or lane_bits % (t["item"] * 8):
            raise ValueError(f"{t['key']}: {t['dtype']} elements do not tile {lane_bits}-bit lanes")
        h = hashlib.sha256()
        for r in _segment_rows(seg):
            if r is None:
                buf += bytes(seg["cols"] * t["item"])
                continue
            data = ck.read(t, seg["row0"] + r, seg.get("col0", 0), seg["cols"])
            h.update(data)
            buf += data
        segs.append({"tensor": t["key"], "shard": t["shard"], "shard_header_sha256": t["header_sha256"],
                     "dtype": t["dtype"], "shape": t["shape"], "row0": seg["row0"], "rows": seg["rows"],
                     "col0": seg.get("col0", 0), "cols": seg["cols"], "row_order": seg.get("row_order"),
                     "source_bytes_sha256": h.hexdigest()})
    n_words = len(rom["instances"]) * spec.words
    if len(buf) > n_words * usable:
        raise ValueError(f"{rom['instances']}: {len(buf)} payload bytes exceed {n_words} words x {usable} B")
    buf += bytes(n_words * usable - len(buf))
    return [int.from_bytes(buf[w * usable:(w + 1) * usable], "little") for w in range(n_words)], segs


def physical_words(logical: list[int], lanes: int, lane_bits: int, skew: int, skew_mod: int) -> list[int]:
    """Physical word p, lane j = lane j of logical word (p - skew * (j mod skew_mod)) mod N."""
    if not skew:
        return list(logical)
    n, mask = len(logical), (1 << lane_bits) - 1
    out = []
    for p in range(n):
        w = 0
        for j in range(lanes):
            w |= ((logical[(p - skew * (j % skew_mod)) % n] >> (j * lane_bits)) & mask) << (j * lane_bits)
        out.append(w)
    return out


def weights_build(spec_path: Path, snapshot: Path, out: Path) -> dict[str, Any]:
    spec_path = Path(spec_path)
    sj = json.loads(spec_path.read_text())
    if sj.get("schema", WEIGHTS_SPEC_SCHEMA) != WEIGHTS_SPEC_SCHEMA:
        raise ValueError(f"unknown spec schema {sj.get('schema')}")
    spec, sheet = _weights_macro(sj, spec_path)
    lane_bits = int(sj.get("lane_bits", 16))
    payload_bits = int(sj.get("payload_bits", (spec.bits // lane_bits) * lane_bits))
    if payload_bits % lane_bits or payload_bits > spec.bits or payload_bits % 8:
        raise ValueError(f"payload_bits {payload_bits} must be a multiple of the lane within {spec.bits}")
    lanes = payload_bits // lane_bits
    ck = Checkpoint(snapshot)
    pin = sj.get("checkpoint", {})
    if pin.get("index_sha256") and pin["index_sha256"] != ck.index_sha256:
        raise ValueError("checkpoint index sha256 differs from the spec pin")
    out = Path(out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    recs = []
    names = [i for rom in sj["roms"] for i in rom["instances"]]
    if len(names) != len(set(names)):
        raise ValueError("instance names repeat")
    for rom in sj["roms"]:
        logical, segs = weights_streams(ck, rom, spec, lane_bits, payload_bits)
        phys = physical_words(logical, lanes, lane_bits, int(rom.get("skew", 0)), int(rom.get("skew_mod", 8)))
        k = len(rom["instances"])
        for i, inst in enumerate(rom["instances"]):
            words = phys[i::k]
            digits = (spec.bits + 3) // 4
            img = out / "images" / f"{inst}.hex"
            img.write_text("".join(f"{w:0{digits}x}\n" for w in words))
            rec = personalise_instance(spec, words, inst, out)
            rec.update({"image": f"images/{inst}.hex", "image_sha256": asap7.sha256_file(img),
                        "pingpong": {"index": i, "of": k}, "skew": int(rom.get("skew", 0)),
                        "skew_mod": int(rom.get("skew_mod", 8)), "segments": segs})
            recs.append(rec)
    man = {"schema": WEIGHTS_MANIFEST_SCHEMA, "generator": f"tools/mem_compiler/rom_gen.py v{GENERATOR_VERSION} weights",
           "macro": spec.name, "macro_sheet_sha256": asap7.sha256_file(sheet), "data_bits": spec.bits,
           "lane_bits": lane_bits, "payload_bits": payload_bits, "ecc": "none", "spec_sha256": asap7.sha256_file(spec_path),
           "checkpoint": {**pin, "index_sha256_seen": ck.index_sha256},
           "payload_policy": "released checkpoint bytes copied unchanged (no arithmetic, no requantisation)",
           "instances": recs, "content_signature": die_signature(recs),
           "viamap_set_sha256": hashlib.sha256("".join(r["viamap_sha256"] for r in
                                                        sorted(recs, key=lambda r: r["instance"])).encode()).hexdigest()}
    (out / "weights.manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    return man


def read_word(spec: RomSpec, rows: list[int], a: int) -> int:
    """One word as the behavioural model reads it: physical row a // mux, column b * mux + a % mux."""
    r, s = divmod(a, spec.mux)
    row = rows[r] >> s
    return sum(((row >> (b * spec.mux)) & 1) << b for b in range(spec.bits))


def weights_expected_lane(ck: Checkpoint, rec: dict[str, Any], spec: RomSpec, lane_bits: int, lanes: int,
                          a: int, j: int) -> int:
    """Expected lane j of macro address a, straight from the checkpoint file offset (independent of the packer)."""
    k, i = rec["pingpong"]["of"], rec["pingpong"]["index"]
    n = k * spec.words
    p = a * k + i
    g = (p - rec["skew"] * (j % rec["skew_mod"])) % n if rec["skew"] else p
    lane_bytes = lane_bits // 8
    byte0 = (g * lanes + j) * lane_bytes                     # byte offset of this lane in the logical stream
    out = b""
    pos = 0
    for seg in rec["segments"]:
        t = ck.tensor(seg["tensor"])
        row_bytes = seg["cols"] * t["item"]
        order = _segment_rows(seg)
        size = len(order) * row_bytes
        if byte0 < pos + size:
            want = lane_bytes
            while want and byte0 < pos + size:
                off = byte0 - pos
                r, cb = divmod(off, row_bytes)
                take = min(want, row_bytes - cb)
                el0, eb = divmod(cb, t["item"])
                if order[r] is None:
                    out += bytes(take)
                else:
                    data = ck.read(t, seg["row0"] + order[r], seg["col0"] + el0, math.ceil((eb + take) / t["item"]))
                    out += data[eb:eb + take]
                want -= take
                byte0 += take
            if not want:
                break
        pos += size
    out += bytes(lane_bytes - len(out))                       # payload tail and padding words read zero
    return int.from_bytes(out, "little")


def weights_verify(manifest_path: Path, snapshot: Path, samples: int = 64, macro_sheet: Path | None = None,
                   full: bool = False) -> dict[str, Any]:
    """Read-back bench: sampled (or every) word of every instance, physical via map against the checkpoint bytes."""
    import random
    manifest_path = Path(manifest_path)
    man = json.loads(manifest_path.read_text())
    sheet = Path(macro_sheet) if macro_sheet else ROOT / "physical/asap7_memory_macros_v2" / man["macro"] / f"{man['macro']}.json"
    spec = spec_from_sheet(sheet)
    lane_bits = man["lane_bits"]
    lanes = man["payload_bits"] // lane_bits
    ck = Checkpoint(snapshot)
    seen = man["checkpoint"].get("index_sha256_seen")
    if seen and seen != ck.index_sha256:
        return {"verdict": "FAIL", "errors": ["checkpoint index differs from the one the images were built from"]}
    bad, checked = [], 0
    for rec in man["instances"]:
        vm = manifest_path.parent / rec["viamap"]
        text = vm.read_text()
        if hashlib.sha256(text.encode()).hexdigest() != rec["viamap_sha256"]:
            bad.append(f"{rec['instance']}: via map hash differs")
            continue
        for seg in rec["segments"]:
            if ck.tensor(seg["tensor"])["header_sha256"] != seg["shard_header_sha256"]:
                bad.append(f"{rec['instance']}: {seg['tensor']} shard header differs from the build")
        rows = [int(x, 16) for x in text.split()]
        rnd = random.Random(int(rec["viamap_sha256"][:16], 16))
        addrs = range(spec.words) if full else sorted({0, spec.words - 1, *(rnd.randrange(spec.words) for _ in range(samples))})
        for a in addrs:
            w = read_word(spec, rows, a)
            for j in range(lanes):
                got = (w >> (j * lane_bits)) & ((1 << lane_bits) - 1)
                want = weights_expected_lane(ck, rec, spec, lane_bits, lanes, a, j)
                if got != want:
                    bad.append(f"{rec['instance']}: addr {a} lane {j} reads {got:x}, checkpoint {want:x}")
                    break
            if w >> (lanes * lane_bits):
                bad.append(f"{rec['instance']}: addr {a} dead bits above the lanes are programmed")
            checked += 1
        if f"{ecc.signature_fast(read_back(spec, rows), spec.bits):08x}" != rec["signature_crc32"]:
            bad.append(f"{rec['instance']}: BIST signature differs")
    return {"verdict": "FAIL" if bad else "PASS", "macro": man["macro"], "instances": len(man["instances"]),
            "words_checked": checked, "lanes_per_word": lanes, "content_signature": die_signature(man["instances"]),
            "errors": bad[:20]}


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
    g = sub.add_parser("gds", help="the content mask of ONE image: its VIA1 programming overlay as GDS (rom_viamap_gds.py)")
    g.add_argument("--macro", type=Path, required=True, help="the macro's datasheet JSON")
    g.add_argument("--viamap", type=Path, required=True, help="<INSTANCE>.viamap.hex")
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--dbu-per-um", type=float)
    g.add_argument("--via-grid", type=Path, help="explicit programming drain coordinates bound to the macro LEF")
    v = sub.add_parser("verify", help="per-content functional/LEC check: via maps against the weight image")
    v.add_argument("--manifest", type=Path, required=True, help="<prefix>.personalisation.json")
    v.add_argument("--image", type=Path, default=None, help="the content file (default: the manifest's)")
    v.add_argument("--macro", type=Path, default=None, help="datasheet JSON of a shape not in physical/ (fresh compile)")
    w = sub.add_parser("weights", help="real checkpoint tensors -> per-instance via maps + sha256 manifest (no requantisation)")
    w.add_argument("--spec", type=Path, required=True, help="opentallas.rom-weights-spec.v1 JSON")
    w.add_argument("--snapshot", type=Path, required=True, help="safetensors snapshot directory")
    w.add_argument("--out", type=Path, required=True)
    vw = sub.add_parser("verify-weights", help="read-back bench: physical via maps against the checkpoint bytes")
    vw.add_argument("--manifest", type=Path, required=True, help="weights.manifest.json")
    vw.add_argument("--snapshot", type=Path, required=True)
    vw.add_argument("--samples", type=int, default=64, help="random addresses per instance (plus first and last)")
    vw.add_argument("--full", action="store_true", help="every address of every instance")
    vw.add_argument("--macro", type=Path, default=None, help="datasheet JSON of a shape not in physical/")
    args = ap.parse_args()
    if args.cmd == "weights":
        man = weights_build(args.spec, args.snapshot, args.out)
        print(json.dumps({"instances": len(man["instances"]), "macro": man["macro"],
                          "content_signature": man["content_signature"], "viamap_set_sha256": man["viamap_set_sha256"]}))
        return 0
    if args.cmd == "verify-weights":
        res = weights_verify(args.manifest, args.snapshot, args.samples, args.macro, args.full)
        print(json.dumps(res, indent=1, sort_keys=True))
        return 0 if res["verdict"] == "PASS" else 1
    if args.cmd == "gds":
        import rom_viamap_gds as VG
        m = VG.Macro(args.macro, via_grid=args.via_grid)
        name = VG.write_overlay(m, args.viamap, args.out, args.dbu_per_um)
        ok = VG.readback_overlay(m, args.out) == VG.read_viamap(args.viamap, m)       # the stream is read back before it is reported
        print(json.dumps({"structure": name, "gds": str(args.out), "layer": [VG.V1_LAYER, VG.V1_DT], "readback": "PASS" if ok else "FAIL",
                          **m.geometry_info()}))
        return 0 if ok else 1
    if args.cmd == "verify":
        res = verify_personalisation(args.manifest, args.image, args.macro)
        print(json.dumps(res, indent=1, sort_keys=True))
        return 0 if res["verdict"] == "PASS" else 1
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
