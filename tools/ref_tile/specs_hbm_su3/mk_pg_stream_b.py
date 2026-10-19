"""HBM-PGSTREAM-B 10-19 (coordinator decision 07:11, lanes/HBM-SAFE-PGSTREAM.md option b): ONE pg_stream tile with two
regional clock roots and the banked 3:4 seam INSIDE as a landed crossing. Replaces the abutted one-root halves
hbm_su_pg_stream_q_1019 + hbm_su_pg_stream_s_1019 (2 x 432 x 216: 2 x 2,346 seam pins, every pin-legal outline 1-3 % util,
GPL-0305 with routability ON) and the two-root hbm_su_pg_stream_1019 (gate FAIL 0ff805777: its 3:4 bridge crossed with
logic, timed at the 1q related default).
RTL top = ot_hbm_su_static_pg_stream_split (pg_stream_q on clk_ctl + pg_stream_s on pg_clk, the banked seam between them;
the lockstep tb_hbm_su_pg_stream_split has always simulated exactly this module). External ports = the old pg_stream ports
(3,580 pins); the 2,346-b seam is internal.
Seam = landed crossings: spec "seam_windows" (tools/ref_tile/clock_entry_constraints.py seam_window_sdc) times every
bank -> reader arc at its calendar window (request 4q / 2q, return 2q / 4q, inject 3q / 7q; q = 277.8 ps at 833.333)
plus the sign-off inter-clock reserve, instead of the 1q - 150 ps related default. The bench window checker asserts the
same per-group windows (seam-window mutant MUT 12 fails by window only).
Geometry: the coordinator estimate ~150 x 150 is not pin-legal (W face 1,183 slice pins -> 8/um > 6/um). The outline is
the proven pg_stream outline 216 x 259.2 (5 x 6 lattice, 1.2:1; gate 0ff805777 converged GPL with routability ON, CTS
spread 60 / 57 ps, trial GRT overflow 0), W 4.7/um, E 4.6/um. Utilisation waived pin-bound (~3,500 um2 synthesized).
Clock pins: clk_ctl at the S-face west end (serial register mass: bridge_q banks / serial_rr / ijq, beside the W slice
face), pg_clk at the S-face east end (VM bank leaves / LG tap / bridge_s beside the E LG face): two regional roots.
Run from the repo root: python3 tools/ref_tile/specs_hbm_su3/mk_pg_stream_b.py"""
import json
from pathlib import Path

name = 'hbm_su_pg_stream_b_1019'
W, H = 216.0, 259.2
S_ = 'rtl/hbm_accel/generic/adapters/static_su'
WIT = 'results/rtl/hbm_pgstream_cdc_r18_1019'
BENCH = 'tools/hbm_static/su_pg_stream_split_vl_run.sh'
B = dict(vmr_cmd=60, su_wq=562, su_rr=514, ij_v=4, ij_row=36, ij_bad=1, pg_fault=1, pos=4,
         lg_rq=34, lg_wq=562, lg_rr=514, lg_w_done=2, lg_read=2, lg_write=2, lg_fault=1,
         far_rq=34, far_wq=562, inj_rd=2, inj_addr=160, far_rr=514, far_w_done=2,
         clk_ctl=1, pg_clk=1, rst_n=1, bridge_rst_n=1)
pins = {'W': ['vmr_cmd', 'su_wq', 'su_rr', 'ij_v', 'ij_row', 'ij_bad', 'pg_fault', 'pos'],
        'E': ['lg_rq', 'lg_wq', 'lg_rr', 'lg_w_done', 'lg_read', 'lg_write', 'lg_fault'],
        'N': ['far_rq', 'far_wq', 'inj_rd', 'inj_addr'],
        'S': ['clk_ctl', 'rst_n', 'bridge_rst_n', 'far_rr', 'far_w_done', 'pg_clk']}


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
pr.update({'clk_ctl': [20.0, 21.333], 'rst_n': [24.0, 25.333], 'bridge_rst_n': [28.0, 29.333],
           'far_rr': [36.0, 180.0], 'far_w_done': [182.0, 185.0], 'pg_clk': [194.0, 195.333]})
serial_in = ['vmr_cmd', 'su_wq', 'rst_n', 'bridge_rst_n']
serial_out = ['su_rr', 'ij_v', 'ij_row', 'ij_bad', 'pg_fault']
core_in = ['pos', 'lg_rr', 'lg_w_done', 'lg_read', 'lg_write', 'far_rq', 'far_wq', 'inj_rd', 'inj_addr']
core_out = ['lg_rq', 'lg_wq', 'lg_fault', 'far_rr', 'far_w_done']


