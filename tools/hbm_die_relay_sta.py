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

RELAY_INS = dict(ss=80.0, ff=47.5, tt=63.5)
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


LIB_TO_INS = dict(ss=110.0, ff=40.0, tt=75.0)   # lib min ck->out minus measured insertion, mean over the 6 blocks with both


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
        out = {c: float(measured[master][c]['mean']) for c in ('ss', 'ff')}
        f = case / f'{master}_tt.lib'
        v = lib_ck_out_min(f) if f.exists() else None
        out['tt'] = round(v - LIB_TO_INS['tt'], 1) if v is not None else round((out['ss'] + out['ff']) / 2, 1)
        return out, 'measured (closure-loop calibrate); tt from the view TT Liberty'
    out = {}
    for c in ('ss', 'ff'):
        f = case / f'{master}_{c}.lib'
        v = lib_ck_out_min(f) if f.exists() else None
        if v is None:
            return None, None
        out[c] = round(v - LIB_TO_INS[c], 1)
    f = case / f'{master}_tt.lib'
    v = lib_ck_out_min(f) if f.exists() else None
    out['tt'] = round(v - LIB_TO_INS['tt'], 1) if v is not None else round((out['ss'] + out['ff']) / 2, 1)
    return out, 'view Liberty min ck->out - offset'


def compose(case, ctx, measured=None):
    xy = places(case)
    rel = relay_clocks(case)
    sinks = {k: dict(v) for k, v in ctx['sinks'].items()}
    # a planned sink whose block the generator split (r25 hfd_cmdproc -> hb_cmdproc_n / _s): each half takes the
    #   parent's region (both halves sit in the parent's outline)
    for k in list(sinks):
        s_ = sinks[k]
        if s_['instance'] not in xy:
            for h in ('_n', '_s'):
                i_ = s_['instance'] + h
                if i_ in xy:
                    sinks[f'{i_}/{s_["port"]}'] = dict(s_, instance=i_, master=s_['master'] + h, split_of=s_['instance'])
            if any(s_['instance'] + h in xy for h in ('_n', '_s')):
                del sinks[k]
    # the plan's sheets carry TARGET insertions ('no calibration yet'); a hardened view's actual insertion is smaller
    #   and its Liberty arcs embed it: entry = region target - ACTUAL insertion keeps every flop at the region target
    # TT region flop targets: the plan has SS / FF only; TT = their mean (interpolation, labelled) -- only the
    #   relative arrival of sinks in one domain matters for timing, and every sink of a region keeps one target
    tgt0 = {r_: list(t_[:2]) + [(t_[0] + t_[1]) / 2] for r_, t_ in ctx['region_flop_target_ps'].items()}
    for k, s_ in sinks.items():
        if 'tt' not in s_.get('entry_ps', {}):        # placeholder / sheet-target sink: TT entry interpolated
            s_['entry_ps'] = dict(s_['entry_ps'], tt=round((s_['entry_ps']['ss'] + s_['entry_ps']['ff']) / 2, 3))
        ins, src = view_insertion(case, s_['master'], measured or {})
        if ins:
            t_ = tgt0[s_['region']]
            s_['internal_ps'] = ins
            s_['insertion_source'] = src
            s_['entry_ps'] = {c: round(t_[n] - ins[c], 3) for n, c in enumerate(('ss', 'ff', 'tt'))}
    tgt = tgt0
    by_dom = defaultdict(list)
    for k, s in sinks.items():
        if s['instance'] in xy:
            by_dom[s['domain']].append((xy[s['instance']], s['region']))
    # chain-aware: the registers of a chain nearer its source take the source block's region, the rest the sink's
    #   (the region crossing then sits on one relay-to-relay hop, as the plan's inter-region budget assumes)
    inst_reg = {s['instance']: (s['domain'], s['region']) for s in sinks.values()}
    want, ramp = {}, {}
    rj = case / 'relays.json'
    for ch in (json.loads(rj.read_text()).get('chains', []) if rj.exists() else []):
        regs = ch.get('regs', [])
        a_, b_ = inst_reg.get(ch.get('src')), inst_reg.get(ch.get('dst'))
        for k, r_ in enumerate(regs):
            end = ch.get('src') if k < (len(regs) + 1) // 2 else ch.get('dst')
            if a_ and b_ and a_[0] != b_[0]:      # a domain-crossing chain: every relay in the endpoint domain it is clocked in
                end = ch.get('src') if rel.get(r_) == a_[0] else ch.get('dst')
            if end in inst_reg:
                want[r_] = inst_reg[end]
            # a chain between two regions of one domain whose flop targets differ (e.g. HUB-Q*.0.0 at 4,003 vs 3,579 ps
            #   SS): the relay flop times ramp linearly from the source target to the sink target, so no single hop
            #   carries the whole inter-region difference (die CTS pads each relay sink to its ramp value)
            if a_ and b_ and a_[0] == b_[0]:
                f = (k + 1) / (len(regs) + 1)
                ta, tb = tgt0[a_[1]], tgt0[b_[1]]
                ramp[r_] = [ta[n] + (tb[n] - ta[n]) * f for n in (0, 1, 2)]
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
        t = ramp.get(inst) if inst in ramp and want.get(inst, (None,))[0] == d else tgt[reg]
        added[f'{inst}/ck'] = dict(instance=inst, port='ck', master='hfd_rly', region=reg, domain=d,
                                   ramped=inst in ramp and t is ramp.get(inst),
                                   internal_ps=dict(RELAY_INS),
                                   entry_ps={c: round(t[n] - RELAY_INS[c], 3) for n, c in enumerate(('ss', 'ff', 'tt'))})
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
    # propagated mode: the clocks start AT the sink pins (no die clock net is traversed) and the view Liberty
    #   clock -> output / setup / hold arcs carry the view's own insertion (write_timing_model, propagated); in ideal
    #   mode OpenSTA strips the macro clock-tree arcs instead (checked on w289 -> relay: 30 ps ideal vs 221 ps arc)
    L += ['foreach e $ot_lat { lassign $e d l p; set_clock_latency -source -clock $d $l $p; incr ot_clock_bound }',
          'set_propagated_clock [all_clocks]',
          'set_clock_uncertainty -setup 0.210 [all_clocks]', 'set_clock_uncertainty -hold 0.025 [all_clocks]',
          # mesochronous domains: no synchronous timing between different die clocks (crossings are FIFO / forwarded)
          'set cl [all_clocks]',
          'foreach a $cl { foreach b $cl { if {[get_name $a] ne [get_name $b]} { set_false_path -from $a -to $b } } }',
          f'puts "OT_CLOCK_CONTEXT corner={corner} bound=$ot_clock_bound missing=[llength $ot_clock_missing]"',
          'puts "OT_CLOCK_MISSING [lrange $ot_clock_missing 0 40]"']
    return '\n'.join(L) + '\n'


