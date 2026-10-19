"""HBM-BANKLAT-SU 10-19: budget variants of the three LG pair tap leaves for the d4g faces bank (+1 pin) and die lanes.
Same RTL, geometry, pins and clocking as the CLOSED kits; only READ_RETURN/WRITE_RETURN (calendar depth) change:
  hbm_su_pg_lgtap_1017            10/7  -> hbm_su_pg_lgtap_rt18_1019            18/15
  hbm_sfu_lg_pair_tap_leaf_1017   14/11 -> hbm_sfu_lg_pair_tap_leaf_rt24_1019   24/21
  hbm_hc_lg_pair_tap_leaf_term_1017 18/15 -> hbm_hc_lg_pair_tap_leaf_term_rt32_1019 32/29
Budget + die pads: results/arch/hbm_banklat_1019/su_sfu_hc_budget_gen2c.json. io_hold_margin 0.03 (KITS rule 10-18).
Benches: the kits' own module benches + the chain bench at the budget (PASS) and at the old values (FAIL)."""
import json, copy
from pathlib import Path
RT = Path('physical/ref_tile')
B = '-GRR_SU=18 -GWR_SU=15 -GRR_SFU=24 -GWR_SFU=21 -GRR_HC=32 -GWR_HC=29'
L = '-GPIN=1 -GLQ=4 -GLR=3 -GFQ=1 -GFR=1 -GHQ=2 -GHR=2'
RUN = 'bash rtl/hbm_accel/generic/adapters/static_su/top/run_lg_chain_banklat.sh {RUN}/bench'
CHAIN = [
    {'name': 'chain_budget', 'cmd': f'{RUN} budget {L} {B}', 'expect': 'pass', 'pass_regex': '^CHAIN PASS',
     'pass_witness': 'results/rtl/hbm_banklat_su_1019/chain_budget.log', 'min_count_regex': 'checks=(\\d+)',
     'threads': 4, 'peak_ram_gb': 4, 'needs': ['verilator']},
    {'name': 'chain_mut_old', 'cmd': f'{RUN} mut_old {L}', 'expect': 'fail', 'fail_regex': '^CHAIN FAIL',
     'fail_witness': 'results/rtl/hbm_banklat_su_1019/chain_mut_old.log', 'threads': 4, 'peak_ram_gb': 4, 'needs': ['verilator']},
    {'name': 'chain_mut_lane', 'cmd': f'{RUN} mut_lane {B} -GPIN=1 -GLQ=4 -GLR=2 -GFQ=1 -GFR=1 -GHQ=2 -GHR=2', 'expect': 'fail',
     'fail_regex': '^CHAIN FAIL', 'fail_witness': 'results/rtl/hbm_banklat_su_1019/chain_mut_lane.log', 'threads': 4,
     'peak_ram_gb': 4, 'needs': ['verilator']}]
CHAIN_SRC = ['rtl/hbm_accel/generic/adapters/static_su/top/run_lg_chain_banklat.sh',
             'rtl/hbm_accel/generic/adapters/static_su/top/tb_hbm_su_lg_chain_banklat.sv',
             'rtl/hbm_accel/generic/adapters/static_su/programme/multirate_bridge.sv',
             'rtl/hbm_accel/generic/adapters/static_su/ot_hbm_su_static_vm_ports.sv',
             'rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pg_lg_tap.sv',
             'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv',
             'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv',
             'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank_term.sv',
             'rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_tap_leaf.sv',
             'rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv', 'rtl/hdc/ot_hdc_delay.sv']
for old, new, rr, wr, who in (('hbm_su_pg_lgtap_1017', 'hbm_su_pg_lgtap_rt18_1019', 18, 15, 'SU'),
                              ('hbm_sfu_lg_pair_tap_leaf_1017', 'hbm_sfu_lg_pair_tap_leaf_rt24_1019', 24, 21, 'SFU'),
                              ('hbm_hc_lg_pair_tap_leaf_term_1017', 'hbm_hc_lg_pair_tap_leaf_term_rt32_1019', 32, 29, 'HC')):
    s = copy.deepcopy(json.loads((RT / old / 'spec.json').read_text()))
    s['name'] = new
    s['params'] = dict(s['params'], READ_RETURN=rr, WRITE_RETURN=wr)
    s['route']['io_hold_margin_ns'] = 0.03
    # ROOT-RST 10-19 rule: the RTL lands the reset itself (same as the closed kit): no wrapper, release unchanged
    s['reset_landing'] = {'enable': False, 'reason': (
        'the RTL lands it: g_rsync.rc (clk_ctl source flop) -> rs[0] -> rs[1] (pg_clk) synchroniser feeds the taps'
        if who == 'SU' else 'the RTL lands it: the leaf boundary reset register rst_pin (cold init holds rst_n >= 2 edges)')}
    if 'pin_regs' in s and 'reason' in s['pin_regs']:
        s['pin_regs']['reason'] = s['pin_regs']['reason'].replace('(10/7)', f'({rr}/{wr})')
    s['structural_change'] = (f'HBM-BANKLAT-SU 10-19: {who} LG pair tap budget variant of the CLOSED {old} for the d4g faces '
        f'bank (pin flop +1) and die lanes: READ_RETURN/WRITE_RETURN {rr}/{wr} (calendar depth only; RTL, outline, pins, '
        'clocking unchanged). Budget/pads results/arch/hbm_banklat_1019/su_sfu_hc_budget_gen2c.json; LAT rule '
        'tools/hbm_die_v16/d4g_bank_latency.py TAP_CHAIN; chain bench tb_hbm_su_lg_chain_banklat (budget PASS, '
        'old values / one lane short FAIL).')
    j = s['job']
    j['owner'] = 'Claude:HBM-BANKLAT-SU'; j['branch'] = 'claude/hbm-banklat-su-1019'; j['tag'] = 'b1'
    j['purpose'] = f'd4g {who} LG pair tap at the bank-latency budget {rr}/{wr} (faces bank pin flop + GEN2c/GEN2d lanes)'
    j['record_to'] = 'results/rtl/ref_tile/' + new; j['views_to'] = f'physical/ref_tile/{new}/views'; j['auto_merge'] = False
    j['reroute_reason'] = f'rtl_change: param READ_RETURN/WRITE_RETURN -> {rr}/{wr} of the closed {old} (bank pin flop + lanes)'
    j['extra_paths'] = sorted(set(j.get('extra_paths', []) + [p for p in CHAIN_SRC if p not in s['sources']]))
    j['benches'] = [b for b in j['benches']] + copy.deepcopy(CHAIN)
    out = Path('tools/ref_tile/specs_hbm_su3') / f'{new}.json'
    out.write_text(json.dumps(s, indent=1) + '\n'); print(out)
