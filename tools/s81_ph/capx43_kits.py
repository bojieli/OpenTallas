#!/usr/bin/env python3
"""Pin plans + ref_tile specs of the DECISION B capture data-half leaves (claude S-VM-CAPT-X8, 2026-10-16).

dsfd_capt_x8_data_e / _w (old 108 x 162 two-clock leaf) -> two single-clock leaves that abut on a bank seam:
  dsfd_capt_x8x_t_<s>  ck   21.6 x 172.8  f_w (+ t_ho) on the outer face (E for _e, W for _w), banks on the seam face
  dsfd_capt_x8x_s_<s>  ckv  86.4 x 172.8  banks on the seam face, t_vm on S (old M3/M5 pattern), ckv/rsv on N
Parent footprint 108 x 172.8 (old 108 x 162).  BIT-MAJOR seam (VM x43 F4 precedent): for row r, word bit j the four
bank bits b0..b3 are adjacent 2-track M4 pins (0.096 um) around the y of f_w[52 r + j] on the opposite face, so every
f_w pin -> bank flop -> seam pin is a straight 21.6 um row; s_mark[r] / s_par[r] take the slot after row r.
The seam has 8 x 53 slots x 0.384 um = 162.8 um, hence the 172.8 um height (>= 4.32 um corner keep-out).
Usage: capx43_kits.py   (writes physical/s81_die_pins/capture_split_1016/dsfd_capt_x8x_*.tcl + specs)
"""
import json, math, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
PINS = ROOT / 'physical/s81_die_pins/capture_split_1016'
SPECS = ROOT / 'tools/ref_tile/specs_s81_capture_split_1016'
H, WT, WS = 172.8, 21.6, 86.4
TRK, Y0, SLOT = 0.048, 0.012, 0.384
M4 = '-pin_size {0.192 0.024}'
M5 = '-pin_size {0.024 0.192}'
SRC = 'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_x8_x43.sv'


def snap(y):
    return round(Y0 + round((y - Y0) / TRK) * TRK, 6)


def slots():
    """[(y_centre, f_w index or None, [(seam pin, dy)])] in slot order, plus the t_ho y"""
    n = 8 * 53 + 1
    start = snap((H - (n - 1) * SLOT) / 2)
    out = []
    k = 0
    for r in range(8):
        for j in range(52):
            y = round(start + k * SLOT, 6)
            out.append((y, 52 * r + j, [(f'b[{208 * r + 52 * b + j}]', (b - 1.5) * 0.096) for b in range(4)]))
            k += 1
        y = round(start + k * SLOT, 6)
        out.append((y, None, [(f's_mark[{r}]', -0.048), (f's_par[{r}]', 0.048)]))
        k += 1
    t_ho = round(start + k * SLOT, 6)
    assert start >= 4.32 and t_ho <= H - 4.32, (start, t_ho)
    return out, t_ho


def line(name, layer, x, y, size):
    return f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.6f} {y:.6f}}} {size} -force_to_die_boundary'


def old_tvm():
    """the old leaf's t_vm S-face pins (layer, x, size), recentred into the 86.4 um serial leaf by -46 x 0.144 um"""
    pat = re.compile(r'-pin_name \{t_vm\[(\d+)\]\} -layer (M\d) -location \{([\d.]+) [\d.]+\} (-pin_size \{[^}]*\})')
    res = {}
    for l in (PINS / 'dsfd_capt_x8_data_e.tcl').read_text().splitlines():
        m = pat.search(l)
        if m:
            res[int(m.group(1))] = (m.group(2), round(float(m.group(3)) - 46 * 0.144, 6), m.group(4))
    assert len(res) == 832 and min(v[1] for v in res.values()) >= 3.0 and max(v[1] for v in res.values()) <= WS - 3.0
    return res


