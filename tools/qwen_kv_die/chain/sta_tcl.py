#!/usr/bin/env python3
"""kv-die: the die STA script (GRT parasitics) for die_chain.sh.
usage: sta_tcl.py <kv|r22k> <tt|ff> <out.tcl> [clock plan.json]

qwendie-1011 (textbook audit class 1): with a clock plan (tools/budgets/clock_plan.py record of the die's clock-only
CTS, htop + hreg) every CTS sink pin gets its MEASURED clock arrival as a per-pin clock latency (FF run: the FF
insertion; TT run: mean of the SS and FF insertions -- interpolated, the plan measures SS / FF only), written to
clock_lat_<c>.tcl next to the script and sourced after the clocks.  Without it the die clock is ideal (pathfinding)."""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
die, c, out = sys.argv[1:4]
# qwendie-1012 RELAUNCH7: clock-path OCV in the die STA itself (tools/budgets/common.py OCV, rom_die_clocking_decision
# 5 % on the NON-SHARED clock insertion).  With ideal per-pin latencies OpenSTA has no clock tree and no CRPR, so the
# bound is built from the plan's tree / region structure:
#   per sink k:  x_k = (k's arrival below its region's shared part, minus the region's minimum) + its view's own
#                ETM insertion  ->  latency -max += OCV x_k, -min -= OCV x_k   (non-shared for ANY partner, also intra)
#   per region:  one ideal clock per (domain, region) on the region's sink pins (same period / waveform as the
#                domain clock, synchronous), and an inter-clock uncertainty for every ordered pair of regions of one
#                domain = base + OCV (R_a + R_b), R_r = min non-shared arrival of the region w.r.t. the other region:
#                same tree -> below the trunk fork (region tree + region pad / delay line), other tree -> the whole
#                arrival (trees of one domain share only the PLL output pin).
# so a launch/capture pair in different regions sees OCV (u_launch + u_capture) of its real non-shared insertion and an
# intra-region pair OCV (x_launch + x_capture).  OT_STA_OCV=0 is ONLY for the parity check against the ideal runs.
OCV = float(os.environ.get('OT_STA_OCV', '0.05'))
INTER_BOUND_SS = 150.0     # common.SKEW_INTER_PS: pass criterion for the cross-region pair skew bound
plan = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
L = '/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_'
C = c.upper()
libs = [f'{L}AO_RVT_{C}_nldm_211120.lib.gz', f'{L}INVBUF_RVT_{C}_nldm_220122.lib.gz', f'{L}OA_RVT_{C}_nldm_211120.lib.gz',
        f'{L}SEQ_RVT_{C}_nldm_220123.lib', f'{L}SIMPLE_RVT_{C}_nldm_211120.lib.gz', f'/work/libs/qfd_elements_{c}.lib']
def domain_of(root):
    """STA clock (as created below) of a plan tree root [inst, pin]; None = not a synchronous die clock here"""
    i, p = (root or ['?', '?'])[:2]
    if die == 'kv':
        return 'stream' if i == 'pll' else (f'hclk_{i[5:]}' if i.startswith('ctrl_') and p == 'pll_hbm' else None)
    if i == 'clk_rx':
        return 'stream'
    return {'pll_serial': 'serial', 'pll_ucie': 'ucie', 'pll_serdes': 'serdes'}.get(p) if i == 'io_collective' else None
PERIOD = dict(stream=833.333, serial=833.333 * 4.0 / 3.0, ucie=833.333, serdes=833.333)
if die == 'kv':
    libs.append(f'/work/libs/ot_hbm3e_phy_{c}.lib')
    clocks = """create_clock -name stream -period 833.333 [get_pins -quiet {pll/pll_WS pll/pll_WN pll/pll_ES pll/pll_EN pll/pll_c pll/pll_fwd}]
foreach s {WS WN ES EN} { create_clock -name hclk_$s -period 1024 [get_pins -quiet ctrl_$s/pll_hbm] }
"""
    DOMS = ['stream', 'hclk_WS', 'hclk_WN', 'hclk_ES', 'hclk_EN']
else:
    clocks = """create_clock -name stream -period 833.333 [get_pins -quiet {clk_rx/pll_*}]
create_clock -name serial -period [expr {833.333*4.0/3.0}] [get_pins -quiet io_collective/pll_serial]
foreach k {ucie serdes} { create_clock -name $k -period 833.333 [get_pins -quiet io_collective/pll_$k] }
"""
    DOMS = ['stream', 'serial', 'ucie', 'serdes']
