#!/usr/bin/env python3
"""Pin plans + ref_tile specs of the DECISION B capture data-half leaves (claude S-VM-CAPT-X8, 2026-10-16).

dsfd_capt_x8_data_e / _w (old 108 x 162 two-clock leaf) -> two single-clock leaves that abut on a bank seam:
  dsfd_capt_x8x_t_<s>  ck   32.4 x 172.8  f_w (+ t_ho) on the outer face (E for _e, W for _w), banks on the seam face
  dsfd_capt_x8x_s_<s>  ckv  86.4 x 172.8  banks on the seam face, t_vm on S (old M3/M5 pattern), ckv/rsv on N
Parent footprint 118.8 x 172.8 (old 108 x 162).  t width 32.4 (not 21.6): split1016x gate oflop WARN, two 10.5
pins/um faces need 10.58 um of hold-stage + pin-flop depth each, > 45% of a 17.3 um core (GRT-0116 class); 37% at 32.4.  BIT-MAJOR seam (VM x43 F4 precedent): for row r, word bit j the four
bank bits b0..b3 are adjacent 2-track M4 pins (0.096 um) around the y of f_w[52 r + j] on the opposite face, so every
f_w pin -> bank flop -> seam pin is a straight 21.6 um row; s_mark[r] / s_par[r] take the slot after row r.
The seam has 8 x 53 slots x 0.384 um = 162.8 um, hence the 172.8 um height (>= 4.32 um corner keep-out).
split1016y (claude S-VM-CAPT-X8S, 2026-10-16): the serial leaf is HS = 183.6 tall and its seam starts DS = 10.8 um higher
than the t leaf's (t unchanged, 32.4 x 172.8, its closed split1016x views stand).  In the parent the t leaf sits DS above
the s leaf origin (tops flush: ck/rst/ckv/rsv on one N edge), so every seam pin is still mirror-aligned; the parent bbox
is 118.8 x 183.6 with a free 32.4 x 10.8 notch under t beside the t_vm S face.  Why: split1016x s_e / s_w routed CLOSED
but failed native capture (s_e b[188] 211.4, 12 pins; s_w b[3] 200.4, 4 pins), all row 0.  OpenSTA on the s_e route:
row-0 stage-A flops (y 8-23 um, inside the S-face t_vm stage-B band y 2-14) take ckv from the band's clock branch at
172-176 ps vs 133-143 for rows 3-6; against the 130.6 ps IO reference the input hold repair puts 4-5 BUFx2 on every
row-0 seam path (TT data 209.5 ps).  Capture flops at y >= 20 um measured <= 173 ps.  Moving the seam up 10.8 um puts
row 0's stage-A flops at y >= 16 above the band.  Zero added latency (no RTL change).
split1016z (claude S-VM-CAPT-X8S2, 2026-10-16): same outline / seam as split1016y, but the serial leaf takes the ckv
root on TWO literal entries (clock multiple_cts_roots, related same frequency, phase 0): ckv[0] -> stage A bank reads,
row counters, s_mark / s_par, reset chain (E-face seam column); ckvb[0] -> stage B t_vm output flops (S-face band).
Why: split1016y s_e routed CLOSED but still failed native capture (b[248] 197.6, 38 pins, rows 0-2).  OpenSTA on that
route: one TritonCTS tree, top split clkbuf_1_0_0 carries rows 0-2 AND the 832-flop S band (clkbuf_3_2_0 alone drives
15 band leaves), clkbuf_1_1_0 rows 3-7; stage-A clock (ins - setup) 119..173 ps, rows 0-2 median 141-155 vs rows 3-5
137-139; the input hold repair against the 150.1 ps pin-flop reference put 5 BUFx2 + 3 logic on the worst row 0-2
paths (TT data 185 ps) vs 1-2 on rows 3-5 (capture <= 166).  s_w split1016y: b[624] 192.3 (row 3), spread 65.6.  With
its own root the stage-A column is one balanced spine-like tree, so its boundary reference and every capture flop's
clock coincide.  Same logic and cycles (stage B registers stage A one serial edge later); t leaves unchanged.
Usage: capx43_kits.py   (writes physical/s81_die_pins/capture_split_1016/dsfd_capt_x8x_*.tcl + specs)
"""
import json, math, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
PINS = ROOT / 'physical/s81_die_pins/capture_split_1016'
SPECS = ROOT / 'tools/ref_tile/specs_s81_capture_split_1016'
H, WT, WS = 172.8, 32.4, 86.4
HS, DS = 183.6, 10.8          # serial leaf height, its seam offset above the t leaf's (split1016y)
TRK, Y0, SLOT = 0.048, 0.012, 0.384
M4 = '-pin_size {0.192 0.024}'
M5 = '-pin_size {0.024 0.192}'
SRC = 'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_x8_x43.sv'


