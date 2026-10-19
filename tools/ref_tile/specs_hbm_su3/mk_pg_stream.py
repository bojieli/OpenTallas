"""TW-HBM-PGLG 10-19: kit spec for ot_hbm_su_static_pg_stream, the pg_clk (4:3) STREAM service of one LIGHT SU port-group
slice (two VM bank leaves, their serial<->stream multirate bridges, the PG_RSYNC leaf reset synchroniser, the LG tap pair
ot_hbm_su_static_pg_lg_tap and the COLLPORT inject slots). Sibling LEAF of the landed region slice
ot_hbm_su_static_pgslice_rgf_lp (kit hbm_su_pgslice_lg_light_d4g): it abuts the slice's S band at the slice E face.
Geometry follows the CLOSED LG tap leaf hbm_su_pg_lgtap_1017 (216 wide, 1,112-bit LG faces) grown one lattice row for
the slice-side face: 216 x 259.2 (43.2 lattice). Clock = two related roots of the die PLL (pg_clk core, clk_ctl serial
4/3) under related_pll_ratio: every bridge slot / inject slot / reset crossing is ordinary STA at the related edges.
Run from the repo root: python3 tools/ref_tile/specs_hbm_su3/mk_pg_stream.py"""
import json
from pathlib import Path

name = 'hbm_su_pg_stream_1019'
W, H = 216.0, 259.2
S_ = 'rtl/hbm_accel/generic/adapters/static_su'
WIT = 'results/rtl/tw_hbm_pglg_1019'
BENCH = 'tools/hbm_static/su_pgslice_rg_vl_run.sh'
B = dict(vmr_cmd=60, su_wq=562, su_rr=514, ij_v=4, ij_row=36, ij_bad=1, pg_fault=1, pos=4,
         lg_rq=34, lg_wq=562, lg_rr=514, lg_w_done=2, lg_read=2, lg_write=2, lg_fault=1,
         far_rq=34, far_wq=562, inj_rd=2, inj_addr=160, far_rr=514, far_w_done=2,
         clk_ctl=1, pg_clk=1, rst_n=1, bridge_rst_n=1)
ctl = ['clk_ctl', 'pg_clk', 'rst_n', 'bridge_rst_n']
# W = slice S band (serial side: fill requests, drain writes, fill returns, inject decode, faults, strap);
# E = LG near (the quarter's LG VM bank); N = far LG requests + COLL inject slots; S = far LG returns + clocks/reset at
# the S-face centre (pin flops on every face are the register mass).
pins = {'W': ['vmr_cmd', 'su_wq', 'su_rr', 'ij_v', 'ij_row', 'ij_bad', 'pg_fault', 'pos'],
        'E': ['lg_rq', 'lg_wq', 'lg_rr', 'lg_w_done', 'lg_read', 'lg_write', 'lg_fault'],
        'N': ['far_rq', 'far_wq', 'inj_rd', 'inj_addr'],
        'S': ['far_rr'] + ctl + ['far_w_done']}


def ranges(order, lo, hi):
    tot = sum(max(B[p], 4) for p in order)
    out, y = {}, lo
    for p in order:
        w = (hi - lo) * max(B[p], 4) / tot
        out[p] = [round(y, 3), round(y + w, 3)]
        y += w
    return out


pr = {}
pr.update(ranges(pins['W'], 4.0, H - 4.0))
pr.update(ranges(pins['E'], 4.0, H - 4.0))
pr.update(ranges(pins['N'], 4.0, W - 4.0))
pr.update({'far_rr': [4.0, 103.0]})
pr.update({p: [round(104.0 + 2.0 * i, 3), round(105.333 + 2.0 * i, 3)] for i, p in enumerate(ctl)})
pr.update({'far_w_done': [113.0, 116.0]})
serial_in = ['vmr_cmd', 'su_wq', 'rst_n', 'bridge_rst_n']
serial_out = ['su_rr']
core_in = ['pos', 'lg_rr', 'lg_w_done', 'lg_read', 'lg_write', 'far_rq', 'far_wq', 'inj_rd', 'inj_addr']
core_out = ['lg_rq', 'lg_wq', 'lg_fault', 'far_rr', 'far_w_done', 'ij_v', 'ij_row', 'ij_bad', 'pg_fault']
benches = [dict(name='rg_lockstep', cmd=f'bash {BENCH} {{RUN}}/bench/m0 0 1200', expect='pass',
                pass_regex='PGSLICE_RG PASS checks=', pass_witness=f'{WIT}/m0/bench.log', threads=8, peak_ram_gb=56,
                needs=['verilator']),
           dict(name='rg_mut8', cmd=f'bash {BENCH} {{RUN}}/bench/m8 8 1200', expect='fail',
                fail_regex='PGSLICE_RG FAIL errors=', fail_witness=f'{WIT}/m8/bench.log', threads=8, peak_ram_gb=56,
                needs=['verilator'], why='stream tile: COLLPORT inject slot read one slot late (ij decode of the wrong pg_clk slot)')]
