#!/usr/bin/env python3
"""el1013-s81-vmfe/B5: ref_tile M5 specs of the ten new leaf masters of dsfd_vm_fe_h (RTL FROZEN 693940a56).

  python3 tools/s81_ph/s81_ph_vm_fe_h_leaf_specs.py     -> tools/ref_tile/specs_s81vmfe/<kit>.json  (then ref_tile.py gen)

Outlines = results/arch/s81_vm_fe_h_plan_1013.json `leaf_outlines` (measured std areas).  Pin FACES follow the data flow every
arrangement of the front end shares (die / clt words in on N, slice words out on S towards dsfd_vm_fsr, lane return and
control on the lane's side face towards fld, relay tiles straight through); pin RANGES keep each bus in bit order.  The exact
abutment plan (io_tcl) waits for a passing parent floorplan: the plan JSON says FAIL at 1,520.064 x 691.20."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import textbook_lint as TL  # noqa: E402

PLAN = json.loads((ROOT / 'results/arch/s81_vm_fe_h_plan_1013.json').read_text())
SRC = ['rtl/dsrom_sys/s81_ph/vm/dsfd_vm_fe_h.sv', 'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv', 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv',
       'rtl/dsrom_sys/mtp/dsfd_vm_wfc_ep.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv',
       'rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv', 'rtl/lib/ot_async_fifo.sv',
       'rtl/lib/ot_reset_sync.sv', 'rtl/common/ot_ratio_cdc_fifo.sv']
SRAM = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2'
EXTRA = ['rtl/dsrom_sys/s81_ph', 'rtl/dsrom_sys/mtp', 'rtl/dsrom_sys/s81_ctrl', 'rtl/lib', 'rtl/common', 'tools/s81_vm', 'tools/s81_ph',
         'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2', SRAM, 'physical/s81_ph_views/vm_master', 'results/arch']
STR = 'physical/s81_ph_views/vm_master/fe_h_str_clock_ref.sdc'
DENSE = {'pin_v': 'M3 M5', 'pin_balance': {'group_max': 32, 'h': 'M4', 'v': 'M3 M5'}}
# leaf: (pins by face, reset ports, pin ranges, route extras, what)
L = {
 'fxs': ({'N': ['w_v', 'w_row', 'w_m', 'w_d', 'w_flt', 'sok_o', 'rn_o'], 'S': ['s_o', 'k_o', 'clf_o'], 'W': ['ck', 'rni']}, ['rni'],
         {'w_d': [20.0, 226.0], 's_o': [2.4, 225.6], 'k_o': [226.0, 236.4], 'clf_o': [236.6, 239.4]}, DENSE,
         'order tile of 4 capture lanes: clt words in on N, 4 kept slice copies + counter copy out on S'),
 'fxr': ({'N': ['i', 'i_rf'], 'S': ['o', 'o_rf'], 'W': ['ck', 'rni'], 'E': ['rn_o']}, ['rni'],
         {'i': [2.4, 50.4], 'i_rf': [50.6, 51.6], 'o': [2.4, 50.4], 'o_rf': [50.6, 51.6]}, DENSE,
         'slice-bundle relay tile (592 b + rf): in-pin flop -> out-pin flop, N to S'),
 'frr': ({'N': ['i'], 'S': ['o'], 'W': ['ck']}, [], {'i': [2.4, 40.8], 'o': [2.4, 40.8]}, DENSE, 'lane-return mid-hop relay (526 b, one flop a bit)'),
 'fra': ({'W': ['i', 'ck'], 'E': ['o']}, [], {}, {}, 'LARM mid-hop relay (15 b, one flop a bit)'),
 'frg': ({'W': ['i', 'ck'], 'E': ['o']}, [], {}, {}, 'grant mid-hop relay (1 b)'),
 'flt': ({'N': ['p_v', 'p_t', 'p_m', 'p_d', 'p_flt'], 'W': ['ret', 'av', 'ok', 'ovf', 'sflt', 'g', 'arm_v', 'arm_base', 'rni', 'rn_o', 'ck', 'stride', 'off']},
         ['rni'], {'p_d': [8.0, 208.0], 'ret': [8.0, 117.0]}, {'peak_ram_gb': 32},
         'landing lane: 64 x 512 SRAM + row relay; producer word in on N, return word + control on the side face towards fld (W, or E mirrored MY)'),
 'fld': ({'N': ['ret'], 'S': ['s_o', 'k_o', 'g', 't_cts', 'ovr_o', 'sflt_o', 'rn_o', 'av', 'ok', 'ovf', 'sflt'], 'W': ['ck', 'rni']}, ['rni'],
         {'ret': [2.4, 256.8], 's_o': [2.4, 150.0]}, DENSE, 'landing drain: 10 x 526-b return words in, arbiter, ports 10 / 11 order registers'),
 'fcc': ({'N': ['vwe', 'vwa', 'vwd', 'vre', 'vra', 'cks', 'rss'], 'S': ['s_o'], 'E': ['k_o', 'so_o', 'rn_o'], 'W': ['ck', 'rni']}, ['rni', 'rss'],
         {'vwd': [20.0, 160.0], 's_o': [2.4, 179.0]}, {'peak_ram_gb': 48, 'threads': 16},
         'ctrl ratio CDC (cks -> ck), ports 3 / 4 order registers'),
 'fcw': ({'N': ['f_swv', 'f_swd', 't_swg', 'f_srv', 'f_srd', 't_srg', 't_ks', 'rst'], 'S': ['s_o'], 'E': ['k_o', 'err_o', 'rn_o'], 'W': ['ck', 'rni']},
         ['rni', 'rst'], {'f_swd': [10.0, 130.0], 's_o': [2.4, 148.8]}, DENSE, 'WFC endpoint without the dead write queue, ports 0 / 1 order registers'),
 'fcn': ({'N': ['cv', 'cd', 'dv', 'dt', 'f_cq', 'c_wv', 'c_wd', 'c_wr', 't_rdy', 'rst', 'rss', 'cks', 'k_i', 'clf_i'],
          'S': ['s_o', 'rf_o', 'f_p2c', 'fe_flt'], 'E': ['arm_v', 'arm_base', 'so_i', 'ovr_i', 'sflt_i', 'err_i', 'rn_o'], 'W': ['ck']}, ['rst', 'rss'],
         {'k_i': [2.4, 150.0], 's_o': [2.4, 232.0]}, {**DENSE, 'peak_ram_gb': 48},
         'central: command decode, counter K, done mux, ports 2 / 5 .. 9 order registers, reset root'),
}
mods = TL.rtl_modules([(ROOT / SRC[0]).read_text(errors='replace')])
out = ROOT / 'tools/ref_tile/specs_s81vmfe'; out.mkdir(parents=True, exist_ok=True)
for leaf, (pins, rst, rng, rx, what) in L.items():
    top = f'dsfd_vm_{leaf}'
    ports = TL.module_port_dirs(mods[top]); named = [p for v in pins.values() for p in v]
    assert sorted(named) == sorted(ports), (leaf, sorted(set(ports) ^ set(named)))
    fp = PLAN['leaf_outlines'][top]
    s = {'name': f'{top}_m5', 'top': top, 'kind': 'tile', 'sources': SRC + ([f'{SRAM}/ot_sram_1r1w_64x512_m1_r2c2_bb.v'] if leaf == 'flt' else []),
         'orfs_vars': {'VERILOG_INCLUDE_DIRS': 'rtl/dsrom_sys/s81_ph/vm'}, 'clock_port': 'ck', 'reset_ports': rst,
         'outline': {'w': fp['outline'][0], 'h': fp['outline'][1]}, 'std_area_um2': fp['std_cell_area_um2'], 'pins': pins, 'pin_ranges': rng,
         'macros': [{'view': SRAM, 'count': 1, 'at': fp['macro_at']}] if leaf == 'flt' else [],
         'route': {'pd': 0.5, 'threads': 8, 'peak_ram_gb': 24, 'hold_margin_ns': 0.03, **rx},
         'job': {'owner': 'Claude:el1013-s81-vmfe/B5', 'branch': 'claude/el1013-s81-vmfe', 'tag': 'p1', 'extra_paths': EXTRA,
                 'benched_by': 's81_vm_fe_h_lockstep',
                 'purpose': f'el1013-s81-vmfe/B5 dsfd_vm_fe_h leaf {top} at M5 ({what}); RTL FROZEN 693940a56 (lockstep 9/9 bit-exact, 4 hierarchy '
                            f'mutants fail, pin-register check PASS); {fp["flops"]} mapped flops, std {fp["std_cell_area_um2"]} um2 measured, outline '
                            f'{fp["outline"][0]} x {fp["outline"][1]}.  ck signed off at 833.3 ps (VM serial clock is 1,111.1 ps: stricter). PIN FACES by '
                            'data flow, bit-ordered ranges; the exact abutment plan waits for a passing parent floorplan '
                            '(results/arch/s81_vm_fe_h_plan_1013.json: FAIL at 1,520.064 x 691.20, 8 of 10 lanes), so this route is first closure '
                            'evidence of the leaf and is re-routed if its faces move.'}}
    if leaf in ('fcc', 'fcn'): s['sdc_extra'] = [STR]
    (out / f'{top}_m5.json').write_text(json.dumps(s, indent=1) + '\n')
    print(top, fp['outline'], {f: len(v) for f, v in pins.items()})
