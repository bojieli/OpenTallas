"""TW3-PGSTREAM 10-19: kits for the ONE-ROOT halves of the LIGHT SU slice stream sibling (coordinator 10-19: the pg_stream
3:4 bridge FAILS inside one tile -- gate hbm_su_pg_stream_1019, commit 0ff805777: cross_clock TT setup -126.9 ps
rr_slot -> serial_rr and -479.3 ps sq -> ij register). ot_hbm_su_static_pg_stream -> ot_hbm_su_static_pg_stream_q
(clk_ctl, serial, faces the slice S band) + ot_hbm_su_static_pg_stream_s (pg_clk, stream: VM bank leaves, LG tap, inject),
abutted along a 2,346-b banked seam (HBM-CXDL dl_s/dl_q, S81 x34_s/_t precedent). Each half has one clock root and is
signed off at 833.333 ps (the serial half conservatively at the stream period, as bridge_release_s / cx_dlq). The seam
arcs are die-level 3:4 arcs with static calendar windows (request >= 4q setup / 2q hold, return 2q / 4q, inject 3q / 7q;
measured by the bench window checker); die STA owns them.
Geometry: the pair is 302.4 x 432 (q 86.4 + s 216): the seam is 2,346 b, <= 6/um needs >= 391 um of face.
Run from the repo root: python3 tools/ref_tile/specs_hbm_su3/mk_pg_stream_split.py"""
import json
from pathlib import Path

S_ = 'rtl/hbm_accel/generic/adapters/static_su'
WIT = 'results/rtl/tw3_pgstream_1019'
BENCH = 'tools/hbm_static/su_pg_stream_split_vl_run.sh'
H = 432.0
SRC_Q = [f'{S_}/top/ot_hbm_su_static_pg_stream_split.sv', f'{S_}/programme/multirate_bridge_split.sv',
         'rtl/lib/ot_rst_relay.sv']
SRC_S = SRC_Q + [f'{S_}/ot_hbm_su_static_vm_bank_leaf_s.sv', f'{S_}/ot_hbm_su_static_vm_ports.sv',
                 'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv',
                 'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv', 'rtl/hdc/ot_hdc_delay.sv']
B = dict(clk_ctl=1, pg_clk=1, rst_n=1, bridge_rst_n=1, pos=4,
         vmr_cmd=60, su_wq=562, su_rr=514, ij_v=4, ij_row=36, ij_bad=1, pg_fault=1,
         rq_b0=34, rq_b1=34, wq_b0=562, wq_b1=562, rr_b0=514, rr_b1=514, ijb0=41, ijb1=41, ijb2=41, pgf_s=1,
         rc_leaf=1, rc_tap=1,
         inj_rd=2, inj_addr=160, lg_rq=34, lg_wq=562, lg_rr=514, lg_w_done=2, lg_read=2, lg_write=2, far_rq=34,
         far_wq=562, far_rr=514, far_w_done=2, lg_fault=1)
# one seam order for both faces (q E == s W, same y ranges): abutted pins line up
SEAM = ['rc_leaf', 'rc_tap', 'rq_b0', 'wq_b0', 'rr_b0', 'ijb0', 'ijb1', 'ijb2', 'pgf_s', 'rr_b1', 'wq_b1', 'rq_b1']


def ranges(order, lo, hi, gap=0.6):
    tot = sum(max(B[p], 2) for p in order)
    sp = hi - lo - gap * (len(order) - 1)
    out, y = {}, lo
    for p in order:
        w = sp * max(B[p], 2) / tot
        out[p] = [round(y, 3), round(y + w, 3)]
        y += w + gap
    return out


def centre(order, span, step=2.0):
    lo = span / 2 - step * len(order) / 2
    return {p: [round(lo + step * i, 3), round(lo + step * i + 1.333, 3)] for i, p in enumerate(order)}


WHY = ('TW3-PGSTREAM 10-19 (coordinator 10-19): hbm_su_pg_stream_1019 (two-root 4:3 leaf, gate FAIL committed 0ff805777: '
       'cross_clock TT setup -126.9 ps bridge rr_slot -> serial_rr, -479.3 ps sq -> ij register; a 3:4 crossing with logic '
       'cannot close inside one leaf, related-clock STA times it at the 1q VCO tick less the 150 ps distinct-entry '
       'reserve) split into ONE-ROOT halves pg_stream_q (clk_ctl) + pg_stream_s (pg_clk) over a 2,346-b banked seam: '
       'bridges = 2-bank request/return seams (request bank n mod 2 written at serial n, read at the old stream launch '
       'edge; return banks read one serial edge early into a staging register), inject = 3 decode banks (stream slots '
       '0/1/3) read by a serial register, resets = the old synchronisers cut between their source and pg_clk stages, '
       'pg fault = 2-flop synchroniser. Lockstep vs the current pg_stream (tb_hbm_su_pg_stream_split, Verilator 5.050): '
       'PASS checks=7178 at RR 10/7, 18/15 and QID 0; seam windows measured request 4q/2q, return 2q/4q, inject 3q/7q; '
       'edges unchanged except ij +1 serial and pg_fault +2 serial (H-D4G). Mutants 1/2/3/6/8/9 FAIL (3 = staging '
       'removed: functionally equal, caught by the window checker). ')
