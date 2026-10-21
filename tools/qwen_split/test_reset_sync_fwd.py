#!/usr/bin/env python3
"""QW-G5NOROOT 10-20: reset release into a FORWARDED package clock (reset_sync_contract.fwd_clocks).

g5 (dv2f20g5): rstt_rst_d2d__fo1__r4_21 / __fo2__r4_6 (clk_d2d tree) drove rly_lnk_fwd_epoch*_0.en, hop-0 stations on
n_pll_fwd (ckb_rom.pll_ck, the ROM-link clock forwarded from the other die); ck_domain('pll_fwd') was the default 'stream'
(mesochronous) so the release was a plain single-flop capture (die STA reset class -9036 ps).  Now:
  * fwd_clocks(model) = {pll_fwd}: driven by a qfd_ckbump, reaching no qfd_clkrx (ckb_core -> clk_rx is the core feed);
  * plan() re-clocks that last repeater onto pll_fwd (2-flop synchroniser, d = declared endpoint) and audit() is clean;
  * mutant: without fwd the plan leaves it and audit(fwd) reports the stream -> fwd release; a leaf shared with a
    clk_d2d sink is refused (no single synchronising clock);
  * the netlist form (netlist_fwd_clocks / model_from_netlist) finds the same clock and the same untreated hop.
    python3 tools/qwen_split/test_reset_sync_fwd.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reset_sync_contract as R  # noqa: E402


class I:
    def __init__(self, name, master):
        self.name, self.master = name, master


model = dict(insts=[I('ckb_rom', 'qfd_ckbump'), I('ckb_core', 'qfd_ckbump'), I('clk_rx', 'qfd_clkrx'),
                    I('rly_ep_0', 'qfd_rlyh0_1_NS_65x30'), I('rly_land', 'qfd_landh_1_EW_65x30')],
             buses=[('pll_fwd', 'clock_trunk', 1, [('ckb_rom', 'pll_ck'), ('rly_ep_0', 'ck')]),
                    ('pll_core', 'clock_trunk', 1, [('ckb_core', 'pll_ck'), ('clk_rx', 'pll_fwd')]),
                    ('clk_d2d', 'clock_trunk', 1, [('clk_rx', 'pll_d2d'), ('rly_land', 'ck')])])
fwd = R.fwd_clocks(model)
assert fwd == {'pll_fwd'}, fwd
assert R.ck_domain('n_pll_fwd', fwd) == 'fwd:pll_fwd' and R.ck_domain('n_pll_fwd') == 'stream'
assert R.foreign(R.ck_domain('clk_d2d', fwd), R.ck_domain('pll_fwd', fwd), R.mesochronous())

cells = [('rstt_20', 'qfd_rst_rep', 0, 0, 'rst_d2d', 0), ('rstt_21', 'qfd_rst_rep', 0, 0, 'rst_d2d', 0)]
wires = [('n_t20', 'rst_d2d', [('rstt_20', 'q0'), ('rstt_21', 'd')]), ('n_t21', 'rst_d2d', [('rstt_21', 'q0'), ('rly_ep_0', 'en')]),
         ('n_t22', 'rst_d2d', [('rstt_20', 'q1'), ('rly_land', 'rs')])]
ck_of_bus = {'rst_d2d': 'clk_d2d'}
ckof = {'rly_ep_0': [('pll_fwd', 'ck')], 'rly_land': [('clk_d2d', 'ck')]}
mof = {i.name: i.master for i in model['insts']} | {'rstt_20': 'qfd_rst_rep', 'rstt_21': 'qfd_rst_rep'}
p = R.plan(cells, wires, ck_of_bus, ckof, mof, {}, None, fwd=fwd)
assert p['reclock'] == {'rstt_21': 'pll_fwd'} and not p['errors'], p
assert [e['pin'] for e in p['endpoints']] == ['rstt_21/d'] and 'fwd:pll_fwd' in p['endpoints'][0]['why']
rclk = {c[0]: p['reclock'].get(c[0], 'clk_d2d') for c in cells}
assert R.audit(wires, rclk, ckof, mof, p['endpoints'], fwd=fwd) == []
# mutant: the g5 form (no forwarded domain) -> no re-clock; the fwd-aware audit names the untreated release
p0 = R.plan(cells, wires, ck_of_bus, ckof, mof, {}, None)
assert p0['reclock'] == {}
bad = R.audit(wires, {c[0]: 'clk_d2d' for c in cells}, ckof, mof, p0['endpoints'], fwd=fwd)
assert [b['hop'] for b in bad] == ['rstt_21 -> rly_ep_0/en'] and 'fwd:pll_fwd' in bad[0]['cls'], bad
# mutant: the leaf also drives a clk_d2d sink -> refused
w2 = wires[:1] + [('n_t21', 'rst_d2d', [('rstt_21', 'q0'), ('rly_ep_0', 'en'), ('rly_land', 'rs')])]
assert R.plan(cells, w2, ck_of_bus, ckof, mof, {}, None, fwd=fwd)['errors']

# netlist form
net = '\n'.join(['  qfd_ckbump ckb_rom (.pll_ck(n_pll_fwd), .rs(n_rst_fwd));', '  qfd_ckbump ckb_core (.pll_ck(n_pll_core));',
                 '  qfd_clkrx clk_rx (.pll_d2d(n_clk_d2d), .pll_fwd(n_pll_core));',
                 '  qfd_rst_rep rstt_20 (.clk(n_clk_d2d), .d(n_t19), .q0(n_t20));',
                 '  qfd_rst_rep rstt_21 (.clk(n_clk_d2d), .d(n_t20), .q0(n_t21));',
                 '  qfd_rlyh0_1_NS_65x30 rly_ep_0 (.a(n_a), .b(n_b), .ck(n_pll_fwd), .en(n_t21));', ''])
assert R.fwd_of_netlist(net) == {'pll_fwd'}
c_, w_, ckb, ck_, m_ = R.model_from_netlist(net)
assert ck_['rly_ep_0'] == [('pll_fwd', 'ck')]
bad = R.audit(w_, dict(ckb), ck_, m_, [], fwd=R.fwd_of_netlist(net))
assert [b['hop'] for b in bad] == ['rstt_21 -> rly_ep_0/en'], bad
net2 = net.replace('qfd_rst_rep rstt_21 (.clk(n_clk_d2d)', 'qfd_rst_rep rstt_21 (.clk(n_pll_fwd)')
c_, w_, ckb, ck_, m_ = R.model_from_netlist(net2)
bad = R.audit(w_, dict(ckb), ck_, m_, [dict(pin='rstt_21/d')], fwd=R.fwd_of_netlist(net2))
assert bad == [], bad
print('TEST_RESET_SYNC_FWD PASS')
