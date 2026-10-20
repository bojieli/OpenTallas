"""HBM-HCBANK 10-19: two kit fixes found by the HCRING pord1 gates; run in the worktree root (idempotent), then
`ref_tile.py gen` the two specs.

1. e2 (ot_hbm_hc_bankq_ft_static) carries the corner banks' resets through the tile (fa_rst_n -> fa_rst_n_o,
   fb_rst_n -> fb_rst_n_o).  ot_pin_regs (83a02883d) refuses a reset-named input that is not declared
   ("legacy reset regexp/default matches undeclared reset fa_rst_n", then "... fa_rst_n_o").  Declare all four as
   reset_ports (an output reset port passes straight through the wrapper); the
   RESET-LANDING rule then lands them at the S face in 2 registered stages like rst_n, so the feed is a registered
   feed (as its beat/write feeds already are) instead of a 734 um combinational reset wire.  Cost: the corner banks
   (b1/b3/b5/b7) release reset 2 cycles after the edge banks; reset release is a scheduled constant and the ring
   starts only on hub descriptors issued long after reset (no schedule change).
2. b0 (ot_hbm_hc_bankq0_static) takes DRLY 2 (HC-RINGPLAN GEN2d closed ring, claude/hc-ringplan-1019 9d1689ba4:
   b7 abuts b0, no hcx die relay, bankq0 DRLY 1 -> 2).  Its benches run the ring with that config
   (HC_XDEF "+define+HC_DRLY=2 +define+HC_XRLY=0"); fail witness re-run under the same config.
"""
import json
from pathlib import Path
RT = Path('physical/ref_tile')
XDEF = '+define+HC_DRLY=2 +define+HC_XRLY=0'
W_NEW = 'results/rtl/hbm_hc_ring_1019_drly2/ring_mut1.log'

p = RT / 'hbm_hcq_bank_e2_1017' / 'spec.json'
s = json.loads(p.read_text())
s['reset_ports'] = ['rst_n', 'fa_rst_n', 'fb_rst_n', 'fa_rst_n_o', 'fb_rst_n_o']
p.write_text(json.dumps(s, indent=1) + '\n')

p = RT / 'hbm_hcq_bank_b0_1017' / 'spec.json'
s = json.loads(p.read_text())
s['params']['DRLY'] = 2
for b in s['job']['benches']:
    if 'HC_XDEF' not in b['cmd']:
        b['cmd'] = f"HC_XDEF='{XDEF}' " + b['cmd']
    if b.get('fail_witness'):
        b['fail_witness'] = W_NEW
if 'results/rtl/hbm_hc_ring_1019_drly2' not in s['job']['extra_paths']:
    s['job']['extra_paths'].append('results/rtl/hbm_hc_ring_1019_drly2')
s['structural_change'] = s['structural_change'].split(' HCBANK 10-19:')[0] + (
    ' HCBANK 10-19: DRLY 2 (HC-RINGPLAN GEN2d closed ring: b7 abuts b0, hcx die relay removed; the 2-stage chain-exit'
    ' relay of bank 7 now sits in b0).')
p.write_text(json.dumps(s, indent=1) + '\n')
print('ok')