benches = [
    dict(name='pgs_split_lockstep', cmd=f'bash {BENCH} {{RUN}}/bench/m0 0 1500 1 10 7', expect='pass',
         pass_regex='PG_STREAM_SPLIT PASS checks=', min_count_regex='checks=(\\d+)', pass_witness=f'{WIT}/m0/bench.log',
         threads=4, peak_ram_gb=8, needs=['verilator']),
    dict(name='pgs_split_lockstep_rt18', cmd=f'bash {BENCH} {{RUN}}/bench/rt18 0 1500 1 18 15', expect='pass',
         pass_regex='PG_STREAM_SPLIT PASS checks=', min_count_regex='checks=(\\d+)', pass_witness=f'{WIT}/rt18/bench.log',
         threads=4, peak_ram_gb=8, needs=['verilator']),
    dict(name='pgs_split_mut3', cmd=f'bash {BENCH} {{RUN}}/bench/m3 3 1500 1 10 7', expect='fail',
         fail_regex='PG_STREAM_SPLIT FAIL errors=', fail_witness=f'{WIT}/m3/bench.log', threads=4, peak_ram_gb=8,
         needs=['verilator'], why='return staging removed: bank rewritten 0 ps after its read (seam window checker)'),
    dict(name='pgs_split_mut2', cmd=f'bash {BENCH} {{RUN}}/bench/m2 2 1500 1 10 7', expect='fail',
         fail_regex='PG_STREAM_SPLIT FAIL errors=', fail_witness=f'{WIT}/m2/bench.log', threads=4, peak_ram_gb=8,
         needs=['verilator'], why='stream half reads the wrong request bank'),
    dict(name='pgs_split_mut8', cmd=f'bash {BENCH} {{RUN}}/bench/m8 8 1500 1 10 7', expect='fail',
         fail_regex='PG_STREAM_SPLIT FAIL errors=', fail_witness=f'{WIT}/m8/bench.log', threads=4, peak_ram_gb=8,
         needs=['verilator'], why='serial half reads the wrong inject bank'),
]
EXTRA = [BENCH, 'rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_split.sv', f'{S_}/top/ot_hbm_su_static_pg_stream.sv',
         f'{S_}/top/ot_hbm_su_static_pg_lg_tap.sv', f'{S_}/programme/multirate_bridge.sv',
         f'{S_}/ot_hbm_su_static_vm_bank_leaf_s.sv', f'{S_}/ot_hbm_su_static_vm_ports.sv',
         'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv',
         'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv', 'rtl/hdc/ot_hdc_delay.sv', WIT]


# TW5-PGSTREAM 10-19: gate try 3 (24dac678d, --cts) FAILED both halves in GPL: GPL-0305 RePlAce divergence after the
# routability loop (q: 930 um2 movable in 35,104 um2, routability inflation +323 %, overflow stuck at 0.137 while the density
# penalty ran to 1e32; s the same at 0.107). Pin-bound tiles: the seam (2,346 b) sets the 432-um height on both faces and the
# halves abut, so the outline stays; routability-driven GPL off (precedent dsfd_vm_static_wfc_ctl_r4/r5, smn_fcxr_ref_fa r2,
# smh_fcxr_ref_p35 lf CLOSED). The trial GRT / route GRT still measure congestion.
PIN_BOUND = {
    'hbm_su_pg_stream_q_1019': 'E seam 2,346 b at 5.4/um and W slice S band 1,178 b set the 432-um height (abuts s); '
                               'width 86.4 is the minimum for two 4-column pin-flop bands plus the bank muxes',
    'hbm_su_pg_stream_s_1019': 'W seam 2,346 b at 5.4/um (abuts q) sets the 432-um height; N far requests + COLL inject '
                               '762 b and S far returns 516 b set the 216-um width',
}


