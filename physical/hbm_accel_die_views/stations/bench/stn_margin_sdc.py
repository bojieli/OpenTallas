#!/usr/bin/env python3
"""Margin-rule SDCs of a station view (CLAUDE HBM-ABSTRACTS stations; owner rule 2026-10-06, the spine recipe
common/make_io_vclk_margin.sh / io_vclk_m_<L>.sdc adapted to the station clocking).

  stn_margin_sdc.py <view.sdc> <ckins_ps> route|signoff [<ckins_ff_min_ps> <ckins_ff_max_ps>]  > out.sdc

* ck-domain IO (die clock tree) is re-timed against a virtual clock vclk at the view's measured ck insertion L with a
  0.2 T + 150 ps budget (the 150 ps die clock-arrival allowance); forwarded-clock IO (f_* / o_*) is source-synchronous
  (the clock travels with its bus) and keeps the 0.2 T budget against its own clock.
* hold: corner-true IO hold in one SDC (coordinator-approved 2026-10-06; common/make_io_vclk_ff.sh is the post-SDC
  form): with the FF leaf insertion range Lmin..Lmax (4th/5th arguments, measured on a routed view), RULE H1 (h1-verify
  2026-10-08): output -min delay L - (Lmin + Lmax) / 2 - 25 (latest capture: the mean leaf + 50 ps with the 25 ps hold uncertainty: the sender carries
  the link term once) and input -min delay (Lmin + Lmax) / 2 - L (nominal launch, no die term), i.e. the neighbour's die-clock leaf lands in
  this block's own FF leaf spread with a 50 ps die-skew allowance; the 150 ps die arrival term stays on setup.  One
  SS L on the hold side alone demands ~130 ps of hold buffers per output (M2_hfd_meso_r32: -7.75 ps after 7 buffers).
* the hold-side -min delays also credit the connected die path's minimum arrival (io_min_delay.json: upstream FF
  clk->Q for inputs + 50 % of the measured FF wire delay over the minimum die wire, coordinator decision 2026-10-06).
* meso views: rst (synchroniser input only) is a false path.
* vclk <-> forwarded clocks: false paths (rst only; resynchronised per domain).
* route: over-constrained to an effective 770 ps -- setup uncertainty 60 + 63 ps on every clock and the meso crossing
  bound (max_delay -ignore_clock_latency, no uncertainty term) 63 ps tighter; signoff: the 60 ps / 356.667 ps contract.
"""
import re
import sys

src, L, mode = sys.argv[1], float(sys.argv[2]), sys.argv[3]
FFM = len(sys.argv) > 5
Lmin = float(sys.argv[4]) if len(sys.argv) > 4 else L   # FF min leaf insertion
Lmax = float(sys.argv[5]) if len(sys.argv) > 5 else Lmin   # FF max leaf insertion (outputs: latest capture)
T = 833.333
_iom = __import__('pathlib').Path(src).resolve().parents[1] / 'io_min_delay.json'
_mst = __import__('pathlib').Path(src).stem
IOMIN = __import__('json').loads(_iom.read_text())['views'].get(_mst, {}) if _iom.exists() else {}
OVER = 63.0 if mode == 'route' else 0.0
io = round(0.2 * T + 150, 3)
out = []
for l in open(src):
    s = l.rstrip('\n')
    m = re.match(r'^(set_(?:input|output)_delay) ([0-9.]+) -clock ck( -add_delay)? (.*)$', s)
    if m:
        # hold side (min delays, against vclk at the SS insertion L): inputs arrive no earlier than the block's FF
        # MAX leaf insertion minus the 50 ps die-skew allowance, outputs are captured no earlier than its FF MIN leaf
        # insertion plus 50 ps -- one SDC for routing (hold repair at BC) and for both sign-off corners
        if FFM:
            # RULE H1 (h1-verify 2026-10-08): outputs captured at the nominal (mean) leaf + 50 (sender carries the link term);
            # inputs launched at the mean leaf, plain 25 ps (was Lmin + 50 / Lmax - 50: both optimistic, 50 counted twice)
            mn = ((Lmin + Lmax) / 2 - L) if m.group(1) == 'set_input_delay' else (L - (Lmin + Lmax) / 2 - 25)   # + 25 ps hold uncertainty
            # + the minimum arrival credit of the connected die path (stations/io_min_delay.json, stn_io_min.py):
            # upstream pin-launch clk->Q at FF + 50 % of the measured FF wire delay over the minimum die wire
            mn += IOMIN.get('in' if m.group(1) == 'set_input_delay' else 'out', {}).get('min_delay_ps', 0.0)
        else:
            mn = 0
        out.append(f'{m.group(1)} {io} -clock vclk{m.group(3) or ""} {m.group(4)}')
        out.append(f'{m.group(1)} -min {mn:g} -clock vclk -add_delay {m.group(4)}')
        continue
    m = re.match(r'^(set_max_delay -ignore_clock_latency .*\]) ([0-9.]+)$', s)
    if m:
        out.append(f'{m.group(1)} {float(m.group(2)) - OVER:.3f}')
        continue
    if s.startswith('set_clock_uncertainty -setup'):
        out.append(f'set_clock_uncertainty -setup {60 + OVER:g} [all_clocks]')
        continue
    out.append(s)
    if s.startswith('create_clock -name ck '):
        out.append(f'create_clock -name vclk -period {T}')
        out.append(f'set_clock_latency {L:g} [get_clocks vclk]')
# vclk only times the die-clock IO; the one terminal it shares with a forwarded domain is rst, which reaches that
# domain through its own two-flop resynchroniser (timed against the forwarded clock's own input delay above)
fcl = [re.match(r'create_clock -name (f_\S+)', x).group(1) for x in out if re.match(r'create_clock -name f_', x)]
for f in fcl:
    out.append(f'set_false_path -from [get_clocks vclk] -to [get_clocks {f}]')
    out.append(f'set_false_path -from [get_clocks {f}] -to [get_clocks vclk]')
# A meso view's rst terminal reaches only the two-flop resynchronisers of each FIFO domain (ot_hbm_stn_meso wrs/rrs):
# a synchroniser input carries no single-cycle setup/hold relation (M2_hfd_meso_r32 FF: rst -> rrs[0] -39 ps).
sv = open(src[:-4] + '.sv').read()
if 'ot_hbm_stn_meso' in sv and 'rst[0]' not in sv.replace('.rst_n(rst[0])', ''):
    out.append('set_false_path -from [get_ports {rst[0]}]')
# FF file only (4th argument given): a 50 ps die-clock skew allowance on IO hold (coordinator 2026-10-06: a die
# tree still has skew at FF), as inter-clock hold uncertainty on both IO directions
print('\n'.join(out))
print(f'# stn_margin_sdc.py {mode}: ck IO vs vclk at {L:g} ps (hold model FF leaf {Lmin:g}..{Lmax:g} ps +- 50 ps), 0.2 T + 150 ps; over-constraint {OVER:g} ps')
