"""LH-PGVM2 10-19: SAFE kit hbm_su_pg_stream_b_safe2_1019 = the PGSTREAM-B two-root tile (216 x 259.2, banked seam
inside) on the SAFE2 source top ot_hbm_su_static_pg_stream_split_safe2 (results/rtl/hbm_pgstream_safe_1019/safe2/README.md).
Derived from tools/ref_tile/specs_hbm_su3/hbm_su_pg_stream_b_1019.json (mk_pg_stream_b.py); changes:
  * top / sources: + multirate_bridge_regional.sv + ot_hbm_su_static_pg_stream_safe2.sv;
  * reset_landing.stages 1: the kit lands rst_n / bridge_rst_n in ONE face flop; the source owns the rest (rst_n: 2 serial
    stages; bridge_rst_n: serial stage A -> 129 terminals, stream feeder F (clk_ctl) -> P (pg_clk) -> 86 terminals; both
    domains release on the same coincident edge -- the 3-stage clk_ctl kit landing of the b_1019 kit released the stream
    side one stream edge early: tb_hbm_su_pg_stream_kitland FAIL, gate95463 not submittable);
  * seam_windows "from" re-pointed to the regional bank cells (old aliases kept);
  * cdc_synchronizers: leaf / tap chains end on the replicated second stages (u_s.lr / u_s.tr, kept copies of ONE logical
    flop), + bridge_stream_reset (bf -> bp -> bs, the stream reset feeder);
  * benches: tb_hbm_su_pg_stream_safe2 (run_safe2.sh), witnesses results/rtl/hbm_pgstream_safe_1019/safe2/bench_r7;
  * SAFE r5: inj_rd / inj_addr captured per inject region on pg_clk (+1 stream edge on the inject path, LEAD-HBM 10-19,
    priced in lanes/LH-REPRICE3.md); r6/r7: the {bad} inject region split into four group instances (pairwise conflict
    flag), census 0 roots > 32 (max 32, 9,496 FF, 4,185 um2).
Run from the repo root: python3 tools/ref_tile/specs_hbm_su3/mk_pg_stream_b_safe2.py"""
import json
from pathlib import Path

base = json.loads(Path('tools/ref_tile/specs_hbm_su3/hbm_su_pg_stream_b_1019.json').read_text())
name = 'hbm_su_pg_stream_b_safe2_1019'
S_ = 'rtl/hbm_accel/generic/adapters/static_su'
WIT = 'results/rtl/hbm_pgstream_safe_1019/safe2/bench_r7'
BENCH = 'tools/hbm_static/pgstream_safe/run_safe2.sh'


def bench(nm, sub, mut, rr=18, wr=15, qid=1, why=None):
    b = dict(name=nm, cmd=f'bash {BENCH} {{RUN}}/bench/{sub} {mut} {qid} {rr} {wr} safe2', threads=4, peak_ram_gb=8,
             needs=['verilator'])
    if why is None:
        b.update(expect='pass', pass_regex='PG_STREAM_SPLIT PASS checks=', min_count_regex='checks=(\\d+)',
                 pass_witness=f'{WIT}/{sub}/bench.log')
    else:
        b.update(expect='fail', fail_regex='PG_STREAM_SPLIT FAIL errors=', fail_witness=f'{WIT}/{sub}/bench.log', why=why)
    return b


benches = [
    bench('pgs_s2_lockstep', 'rr18', 0),
    bench('pgs_s2_lockstep_rr10_regression', 'rr10', 0, 10, 7),
    bench('pgs_s2_lockstep_qid0', 'qid0', 0, qid=0),
    bench('pgs_s2_mut1', 'm1', 1, why='serial return / done bank read select inverted'),
    bench('pgs_s2_mut2', 'm2', 2, why='stream half reads the wrong request bank'),
    bench('pgs_s2_mut3', 'm3', 3, why='return staging removed: bank rewritten 0 ps after its read (window checker)'),
    bench('pgs_s2_mut6', 'm6', 6, why='serial request bank write select inverted'),
    bench('pgs_s2_mut8', 'm8', 8, why='serial half reads the wrong inject bank'),
    bench('pgs_s2_mut12_seam_window', 'm12', 12, why='request bank read one stream edge early into a pre-stage (same data): '
          'setup 1q < the declared 4q window; window checker only'),
    bench('pgs_s2_mut13_fault_publish', 'm13', 13, why='registered fault source inverted (independent publication + '
          'two-stage serial capture scoreboard)'),
    bench('pgs_s2_mut14_cross_reset', 'm14', 14, why='serial bridge reset must not clear stream-local sticky fault publication'),
]
seam = {w['name']: w for w in base['seam_windows']}
seam['bridge_request']['from'] = ['*u_bq.req*wq_b0*', '*u_bq.req*wq_b1*'] + seam['bridge_request']['from']
seam['bridge_return']['from'] = ['*u_bs.ret*rr_b0*', '*u_bs.ret*rr_b1*'] + seam['bridge_return']['from']
seam['inject']['from'] = ['*u_s.g_ij*q0*', '*u_s.g_ij*q1*', '*u_s.g_ij*q2*'] + seam['inject']['from']
seam['inject']['why'] += ('; SAFE2: banks q0/q1/q2 in the 5 kept inject regions u_s.g_ij[r].u_r (same sp calendar), inputs '
                          'captured one stream edge earlier (r5)')