def pins(side, half):
    """half 't' / 's'; side 'e' / 'w'.  Returns (tcl text, faces dict)"""
    sl, t_ho = slots()
    hdr = [f'# claude S-VM-CAPT-X8 2026-10-16 (tools/s81_ph/capx43_kits.py): dsfd_capt_x8x_{half}_{side}, DECISION B '
           f'single-clock leaf of dsfd_capt_x8_data_{side}.',
           '# BIT-MAJOR bank seam: b[208 r + 52 k + j] (bank k of row r, word bit j) at y(f_w[52 r + j]) + (k - 1.5) x 0.096 '
           'on the seam face of BOTH leaves (they abut); s_mark/s_par[r] in the slot after row r.  M4 E/W, M5 N, M3/M5 S.']
    L = []
    if half == 't':
        W = WT
        outer_x, seam_x = (W, 0.0) if side == 'e' else (0.0, W)
        L += [line('ck[0]', 'M5', 10.092, H, M5), line('rst[0]', 'M5', 11.916, H, M5)]
        for y, fi, seam in sl:
            if fi is not None:
                L.append(line(f'f_w[{fi}]', 'M4', outer_x, y, M4))
            L += [line(n, 'M4', seam_x, round(y + dy, 6), M4) for n, dy in seam]
        L.append(line('t_ho[0]', 'M4', outer_x, t_ho, M4))
        o, s_ = ('E', 'W') if side == 'e' else ('W', 'E')
        faces = {o: ['f_w', 't_ho'], s_: ['b', 's_mark', 's_par'], 'N': ['ck', 'rst'], 'S': []}
    else:
        W = WS
        seam_x = W if side == 'e' else 0.0
        L += [line('ckv[0]', 'M5', 40.044, H, M5), line('rsv[0]', 'M5', 42.444, H, M5)]
        for y, fi, seam in sl:
            L += [line(n, 'M4', seam_x, round(y + dy, 6), M4) for n, dy in seam]
        for i, (lay, x, size) in sorted(old_tvm().items()):
            L.append(line(f't_vm[{i}]', lay, x, 0.0, size))
        s_ = 'E' if side == 'e' else 'W'
        faces = {s_: ['b', 's_mark', 's_par'], 'S': ['t_vm'], 'N': ['ckv', 'rsv']}
        faces.setdefault('E' if side == 'w' else 'W', [])
    return '\n'.join(hdr + L) + '\n', faces


LINT = ("mkdir -p {RUN} && printf '%s\\n' 'module ot_lint_top; TOP u_top (); endmodule' > {RUN}/ot_lint_top.sv && "
        "verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN "
        "-Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top {RUN}/ot_lint_top.sv " + SRC + " && echo lint-ok")


