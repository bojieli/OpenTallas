"""HBM-SU3 10-17: kit spec for ot_hbm_su_static_pg_lg_tap (SU-level LG pair tap + serial->stream reset synchroniser),
the hardened tap child of ot_hbm_su_static_pgslice_lg. Geometry = the CLOSED SFU-level pair tap leaf (216 x 216, same
1,112-bit faces), clock = two related roots (pg_clk core, clk_ctl serial 4/3) with the reviewed cdc_synchronizers mode."""
import json, copy
from pathlib import Path
RT = Path('physical/ref_tile')
base = json.loads((RT / 'hbm_sfu_lg_pair_tap_leaf_1017/spec.json').read_text())
name = 'hbm_su_pg_lgtap_1017'
s = copy.deepcopy(base)
W = H = 216.0
s['name'] = name; s['top'] = 'ot_hbm_su_static_pg_lg_tap'
s['sources'] = ['rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pg_lg_tap.sv',
                'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv',
                'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv', 'rtl/hdc/ot_hdc_delay.sv']
s['params'] = {'READ_RETURN': 10, 'WRITE_RETURN': 7}
s['clock_port'] = 'pg_clk'; s['reset_ports'] = ['rst_n']
s['std_area_um2'] = 1200
B = dict(local_rq=34, local_wq=562, local_rr=514, local_w_done=2, far_rq=34, far_wq=562, far_rr=514, far_w_done=2,
         near_rq=34, near_wq=562, near_rr=514, near_w_done=2, pg_clk=1, clk_ctl=1, rst_n=1, local_read=2, local_write=2, fault=1)
ctl = ['local_read', 'local_write', 'pg_clk', 'clk_ctl', 'rst_n', 'fault']
# W = far (SFU-level taps), E = near (VM bank), N = slice leaf requests, S = returns to the slice leaves; the clock and
# reset pins sit at the S-face centre beside the tap registers (pin flops on every face = the register mass).
pins = {'W': ['far_rq', 'far_wq', 'far_rr', 'far_w_done'], 'E': ['near_rq', 'near_wq', 'near_rr', 'near_w_done'],
        'N': ['local_rq', 'local_wq'], 'S': ['local_rr'] + ctl + ['local_w_done']}
s['pins'] = pins


def ranges(order, bits, lo, hi):
    tot = sum(bits[p] for p in order); out = {}; y = lo
    for p in order:
        w = (hi - lo) * bits[p] / tot; out[p] = [round(y, 3), round(y + w, 3)]; y += w
    return out


pr = {}
for f in 'WE':
    pr.update(ranges(pins[f], {p: max(B[p], 4) for p in pins[f]}, 4.0, H - 4.0))
pr.update(ranges(pins['N'], {p: B[p] for p in pins['N']}, 4.0, W - 4.0))
pr.update({'local_rr': [4.0, 103.0]}); pr.update(ranges(ctl, {p: 1 for p in ctl}, 104.0, 112.0))
pr.update({'local_w_done': [113.0, 116.0]})
s['pin_ranges'] = pr
s['clock'] = 'multiple_cts_roots'
s['clock_ports'] = ['pg_clk', 'clk_ctl']
s['clock_data_paths'] = 'related_pll_ratio'
s['clock_relationship'] = {'kind': 'same_pll_fixed_phase', 'ratio': [4, 3], 'phase_ps': 0}
s['clock_entry_domains'] = {
    'core': {'ratio': [1, 1], 'ports': ['pg_clk'],
             'inputs': ['local_rq', 'local_wq', 'far_rq', 'far_wq', 'local_read', 'local_write', 'near_rr', 'near_w_done'],
             'outputs': ['near_rq', 'near_wq', 'local_rr', 'far_rr', 'local_w_done', 'far_w_done', 'fault']},
    'serial': {'ratio': [4, 3], 'ports': ['clk_ctl'], 'inputs': ['rst_n'], 'outputs': []}}