WHY = ('LH-PGVM2 10-19 SAFE kit of the PGSTREAM-B tile on the SAFE2 source top (results/rtl/hbm_pgstream_safe_1019/safe2): '
       'the 14 roots >32 of 47d9b210c (bridge_rst_n 1,726, tap selects 564, tap/leaf reset 92/73, inject decode 83) '
       'replaced by kept source trees / per-region copies, inject pins captured per region (+1 stream edge, H-D4G), and '
       'the reset landing moved into the source so both roots release on the same coincident edge (the b_1019 kit '
       '3-stage clk_ctl landing released the stream side one edge early: kitland lockstep FAIL, gate95463 not submittable).')
s = dict(base)
s.update(
    name=name, top='ot_hbm_su_static_pg_stream_split_safe2',
    sources=base['sources'] + [f'{S_}/programme/multirate_bridge_regional.sv', f'{S_}/top/ot_hbm_su_static_pg_stream_safe2.sv'],
    reset_landing=dict(enable=True, stages=1, clock='clk_ctl',
                       why='ONE face flop per reset port; the SAFE2 source owns the remaining stages (rst_n: 2 serial; '
                           'bridge_rst_n: balanced kept tree, serial stage A -> terminals and stream feeder F -> P -> '
                           'terminals) so both clock roots leave reset on the same coincident edge 12q after the face flop'),
    pin_regs=dict(enable=False, reason=(
        'Every boundary bit has its register in RTL: vmr_cmd/su_wq go straight into the request bank region flops, su_rr '
        '/ ij_* / pg_fault are return-region / inject-region / synchroniser flops, the LG tap registers its local/far/'
        'near inputs and outputs, inj_rd/inj_addr are captured per inject region on pg_clk (SAFE2 r5). A wrapper stage '
        'would move the fixed 3:4 seam calendar (windows 2q..7q) and the release VM 18/15 calendar.')),
    std_area_um2=4200,
    structural_change=WHY,
    seam_windows=[seam['bridge_request'], seam['bridge_return'], seam['inject']],
    cdc_synchronizers=[
        base['cdc_synchronizers'][0],
        dict(name='pg_leaf_reset', src_domain='serial', dst_domain='core', source='u_q.rcl',
             chain=['u_s.rq_s0', 'u_s.lr[0]'], sync_max_delay_ps=250,
             why='serial leaf reset source -> stage 1 u_s.rq_s0 -> stage 2 = 5 kept identical copies u_s.g_lr[*] (one '
                 'logical flop; per-load-group copies for fanout <= 32); same two pg_clk ages as b_1019'),
        dict(name='pg_tap_reset', src_domain='serial', dst_domain='core', source='u_q.rct',
             chain=['u_s.rs_s0', 'u_s.tr[0]'], sync_max_delay_ps=250,
             why='serial tap reset source -> stage 1 u_s.rs_s0 -> stage 2 = 8 kept identical copies u_s.g_tr[*]'),
        dict(name='bridge_stream_reset', src_domain='serial', dst_domain='core', source='bf[0]',
             chain=['bp[0]', 'bs[0]'], sync_max_delay_ps=250,
             why='bridge_rst_n stream feeder: F (clk_ctl, C+4q; 3 kept copies, one logical flop) -> P (pg_clk C+6q, 2q '
                 'after the release launch) -> 86 kept stream terminals (C+9q) -> stream loads count from C+12q, the '
                 'same coincident edge as the serial loads'),
    ],
)
s['pin_ranges'] = base['pin_ranges']
s['fill_reason'] = dict(pin_bound=base['fill_reason']['pin_bound'].replace('~3,500 um2', '~4,200 um2 (SAFE2 r7 map: 4,185)'))
s['job'] = dict(owner='Claude:LEAD-HBM/LH-PGVM2', branch='claude/lh-pgvm-pgsafe-1019', tag='s2',
                purpose='HBM die d4g LIGHT SU slice stream sibling: PGSTREAM-B two-root tile, SAFE2 source (roots <=32, '
                        'source-owned epoch-exact reset tree, inject pin capture)',
                record_to=f'results/rtl/ref_tile/{name}', views_to=f'physical/ref_tile/{name}/views', auto_merge=False,
                reroute_reason=dict(kind='rtl_change', what='SAFE2 source top (safe-design checklist redesign of the '
                                    'PGSTREAM-B tile) + 1-stage kit landing', why=WHY[:600]),
                extra_paths=[BENCH, 'tools/hbm_static/pgstream_safe/gen_safe2_tb.py',
                             'rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_safe2.sv',
                             'rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_regional.sv',
                             f'{S_}/top/ot_hbm_su_static_pg_stream.sv', f'{S_}/top/ot_hbm_su_static_pg_stream_regional.sv',
                             f'{S_}/top/ot_hbm_su_static_pg_lg_tap.sv', f'{S_}/programme/multirate_bridge.sv', WIT],
                benches=benches)
out = Path('tools/ref_tile/specs_hbm_su3') / f'{name}.json'
out.write_text(json.dumps(s, indent=1) + '\n')
print(out)