def spec(side, half, faces):
    top = f'dsfd_capt_x8x_{half}_{side}'
    w = WT if half == 't' else WS
    clk, rst = ('ck[0]', 'rst') if half == 't' else ('ckv[0]', 'rsv')
    why = (f'New single-clock leaf {top} (DECISION B: replaces the two-clock dsfd_capt_x8_data_{side} hard leaf, '
           'split1016 FF hold -84 ps on 3,376 intra-leaf 4:3 R2R arcs); no prior slot or closed view')
    benches = [
        {"name": "lint", "cmd": LINT.replace('TOP', top), "expect": "pass", "threads": 1, "peak_ram_gb": 4,
         "needs": ["verilator"]},
        {"name": "x8_x43_unit", "cmd": "bash tools/s81_ph/capx43_bench.sh {RUN}/u", "expect": "pass",
         "pass_regex": "^CAPX43_BENCH PASS$", "threads": 8, "peak_ram_gb": 4, "needs": ["verilator"]},
        {"name": "capture_split_exact",
         "cmd": "bash tools/s81_ph/capc_split_bench.sh {RUN}/bench eq 'mix mix11 mix12 mix13 trace err over range rreq'",
         "expect": "pass", "pass_regex": "^CAPC_BENCH PASS cases=9$", "threads": 8, "peak_ram_gb": 16},
        {"name": "capture_split_mutant_drop1",
         "cmd": "bash tools/s81_ph/capc_split_bench.sh {RUN}/mut mut 'mix' S81PH_CAPX_MUT_DROP1",
         "expect": "fail", "fail_regex": "CAPC_SEQ words=.*seq_mismatches=[1-9]", "threads": 8, "peak_ram_gb": 16},
    ]
    return {
        "name": f"{top}_split1016x", "top": top, "kind": "tile", "sources": [SRC], "params": {},
        "clock_port": clk, "reset_ports": [rst], "outline": {"w": w, "h": H, "exact": True}, "macros": [],
        "pins": faces, "io_tcl": f"physical/s81_die_pins/capture_split_1016/{top}.tcl", "children": [], "inter": [],
        "recipe": 2, "io_flop_at_pins": {"cols": 4, "allow_none": True}, "inhold": True, "outhold": False,
        "keep_pin_regs": True, "pin_reg_split": True, "hold_pad": {"cell": "HB2xp67_ASAP7_75t_R"}, "layer_cap": "M5",
        "route": {"pd": 0.45, "threads": 8, "peak_ram_gb": 16, "period_ps": 770, "hold_margin_ns": 0.03,
                  "macro_halo_um": 5.4},
        "clock": "cts",
        "structural_change": (
            f"DECISION B successor of dsfd_capt_x8_data_{side} (split1016 / split1016b: FF hold -84 ps on 3,376 intra-leaf "
            "ck->ckv R2R arcs of 8 x ot_ratio_cdc_fifo, hold repair stalled: the 256.67 ps 4:3 window cannot carry the "
            "100 ps hold + 150 ps setup cross-entry reserve).  The 8 dsfd_capt_row_local rows (dynamic hold queue + pair "
            "packer + ratio FIFO) become fixed-bank 3:4 transfers on the common epoch (ot_s81_vm_x43 contract) split per "
            "clock root: dsfd_capt_x8x_t (ck) samples f_w into bank n at EVERY stream index n = 0..3 (no index is a fault: "
            "capture words arrive on any stream cycle); dsfd_capt_x8x_s (ckv) reads b0+b1 at serial edge 2, b2 at edge 0, "
            "b3 at edge 1 (stage A) and registers t_vm one serial edge later at the S face (stage B).  Hold queue removed "
            "(no word can be refused); t_ho = sticky epoch-slip fault (stream side checks the serial marker/parity).  "
            "Latency f_w sample edge -> t_vm: 3.333/2.500/2.778/3.056 ns for n = 0/1/2/3, one serial cycle LESS than the "
            "old leaf's best case (measured: tb_dsfd_capt_x8_x43).  Every leaf pin is a flop; outhold off (bank outputs "
            "rewritten >= 1.11 ns after their fixed read).  Parent footprint 108 x 172.8 (old 108 x 162): bit-major seam "
            "needs 1,680 M4 pins at 0.096 um."),
        "slot_change_request": {"contract": "S81 capture split 1016 (codex/s81-hub-parents-0811)",
                                "version": "x43-x8-1016", "why": why},
        "reroute_reason": {"kind": "slot_change",
                           "slot_change_request": {"contract": "S81 capture split 1016 (codex/s81-hub-parents-0811)",
                                                   "version": "x43-x8-1016", "why": why},
                           "why": "new single-clock leaf master; no closed view exists for this block",
                           "contract": "S81 capture split 1016: dsfd_capt_x8_data DECISION B x43 split"},
        "job": {
            "owner": "claude:S-VM-CAPT-X8", "branch": "codex/s81-hub-parents-0811", "tag": "x43",
            "purpose": (f"DECISION B {top}: single-clock leaf of the static capture data-half transfer; capture split "
                        "bench (row-word sequences + status/t_cd) + unit/slip bench + DROP1 mutant, TT/FF/DRC0 + native "
                        "audit; parent 3:4 seam arcs (epoch multicycle) open at die level"),
            "extra_paths": ["tools/s81_ph", "rtl/dsrom_sys/s81_ph", "rtl/common", "rtl/dsrom_sys/s81_glue", "rtl/hdc",
                            "physical/s81_die_pins/capture_split_1016"],
            "benches": benches},
    }


def main():
    for side in 'ew':
        for half in 'ts':
            tcl, faces = pins(side, half)
            top = f'dsfd_capt_x8x_{half}_{side}'
            (PINS / f'{top}.tcl').write_text(tcl)
            (SPECS / f'{top}.json').write_text(json.dumps(spec(side, half, faces), indent=1) + '\n')
            print(top, tcl.count('place_pin'), 'pins')


if __name__ == '__main__':
    main()