s = dict(
    name=name, top='ot_hbm_su_static_pg_stream', kind='tile',
    sources=[f'{S_}/top/ot_hbm_su_static_pg_stream.sv', f'{S_}/top/ot_hbm_su_static_pg_lg_tap.sv',
             f'{S_}/programme/multirate_bridge.sv', f'{S_}/ot_hbm_su_static_vm_bank_leaf_s.sv',
             f'{S_}/ot_hbm_su_static_vm_ports.sv', 'rtl/lib/ot_rst_relay.sv',
             'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv',
             'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv', 'rtl/hdc/ot_hdc_delay.sv'],
    params=dict(QID=1, G=2, READ_RETURN=10, WRITE_RETURN=7, MULTIRATE=1, COLLPORT=1, RSYNC=1, STRAP=1),
    clock_port='pg_clk', reset_ports=['rst_n', 'bridge_rst_n'],
    # ROOT-RST landing on the serial root in 3 stages = one 3:4 epoch (3 serial = 4 stream edges): the bridge / inject
    # slot counters (bridge_rst_n, both roots) still release on an epoch-aligned edge, so their phase relation to the
    # die's common epoch is unchanged; reset release is one epoch later (scheduled constant, reported to H-D4G).
    reset_landing=dict(enable=True, stages=3, clock='clk_ctl',
                       why='3 serial stages = one 3:4 epoch: bridge/inject slot phase vs the common epoch preserved'),
    pins=pins, outline=dict(w=W, h=H, exact=True),
    layer_cap='M5', signal_max_layer='M5', pg_layer='M5', recipe=4,
    route=dict(pd=0.5, threads=4, peak_ram_gb=8, hold_margin_ns=0.03, macro_halo_um=5.4, pin_h='M4', pin_v='M3 M5',
               pin_balance=dict(h='M4', v='M3 M5', group_max=1), io_hold_margin_ns=0.03,
               synth_keep_modules=['ot_hbm_vm_lg_keep_reg']),
    pin_regs=dict(enable=False, reason=(
        'Every boundary bit already has its register in RTL: the multirate bridges write their serial slots straight '
        'from vmr_cmd/su_wq and drive su_rr from serial_rr registers; the LG tap registers its local/far/near inputs at '
        'the pins and its mux/output stage; the inject slots capture inj_rd/inj_addr on pg_clk. ij_*/pg_fault are '
        'decoded from those registers (timed as the related 4:3 crossing into the slice S band). Wrapper flops would '
        'add edges to the fixed VM calendar (10/7) and the slice offsets of the lockstep bench.')),
    io_flop_at_pins=dict(cols=4, allow_none=True), keep_pin_regs=True, inhold=False, outhold=False,
    std_area_um2=6000,
    structural_change=(
        'TW-HBM-PGLG 10-19: the pg_clk service of ot_hbm_su_static_pgslice_lg split out of the slice so the landed '
        'region slice (hbm_su_pgslice_lg_light_d4g) is single-frequency (PL-KIT landed clusters are related_same_frequency '
        'only). Contents = exactly the pg_clk logic of pgslice_lg (STRAP/RSYNC/MULTIRATE/COLLPORT); replaces the '
        'pg_lg_tap child (hbm_su_pg_lgtap_1017 CLOSED) inside it. Edges unchanged against pgslice_lg: lockstep '
        'tb_hbm_su_pgslice_rg (rgf_lp + pg_stream vs pgslice_lg) PASS checks=29952; stream mutant MUT 8 FAILS.'),
    job=dict(owner='Claude:TW-HBM-PGLG', branch='claude/tw-hbm-pglg-1019', tag='r1',
             purpose='HBM die d4g LIGHT SU slice stream sibling leaf (VM bank leaves + multirate bridges + LG tap + inject slots)',
             record_to=f'results/rtl/ref_tile/{name}', views_to=f'physical/ref_tile/{name}/views', auto_merge=False,
             extra_paths=[BENCH, 'rtl/test/hbm_accel/generic/tb_hbm_su_pgslice_rg.sv',
                          f'{S_}/top/ot_hbm_su_static_pgslice_rg.sv', f'{S_}/top/ot_hbm_su_static_pgslice_rgf.sv',
                          f'{S_}/top/lp', f'{S_}/top/ot_hbm_su_pgrg_parts.sv',
                          f'{S_}/top/ot_hbm_su_static_pgslice_lg.sv', f'{S_}/top/ot_hbm_su_static_pgslice.sv',
                          f'{S_}/arithmetic', f'{S_}/data_store', f'{S_}/reduction/ot_hbm_su_red_pretree.sv',
                          'rtl/common/landed_parent/ot_pl_land.sv', 'rtl/hbm_accel/generic/vm/static', 'rtl/hdc', 'rtl/proto',
                          'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2',
                          'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2', WIT],
             benches=benches),
    macros=[], children=[], inter=[], hold_budget='die', pin_ranges=pr,
    clock='multiple_cts_roots', clock_ports=['pg_clk', 'clk_ctl'], clock_data_paths='related_pll_ratio',
    clock_relationship=dict(kind='same_pll_fixed_phase', ratio=[4, 3], phase_ps=0),
    clock_entry_domains={'core': dict(ratio=[1, 1], ports=['pg_clk'], inputs=core_in, outputs=core_out),
                         'serial': dict(ratio=[4, 3], ports=['clk_ctl'], inputs=serial_in, outputs=serial_out)},
)
out = Path('tools/ref_tile/specs_hbm_su3') / f'{name}.json'
out.write_text(json.dumps(s, indent=1) + '\n')
print(out)
