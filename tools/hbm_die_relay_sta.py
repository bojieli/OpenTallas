#!/usr/bin/env python3
"""HBM die STA on the relay-instanced die (tools/hbm_die_views.py die --case sta --relays) with the planned clock entry.

Clock model (same contract as tools/hbm_die_clock_context.py): every die clock sink is an ideal clock pin with a
per-corner source latency = its clock-plan region flop target - the block's own insertion.  The relays / wire stages
(hfd_rly_*) are new die sinks the plan does not list: each joins the region of the nearest planned sink of its own
clock domain (die CTS delivers that region's flop target to it) and its entry is that target - the relay's internal
insertion (relay Liberty recipe: SS 70..90 ps, FF 40..55 ps; mid values).  No physical clock-tree credit.

Writes <case>/run_clock_{ss,ff}.tcl (the case's load / placement / placement-parasitics prefix + clocks + reports) and
<case>/relay_clock_context.json.  The reports dump every failing endpoint (start, end, slack) to paths_<corner>.txt so
tools/hbm_die_relay_sta.py --budgets turns them into per-path budgets.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

RELAY_INS = dict(ss=80.0, ff=47.5)
DOM = {'n_clk_stream': 'clk_stream', 'n_clk_serial': 'clk_serial', 'n_clk_hbm': 'clk_hbm', 'n_clk_link': 'clk_link'}
PERIOD_PS = {'clk_stream': 833.333, 'clk_serial': 1111.111, 'clk_hbm': 1024.0, 'clk_link': 833.333}


def places(case):
    xy = {}
    for ln in (case / 'place.tcl').read_text().splitlines():
        m = re.match(r'\s*\S*place\S*\s+(\S+)\s+([-\d.]+)\s+([-\d.]+)', ln)
        if m:
            xy[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return xy


def relay_clocks(case):
    out = {}
    for m in re.finditer(r'\n\s*(hfd_rly_\d+)\s+(\S+)\s*\(\.ck\((\S+?)\)', (case / 'die.v').read_text()):
        out[m.group(2)] = DOM.get(m.group(3).split('[')[0], 'clk_stream')
    return out


LIB_TO_INS = dict(ss=110.0, ff=40.0)   # lib min ck->out minus measured insertion, mean over the 6 blocks with both


def lib_ck_out_min(path):
    t = Path(path).read_text()
    v = [float(m.group(1)) for m in re.finditer(
        r'related_pin : "ck(?:\[0\])?";\s*timing_type : rising_edge;\s*cell_rise\([^)]*\) \{\s*index_1[^;]*;\s*'
        r'(?:index_2[^;]*;\s*)?values\("([-\d.]+)', t)]
    return min(v) if v else None


def view_insertion(case, master, measured):
    """the hardened view's own clock insertion (ps per corner): the closure loop's measured CTS insertion when it has
    one, else the view Liberty's fastest clock -> output arc less the measured lib-to-insertion offset; None when the
    master has no view Liberty (generated placeholder: the sheet target stays)"""
    if master in measured:
        return {c: float(measured[master][c]['mean']) for c in ('ss', 'ff')}, 'measured (closure-loop calibrate)'
    out = {}
    for c in ('ss', 'ff'):
        f = case / f'{master}_{c}.lib'
        v = lib_ck_out_min(f) if f.exists() else None
        if v is None:
            return None, None
        out[c] = round(v - LIB_TO_INS[c], 1)
    return out, 'view Liberty min ck->out - offset'


def compose(case, ctx, measured=None):
    xy = places(case)
    rel = relay_clocks(case)
    sinks = {k: dict(v) for k, v in ctx['sinks'].items()}
    # the plan's sheets carry TARGET insertions ('no calibration yet'); a hardened view's actual insertion is smaller
    #   and its Liberty arcs embed it: entry = region target - ACTUAL insertion keeps every flop at the region target
    tgt0 = ctx['region_flop_target_ps']
    for k, s_ in sinks.items():
        ins, src = view_insertion(case, s_['master'], measured or {})
        if ins:
            t_ = tgt0[s_['region']]
            s_['internal_ps'] = ins
            s_['insertion_source'] = src
            s_['entry_ps'] = {c: round(t_[n] - ins[c], 3) for n, c in enumerate(('ss', 'ff'))}
    tgt = ctx['region_flop_target_ps']
    by_dom = defaultdict(list)
    for k, s in sinks.items():
        if s['instance'] in xy:
            by_dom[s['domain']].append((xy[s['instance']], s['region']))
    # chain-aware: the registers of a chain nearer its source take the source block's region, the rest the sink's
    #   (the region crossing then sits on one relay-to-relay hop, as the plan's inter-region budget assumes)
    inst_reg = {s['instance']: (s['domain'], s['region']) for s in sinks.values()}
    want = {}
    rj = case / 'relays.json'
    for ch in (json.loads(rj.read_text()).get('chains', []) if rj.exists() else []):
        regs = ch.get('regs', [])
        for k, r_ in enumerate(regs):
            end = ch.get('src') if k < (len(regs) + 1) // 2 else ch.get('dst')
            if end in inst_reg:
                want[r_] = inst_reg[end]
    added, nodom = {}, []
    for inst, d in sorted(rel.items()):
        if inst not in xy or not by_dom.get(d):
            nodom.append(inst)
            continue
        p = xy[inst]
        if inst in want and want[inst][0] == d:
            reg = want[inst][1]
        else:
            _, reg = min(by_dom[d], key=lambda q: abs(q[0][0] - p[0]) + abs(q[0][1] - p[1]))
        t = tgt[reg]
        added[f'{inst}/ck'] = dict(instance=inst, port='ck', master='hfd_rly', region=reg, domain=d,
                                   internal_ps=dict(RELAY_INS),
                                   entry_ps={c: round(t[n] - RELAY_INS[c], 3) for n, c in enumerate(('ss', 'ff'))})
    return added, nodom, sinks


def constraints(sinks, corner):
    L = ['set_cmd_units -time ns -capacitance fF',
         'set ot_clock_missing {}', 'set ot_clock_bound 0', 'set ot_dom [dict create]', 'set ot_lat {}']
    for key, s in sorted(sinks.items()):
        pin = key if '[' in s['port'] else key + '[0]'
        L.append(f'set p [get_pins -quiet {{{pin}}}]; if {{![llength $p]}} {{ set p [get_pins -quiet {{{key}}}] }}; '
                 f'if {{![llength $p]}} {{ lappend ot_clock_missing {{{pin}}} }} else {{ dict lappend ot_dom {s["domain"]} $p; '
                 f'lappend ot_lat [list {s["domain"]} {s["entry_ps"][corner] / 1000:.6f} $p] }}')
    for d, per in PERIOD_PS.items():
        L.append(f'if {{[dict exists $ot_dom {d}]}} {{ create_clock -name {d} -period {per / 1000:.6f} [dict get $ot_dom {d}] }}')
    L += ['foreach e $ot_lat { lassign $e d l p; set_clock_latency -source -clock $d $l $p; incr ot_clock_bound }',
          'set_clock_uncertainty -setup 0.210 [all_clocks]', 'set_clock_uncertainty -hold 0.025 [all_clocks]',
          # mesochronous domains: no synchronous timing between different die clocks (crossings are FIFO / forwarded)
          'set cl [all_clocks]',
          'foreach a $cl { foreach b $cl { if {[get_name $a] ne [get_name $b]} { set_false_path -from $a -to $b } } }',
          f'puts "OT_CLOCK_CONTEXT corner={corner} bound=$ot_clock_bound missing=[llength $ot_clock_missing]"',
          'puts "OT_CLOCK_MISSING [lrange $ot_clock_missing 0 40]"']
    return '\n'.join(L) + '\n'


def report(corner):
    k = 'max' if corner == 'ss' else 'min'
    return f'''
puts "OT_WNS corner={corner} [sta::format_time [sta::worst_slack -{k}] 4] tns=[sta::format_time [sta::total_negative_slack -{k}] 3]"
set f [open /out/paths_{corner}.txt w]
set n 0
foreach pe [find_timing_paths -path_delay {k} -corner {corner} -group_path_count 200000 -endpoint_path_count 1 -slack_max 0.0] {{
  puts $f "[get_full_name [get_property $pe startpoint]] [get_full_name [get_property $pe endpoint]] [get_property $pe slack]"
  incr n
}}
close $f
puts "OT_FAIL_ENDPOINTS corner={corner} n=$n"
report_checks -path_delay {k} -corner {corner} -group_path_count 10 -format full_clock_expanded -digits 4 -fields {{slew cap input_pins}}
puts OT_DONE
'''


def budgets(case):
    """per-path budgets: failing endpoints grouped by (start instance, end instance) with worst slack and count"""
    out = {}
    for c in ('ss', 'ff'):
        p = case / f'paths_{c}.txt'
        if not p.exists():
            continue
        g = defaultdict(lambda: [0, 0.0, None])
        for ln in p.read_text().splitlines():
            a, b, s = ln.split()
            s = float(s) * 1000.0
            key = (a.split('/')[0], b.split('/')[0])
            r = g[key]
            r[0] += 1
            if r[2] is None or s < r[1]:
                r[1], r[2] = s, (a, b)
        rows = sorted(([k[0], k[1], v[0], round(v[1], 1), v[2]] for k, v in g.items()), key=lambda r: r[3])
        out[c] = dict(failing_endpoints=sum(r[2] for r in rows), instance_pairs=len(rows), rows=rows)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case', required=True)
    ap.add_argument('--clock-context', help='clock_context.json from tools/hbm_die_clock_context.py')
    ap.add_argument('--budgets', action='store_true')
    ap.add_argument('--measured', help='measured_insertion.json (closure-loop calibrate) for view insertion')
    a = ap.parse_args()
    case = Path(a.case)
    if a.budgets:
        b = budgets(case)
        (case / 'path_budgets.json').write_text(json.dumps(b, indent=0))
        print(json.dumps({c: {k: v for k, v in x.items() if k != 'rows'} for c, x in b.items()}))
        return
    ctx = json.loads(Path(a.clock_context).read_text())
    measured = json.loads(Path(a.measured).read_text())['blocks'] if a.measured else {}
    added, nodom, sinks0 = compose(case, ctx, measured)
    sinks = dict(sinks0, **added)
    (case / 'relay_clock_context.json').write_text(json.dumps(dict(view_sinks=sinks0, relay_sinks=added, relays_without_domain=nodom,
                                                                   relay_internal_ps=RELAY_INS), indent=0))
    base = (case / 'run.tcl').read_text()
    prefix = base.partition('set_cmd_units -time ns')[0]
    assert 'estimate_parasitics' in prefix, 'case run.tcl has no parasitics step before the clock boundary'
    for c in ('ss', 'ff'):
        (case / f'run_clock_{c}.tcl').write_text(prefix + constraints(sinks, c) + report(c))
    print(json.dumps(dict(planned_sinks=len(ctx['sinks']), relay_sinks=len(added), relays_without_domain=len(nodom))))


if __name__ == '__main__':
    main()