def snap(y):
    return round(Y0 + round((y - Y0) / TRK) * TRK, 6)


def slots(dy=0.0, h=H):
    """[(y_centre, f_w index or None, [(seam pin, dy)])] in slot order, plus the t_ho y.  dy: the leaf's seam offset
    (0 for t, DS for the HS-tall s leaf), h: the leaf height (keep-out check)"""
    n = 8 * 53 + 1
    start = round(snap((H - (n - 1) * SLOT) / 2) + dy, 6)
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
    assert start >= 4.32 and t_ho <= h - 4.32, (start, t_ho)
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
    sl, t_ho = slots() if half == 't' else slots(DS, HS)
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
        hdr.append(f'# split1016y: serial leaf {WS} x {HS}, seam {DS} um above the t leaf seam (the parent places t {DS} um above '
                   'this leaf origin, tops flush); row 0 clear of the S-face t_vm stage-B band.')
        hdr.append('# split1016z: ckvb[0] = second literal entry of the ckv root (stage B t_vm flops); ckv[0] = stage A.')
        L += [line('ckv[0]', 'M5', 40.044, HS, M5), line('rsv[0]', 'M5', 42.444, HS, M5),
              line('ckvb[0]', 'M5', 44.844, HS, M5)]                  # split1016z stage-B entry
        for y, fi, seam in sl:
            L += [line(n, 'M4', seam_x, round(y + dy, 6), M4) for n, dy in seam]
        for i, (lay, x, size) in sorted(old_tvm().items()):
            L.append(line(f't_vm[{i}]', lay, x, 0.0, size))
        s_ = 'E' if side == 'e' else 'W'
        faces = {s_: ['b', 's_mark', 's_par'], 'S': ['t_vm'], 'N': ['ckv', 'rsv', 'ckvb']}
        faces.setdefault('E' if side == 'w' else 'W', [])
    return '\n'.join(hdr + L) + '\n', faces


LINT = ("mkdir -p {RUN} && printf '%s\\n' 'module ot_lint_top; TOP u_top (); endmodule' > {RUN}/ot_lint_top.sv && "
        "verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN "
        "-Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top {RUN}/ot_lint_top.sv " + SRC + " && echo lint-ok")


NATIVE = 'results/arch/s81_hub_parents_1016/native_audit_capture_1316/native_audit_x8x.json'
NATIVE_FAIL = {'e': ('b[188]', 211.4, 12, 177.6), 'w': ('b[3]', 200.4, 4, 168.0)}   # pin, capture, pins over, launch