def mk(name, top, params, ck, rsts, land, W, pins, pr, std, srcs, why, keep=None):
    route = {'pd': 0.5, 'period_ps': 833.333, 'threads': 8, 'peak_ram_gb': 12, 'hold_margin_ns': 0.03,
             'macro_halo_um': 5.4, 'pin_h': 'M4', 'pin_v': 'M3 M5', 'pin_balance': {'h': 'M4', 'v': 'M3 M5', 'group_max': 1},
             'io_hold_margin_ns': 0.03}
    if keep:
        route['synth_keep_modules'] = keep
    s = {'name': name, 'top': top, 'kind': 'tile', 'sources': srcs, 'params': params,
         'clock_port': ck, 'reset_ports': rsts, 'reset_landing': land,
         'outline': {'w': W, 'h': H, 'exact': True}, 'std_area_um2': std, 'layer_cap': 'M5', 'signal_max_layer': 'M5',
         'pg_layer': 'M5', 'recipe': 4, 'macros': [], 'children': [], 'inter': [], 'pins': pins, 'pin_ranges': pr,
         'route': route, 'orfs_vars': {'GPL_ROUTABILITY_DRIVEN': '0'},
         'fill_reason': {'pin_bound': PIN_BOUND[name]}, 'io_flop_at_pins': {'cols': 4, 'allow_none': True}, 'inhold': False, 'outhold': False,
         'keep_pin_regs': True, 'hold_budget': 'die',
         'pin_regs': {'enable': False, 'reason': (
             'Every boundary bit has its register in RTL: request/return/inject banks are written straight from the '
             'pins / seam and read by a mux into a register (serial_rr, stream launch, ijq); every output is a register '
             '(ij banks, launch, tap) or the synchroniser / sticky-fault OR. A wrapper stage would move the fixed 3:4 '
             'seam calendar (windows 2q..7q) and the VM 10/7 calendar.')},
         'structural_change': why,
         'job': {'owner': 'Claude:TW3-PGSTREAM', 'branch': 'claude/tw3-pgstream-1019', 'tag': 'p1',
                 'purpose': 'HBM die d4g LIGHT SU slice stream sibling, one-root half: ' + top,
                 'record_to': f'results/rtl/ref_tile/{name}', 'views_to': f'physical/ref_tile/{name}/views',
                 'auto_merge': False,
                 'reroute_reason': {'kind': 'rtl_change', 'what': 'one-root split of hbm_su_pg_stream_1019 (gate FAIL 0ff805777)',
                                    'why': why[:600]},
                 'extra_paths': EXTRA, 'benches': benches}}
    out = Path('tools/ref_tile/specs_hbm_su3') / f'{name}.json'
    out.write_text(json.dumps(s, indent=1) + '\n')
    print(out)


seam_pr = ranges(SEAM, 4.0, H - 4.0)
# ---- q (serial): W slice S band, E seam, N clocks/resets
WQ = 86.4
pins_q = {'W': ['vmr_cmd', 'su_wq', 'su_rr', 'ij_v', 'ij_row', 'ij_bad', 'pg_fault'], 'E': SEAM,
          'N': ['clk_ctl', 'rst_n', 'bridge_rst_n']}
pr_q = dict(seam_pr)
pr_q.update(ranges(pins_q['W'], 4.0, H - 4.0, gap=1.2))
pr_q.update(centre(pins_q['N'], WQ))
mk('hbm_su_pg_stream_q_1019', 'ot_hbm_su_static_pg_stream_q', {'READ_RETURN': 10, 'WRITE_RETURN': 7}, 'clk_ctl',
   ['rst_n', 'bridge_rst_n'],
   {'enable': True, 'stages': 3, 'why': '3 serial stages = one 3:4 epoch (12q): the bridge / inject slot counters release on '
    'the same epoch-aligned edge relative to the stream half (4 pg_clk stages); reset release +1 epoch (H-D4G)'},
   WQ, pins_q, pr_q, 2600, SRC_Q,
   WHY + 'q (serial, x8 LIGHT slices): W slice S band 1,178 b (2.7/um), E seam 2,346 b (5.4/um), clocks/resets N centre.')
# ---- s (stream): W seam, E LG near, N far requests + COLL inject + strap, S far returns + clock/reset
WS = 216.0
pins_s = {'W': SEAM, 'E': ['lg_rq', 'lg_wq', 'lg_rr', 'lg_w_done', 'lg_read', 'lg_write', 'lg_fault'],
          'N': ['far_rq', 'far_wq', 'inj_rd', 'inj_addr', 'pos'], 'S': ['far_rr', 'pg_clk', 'bridge_rst_n', 'far_w_done']}
pr_s = dict(seam_pr)
pr_s.update(ranges(pins_s['E'], 4.0, H - 4.0, gap=1.2))
pr_s.update(ranges(pins_s['N'], 4.0, WS - 4.0, gap=1.2))
pr_s.update({'far_rr': [4.0, 103.0], 'pg_clk': [104.0, 105.333], 'bridge_rst_n': [106.0, 107.333],
             'far_w_done': [113.0, 116.0]})
mk('hbm_su_pg_stream_s_1019', 'ot_hbm_su_static_pg_stream_s', {'QID': 1, 'G': 2, 'READ_RETURN': 10, 'WRITE_RETURN': 7,
   'STRAP': 1}, 'pg_clk', ['bridge_rst_n'],
   {'enable': True, 'stages': 4, 'why': '4 pg_clk stages = one 3:4 epoch (12q), matching the serial half (3 clk_ctl stages)'},
   WS, pins_s, pr_s, 4200, SRC_S,
   WHY + 's (stream, x8): W seam 2,346 b (5.4/um), E LG near 1,117 b (2.6/um), N far requests + COLL inject 762 b (3.5/um), '
   'S far returns 516 b + pg_clk / bridge_rst_n.', keep=['ot_hbm_vm_lg_keep_reg'])
