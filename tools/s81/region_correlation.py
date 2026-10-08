#!/usr/bin/env python3
"""S81 die representative-region DRT: STA decks and the GRT-vs-DRT correlation record (CLAUDE S81-DIE, 2026-10-07).

  sta-tcl --kit K --region D     writes D/sta_{ss,ff}_{grt,drt}.tcl: the die STA kit's constraints (libs, uncertainty,
                                 clock groups, false paths, planned latencies) on the cropped window netlist, clocks on
                                 the window's clock ports (or on their source pin when it lies inside), one deck per
                                 parasitic source (GRT estimate / RCX of the detail route)
  record --region D --name N --box x0 y0 x1 y1
                                 D/region.json: crop, DRT convergence, DRC, antenna, wire-length correlation, slack
                                 correlation (per common endpoint, SS setup and FF hold)
Used by physical/s81_die_views/dietop/dietop_region.sh.
"""
import argparse
import csv
import json
import re
import statistics
from pathlib import Path

CLOCK_NETS = re.compile(r'^(clk_(stream|serial|hbm)|ck_col_\d+)$')


def sta_tcl(kit, region):
    v = (region / 'region.v').read_text() if (region / 'region.v').exists() else ''
    ports = set(re.findall(r'^\s*(?:input|output|inout)\s+(?:\[[^\]]+\]\s*)?(p_[\w\[\]$]+)\s*[;,]', v, re.M))
    for corner in ('ss', 'ff'):
        src = (kit / f'sta_{corner}.tcl').read_text().splitlines()
        keep, clocks = [], []
        for ln in src:
            if ln.startswith(('read_verilog', 'link_design', 'if {[file exists /kit/die.spef]}', 'report_', 'source /kit/latency')):
                continue
            m = re.match(r'create_clock -name (\S+) -period (\S+) \[get_pins (?:-quiet )?\{(\S+)(?: \S+)?\}\]', ln)
            if m:
                clocks.append(m.groups())
                continue
            if ln.startswith('set_clock_latency -source'):
                keep.append('catch {' + ln + '}')
                continue
            keep.append(ln)
        head = [l for l in keep if l.startswith(('set libs', 'foreach l $libs'))]
        rest = [l for l in keep if l not in head]
        for par in ('grt', 'drt'):
            T = list(head) + ['read_verilog /r/region.v', 'link_design dsfd_die', f'read_spef /r/region_{par}.spef']
            for name, per, pin in clocks:
                port = f'p_n_{name}\\[0\\]'
                T.append(f'if {{[llength [get_pins -quiet {{{pin} {pin}[0]}}]]}} {{ create_clock -name {name} -period {per} '
                         f'[get_pins -quiet {{{pin} {pin}[0]}}] }} elseif {{[llength [get_ports -quiet {{{port}}}]]}} {{ create_clock '
                         f'-name {name} -period {per} [get_ports {{{port}}}] }} else {{ create_clock -name {name} -period {per} }}')
            lat = kit / f'latency_{corner}.tcl'
            if lat.exists():
                T.append(f'foreach ln [split [read [open /kit/latency_{corner}.tcl]] "\\n"] {{ catch {{ eval $ln }} }}')
            T += [l.replace('[get_clocks -quiet {clk_stream ck_col_*}]', '[get_clocks -quiet {clk_stream ck_col_*}]') for l in rest]
            dly = 'max' if corner == 'ss' else 'min'
            T += [f'report_checks -path_delay {dly} -group_path_count 5000 -endpoint_path_count 1 -format end '
                  f'-digits 1 > /r/end_{corner}_{par}.rpt',
                  f'puts "OT_WNS {corner} {par} [sta::format_time [sta::worst_slack_cmd {dly}] 1]"',
                  f'report_checks -path_delay {dly} -group_path_count 20 -digits 1 > /r/paths_{corner}_{par}.rpt']
            (region / f'sta_{corner}_{par}.tcl').write_text('\n'.join(T) + '\n')