def spec_y(side, sp):
    """split1016y successor of the serial leaf: HS outline, seam DS up; same RTL, benches and recipe"""
    top = sp['top']
    pin, cap, n, lw = NATIVE_FAIL[side]
    sp.pop('slot_change_request', None)
    sp['name'] = f'{top}_split1016y'
    sp['outline'] = {"w": WS, "h": HS, "exact": True}
    fix = (f"seam slot block {DS} um higher in a {WS} x {HS} serial leaf (was {WS} x {H}, seam from y 4.99): row 0's "
           "stage-A capture flops leave the S-face t_vm stage-B band (y 2-14) and its late ckv branch (row 0 ckv "
           "172-176 ps vs 133-143 mid rows; input hold repair put 4-5 BUFx2 on each row-0 seam path, TT data 209.5 ps); "
           "t leaf unchanged, the parent places it DS above the s origin so the seam stays mirror-aligned; no RTL change")
    sp['structural_change'] = (f"split1016y re-kit of {top} (closed split1016x view fails native capture: {pin} {cap} ps, "
                               f"{n} pins, all row 0): " + fix + ".  " + sp['structural_change'])
    sp['reroute_reason'] = {"kind": "pin_register", "source": NATIVE, "cell": top, "capture_ps": cap,
                            "launch_ps": lw, "fix": fix}
    sp['job']['owner'] = 'claude:S-VM-CAPT-X8S'
    sp['job']['branch'] = 'claude/svm-capt-x8s-1016'
    return sp


NATIVE_Y = 'results/arch/s81_hub_parents_1016/native_audit_capture_1316/native_audit_x8x_split1016y.json'
NATIVE_Y_FAIL = {'e': ('b[248]', 197.6, 38, 196.8), 'w': ('b[624]', 192.3, 2, 184.5)}   # pin, capture, pins over, launch
# split1016z s_w (b786448b1) routed FF -1.43 on ONE cross-entry ad0 -> bd0 arc (100 ps die-skew hold reserve); the default
# hold ECO (goal HM 18 + allowance -> window 36.9 ps) then padded 894 endpoints incl. 230 seam inputs: native capture
# 168.6 pre-ECO -> 219.6 (b[1197], 63 pins).  s_e (no ECO) PASSES 163.6 / 202.3.  HOLD_ECO keeps a near-miss ECO on the
# missing arcs: goal 3 ps + allowance -> window ~22 ps < the 25.5 ps worst seam-input hold slack of that route.
NATIVE_Z = 'results/arch/s81_hub_parents_1016/native_audit_capture_1316/native_audit_x8x_split1016z.json'
NATIVE_Z_FAIL = {'w': ('b[1197]', 219.6, 63, 204.1)}
HOLD_ECO = {"hold_margin_ps": 3, "why": (
    "native capture <= 190 on every seam input: the default +18 ps ECO goal pads every input pin under ~37 ps of hold slack "
    "when one internal cross-entry arc misses (split1016z s_w: capture 168.6 -> 219.6); acceptance stays FF >= 0 with the "
    "25 ps hold uncertainty and the 100 ps cross-entry die-skew reserve")}


