#!/usr/bin/env python3
"""ASAP7 SRAM compiler: 1RW, 1R1W and 2RW macros with row and column redundancy.

For each requested configuration (``words x bits``, column mux, banks, port
type, spare rows, spare IO columns) it writes, under ``--out/<name>/``:

* ``<name>.lef``            abstract (size, M4 pins, M4 VDD/VSS straps, M1-M4 OBS)
* ``<name>_{tt,ss,ff}.lib`` NLDM liberty per ASAP7 corner (ps / fF / fJ / nW)
* ``<name>.v``              behavioural model: the physical array, the repair
                            steering and (under OT_MEM_FAULTS) the fault model
* ``<name>_bb.v``           blackbox for synthesis and place-and-route
* ``<name>.json``           datasheet: geometry, area breakdown, density,
                            timing and energy per corner, every constant's grade

The area model is the measured ASAP7 6T bitcell (DRC-clean, this repository)
plus a periphery whose one free dimension is calibrated to a published 7 nm
macro (Yokoyama et al., VLSI 2020, 29.2 Mb/mm2); the timing model is an
Elmore/charge model on ASAP7's own wire RC and standard-cell FO4 per corner.
The approach is FakeRAM2.0's -- abstract views for the flow, no transistor
layout -- but every number is derived rather than typed in.

    python3 tools/mem_compiler/sram_gen.py --config configs/memories/asap7_macros.json \\
        --out physical/asap7_memory_macros
    python3 tools/mem_compiler/sram_gen.py --name x --words 256 --bits 64 --mux 4 --out /tmp/m
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asap7  # noqa: E402
import behav  # noqa: E402
from views import Pin, Timing, blackbox_verilog, macro_outline, write_lef, write_liberty  # noqa: E402

PORT_TYPES = ("1rw", "1r1w", "2rw")
GENERATOR_VERSION = "1.0"


@dataclass
class SramSpec:
    name: str
    words: int
    bits: int
    mux: int = 4
    banks: int = 1
    ports: str = "1rw"
    spare_rows: int = 0
    spare_cols: int = 0

    def validate(self) -> None:
        if self.ports not in PORT_TYPES:
            raise ValueError(f"{self.name}: ports must be one of {PORT_TYPES}")
        if self.mux not in (1, 2, 4, 8, 16):
            raise ValueError(f"{self.name}: column mux must be 1, 2, 4, 8 or 16")
        if self.words % (self.mux * self.banks):
            raise ValueError(f"{self.name}: words must be a multiple of mux x banks")
        if self.words // self.mux < 2 or self.bits < 2:
            raise ValueError(f"{self.name}: at least two rows and two bits")
        if self.spare_rows > 8 or self.spare_cols > 8:
            raise ValueError(f"{self.name}: at most 8 spare rows and 8 spare columns")

    @property
    def rows(self) -> int:           # main physical rows (all banks)
        return self.words // self.mux

    @property
    def rows_per_bank(self) -> int:
        return self.rows // self.banks

    @property
    def cols(self) -> int:           # physical columns incl. spare IO columns
        return (self.bits + self.spare_cols) * self.mux

    @property
    def addr_bits(self) -> int:
        return behav._clog2(self.words)


def clog2(n: int) -> int:
    return behav._clog2(n)


# ---------------------------------------------------------------------------
# pins
# ---------------------------------------------------------------------------

def pins_for(spec: SramSpec) -> list[Pin]:
    aw, b = spec.addr_bits, spec.bits
    pins = [Pin("clk", 1, "input", "clock")]
    if spec.ports == "1rw":
        pins += [Pin("ce_in", 1, "input", "control"), Pin("we_in", 1, "input", "control"),
                 Pin("addr_in", aw, "input", "control"), Pin("wd_in", b, "input", "data_in"),
                 Pin("w_mask_in", b, "input", "data_in"), Pin("rd_out", b, "output", "data_out")]
    elif spec.ports == "1r1w":
        pins += [Pin("r_ce_in", 1, "input", "control"), Pin("r_addr_in", aw, "input", "control"),
                 Pin("rd_out", b, "output", "data_out"),
                 Pin("w_ce_in", 1, "input", "control"), Pin("w_addr_in", aw, "input", "control"),
                 Pin("wd_in", b, "input", "data_in"), Pin("w_mask_in", b, "input", "data_in")]
    else:
        for p in ("a", "b"):
            pins += [Pin(f"{p}_ce_in", 1, "input", "control"), Pin(f"{p}_we_in", 1, "input", "control"),
                     Pin(f"{p}_addr_in", aw, "input", "control"), Pin(f"{p}_wd_in", b, "input", "data_in"),
                     Pin(f"{p}_w_mask_in", b, "input", "data_in"), Pin(f"{p}_rd_out", b, "output", "data_out")]
    pins += behav.repair_pins(spec.spare_rows, spec.spare_cols, spec.rows, spec.bits)
    return pins


# ---------------------------------------------------------------------------
# area model
# ---------------------------------------------------------------------------

def _geometry_constants(cal: dict[str, Any]) -> dict[str, float]:
    g = dict(asap7.ASSUMED["periphery_geometry_um"]["value"])
    g["column_fixed"] = solve_column_fixed(g)
    return g


def _periphery(spec: SramSpec, g: dict[str, float]) -> dict[str, float]:
    ports_dec = 1 if spec.ports == "1rw" else 2
    col_mult = {"1rw": 1.0, "1r1w": 1.5, "2rw": 2.0}[spec.ports]
    dec_w = ports_dec * (g["decoder_fixed"] + g["decoder_per_row_bit"] * math.log2(spec.rows_per_bank))
    dec_w += g["fuse_compare_per_spare"] * (spec.spare_rows + spec.spare_cols)
    col_h = col_mult * (g["column_fixed"] + g["column_per_mux_bit"] * math.log2(spec.mux))
    if spec.spare_cols:
        col_h += 0.4  # spare-IO steering multiplexers
    ctrl_h = g["control_extra"] if spec.banks > 1 else 0.0
    return {"decoder_width_um": dec_w, "column_height_um": col_h, "bank_control_height_um": ctrl_h}


def solve_column_fixed(g: dict[str, float]) -> float:
    """The one periphery dimension calibrated to the published 7 nm macro.

    A 512 x 512 cell array with a 4:1 column multiplexer (2,048 words x 128
    bits, 1RW, no spares) must reach the published macro efficiency
    (29.2 Mb/mm2 on a 0.027 um2 cell = 0.788).
    """
    cells = asap7.bitcells()["sram_6t"]
    eff = asap7.published_macro_efficiency()
    aw = 512 * cells["col_pitch_um"]
    ah = 512 * cells["row_pitch_um"]
    dec_w = g["decoder_fixed"] + g["decoder_per_row_bit"] * math.log2(512)
    total = aw * ah / eff
    col_h = total / (aw + dec_w) - ah
    return col_h - g["column_per_mux_bit"] * math.log2(4)


def area_model(spec: SramSpec, cal: dict[str, Any]) -> dict[str, Any]:
    cells = asap7.bitcells()["sram_6t"]
    ratio = 1.0 if spec.ports == "1rw" else asap7.ASSUMED["dual_port_cell_area_ratio"]["value"][spec.ports]
    col_pitch = cells["col_pitch_um"] * ratio
    row_pitch = cells["row_pitch_um"]
    g = _geometry_constants(cal)
    per = _periphery(spec, g)
    array_w = spec.cols * col_pitch
    rows_b = [spec.rows_per_bank + (spec.spare_rows if k == 0 else 0) for k in range(spec.banks)]
    array_h = sum(r * row_pitch for r in rows_b)
    core_w = array_w + per["decoder_width_um"]
    core_h = array_h + spec.banks * per["column_height_um"] + per["bank_control_height_um"]
    return {
        "cell_area_um2": cells["area_um2"] * ratio,
        "cell_col_pitch_um": col_pitch, "cell_row_pitch_um": row_pitch,
        "array_width_um": array_w, "array_height_um": array_h,
        "data_array_area_um2": spec.words * spec.bits * cells["area_um2"] * ratio,
        "physical_array_area_um2": array_w * array_h,
        "core_width_um": core_w, "core_height_um": core_h,
        **per, "geometry_constants_um": g,
    }


# ---------------------------------------------------------------------------
# timing and energy model
# ---------------------------------------------------------------------------

def timing_model(spec: SramSpec, area: dict[str, Any], cal: dict[str, Any], corner: str) -> Timing:
    c = cal["corners"][corner]
    tt = cal["corners"]["tt"]
    fo4 = c["fo4_ps"]
    k = asap7.ASSUMED["periphery_fo4_budget"]["value"]
    v = c["voltage_v"]
    cg_fin = asap7.gate_cap_per_fin_ff(cal)
    r_m2, c_m2 = asap7.SETRC["M2"]
    r_m1, c_m1 = asap7.SETRC["M1"]
    # wordline: M2 across the columns of one bank, two 1-fin pass gates per cell
    wl_len = area["array_width_um"]
    c_wl = wl_len * c_m2 + spec.cols * 2 * cg_fin
    r_wl = wl_len * r_m2
    drive = min(8.0, max(1.0, c_wl / (16.0 * c["inv4_cin_ff"])))
    r_drv = c["inv4_r_kohm"] / drive
    t_wl = r_drv * c_wl + 0.38 * r_wl * c_wl
    if spec.cols > 256:
        # centre-driven (split) wordline, as the published 512-column macro does with its
        # dual-edge drivers: each half is half as long, so the distributed RC falls 4x
        t_wl = r_drv * c_wl + 0.38 * r_wl * c_wl / 4.0
    # bitline: M1 down the rows of one bank, one junction per cell
    rows_bl = spec.rows_per_bank + spec.spare_rows
    c_bl = rows_bl * (area["cell_row_pitch_um"] * c_m1 + asap7.ASSUMED["drain_cap_per_cell_ff"]["value"])
    i_cell = asap7.ASSUMED["sram_cell_read_current_ua"]["value"] * tt["fo4_ps"] / fo4
    dv = asap7.ASSUMED["sram_sense_swing_v"]["value"]
    t_bl = c_bl * dv / i_cell * 1000.0            # fF * V / uA = ns -> ps
    t_ctrl = k["clock_and_latch"] * fo4
    t_dec = (k["decoder_fixed"] + k["decoder_per_address_bit"] * math.log2(spec.rows_per_bank)) * fo4
    if spec.banks > 1:
        t_dec += fo4
    if spec.spare_rows:
        t_dec += fo4                               # spare-row address compare in parallel, 1 FO4 to steer
    t_mux = k["mux_per_level"] * math.log2(spec.mux) * fo4
    t_sa = k["sense"] * fo4
    t_out = k["output"] * fo4 + (0.5 * fo4 if spec.spare_cols else 0.0)
    out_r = c["inv4_r_kohm"] / 2.0                 # INVx8-class output driver
    clk_q = t_ctrl + t_dec + t_wl + t_bl + t_mux + t_sa + t_out + out_r * 0.72
    r_wd = c["inv4_r_kohm"] / 2.0
    t_write = t_ctrl + t_dec + t_wl + k["write_driver"] * fo4 + 0.69 * r_wd * c_bl
    t_pre = k["precharge"] * fo4 + 0.69 * (c["inv4_r_kohm"] / 2.0) * c_bl
    read_cycle = t_ctrl + t_dec + t_wl + t_bl + t_sa + t_pre
    write_cycle = t_write + t_pre
    min_period = max(read_cycle, write_cycle)
    # energy (fJ): wordline full swing, every column's bitline to the sense swing on
    # a read, the written columns full swing on a write, periphery per output bit
    e_wl = c_wl * v * v
    e_dec = 20.0 * cg_fin * v * v * math.log2(spec.rows_per_bank)
    e_per = asap7.ASSUMED["periphery_energy_ff_per_bit"]["value"] * spec.bits * v * v
    e_read = e_wl + e_dec + spec.cols * c_bl * v * dv + e_per
    e_write = e_wl + e_dec + spec.bits * c_bl * v * v + (spec.cols - spec.bits) * c_bl * v * dv + e_per
    leak_w_mm2 = asap7.tech_value("power.static_leakage_w_per_mm2.sram_array")
    macro_um2 = area["macro_area_um2"]
    leak_nw = leak_w_mm2 * macro_um2 * 1e-6 * 1e9
    return Timing(
        corner=corner, voltage=v, temperature=c["temperature_c"], clk_to_q_ps=clk_q, out_r_kohm=out_r,
        out_slew_intrinsic_ps=1.5 * fo4, setup_ps=c["dff_setup_ps"] + 1.0 * fo4, hold_ps=c["dff_hold_ps"] + 0.5 * fo4,
        min_period_ps=min_period, min_pulse_ps=0.4 * min_period, read_energy_fj=e_read, write_energy_fj=e_write,
        leakage_nw=leak_nw, pin_cap_ff=c["inv1_cin_ff"], clk_cap_ff=4 * c["inv4_cin_ff"],
        breakdown={"control_ps": t_ctrl, "decode_ps": t_dec, "wordline_ps": t_wl, "bitline_ps": t_bl,
                   "column_mux_ps": t_mux, "sense_ps": t_sa, "output_ps": t_out, "write_ps": t_write,
                   "precharge_ps": t_pre, "read_cycle_ps": read_cycle, "write_cycle_ps": write_cycle,
                   "wordline_cap_ff": c_wl, "bitline_cap_ff": c_bl, "cell_current_ua": i_cell,
                   "fo4_ps": fo4})


# ---------------------------------------------------------------------------
# behavioural model
# ---------------------------------------------------------------------------

def behavioural(spec: SramSpec, pins: list[Pin], header: str) -> str:
    params = {"WORDS": spec.words, "BITS": spec.bits, "MUX": spec.mux, "AW": spec.addr_bits,
              "ROWS": spec.rows, "NSR": spec.spare_rows, "NSC": spec.spare_cols,
              "PR": spec.rows + spec.spare_rows, "PC": spec.cols,
              "RA": clog2(spec.rows), "CB": clog2(spec.bits)}
    body = [
        "    // physical array: main rows, then spare rows; columns bit-interleaved by MUX",
        "    reg [PC-1:0] arr [0:PR-1];",
        "    integer init_i;",
        "    // Power-up content: zero in simulation.  Silicon powers up random; a March C-",
        "    // self-test ends with its (r0) element, so a tested array holds zeros too.",
        "    initial begin",
        "`ifndef OT_MEM_NO_INIT",
        "        for (init_i = 0; init_i < PR; init_i = init_i + 1) arr[init_i] = {PC{1'b0}};",
        "`endif",
        "    end",
        behav.FAULT_BLOCK, behav.HELPERS, behav.WRITE_TASK,
    ]
    if spec.ports == "1rw":
        body += ["    always @(posedge clk) begin",
                 "        if (ce_in && !we_in) rd_out <= word_read(addr_in);",
                 "        if (ce_in && we_in) word_write(addr_in, wd_in, w_mask_in);",
                 "    end"]
    elif spec.ports == "1r1w":
        body += ["    // read-before-write: a same-address read in the write cycle returns the old word",
                 "    always @(posedge clk) begin",
                 "        if (r_ce_in) rd_out <= word_read(r_addr_in);",
                 "        if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in);",
                 "    end"]
    else:
        body += ["    // both reads see the array before either write; on a same-address double write B wins",
                 "    always @(posedge clk) begin",
                 "        if (a_ce_in && !a_we_in) a_rd_out <= word_read(a_addr_in);",
                 "        if (b_ce_in && !b_we_in) b_rd_out <= word_read(b_addr_in);",
                 "        if (a_ce_in && a_we_in) word_write(a_addr_in, a_wd_in, a_w_mask_in);",
                 "        if (b_ce_in && b_we_in) word_write(b_addr_in, b_wd_in, b_w_mask_in);",
                 "    end"]
    return behav.module_text(spec.name, pins, params, "\n".join(body) + "\n", header,
                             spec.spare_rows, spec.spare_cols)


# ---------------------------------------------------------------------------
# compile
# ---------------------------------------------------------------------------

def compile_macro(spec: SramSpec, out_dir: Path | None = None) -> dict[str, Any]:
    spec.validate()
    cal = asap7.calibration()
    pins = pins_for(spec)
    area = area_model(spec, cal)
    w, h, pin_info = macro_outline(area["core_width_um"], area["core_height_um"], pins)
    area["macro_width_um"], area["macro_height_um"] = w, h
    area["macro_area_um2"] = w * h
    area["outline"] = pin_info
    bits_total = spec.words * spec.bits
    area["array_efficiency"] = area["data_array_area_um2"] / area["macro_area_um2"]
    area["density_mb_per_mm2"] = bits_total / area["macro_area_um2"]  # bits/um2 == Mb/mm2
    corners = {c: timing_model(spec, area, cal, c) for c in asap7.CORNERS}
    header = (f"{spec.name}: ASAP7 {spec.ports.upper()} SRAM {spec.words} x {spec.bits}, mux {spec.mux}, "
              f"{spec.banks} bank(s), {spec.spare_rows} spare row(s), {spec.spare_cols} spare IO column(s); "
              f"OpenTallas tools/mem_compiler/sram_gen.py v{GENERATOR_VERSION}")
    tt = corners["tt"]
    sheet: dict[str, Any] = {
        "schema": "opentallas.mem-compiler.sram.v1",
        "generator": f"tools/mem_compiler/sram_gen.py v{GENERATOR_VERSION}",
        "kind": "sram",
        "spec": asdict(spec),
        "physical": {"rows": spec.rows, "rows_per_bank": spec.rows_per_bank, "columns": spec.cols,
                     "spare_rows": spec.spare_rows, "spare_io_columns": spec.spare_cols,
                     "column_interleave": "data bit b, column select s -> physical column b*mux + s"},
        "area": area,
        "capacity_bits": bits_total,
        "timing": {c: asdict(t) for c, t in corners.items()},
        "fmax_mhz": {c: 1e6 / t.min_period_ps for c, t in corners.items()},
        "read_bandwidth_gbit_s_tt": spec.bits * (2 if spec.ports == "2rw" else 1) * 1e3 / tt.min_period_ps,
        "calibration": {"bitcells": asap7.bitcells(), "published": asap7.PUBLISHED,
                        "assumed": asap7.ASSUMED, "stdcell": {"image_id": cal.get("image_id"),
                                                              "file": "tools/mem_compiler/asap7_calibration.json"}},
        "claim_boundary": "abstract views from a calibrated analytical model on measured ASAP7 bitcells and "
                          "ASAP7 standard-cell FO4; no transistor layout, no SPICE of the macro, not silicon; "
                          "ASAP7 is a predictive PDK and nothing here is a foundry N7 number",
    }
    if out_dir is not None:
        d = out_dir / spec.name
        d.mkdir(parents=True, exist_ok=True)
        props = {"width": spec.bits, "depth": spec.words, "banks": spec.banks}
        (d / f"{spec.name}.lef").write_text(write_lef(spec.name, w, h, pins, props))
        mem = {"type": "ram", "address_width": spec.addr_bits, "word_width": spec.bits}
        for c, t in corners.items():
            (d / f"{spec.name}_{c}.lib").write_text(write_liberty(spec.name, t, pins, w * h, mem, header))
        (d / f"{spec.name}.v").write_text(behavioural(spec, pins, "// " + header))
        (d / f"{spec.name}_bb.v").write_text(blackbox_verilog(spec.name, pins, header))
        files = sorted(p.name for p in d.iterdir() if p.name != f"{spec.name}.json")
        sheet["views"] = {f: asap7.sha256_file(d / f) for f in files}
        (d / f"{spec.name}.json").write_text(json.dumps(sheet, indent=2, sort_keys=True) + "\n")
    return sheet


def load_config(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, help="JSON with a 'sram' list of macro specs")
    ap.add_argument("--name")
    ap.add_argument("--words", type=int)
    ap.add_argument("--bits", type=int)
    ap.add_argument("--mux", type=int, default=4)
    ap.add_argument("--banks", type=int, default=1)
    ap.add_argument("--ports", default="1rw", choices=PORT_TYPES)
    ap.add_argument("--spare-rows", type=int, default=0)
    ap.add_argument("--spare-cols", type=int, default=0)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    specs: list[SramSpec] = []
    if args.config:
        specs = [SramSpec(**s) for s in load_config(args.config).get("sram", [])]
    if args.name:
        specs.append(SramSpec(args.name, args.words, args.bits, args.mux, args.banks, args.ports,
                              args.spare_rows, args.spare_cols))
    for spec in specs:
        s = compile_macro(spec, args.out)
        a, t = s["area"], s["timing"]
        print(f"{spec.name}: {a['macro_width_um']:.2f} x {a['macro_height_um']:.2f} um, "
              f"{a['density_mb_per_mm2']:.2f} Mb/mm2, eff {a['array_efficiency']:.3f}, "
              f"clk->q {t['tt']['clk_to_q_ps']:.0f}/{t['ss']['clk_to_q_ps']:.0f}/{t['ff']['clk_to_q_ps']:.0f} ps, "
              f"fmax tt {s['fmax_mhz']['tt']:.0f} MHz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