def bench(nm, sub, mut, rr=18, wr=15, qid=1, why=None):
    b = dict(name=nm, cmd=f'bash {BENCH} {{RUN}}/bench/{sub} {mut} 1500 {qid} {rr} {wr} 1', threads=4, peak_ram_gb=8,
             needs=['verilator'])
    if why is None:
        b.update(expect='pass', pass_regex='PG_STREAM_SPLIT PASS checks=', min_count_regex='checks=(\\d+)',
                 pass_witness=f'{WIT}/{sub}/bench.log')
    else:
        b.update(expect='fail', fail_regex='PG_STREAM_SPLIT FAIL errors=', fail_witness=f'{WIT}/{sub}/bench.log', why=why)
    return b


benches = [
    bench('pgs_b_lockstep', 'm0', 0),
    bench('pgs_b_lockstep_rr10_regression', 'rr10', 0, 10, 7),
    bench('pgs_b_lockstep_qid0', 'qid0', 0, qid=0),
    bench('pgs_b_mut12_seam_window', 'm12', 12, why='seam-window mutant: request bank read one stream edge early into a '
          'pre-stage (same data, same launch edge) -> setup 1q < the declared 4q seam window; window checker only'),
    bench('pgs_b_mut14_cross_reset', 'm14', 14, why='serial bridge reset must not clear stream-local sticky fault publication'),
    bench('pgs_b_mut13_fault_publish', 'm13', 13, why='registered fault source inverted: independent publication and exact two-stage serial capture scoreboard'),
    bench('pgs_b_mut3', 'm3', 3, why='return staging removed: bank rewritten 0 ps after its read (window checker)'),
    bench('pgs_b_mut2', 'm2', 2, why='stream half reads the wrong request bank'),
    bench('pgs_b_mut8', 'm8', 8, why='serial half reads the wrong inject bank'),
]
seam_windows = [
    dict(name='bridge_request', launch='clk_ctl', capture='pg_clk',
         **{'from': ['*u_bq.rq_b0*', '*u_bq.rq_b1*', '*u_bq.wq_b0*', '*u_bq.wq_b1*']}, setup_q=4, hold_q=2,
         why='request bank n mod 2 written at serial n (tick 4n), read at stream 4n+6/5/4, rewritten 4n+8 '
             '(multirate_bridge_split.sv; bench measured 4q / 2q)'),
    dict(name='bridge_return', launch='pg_clk', capture='clk_ctl', **{'from': ['*u_bs.rr_b0*', '*u_bs.rr_b1*']},
         setup_q=2, hold_q=4,
         why='return bank written at the stream capture edge, staged one serial edge early (X = 8 at RR 10/7 and 18/15): '
             'setup 2q, rewrite-after-read 4q (bench measured)'),
    dict(name='inject', launch='pg_clk', capture='clk_ctl', **{'from': ['*u_s.ijb0*', '*u_s.ijb1*', '*u_s.ijb2*']},
         setup_q=3, hold_q=7,
         why='inject banks written at stream 12m / 12m+3 / 12m+9, read at serial 12m+4 / +8 / +12, rewritten one epoch '
             'later (bench measured 3q / 7q)'),
]
WHY = ('HBM-PGSTREAM-B 10-19 (coordinator 07:11, HBM-SAFE-PGSTREAM option b): ONE tile = ot_hbm_su_static_pg_stream_split '
       '(pg_stream_q on clk_ctl + pg_stream_s on pg_clk) with the banked 2,346-b seam INSIDE as landed crossings, two '
       'regional roots. Replaces the abutted q/s halves (2 x 432 x 216; 2 x 2,346 seam pins; pin-legal outlines 1-3 % util; '
       'GPL-0305 under routability ON, gates 20261019-063054) and supersedes hbm_su_pg_stream_1019 (FAIL 0ff805777: '
       'cross_clock -126.9 / -479.3 ps on the 1q related default with logic in the crossing). The seam arcs are now '
       'bank -> mux -> register with calendar windows request 4q/2q, return 2q/4q, inject 3q/7q, constrained by spec '
       'seam_windows (set_max/min_delay, latency included, sign-off inter-clock reserve on top). RTL edges = '
       'TW3-PGSTREAM split (ij +1 serial, pg_fault +2 serial, given to H-D4G). ')
PIN_BOUND = ('3,580 external pins (W 1,183 slice S band, E 1,117 LG near, N 758 far requests + COLL inject, S 522) on '
             '~3,500 um2 synthesized: <= 6/um needs >= 197 um on W/E, so a 40-60 % outline (~80 x 80) cannot carry them; '
             '216 x 259.2 = the proven pg_stream outline (GPL converged with routability ON at 0ff805777). Pin-bound, waived.')