def spec_z(side, sp):
    """split1016z successor: split1016y geometry, two literal ckv entries (stage A / stage B roots)"""
    top = sp['top']
    pin, cap, n, lw = NATIVE_Y_FAIL[side]
    sp['name'] = f'{top}_split1016z'
    sp['clock'] = 'multiple_cts_roots'
    sp['clock_ports'] = ['ckv[0]', 'ckvb[0]']
    sp['clock_data_paths'] = 'related_same_frequency'
    sp['clock_relationship'] = {"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0}
    sp['clock_entry_domains'] = {
        "core": {"ratio": [1, 1], "ports": ["ckv[0]"], "inputs": ["b", "rsv"], "outputs": ["s_mark", "s_par"]},
        "vmb": {"ratio": [1, 1], "ports": ["ckvb[0]"], "inputs": [], "outputs": ["t_vm"]}}
    fix = ("two literal entries of the one ckv root: ckv[0] clocks stage A (seam bank reads), the row counters, s_mark / "
           "s_par and the reset chain; ckvb[0] clocks only the 832 stage-B t_vm flops of the S band.  split1016y's single "
           "tree hung rows 0-2 of stage A on the band's half of the tree (stage-A clock 119..173 ps, 5 hold BUFx2 on the "
           "worst seam paths); with its own root the seam column is balanced to its own boundary reference.  Same RTL "
           "logic and cycles (stage B one serial edge after stage A), split1016y outline and seam")
    sp['structural_change'] = (f"split1016z re-kit of {top} (split1016y routed CLOSED but fails native capture: {pin} {cap} ps, "
                               f"{n} pins): " + fix + ".  " + sp['structural_change'])
    sp['reroute_reason'] = {"kind": "pin_register", "source": NATIVE_Y, "cell": top, "capture_ps": cap,
                            "launch_ps": lw, "fix": fix}
    if side in NATIVE_Z_FAIL:      # the split1016z view of this face is CLOSED but fails native: cite that receipt
        zp, zc, zn, zl = NATIVE_Z_FAIL[side]
        zfix = (f"re-route of the same split1016z kit with a near-miss hold ECO goal (hold_eco.hold_margin_ps "
                f"{HOLD_ECO['hold_margin_ps']}): b786448b1 pre-ECO capture 168.6, FF -1.43 on one ad0 -> bd0 cross-entry arc; "
                "the default ECO window (36.9 ps) padded 230 seam inputs")
        sp['reroute_reason'] = {"kind": "pin_register", "source": NATIVE_Z, "cell": top, "capture_ps": zc,
                                "launch_ps": zl, "fix": zfix}
        sp['structural_change'] = f"split1016z {zp} {zc} ps ({zn} pins) after the default hold ECO: {zfix}.  " + sp['structural_change']
    sp['job']['hold_eco'] = dict(HOLD_ECO)
    sp['job']['owner'] = 'claude:S-VM-CAPT-X8S2'
    sp['job']['branch'] = 'claude/svm-capt-x8s2-1016'
    return sp


def spec(side, half, faces):
    sp = spec_x(side, half, faces)
    return spec_z(side, spec_y(side, sp)) if half == 's' else sp


def spec_x(side, half, faces):
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
         "expect": "fail", "fail_regex": "mismatching_roots=[1-9][0-9]* RESULT FAIL CAPC_EQ mismatches=[1-9][0-9]*.*EQ_FAIL", "threads": 8, "peak_ram_gb": 16},
    ]
    return {
        "name": f"{top}_split1016x", "top": top, "kind": "tile", "sources": [SRC], "params": {},
        "clock_port": clk, "reset_ports": [rst], "outline": {"w": w, "h": H, "exact": True}, "macros": [],
        "pins": faces, "io_tcl": f"physical/s81_die_pins/capture_split_1016/{top}.tcl", "children": [], "inter": [],
        "recipe": 2, "io_flop_at_pins": {"cols": 4, "allow_none": True}, "inhold": True, "outhold": False,
        "keep_pin_regs": True, "pin_reg_split": True, "hold_pad": {"cell": "HB2xp67_ASAP7_75t_R"}, "layer_cap": "M5",
        "route": {"pd": 0.45, "threads": 8, "peak_ram_gb": 16, "period_ps": 770, "hold_margin_ns": 0.03,
                  "macro_halo_um": 5.4},
        "pin_regs": {"enable": False, "reason": (
            "Designed-in pin flops: every output is launched by a flop at its pin (banks / s_mark / s_par / t_vm stage B / "
            "t_ho; io_flop_at_pins), every input is captured by its first flop through at most one fixed-epoch "
            "enable/select mux (bank write enable at sample index n; x43 read select at serial edge 0/1/2; marker/parity "
            "samples at index 2/0) -- those flops ARE the pin registers of the 3:4 transfer.  A separate recipe-3 stage "
            "would add a stream cycle (t) / serial cycle (s) per crossing and sample the banks at every serial edge "
            "(1-tick windows on the seam) for no timing benefit; native audit (capture <= 190 / launch <= 220) applies.")},
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
            "rewritten >= 1.11 ns after their fixed read).  Parent footprint 118.8 x 172.8 (old 108 x 162): bit-major seam "
            "needs 1,680 M4 pins at 0.096 um; t width 32.4 for two 10.5 pins/um faces (gate oflop)."),
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
