#!/usr/bin/env python3
"""Margin-rule SDCs of a station view (CLAUDE HBM-ABSTRACTS stations; owner rule 2026-10-06, the spine recipe
common/make_io_vclk_margin.sh / io_vclk_m_<L>.sdc adapted to the station clocking).

  stn_margin_sdc.py <view.sdc> <ckins_ps> route|signoff [<ckins_ff_min_ps>]  > out.sdc

* ck-domain IO (die clock tree) is re-timed against a virtual clock vclk at the view's measured ck insertion L with a
  0.2 T + 150 ps budget (the 150 ps die clock-arrival allowance); forwarded-clock IO (f_* / o_*) is source-synchronous
  (the clock travels with its bus) and keeps the 0.2 T budget against its own clock.
* vclk latency is corner-true: -max = the SS insertion (setup), -min = the FF minimum insertion when given (hold);
  one SS figure on the hold side would demand ~130 ps of hold buffers per output that the die clock never needs
  (M2_hfd_meso_r32: FF -7.75 ps against 294 ps vclk latency with a 163 ps FF insertion, after 7 hold buffers).
* vclk <-> forwarded clocks: false paths (rst only; resynchronised per domain).
* route: over-constrained to an effective 770 ps -- setup uncertainty 60 + 63 ps on every clock and the meso crossing
  bound (max_delay -ignore_clock_latency, no uncertainty term) 63 ps tighter; signoff: the 60 ps / 356.667 ps contract.
"""
import re
import sys

src, L, mode = sys.argv[1], float(sys.argv[2]), sys.argv[3]
Lmin = float(sys.argv[4]) if len(sys.argv) > 4 else L
T = 833.333
OVER = 63.0 if mode == 'route' else 0.0
io = round(0.2 * T + 150, 3)
out = []
for l in open(src):
    s = l.rstrip('\n')
    m = re.match(r'^(set_(?:input|output)_delay) ([0-9.]+) -clock ck( -add_delay)? (.*)$', s)
    if m:
        out.append(f'{m.group(1)} {io} -clock vclk{m.group(3) or ""} {m.group(4)}')
        out.append(f'{m.group(1)} -min 0 -clock vclk -add_delay {m.group(4)}')
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
        out.append(f'set_clock_latency -max {L:g} [get_clocks vclk]')
        out.append(f'set_clock_latency -min {Lmin:g} [get_clocks vclk]')
# vclk only times the die-clock IO; the one terminal it shares with a forwarded domain is rst, which reaches that
# domain through its own two-flop resynchroniser (timed against the forwarded clock's own input delay above)
fcl = [re.match(r'create_clock -name (f_\S+)', x).group(1) for x in out if re.match(r'create_clock -name f_', x)]
for f in fcl:
    out.append(f'set_false_path -from [get_clocks vclk] -to [get_clocks {f}]')
    out.append(f'set_false_path -from [get_clocks {f}] -to [get_clocks vclk]')
print('\n'.join(out))
print(f'# stn_margin_sdc.py {mode}: ck IO vs vclk at insertion {L:g} ps (hold {Lmin:g} ps), 0.2 T + 150 ps; over-constraint {OVER:g} ps')