s['cdc_synchronizers'] = [{
    'name': 'pg_reset', 'src_domain': 'serial', 'dst_domain': 'core', 'source': 'g_rsync.rc',
    'chain': ['g_rsync.rs[0]', 'g_rsync.rs[1]'], 'sync_max_delay_ps': 250,
    'why': 'serial power-on reset rst_n (pin flop rc on clk_ctl) re-timed by two pg_clk flops into the taps reset '
           '(replaces the r8b single pg_clk flop of the raw serial rst_n; same pattern as col_su r3 stream_reset)'}]
s['pin_regs'] = {'enable': False, 'reason': 'Every boundary bit already has its register in RTL: each static LG tap '
                 'registers its local/far/near inputs at the pins and its mux/output stage; rst_n lands in the serial '
                 'source flop of the synchroniser. Wrapper flops would add edges to the fixed VM calendar (10/7).'}
s['structural_change'] = ('HBM-SU3 10-17 (coordinator 0dg+3): SU-level LG pair tap hardened as its own leaf beside the '
    'pgslice VM bank leaves, with a reviewed 1-bit serial->stream reset synchroniser (clk_ctl rc -> pg_clk rs[0] -> '
    'rs[1]) instead of the r8b single pg_clk flop of the serial rst_n. Datapath = unchanged ot_hbm_vm_lg_pair_tap '
    '(10/7). Pin-bound 216x216 as the CLOSED SFU tap leaf: W far 1,112 / E near 1,112 / N local requests 596 full face '
    '/ S local returns 516 + clocks/reset/selects at the S centre. Benches: tools/hbm_static/su_pg_lg_tap_rsync_run.sh (tap lockstep vs '
    'ot_hbm_vm_lg_pair_tap + exact reset edges; RSYNC_MUT=1 = r8b one-flop reset FAILS) and su_pgslice_lg_rsync_run.sh '
    '(whole pgslice_lg RSYNC=1 vs r8b at die params, leaf + tap synchronisers agree).')
for k in ('slot_change_request',):
    s.pop(k, None)
j = s['job']; j['owner'] = 'Claude:HBM-SU3'; j['branch'] = 'claude/hbm-su3-1017'; j['tag'] = 'r1'
j['purpose'] = 'HBM die d4f su_<q><g> (ot_hbm_su_static_pgslice_lg) LG tap child with a real reset synchroniser (0dg+3)'
j['record_to'] = 'results/rtl/ref_tile/' + name; j['views_to'] = f'physical/ref_tile/{name}/views'; j['auto_merge'] = False
j['extra_paths'] = ['tools/hbm_static/su_pg_lg_tap_rsync_run.sh', 'rtl/test/hbm_accel/generic/tb_hbm_su_pg_lg_tap_rsync.sv']
j['benches'] = [
    {'name': 'rsync_lockstep', 'cmd': 'bash tools/hbm_static/su_pg_lg_tap_rsync_run.sh {RUN}/bench/pos 0', 'expect': 'pass',
     'pass_regex': 'PG_LG_TAP_RSYNC PASS', 'pass_witness': 'results/rtl/hbm_su3_1017/pg_lg_tap_pos.log', 'min_count_regex': 'checks=(\\d+)', 'threads': 1, 'peak_ram_gb': 2, 'needs': ['iverilog']},
    {'name': 'rsync_mutant', 'cmd': 'bash tools/hbm_static/su_pg_lg_tap_rsync_run.sh {RUN}/bench/mut 1', 'expect': 'fail',
     'fail_regex': 'PG_LG_TAP_RSYNC FAIL', 'fail_witness': 'results/rtl/hbm_su3_1017/pg_lg_tap_mut1.log', 'threads': 1, 'peak_ram_gb': 2, 'needs': ['iverilog']}]
out = Path('tools/ref_tile/specs_hbm_su3') / f'{name}.json'
out.write_text(json.dumps(s, indent=1) + '\n'); print(out)
