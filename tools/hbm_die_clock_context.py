#!/usr/bin/env python3
"""Compose measured hierarchical clock entries before HBM die-context STA.

This is a clock-budget implementation, not a claim that the planned padding has
been physically routed.  Each corner gets a separate analysis: SS insertion must
never be used as FF clock latency.  Missing clock/view coverage remains explicit.
"""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path

PERIOD_PS = {'clk_stream': 833.333, 'clk_serial': 1111.111,
             'clk_hbm': 1024.0, 'clk_link': 833.333}


def read(path):
    p = Path(path)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())


def contract(model, plan, sheets):
    by = {i[0]: i for i in model['insts']}
    sinks, missing = {}, []
    targets = defaultdict(lambda: [0.0, 0.0])
    for key, region in plan['sink_region'].items():
        inst, port = key.rsplit('/', 1)
        if inst not in by:
            missing.append({'sink': key, 'reason': 'clock plan instance absent from die model'})
            continue
        master = by[inst][1]
        if master not in sheets:
            missing.append({'sink': key, 'reason': 'no block insertion sheet', 'master': master})
            continue
        ins = sheets[master]['clock']['internal_insertion']
        raw = plan['sink_insertion'][key]
        early = plan['regions'][region].get('early_branch_ps', 0.0)
        # Same compensation equation as budget_sheet.py. Preserve its FF early
        # branch contract; this is planned padding, not extracted die delay.
        for n, c in enumerate(('ss', 'ff')):
            targets[region][n] = max(targets[region][n], raw[n] + ins[c] + early)
        sinks[key] = dict(instance=inst, port=port, master=master, region=region,
                          domain=region.split(':', 1)[0], raw_cts_ps=raw,
                          internal_ps={c: ins[c] for c in ('ss', 'ff')},
                          insertion_grade=ins['grade'], insertion_source=ins['source'])
    for key, sink in sinks.items():
        sink['entry_ps'] = {c: round(targets[sink['region']][n] - sink['internal_ps'][c], 3)
                            for n, c in enumerate(('ss', 'ff'))}
        sink['pad_ps'] = {c: round(sink['entry_ps'][c] - sink['raw_cts_ps'][n], 3)
                          for n, c in enumerate(('ss', 'ff'))}
        if min(sink['pad_ps'].values()) < -0.01:
            raise ValueError(f'{key}: compensated clock requires negative padding')
        if sink['domain'] not in PERIOD_PS:
            raise ValueError(f'{key}: unknown clock domain {sink["domain"]}')
    inst_domains = defaultdict(set)
    for s in sinks.values():
        inst_domains[s['instance']].add(s['domain'])
    crossings = []
    for bid, cls, bits, endpoints in model['buses']:
        if cls in ('clock', 'clock_trunk', 'reset', 'reset_tree', 'top_in', 'fclk'):
            continue
        domains = sorted(set().union(*(inst_domains[e[0]] for e in endpoints)))
        if len(domains) > 1:
            crossings.append(dict(bus=bid, cls=cls, bits=bits, domains=domains,
                                  endpoints=endpoints, timing_exception_applied=False))
    return dict(schema='opentallas.hbm.die_clock_context.v1',
                method='region flop target = max(measured tree entry + block insertion) + planned early-branch reserve; pin entry = target - block insertion',
                period_ps=PERIOD_PS, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                extra_die_setup_skew_ps=150, clock_model='ideal per-pin planned entry, measured clock-only CTS basis',
                physically_routed_clock=False, final_signoff_eligible=False,
                added_data_cycles=0, sinks=sinks, missing=missing,
                cross_domain_interfaces=crossings,
                region_flop_target_ps=dict(targets),
                limitations=['Padding must be implemented and checked against actual die CTS.',
                             'Provisional or absent macro views cannot receive closure credit.',
                             'Forwarded-clock interfaces require their explicit clock contract.',
                             'HBM functional clock is 976.5625MHz (1024ps) per existing protocol/budget contract; a 1.2GHz service requires separate crossing/ratio implementation and pricing.'])