def tt_prefix(prefix, case):
    """OPTION B: add a TT analysis corner (setup sign-off) to the case prefix: every view's TT model, or -- for a view
    without one (interim, no final route) -- its SS model in the TT slot (pessimistic, listed)"""
    out, fallback = [], []
    for ln in prefix.splitlines():
        if ln.strip() == 'define_corners ss ff':
            out.append('define_corners tt ss ff')
            continue
        out.append(ln)
        m = re.match(r'read_liberty -corner ss /work/(\S+)_ss\.lib$', ln.strip())
        if m:
            n = m.group(1)
            if (case / f'{n}_tt.lib').exists():
                out.append(f'read_liberty -corner tt /work/{n}_tt.lib')
            else:
                out.append(f'read_liberty -corner tt /work/{n}_ss.lib')
                fallback.append(n)
    return '\n'.join(out) + '\n', fallback


def report(corner):
    k = 'min' if corner == 'ff' else 'max'
    return f'''
puts "OT_WNS corner={corner} ns=[sta::worst_slack -{k}] tns_ns=[sta::total_negative_slack -{k}]"
set f [open /out/paths_{corner}.txt w]
set n 0
foreach pe [find_timing_paths -path_delay {k} -corner {corner} -group_path_count 200000 -endpoint_path_count 1 -slack_max 0.015] {{
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
    for c in ('tt', 'ss', 'ff'):
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
    ttp, tt_fallback = tt_prefix(prefix, case)
    (case / 'run_clock_tt.tcl').write_text(ttp + constraints(sinks, 'tt') + report('tt'))
    (case / 'tt_fallback.json').write_text(json.dumps(tt_fallback) + '\n')
    print(json.dumps(dict(tt_models_missing=tt_fallback)))
    # OWNER STEER 2026-10-07 (3): die timing on GLOBAL-ROUTE parasitics: full-die GRT (M4-M9, coarse M2/M3 tracks so
    #   the gcell is GRT_TILE_UM, the dietop_round method) -> estimate_parasitics -global_routing -> SS then FF
    tile = 9.6
    p_ = tile / 15.0
    (case / 'make_tracks_coarse.tcl').write_text('\n'.join([
        'make_tracks Pad -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080',
        'make_tracks M9 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080',
        'make_tracks M8 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080',
        'make_tracks M7 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.016 -y_pitch 0.064',
        'make_tracks M6 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.016 -y_pitch 0.064',
        'make_tracks M5 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048',
        'make_tracks M4 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.012 -y_pitch 0.048',
        f'make_tracks M3 -x_offset 0.009 -x_pitch {p_:.3f} -y_offset 0.009 -y_pitch {p_:.3f}',
        f'make_tracks M2 -x_offset 0.009 -x_pitch {p_:.3f} -y_offset 0.045 -y_pitch {p_:.3f}',
        'make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036']) + '\n')
    mt = '/OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl'
    gp = ttp.replace(f'source {mt}', 'source /work/make_tracks_coarse.tcl').replace(
        f'set ::env(MAKE_TRACKS) {mt}', 'set ::env(MAKE_TRACKS) /work/make_tracks_coarse.tcl')
    gp = gp.replace('estimate_parasitics -placement', '''set_routing_layers -signal M4-M9 -clock M4-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.146
set t0 [clock seconds]
global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /out/grt_congestion.rpt
puts "OT_GRT_S [expr {[clock seconds]-$t0}]"
write_guides /out/route.guide
write_db /out/ckpt_grt.odb
report_wire_length -net * -global_route -file /out/wirelength_grt.csv
estimate_parasitics -global_routing''')
    assert 'global_route' in gp
    # OPTION B: setup at TT, hold at FF, SS setup as a sensitivity
    (case / 'run_grt_sta.tcl').write_text(gp + constraints(sinks, 'tt') + report('tt').replace('puts OT_DONE', '')
                                          + constraints(sinks, 'ff') + report('ff').replace('puts OT_DONE', '')
                                          + constraints(sinks, 'ss') + report('ss'))
    print(json.dumps(dict(planned_sinks=len(ctx['sinks']), relay_sinks=len(added), relays_without_domain=len(nodom))))


if __name__ == '__main__':
    main()