# qwen-tp8 r10: a case-specific clock file ($OT_STA_CLOCKS: create_clock lines, first line '# DOMS a b c') replaces the
# built-in die clocks (the merged tp8b die has the KV PLL, the clock receiver and four strip PLLs)
compensated_clock_budget = False
if os.environ.get('OT_STA_CLOCKS'):
    _cp = Path(os.environ['OT_STA_CLOCKS'].format(corner=c))
    if _cp.is_dir():
        _cp = _cp / f'clocks_{c}.tcl'
    elif _cp.name == 'clocks.tcl' and _cp.with_name(f'clocks_{c}.tcl').exists():
        _cp = _cp.with_name(f'clocks_{c}.tcl')
    _ct = _cp.read_text()
    if '# INSERTION_COMPENSATED ' in _ct:
        if '# OWNER_CLOCK_BUDGET v1\n' not in _ct:
            raise ValueError('phi-R clock file lacks strict owner setup/hold budget; regenerate it')
        compensated_clock_budget = True
        if f'# INSERTION_COMPENSATED {c}\n' not in _ct:
            raise ValueError(f'wrong clock measurement corner: {_cp} for {c}')
        if plan:
            raise ValueError('measured clock plan cannot override phi-R source-compensated clocks')
    DOMS = _ct.splitlines()[0].split()[2:]
    clocks = _ct
