#!/usr/bin/env python3
"""Q-ELEM-SUC 2026-10-16: spec of the hardened qfd_sp_su64_sfu parent (kit physical/ref_tile/qfd_sp_su64_sfu_pr).
    make_spec.py   (from the repo root) -> tools/ref_tile/specs_q_su64/qfd_sp_su64_sfu_pr.json + kit pin files"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
NAME = 'qfd_sp_su64_sfu_pr'
KIT = ROOT / 'physical/ref_tile' / NAME
subprocess.run([sys.executable, str(ROOT / 'tools/qwen_split/su64_parent_plan.py'), str(KIT)], check=True)
pins = json.loads((KIT / 'assigned_pins.json').read_text())
children = json.loads((KIT / 'children.json').read_text())
(KIT / 'children.json').unlink()
clocks = ['ck'] + [f'ck_{f}{i}' for f, n in [('head', 64), ('exp', 64), ('rcp', 64), ('rsq', 64), ('align', 16), ('lane', 64),
                                             ('red', 9)] for i in range(n)]
soft = ['ck'] + [f'ck_lane{i}' for i in range(64)] + [f'ck_align{i}' for i in range(16)] + [f'ck_red{i}' for i in range(9)]
hard = {f'ck_{k}{l}': f'u_su.u_su.g_lane[{l}].g_tile.u_tile.u_{k}.u_n/clk' for l in range(64) for k in ('head', 'exp', 'rcp', 'rsq')}
faces = {f: [p for p in v] for f, v in pins['pins'].items()}
faces['ANY'] = clocks
SRCS = [l.strip() for l in (ROOT / 'tools/qwen_split/su64_parent_sources.f').read_text().split('\n') if l.strip()]
B = 'bash tools/qwen_split/run_su64_pinreg_bench.sh {RUN}/bench/%s %d %d'
def bench(name, mode, mut, expect):
    b = dict(name=name, cmd=B % (name, mode, mut), expect=expect, threads=8, peak_ram_gb=48, needs=['verilator'])
    b['pass_regex' if expect == 'pass' else 'fail_regex'] = '^PASS qfd_su64_pinreg' if expect == 'pass' else '^FAIL qfd_su64_pinreg'
    return b
benches = [
    dict(name='lint_parent_hard', cmd='verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DSYNTHESIS '
         '-DOT_SU_LANE_HARD -GPINREG=1 --top-module qfd_sp_su64_sfu ' + ' '.join(SRCS) + ' rtl/test/qwen_split/su64_native_views_bb.v',
         expect='pass', threads=1, peak_ram_gb=8, needs=['verilator']),
    bench('pinreg_su_ops', 0, 0, 'pass'),
    bench('pinreg_copy', 1, 0, 'pass'),
    bench('pinreg_mut_old_vm_edge', 0, 1, 'fail'),
    bench('pinreg_mut_copy_latency', 1, 2, 'fail'),
    bench('pinreg_mut_sd_old_edge', 0, 3, 'fail'),
    bench('pinreg_mut_cp_old_edge', 1, 4, 'fail'),
    dict(name='copy_module_gate', cmd='bash tools/qwen_split/run_su_static_copy_gate.sh {RUN}/bench/copy_module_gate',
         expect='pass', pass_regex='^PASS raw4096words', threads=1, peak_ram_gb=4, needs=['iverilog']),
]
spec = dict(
    name=NAME, top='qfd_sp_su64_sfu', kind='cluster', clock='hybrid_entries', clock_port='ck', clock_ports=clocks,
    clock_cts_roots=soft, required_hybrid_roots=dict(standard_cell_cts=soft, hard_child_entry=hard),
    outline=pins['outline'], children=children, macros=[], sources=SRCS, defines=['OT_SU_LANE_HARD'],
    hard_define='OT_SU_LANE_HARD', params={'PINREG': 1}, layer_cap='M7', recipe=2, reset_ports=['rst_n'],
    keep_pin_regs=True, pin_reg_split=True, inhold=True, outhold=True, io_flop_at_pins={'cols': 8},
    route=dict(pd=0.5, threads=32, peak_ram_gb=160, hold_margin_ns=0.03, macro_halo_um=5.4),
    pins=faces, pin_ranges=pins['pin_ranges'], io_tcl=f'physical/ref_tile/{NAME}/assigned_pins.tcl',
    child_lattice_um=2.16, inter=[], hold_pad={'cell': 'HB2xp67_ASAP7_75t_R'},
    std_area_um2=600000,
    fill_reason={'pin_bound': 'Die frame 3240 x 3672 (q2o1 SU slot, Q-COMPUTE-DIE option (a), 2026-10-16) holds 256 hard '
                 'children (4.84 mm2) in an 8x8 lane grid at 388.8 x 432 (43.2-um child lattice) pitch spread over the whole slot (no empty '
                 'quadrant); the 26,025 data pins on three faces (S 8,511 / W 8,057 / E 7,405 at <= 10.4 pins/um/layer) and '
                 'the face pin registers set the edges.'},
    structural_change=('Hardened qfd_sp_su64_sfu (die master, PINREG=1): 64 x (CROM5 lane head crom5_f + exp/rcp/rsq native45), '
                       'every pin registered (va/ca/xsw/sd/cp pin registers; SU requests/writes keep their far-pin edge via '
                       'RD-1 lane request relays + align EML 1), 256 hard-child clock entries as interior M7 pins over each '
                       'child clock pin, 90 standard-cell CTS roots (ck, ck_lane x64, ck_align x16, ck_red x9; vred soft, its '
                       'closed views fail the native audit).  Schedule deltas: results/rtl/qwen_su64_pinreg_1016/schedule_delta.json.'),
    reroute_reason=dict(kind='rtl_change', source='results/rtl/qwen_su64_pinreg_1016/schedule_delta.json', cell='qfd_sp_su64_sfu',
                        why='First hardened SU parent; replaces the generated q2o1 frame. PINREG removes the comb pin->pin arcs '
                            '(external_vm_a->va, si stage->ca) and registers va/xsw/sd/cp.'),
    job=dict(owner='Claude:Q-ELEM-SUC', branch='claude/qelem-suc-1016', tag='pr1',
             purpose='Hardened SU parent qfd_sp_su64_sfu (PINREG=1) from native lane heads/SFUs, interior clock entries',
             benches=benches, extra_paths=['rtl/test/qwen_split'], cycles_added=0,
             views_to=f'physical/ref_tile/{NAME}/views', record_to=f'results/rtl/ref_tile/{NAME}'),
)
out = ROOT / f'tools/ref_tile/specs_q_su64/{NAME}.json'
out.write_text(json.dumps(spec, indent=1) + '\n')
print(out, len(children), len(clocks))