def _ends(p):
    out = {}
    if not p.exists():
        return out
    for ln in p.read_text().splitlines():
        f = ln.split()
        if len(f) >= 4:
            try:
                out[f[0]] = float(f[-1])
            except ValueError:
                pass
    return out


def _wl(p):
    """report_wire_length -file rows: 'grt: <net> <wl_um> <pins>' (or csv net,wl)"""
    out = {}
    if not p.exists():
        return out
    for ln in p.read_text().splitlines():
        f = ln.replace(',', ' ').split()
        if len(f) >= 3 and f[0] in ('grt:', 'drt:'):
            try:
                out[f[1]] = float(f[2])
            except ValueError:
                pass
        elif len(f) >= 2 and f[0] not in ('tool', 'net', 'Net'):
            try:
                out[f[0]] = float(f[1])
            except ValueError:
                pass
    return out


def record(region, name, box):
    log = (region / 'region.log').read_text(errors='ignore') if (region / 'region.log').exists() else ''
    mc = re.search(r'OT_CROP (.*)', log)
    crop = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', mc.group(1))} if mc else {}
    viol = [int(v) for v in re.findall(r'Number of violations = (\d+)', log)]
    ant = re.findall(r'OT_ANTENNA (\S+)', log)
    fails = re.findall(r'OT_STEP_FAIL (\S+) (.*)', log)
    g, d = _wl(region / 'wirelength_grt.csv'), _wl(region / 'wirelength_drt.csv')
    common = [n for n in g if n in d and g[n] > 0]
    ratios = [d[n] / g[n] for n in common]
    wl = dict(nets=len(common), grt_total_um=round(sum(g[n] for n in common), 1),
              drt_total_um=round(sum(d[n] for n in common), 1))
    if ratios:
        wl.update(total_ratio=round(wl['drt_total_um'] / max(wl['grt_total_um'], 1e-9), 4),
                  median_ratio=round(statistics.median(ratios), 4),
                  p95_ratio=round(sorted(ratios)[int(0.95 * (len(ratios) - 1))], 4),
                  max_ratio=round(max(ratios), 3))
    timing = {}
    for c in ('ss', 'ff'):
        eg, ed = _ends(region / f'end_{c}_grt.rpt'), _ends(region / f'end_{c}_drt.rpt')
        k = [e for e in eg if e in ed]
        dl = [ed[e] - eg[e] for e in k]
        wns = {p: (float(m.group(1)) if (m := re.search(r'OT_WNS %s %s (\S+)' % (c, p),
                   (region / f'sta_{c}_{p}.log').read_text(errors='ignore') if (region / f'sta_{c}_{p}.log').exists() else ''))
                   else None) for p in ('grt', 'drt')}
        timing[c] = dict(check='setup' if c == 'ss' else 'hold', wns_grt_ps=wns['grt'], wns_drt_ps=wns['drt'],
                         endpoints=len(k))
        if dl:
            timing[c].update(delta_drt_minus_grt_ps=dict(mean=round(statistics.mean(dl), 2),
                                                          min=round(min(dl), 2), max=round(max(dl), 2),
                                                          p5=round(sorted(dl)[int(0.05 * (len(dl) - 1))], 2)))
    rec = dict(schema='opentallas.s81.region-drt.v1', name=name, box_um=box, crop=crop,
               drt=dict(violations_per_iter=viol, final_drc=viol[-1] if viol else None, iterations=len(viol)),
               antenna=ant[-1] if ant else None, step_failures=fails, wirelength=wl, timing=timing)
    (region / 'region.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['sta-tcl', 'record'])
    ap.add_argument('--kit', type=Path)
    ap.add_argument('--region', type=Path, required=True)
    ap.add_argument('--name', default='region')
    ap.add_argument('--box', type=float, nargs=4)
    a = ap.parse_args()
    if a.mode == 'sta-tcl':
        sta_tcl(a.kit, a.region)
    else:
        record(a.region, a.name, a.box)


if __name__ == '__main__':
    main()