lat, ocv_src = '', ''
if plan:
    P_ = json.loads(Path(plan).read_text())
    si = P_['sink_insertion']
    # qwendie-1012: a bound hard view's clock pin (clock_plan.py balance 'view_pin_insertion'): OpenSTA takes a pin
    # latency on a macro as its internal-register latency and subtracts the ETM clock-tree path, so the physical pin
    # arrival is written as arrival + insertion (-min min / -max max) and the view's pin lands where the die delivers
    vi = P_.get('view_pin_insertion', {})
    sr, R_ = P_['sink_region'], P_.get('regions', {})
    arr = lambda v: v[1] if c == 'ff' else (v[0] + v[1]) / 2
    vmid = lambda k: (sum(vi[k][c]) / 2) if k in vi else 0.0
    def trunk(r):      # region r's shared (trunk) arrival in this corner: recorded insertion - region tree - region pad
        g = R_.get(r, {})
        ss, ff = (g.get('insertion_ss') or {}).get('mean'), (g.get('insertion_ff') or {}).get('mean')
        if not ss or ff is None:
            return 0.0
        t = max(0.0, ss - (g.get('region_tree_ss') or {}).get('mean', ss) - g.get('planned_root_pad_ss_ps', 0.0))
        return t * ((ff if c == 'ff' else (ss + ff) / 2) / ss)
    tree_of = lambda k: sr[k].split(':', 1)[0]
    dom = {k: domain_of(P_['trees'].get(tree_of(k), {}).get('root')) for k in si if k in sr}
    regs = defaultdict(list)
    for k, d_ in dom.items():
        if d_:
            regs[(d_, sr[k])].append(k)
    tr = {r: trunk(r[1]) for r in regs}
    Rr = {r: max(0.0, min(arr(si[k]) - tr[r] for k in ks)) for r, ks in regs.items()}
    x = {k: max(0.0, arr(si[k]) - tr[r] - Rr[r]) + vmid(k) for r, ks in regs.items() for k in ks}
    def lat_(k, v):
        a, o = arr(v), OCV * x.get(k, 0.0)
        if k in vi:
            mn, mx = vi[k][c]
            return (f'set_clock_latency -min {a + mn - o:.1f} $p; set_clock_latency -max {a + mx + o:.1f} $p')
        if o > 0.05:
            return f'set_clock_latency -min {a - o:.1f} $p; set_clock_latency -max {a + o:.1f} $p'
        return f'set_clock_latency {a:.1f} $p'
    rows = [f'set p [get_pins -quiet {{{k}}}]; if {{[llength $p]}} {{ {lat_(k, v)}; incr ot_lat_n }} else {{ incr ot_lat_miss }}'
            for k, v in sorted(si.items())]
    # one ideal clock per (domain, region) on its sink pins + inter-clock uncertainty = base + OCV (R_a + R_b)
    base = 60.0 if c == 'tt' else 25.0
    sh = 'setup' if c == 'tt' else 'hold'
    rname = {r: f'{r[0]}__r{i}' for i, r in enumerate(sorted(regs))}
    rc, pairs, worst = [], [], defaultdict(lambda: (0.0, None))
    if True:     # region clocks also at OT_STA_OCV=0: that run is the parity check of the mechanism itself
        for r, ks in sorted(regs.items()):
            pins = ' '.join(ks)
            rc.append(f'create_clock -name {rname[r]} -period {PERIOD.get(r[0], 1024.0)} [get_pins -quiet {{{pins}}}]')
        for a_ in sorted(regs):
            for b_ in sorted(regs):
                if a_ == b_ or a_[0] != b_[0]:
                    continue
                same = tree_of(regs[a_][0]) == tree_of(regs[b_][0])
                term = OCV * ((Rr[a_] + Rr[b_]) if same else (Rr[a_] + tr[a_] + Rr[b_] + tr[b_]))
                pairs.append(f'set_clock_uncertainty -{sh} {base + term:.1f} -from [get_clocks {rname[a_]}] -to [get_clocks {rname[b_]}]')
                # worst cross-region pair bound in this corner incl. both sinks' own parts (max x in each region)
                full = term + OCV * (max(x[k] for k in regs[a_]) + max(x[k] for k in regs[b_]))
                if full > worst[a_[0]][0]:
                    worst[a_[0]] = (full, f'{a_[1]}|{b_[1]}')
    # SS-equivalent of a corner delay (clock_plan balance: SS = kss TT, FF = 0.53 SS)
    to_ss = 1.0 / 0.53 if c == 'ff' else 2.0 / (1.0 + 0.53)
    summ = dict(corner=c, ocv=OCV, region_clocks=len(rc), region_pair_uncertainties=len(pairs),
                worst_cross_region_ocv={d_: dict(corner_ps=round(v[0], 1), ss_equiv_ps=round(v[0] * to_ss, 1), pair=v[1],
                                                 within_inter_bound=v[0] * to_ss <= INTER_BOUND_SS) for d_, v in worst.items()},
                max_sink_own_ocv_ps=round(OCV * max(x.values(), default=0.0), 1))
    Path(out).with_name(f'clock_ocv_{c}.json').write_text(json.dumps(summ, indent=1) + '\n')
    Path(out).with_name(f'clock_lat_{c}.tcl').write_text('set ot_lat_n 0; set ot_lat_miss 0\n' + '\n'.join(rows) +
        f'\nputs "OT_CLOCK_PLAN corner={c} sinks={len(rows)} bound=$ot_lat_n missing=$ot_lat_miss"\n')
    lat = f'source /work/clock_lat_{c}.tcl\n'
    if rc:
        grp = defaultdict(list)
        for r in regs:
            grp[r[0]].append(rname[r])
        Path(out).with_name(f'clock_regions_{c}.tcl').write_text('\n'.join(rc) + '\n')
        ocv_src = f'\nsource /work/clock_ocv_{c}.tcl'
        Path(out).with_name(f'clock_ocv_{c}.tcl').write_text('\n'.join(pairs) + f'\nputs "OT_CLOCK_OCV corner={c} ocv={OCV} '
            f'region_clocks={len(rc)} pairs={len(pairs)}"\n')
        # the domain clocks keep every register the plan does not hold; region clocks join their domain's sync group
        clocks += '\nsource /work/clock_regions_' + c + '.tcl\nset_clock_groups -asynchronous ' + ' '.join(
            '-group [get_clocks {' + ' '.join([d_] + sorted(grp.get(d_, []))) + '}]' for d_ in DOMS)
mm, unc = ('max', 'set_clock_uncertainty -setup 60 [all_clocks]') if c in ('tt', 'ss') else ('min', 'set_clock_uncertainty -hold 25 [all_clocks]')
if compensated_clock_budget:
    # phi-R files carry the owner setup skew and H1 hold bounds themselves.
    # The generic 60/25 defaults would overwrite these strict budgets.
    unc = ''
if not compensated_clock_budget and 'set_clock_groups' not in clocks:
    clocks += '\nset_clock_groups -asynchronous ' + ' '.join(f'-group {d_}' for d_ in DOMS)
