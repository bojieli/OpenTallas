#!/usr/bin/env python3
"""Pin plans + ref_tile specs of the DECISION B capture status leaves (S-VM, 2026-10-16).

dsfd_capt_status_dual (two-clock ratio-FIFO leaf) -> two single-clock 21.6 x 86.4 leaves that abut on a bank seam
(rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_status_x43.sv):
  dsfd_capt_status_x43_t  ck   f_sn on E, banks b0/b2/b3 + bpar/t_mark on the W seam, ck/rst on N (M5)
  dsfd_capt_status_x43_s  ckv  banks on the E seam, t_st on W, ckv/rsv on N (M5)
BIT-MAJOR seam: b0[i] / b2[i] / b3[i] at y = 4.332 + 0.384 (3i + 0/1/2) (8 M4 tracks, the gate's oflop face-density
limit), bpar[2:0] / t_mark after bit 63; f_sn[i] (T east) and t_st[i] (S west) at the centre of bit i's triplet, so
every bit runs in a straight row across both leaves.

Reproduces the committed files written by hand at cd7c02a09 / 61d167710 byte-identically (capture_split_specs.py
--check and test_capture_split_regen.py enforce it).
Usage: capx43_status_kits.py   (writes physical/s81_die_pins/capture_split_1016/dsfd_capt_status_x43_{t,s}.tcl + specs)
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PINS = ROOT / 'physical/s81_die_pins/capture_split_1016'
SPECS = ROOT / 'tools/ref_tile/specs_s81_capture_split_1016'
SRC = 'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_status_x43.sv'
W, H = 21.6, 86.4
Y0, SLOT = 4.332, 0.384
M4 = '-pin_size {0.192 0.024}'
M5 = '-pin_size {0.024 0.192}'
HALVES = ('t', 's')
CLK = dict(t=('ck', 'rst'), s=('ckv', 'rsv'))
ROLE = dict(t='stream', s='serial')
IO = dict(t='f_sn', s='t_st')        # the leaf's die-facing bus (T east / S west)


def line(name, layer, x, y, size):
    return f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.6f} {y:.6f}}} {size} -force_to_die_boundary'


def header(half):
    return [
        f'# S-VM-CAPT-STATUS 2026-10-16: explicit pin plan of the {ROLE[half]} (_{half}, {CLK[half][0]}) leaf of dsfd_capt_status_dual (DECISION B x43 split).',
        "# Faces as dsfd_capt_status_dual.tcl (f_sn E, t_st W; clock + reset N, M5).  BIT-MAJOR bank seam over the face: b0[i] / b2[i] / b3[i]",
        "# at y = 4.332 + 0.384 (3i + 0/1/2) (8 M4 tracks; the gate's oflop face-density limit), bpar[2:0] / t_mark after bit 63, on the T west",
        "# face and the S east face (the leaves abut: S west, T east, 2 x 21.6 x 86.4); f_sn[i] (T east) and t_st[i] (S west) at the",
        "# centre of bit i's triplet, so every bit runs in a straight row across both leaves."]


def pins(half):
    """the pin Tcl text of one leaf"""
    seam_x = 0.0 if half == 't' else W        # T's seam is its west face, S's its east face
    io_x = W if half == 't' else 0.0
    ck, rs = CLK[half]
    io = [line(f'{IO[half]}[{i}]', 'M4', io_x, Y0 + SLOT * (3 * i + 1), M4) for i in range(64)]
    seam = [line(f'b{b}[{i}]', 'M4', seam_x, Y0 + SLOT * (3 * i + k), M4) for i in range(64) for k, b in enumerate((0, 2, 3))]
    seam += [line(f'bpar[{j}]', 'M4', seam_x, Y0 + SLOT * (192 + j), M4) for j in range(3)]
    seam += [line('t_mark', 'M4', seam_x, Y0 + SLOT * 195, M4)]
    out = header(half) + [line(f'{ck}[0]', 'M5', 10.092, H, M5), line(f'{rs}[0]', 'M5', 11.916, H, M5)]
    out += io + seam if half == 't' else seam + io
    return '\n'.join(out) + '\n'


STRUCT = ("DECISION B successor of the dsfd_capt_status_dual hard leaf (split1016: FF hold -81 ps on the intra-leaf "
          "ot_ratio_cdc_fifo 1-tick 4:3 arcs, hold repair stalled; split1016b co-located entries, same RTL). The ratio FIFO is "
          "replaced by a fixed-phase 3-bank x43 transfer split per clock root (ot_s81_vm_x43 pattern, CLOSED VM x43 leaves): "
          "dsfd_capt_status_x43_t (ck) samples f_sn at stream index 0/2/3 into banks b0/b2/b3; dsfd_capt_status_x43_s (ckv) "
          "reads them at serial edge 2/0/1 into t_st. Marker moved to stream index 2 so no cross-root arc has a 1-tick window "
          "(worst setup 2 ticks = 513 ps). dsfd_capt_status_dual is now a logic-free wrapper. Latency: f_sn on t_st 6/7/8 VCO "
          "ticks after stream index 2/3/0 (stream index 1 not sampled); epoch-reset startup contract. ")
LEAF = dict(
    t="T leaf: 192 bank flops + epoch counter/parity/marker; outputs all flops; outhold off (VM x43_t precedent: bank read "
      ">= 1 tick after launch, rewritten >= 4 ticks after the fixed read). ",
    s="S leaf: input pin registers sh0/sh2/sh3/bq at every serial edge (zero added latency), fixed-edge 3:1 select into stq "
      "(64 flops), epoch parity + marker assertions (sticky, OR-ed into t_st[3]); inhold pads the coincident-edge b0 arc. ")
TAIL = "Seam pins spread at 8 M4 tracks (gate oflop face density); f_sn / t_st moved to the centre of their bit's triplet."
PIN_REGS = dict(
    t="Every output (b0/b2/b3, bpar, t_mark) is a dedicated flop and every data input f_sn lands directly in the bank flops "
      "(one phase hold-mux): the banks ARE the pin registers. A generic recipe-3 input/output register would shift the fixed "
      "3:4 sample indices by one stream cycle (unpriced against the epoch schedule and the S leaf's fixed read edges).",
    s="Every input (b0/b2/b3/bpar, t_mark) is registered in RTL at every serial edge (sh0/sh2/sh3/bq/mk, zero added latency, "
      "see dsfd_capt_status_x43.sv) and t_st is the stq flop. A generic recipe-3 output register would add one serial cycle to "
      "the status lane (unpriced).")
SEAM = ['b0', 'b2', 'b3', 'bpar', 't_mark']
TB = ('rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_status_x43.sv rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_split.sv '
      'rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_ph/test/tb_dsfd_capt_status_x43.sv')


def benches():
    sim = f'mkdir -p {{RUN}} && iverilog -g2012 -o {{RUN}}/sim -s tb_dsfd_capt_status_x43 {TB} && '
    return [
        dict(name='lint', cmd="mkdir -p {RUN} && printf '%s\\n' 'module ot_lint_top; dsfd_capt_status_dual u_top (); endmodule' > "
             "{RUN}/ot_lint_top.sv && verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN "
             "-Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top {RUN}/ot_lint_top.sv rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_split.sv "
             "rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_status_x43.sv rtl/hdc/ot_hdc_prefix.sv rtl/dsrom_sys/s81_ph/ot_s81ph_cap_tile.sv "
             "rtl/common/ot_ratio_cdc_fifo.sv rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_cd.sv && echo lint-ok",
             expect='pass', threads=1, peak_ram_gb=4, needs=['verilator']),
        dict(name='status_x43_unit', cmd=sim + 'for m in 0 1 2 3; do vvp -n {RUN}/sim +mode=$m; done', expect='pass',
             pass_regex='TB_STX43 PASS mode 0 words', threads=1, peak_ram_gb=2, needs=['iverilog']),
        dict(name='status_x43_unit_slip', cmd=sim + 'for m in 1 2 3; do vvp -n {RUN}/sim +mode=$m; done', expect='pass',
             pass_regex='TB_STX43 PASS mode 3 fault', threads=1, peak_ram_gb=2, needs=['iverilog']),
        dict(name='status_x43_unit_mut_phase', cmd=f'mkdir -p {{RUN}} && iverilog -g2012 -DDSFD_CAPT_STX43_MUT_PHASE -o {{RUN}}/simp '
             f'-s tb_dsfd_capt_status_x43 {TB} && vvp -n {{RUN}}/simp +mode=0', expect='fail', fail_regex='TB_STX43 FAIL mode 0',
             threads=1, peak_ram_gb=2, needs=['iverilog']),
        dict(name='capture_split_exact', cmd="bash tools/s81_ph/capc_split_bench.sh {RUN}/bench eq 'mix mix11 mix12 mix13 trace err over range rreq'",
             expect='pass', pass_regex='^CAPC_BENCH PASS cases=9$', threads=8, peak_ram_gb=16),
        dict(name='capture_split_mutant', cmd="bash tools/s81_ph/capc_split_bench.sh {RUN}/mut mut 'mix' S81PH_CAPS_MUT_STATUS",
             expect='fail', fail_regex='CAPC_EQ mismatches=[1-9][0-9]*.*EQ_FAIL', threads=8, peak_ram_gb=16)]


def spec(half):
    top = f'dsfd_capt_status_x43_{half}'
    ck, rs = CLK[half]
    faces = dict(E=[IO[half]], W=list(SEAM), N=[ck, rs], S=[]) if half == 't' else dict(E=list(SEAM), W=[IO[half]], N=[ck, rs], S=[])
    why = f'New single-clock leaf {top} (replaces the two-clock dsfd_capt_status_dual hard leaf); no prior slot or closed view'
    scr = dict(contract='S81 capture split 1016 (codex/s81-hub-parents-0811)', version='x43-status-1016', why=why)
    return dict(
        name=top + '_split1016x', top=top, kind='tile', sources=[SRC], params={}, clock_port=ck + '[0]', reset_ports=[rs],
        outline=dict(w=W, h=H), macros=[], pins=faces, io_tcl=str((PINS / (top + '.tcl')).relative_to(ROOT)), children=[], inter=[],
        recipe=2, io_flop_at_pins=dict(cols=4, allow_none=True), inhold=True, outhold=False, keep_pin_regs=True, pin_reg_split=True,
        hold_pad=dict(cell='HB2xp67_ASAP7_75t_R'), layer_cap='M5',
        route=dict(pd=.45, threads=8, peak_ram_gb=16, period_ps=770, hold_margin_ns=.03, macro_halo_um=5.4), clock='cts',
        structural_change=STRUCT + LEAF[half] + TAIL, slot_change_request=dict(scr),
        reroute_reason=dict(kind='slot_change', slot_change_request=dict(scr),
                            why='new single-clock leaf master; no closed view exists for this block',
                            contract='S81 capture split 1016: dsfd_capt_status_dual DECISION B x43 split'),
        job=dict(owner='claude:S-VM-CAPT-STATUS', branch='codex/s81-hub-parents-0811', tag='x43',
                 purpose=f'DECISION B {top}: single-clock leaf of the fixed-phase status transfer; exact capture split bench (x43 sample '
                         'rule) + unit/epoch-slip benches + mutants, TT/FF/DRC0 + native audit; parent 3:4 arcs open',
                 extra_paths=['tools/s81_ph', 'rtl/dsrom_sys/s81_ph', 'rtl/common', 'rtl/dsrom_sys/s81_glue', 'rtl/hdc',
                              'physical/s81_die_pins/capture_split_1016'], benches=benches()),
        pin_regs=dict(enable=False, reason=PIN_REGS[half]))


def outputs():
    """{path: text} of the two status leaves' pin Tcl + spec json"""
    out = {}
    for half in HALVES:
        top = f'dsfd_capt_status_x43_{half}'
        out[PINS / (top + '.tcl')] = pins(half)
        out[SPECS / (top + '.json')] = json.dumps(spec(half), indent=1) + '\n'
    return out


if __name__ == '__main__':
    for path, text in outputs().items():
        path.write_text(text)
        print('CAPX43_STATUS_KIT', path.relative_to(ROOT))