s = dict(
    name=name, top='ot_hbm_su_static_pg_stream_split', kind='tile',
    sources=[f'{S_}/top/ot_hbm_su_static_pg_stream_split.sv', f'{S_}/programme/multirate_bridge_split.sv',
             'rtl/lib/ot_rst_relay.sv', f'{S_}/ot_hbm_su_static_vm_bank_leaf_s.sv', f'{S_}/ot_hbm_su_static_vm_ports.sv',
             'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv',
             'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv', 'rtl/hdc/ot_hdc_delay.sv'],
    params=dict(QID=1, G=2, READ_RETURN=18, WRITE_RETURN=15, STRAP=1, FAULT_REG=1),
    clock_port='pg_clk', reset_ports=['rst_n', 'bridge_rst_n'],
    reset_landing=dict(enable=True, stages=3, clock='clk_ctl',
                       why='3 serial stages = one 3:4 epoch (12q): bridge / inject slot counters of both roots release on '
                           'the same epoch-aligned edge (as hbm_su_pg_stream_1019)'),
    pins=pins, outline=dict(w=W, h=H, exact=True),
    layer_cap='M5', signal_max_layer='M5', pg_layer='M5', recipe=4,
    route=dict(pd=0.5, period_ps=833.333, threads=8, peak_ram_gb=12, hold_margin_ns=0.03, macro_halo_um=5.4, pin_h='M4',
               pin_v='M3 M5', pin_balance=dict(h='M4', v='M3 M5', group_max=1), io_hold_margin_ns=0.03,
               synth_keep_modules=['ot_hbm_vm_lg_keep_reg']),
    pin_regs=dict(enable=False, reason=(
        'Every boundary bit has its register in RTL: vmr_cmd/su_wq go straight into the request bank flops, su_rr / '
        'ij_* / pg_fault are serial_rr / ijq / synchroniser flops, the LG tap registers its local/far/near inputs and '
        'outputs, inj_rd/inj_addr are decoded into the inject bank flops. A wrapper stage would move the fixed 3:4 seam '
        'calendar (windows 2q..7q) and the release VM 18/15 calendar.')),
    io_flop_at_pins=dict(cols=4, allow_none=True), keep_pin_regs=True, inhold=False, outhold=False,
    std_area_um2=3500, fill_reason=dict(pin_bound=PIN_BOUND),
    structural_change=WHY,
    job=dict(owner='Codex:PGSTREAM-CDC', branch='codex/pgstream-cdc-1019', tag='b2',
             purpose='HBM die d4g LIGHT SU slice stream sibling: one two-root tile, banked seam inside (landed crossings)',
             record_to=f'results/rtl/ref_tile/{name}', views_to=f'physical/ref_tile/{name}/views', auto_merge=False,
             reroute_reason=dict(kind='rtl_change', what='merge of the one-root halves hbm_su_pg_stream_q/_s_1019 into one '
                                 'two-root tile with the banked seam inside (coordinator 07:11 option b)', why=WHY[:600]),
             extra_paths=[BENCH, 'rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_split.sv',
                          f'{S_}/top/ot_hbm_su_static_pg_stream.sv', f'{S_}/top/ot_hbm_su_static_pg_lg_tap.sv',
                          f'{S_}/programme/multirate_bridge.sv', WIT],
             benches=benches),
    macros=[], children=[], inter=[], hold_budget='die', pin_ranges=pr,
    clock='multiple_cts_roots', clock_ports=['pg_clk', 'clk_ctl'], clock_data_paths='related_pll_ratio',
    clock_relationship=dict(kind='same_pll_fixed_phase', ratio=[4, 3], phase_ps=0),
    clock_entry_domains={'core': dict(ratio=[1, 1], ports=['pg_clk'], inputs=core_in, outputs=core_out),
                         'serial': dict(ratio=[4, 3], ports=['clk_ctl'], inputs=serial_in, outputs=serial_out)},
    seam_windows=seam_windows,
    cdc_synchronizers=[
        dict(name='pg_fault_level', src_domain='core', dst_domain='serial',
             source='u_s.g_pgf_reg.pgf_q', chain=['u_q.fs[0]', 'u_q.fs[1]'], sync_max_delay_ps=250,
             why='stream fault OR published by one source register, then exact two-stage serial level synchronizer; '
                 'one added stream publication edge, no data-calendar effect'),
        dict(name='pg_leaf_reset', src_domain='serial', dst_domain='core',
             source='u_q.rcl', chain=['u_s.rq_s[0]', 'u_s.rq_s[1]'], sync_max_delay_ps=250,
             why='existing serial reset source followed by exact two-stage stream reset release synchronizer; unchanged edges'),
        dict(name='pg_tap_reset', src_domain='serial', dst_domain='core',
             source='u_q.rct', chain=['u_s.rs_s[0]', 'u_s.rs_s[1]'], sync_max_delay_ps=250,
             why='existing serial reset source followed by exact two-stage stream reset release synchronizer; unchanged edges'),
    ],
)
out = Path('tools/ref_tile/specs_hbm_su3') / f'{name}.json'
out.write_text(json.dumps(s, indent=1) + '\n')
print(out)