unc += ocv_src
rd = '\n'.join(f'read_liberty {x}' for x in libs)
# die-evidence-2 2026-10-09: ETM-bound element views (tools/qwen_die_etm_map.py: routed sign-off ETMs of slab_m8 /
# cst / chead) are read FIRST when the run's libs carry them; qfd_elements_<c>.lib then holds only the ASSUMED rest
rd = f'if {{[file exists /work/libs/qfd_etm_{c}.lib]}} {{ read_liberty /work/libs/qfd_etm_{c}.lib }}\n' + rd
# kv-die lead 2026-10-12 (die_iter_1012): per-view ETMs bound by tools/qwen_kv_die/bind_views.py (one lib per master)
rd = f'foreach f [lsort [glob -nocomplain /work/libs/qfd_etm_*_{c}.lib]] {{ read_liberty $f }}\n' + rd
summary = (f'report_checks -path_delay {mm} -group_path_count 3000000 -endpoint_path_count 1 -unique_paths_to_endpoint '
           f'-format summary > /work/grt_{c}_summary.rpt') if (die == 'kv' or os.environ.get('OT_STA_SUMMARY')) else ''
# DIE-FLOW 2026-10-17 (FLOW-HOLD D1-D3, OT_HOLD_BUDGET=die): per-link FF hold dump for tools/die_hold_budget.py
# (launch-min from the bound ETMs, delta, H, U per endpoint path; OT_HOLD_DUMP_PATHS endpoints, default 200000)
hold_dump = ''
if os.environ.get('OT_HOLD_BUDGET') == 'die' and c == 'ff':
    hold_dump = (f"\n  report_checks -path_delay min -group_path_count {int(os.environ.get('OT_HOLD_DUMP_PATHS', '200000'))} "
                 f"-endpoint_path_count 1 -format full_clock_expanded -digits 1 > /work/hold_links_ff.rpt")
tcl = f"""proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag rss_mb=[expr {{$r/1024}}] t=[clock seconds]"; flush stdout }}
proc step {{name body}} {{ set t0 [clock milliseconds]
  if {{[catch {{uplevel 1 $body}} err]}} {{ puts "OT_STEP_FAIL $name $err" }}
  puts "OT_TIME step=$name s=[format %.1f [expr {{([clock milliseconds]-$t0)/1000.0}}]]"; mem $name }}
# qwendie-1012 RELAUNCH7: a missing liberty is fatal (kv it1b-it1d ran without ot_hbm3e_phy_<c>.lib: step only logged
# OT_STEP_FAIL and the PHY instances were black boxes -- their paths were never timed)
if {{[catch {{
{rd}
}} err]}} {{ puts "OT_STEP_FAIL libs $err"; exit 1 }}
step load {{ read_db /work/ckpt_grt.odb }}
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
# die-evidence-2 2026-10-09: GRT parasitics from the SPEF the GRT session wrote (grt.tcl step spef).  The old
# read_guides + estimate_parasitics -global_routing path gave no wire RC (GRT-0008): the run now fails without the SPEF.
if {{![file exists /work/die_grt.spef]}} {{ puts "OT_STEP_FAIL spef missing: /work/die_grt.spef (GRT-0008: guides carry no RC)"; exit 1 }}
# ds-1010 10-10: a failed read_spef must stop the run (the step proc only logs): KV11's first STA timed the die with no wire RC
if {{[catch {{read_spef /work/die_grt.spef}} err]}} {{ puts "OT_STEP_FAIL spef $err"; exit 1 }}
{clocks}
{lat}{unc}
step sta {{
  report_checks -path_delay {mm} -group_path_count 3000000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /work/grt_{c}_ends.rpt
  # qwen-split kvsys 10-14: startpoint of every endpoint's worst path (the classifier needs the LAUNCH instance; the end
  # report alone left 429 k kvs1 endpoints 'unresolved_driver' on bundled / mixed-direction die nets)
  {summary}
  report_checks -path_delay {mm} -group_path_count 5 -fields {{slew cap input_pins nets}} -digits 1 > /work/grt_{c}_paths.rpt
  report_tns; report_wns; report_worst_slack -{mm}
  report_check_types -max_slew -max_capacitance -violators > /work/grt_{c}_drv.rpt{hold_dump}
}}
puts OT_STA_DONE
"""
open(out, 'w').write(tcl)