def constraints(rec, corner):
    lines = ['set_cmd_units -time ns -capacitance fF',
             '# Clock nets are ideal here: data wires retain their actual parasitics.',
             '# The clock plan supplies pin arrival; do not propagate the unrouted clock net.',
             'set ot_clock_missing {}', 'set ot_clock_bound 0', 'set ot_bound_names [dict create]',
             'proc ot_clock_pin {name} {',
             '  set inst [lindex [split $name /] 0]',
             '  foreach p [get_pins -quiet "$inst/*"] {',
             '    if {[get_full_name $p] eq $name} { return $p }',
             '  }', '  return {}', '}',
             'set ot_domain_pins [dict create]']
    for key, s in rec['sinks'].items():
        pin = key if '[' in s['port'] else key + '[0]'
        lines += [f'set p [ot_clock_pin {{{pin}}}]',
                  f'if {{![llength $p]}} {{ lappend ot_clock_missing {{{pin}}} }} else {{ dict lappend ot_domain_pins {s["domain"]} $p }}']
    for domain, period in PERIOD_PS.items():
        lines += [f'if {{[dict exists $ot_domain_pins {domain}]}} {{',
                  f'  create_clock -name {domain} -period {period / 1000:.9f} [dict get $ot_domain_pins {domain}]',
                  '}']
    for key, s in rec['sinks'].items():
        pin = key if '[' in s['port'] else key + '[0]'
        lines += [f'set p [ot_clock_pin {{{pin}}}]',
                  f'if {{[llength $p]}} {{ set_clock_latency -source -clock {s["domain"]} {s["entry_ps"][corner] / 1000:.9f} $p; dict set ot_bound_names {{{pin}}} 1; incr ot_clock_bound }}']
    lines += ['set_clock_uncertainty -setup 0.210 [all_clocks]',
              'set_clock_uncertainty -hold 0.025 [all_clocks]',
              '# 60 ps setup policy + unchanged conservative 150 ps die skew allowance.',
              'puts "OT_CLOCK_CONTEXT corner=' + corner + ' bound=$ot_clock_bound missing=[llength $ot_clock_missing]"',
              'puts "OT_CLOCK_MISSING $ot_clock_missing"',
              'set ot_unmapped_clock_pins {}',
              'foreach net {n_clk_stream n_clk_serial n_clk_hbm n_clk_link} {',
              '  foreach p [get_pins -quiet -of_objects [get_nets -quiet "$net $net\\[0\\]"]] {',
              '    set n [get_full_name $p]',
              '    if {![dict exists $ot_bound_names $n]} {lappend ot_unmapped_clock_pins $n}',
              '  }', '}',
              'puts "OT_CLOCK_UNMAPPED count=[llength $ot_unmapped_clock_pins] pins=$ot_unmapped_clock_pins"']
    return '\n'.join(lines) + '\n'


def report(corner):
    kind = 'max' if corner == 'ss' else 'min'
    return f'''
set ot_worst NA
foreach p [find_timing_paths -path_delay {kind} -corner {corner} -group_path_count 1] {{
  set s [get_property $p slack]
  if {{$ot_worst eq "NA" || $s < $ot_worst}} {{set ot_worst $s}}
}}
puts "OT_CLOCK_CONTEXT_SLACK corner={corner} path={kind} slack_ns=$ot_worst"
report_checks -path_delay {kind} -corner {corner} -group_path_count 5 -format full_clock_expanded -digits 6 -fields {{slew cap input_pins}}
check_setup
puts OT_CLOCK_CONTEXT_DONE
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--die-model', required=True)
    ap.add_argument('--clock-plan', required=True)
    ap.add_argument('--sheets', required=True)
    ap.add_argument('--sta-base', help='existing die STA Tcl; preserve its loading, geometry and parasitics prefix')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    paths = [Path(a.die_model), Path(a.clock_plan)]
    sheets = {p.stem: read(p) for p in Path(a.sheets).glob('*.json')}
    rec = contract(read(a.die_model), read(a.clock_plan), sheets)
    used = sorted({s['master'] for s in rec['sinks'].values()})
    paths += [Path(a.sheets) / (m + '.json') for m in used]
    if a.sta_base:
        paths += [Path(a.sta_base)]
    rec['input_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'clock_context.json').write_text(json.dumps(rec, indent=1) + '\n')
    for c in ('ss', 'ff'):
        body = constraints(rec, c)
        (out / f'clock_context_{c}.tcl').write_text(body)
        if a.sta_base:
            base = Path(a.sta_base).read_text()
            prefix, sep, _ = base.partition('set_cmd_units -time ns')
            if not sep:
                raise ValueError('STA base has no explicit ns-unit/clock boundary')
            (out / f'run_clock_{c}.tcl').write_text(prefix + body + report(c))
    print(json.dumps(dict(sinks=len(rec['sinks']), missing=len(rec['missing']),
                          regions=len(rec['region_flop_target_ps']), physical_clock=False)))


if __name__ == '__main__':
    main()
