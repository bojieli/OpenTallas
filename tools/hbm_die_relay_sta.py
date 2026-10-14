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
SKEW_ALL = False        # --skew-all: 60 + 150 ps on every endpoint (the pre-rule uniform budget)
R_COMMON_MAX_PS, SPREAD_MAX_PS = 300.0, 80.0


def view_clock_trees(case, master):
    """Explicit ETM insertion per clock pin and corner, in Liberty ps units."""
    out = {}
    for corner in ('ss', 'ff', 'tt'):
        path = case / f'{master}_{corner}.lib'
        if not path.exists():
            continue
        text = path.read_text()
        pins = {}
        # Balance braces so a timing group cannot consume the following pin.
        for match in re.finditer(r'\bpin\s*\(\s*"?([^"\s)]+)"?\s*\)\s*\{', text):
            depth, end = 1, match.end()
            while end < len(text) and depth:
                depth += (text[end] == '{') - (text[end] == '}')
                end += 1
            body = text[match.end():end - 1]
            tree = {}
            for arc in re.finditer(r'timing_type\s*:\s*(min|max)_clock_tree_path\s*;.*?cell_rise\s*\([^)]*\)\s*\{[^}]*?values\s*\(\s*"\s*([-\d.]+)', body, re.S):
                tree[arc.group(1)] = float(arc.group(2))
            if tree:
                pins[match.group(1)] = tree
        if pins:
            out[corner] = pins
    # tt_prefix binds SS Liberty if this view has no TT model.
    if not (case / f'{master}_tt.lib').exists() and 'ss' in out:
        out['tt'] = out['ss']
    return out


def view_spread(case, master, measured=None):
    """Boundary clock-arrival spread from the routed insertion measurement.

    Liberty min/max_clock_tree_path arcs normalize the ETM timing reference:
    extrema across clock pins can describe different clock trees and timing
    envelopes, rather than one sampled boundary population. They cannot by
    themselves establish the measured boundary skew bound.
    """
    record = (measured or {}).get(master, {})
    out = {}
    for c in ('ss', 'ff', 'tt'):
        corner = record.get(c, {})
        boundary = corner.get('kind') == 'boundary' or record.get('boundary_n', 0) > 0
        if boundary and 'routed' in record.get('parasitics', '') and 'min' in corner and 'max' in corner:
            out[c] = round(float(corner['max']) - float(corner['min']), 1)
    return out


def delivery_record(case, sinks, measured=None):
    """clock delivery per tile class (master): R per corner and its source, level (common <= 300 ps / early tap),
    entry = phi - R as the STA binds it, boundary spread and the spread defect, instances; also tags every sink with
    its level (constraints() reads it)"""
    by = defaultdict(list)
    for k, s in sinks.items():
        by[s['master']].append(s)
    tiles = {}
    for mst, ss in sorted(by.items()):
        ins = next((s.get('internal_ps') for s in ss if s.get('internal_ps')), None)
        src = next((s.get('insertion_source') for s in ss if s.get('insertion_source')), None)
        r_tt = (ins or {}).get('tt')
        level = 'unmeasured' if r_tt is None else ('common' if r_tt <= R_COMMON_MAX_PS else 'early_tap')
        if mst == 'hfd_rly':
            src = 'relay recipe (analytic)'
        spr = view_spread(case, mst, measured)
        trees = view_clock_trees(case, mst)
        for s in ss:
            s['level'] = level
            s['etm_tree_ps'] = trees
        ent = sorted({round(s['entry_ps']['tt'], 1) for s in ss if 'tt' in s.get('entry_ps', {})})
        tiles[mst] = dict(instances=len({s['instance'] for s in ss}), clock_pins=len(ss), R_ps=ins, R_source=src, level=level,
                          spread_source='routed boundary insertion metadata' if spr else None,
                          etm_clock_tree_ps=trees or None,
                          hop_skew_ps=90 if level == 'common' else 150, missing_R_evidence=r_tt is None,
                          spread_ps=spr or None,
                          spread_defect=bool(spr and max(spr.values()) > SPREAD_MAX_PS),
                          entry_tt_ps=[ent[0], ent[-1]] if ent else None,
                          regions=len({s.get('region') for s in ss}))
    return dict(sta_reference='source entry_ps remains physical phi - R; propagated source clocks retain the ETM I/O '
                              'tables unchanged in the validated OpenSTA 3.1.0 flow; tree arcs are metadata only',
                rule='clock pin delivered at phi - R (region flop target - the bound view\'s insertion); R <= 300 ps one '
                     'level (hop budget 60 + SKEW 90), R > 300 ps early tap (60 + SKEW 150 on hops with either endpoint on an early tap); '
                     'missing R uses conservative SKEW 150 in both directions until measured; boundary spread <= 80 ps', skew_all=SKEW_ALL, tiles=tiles,
                summary=dict(common=sum(1 for t_ in tiles.values() if t_['level'] == 'common'),
                             early_tap=sorted(k for k, t_ in tiles.items() if t_['level'] == 'early_tap'),
                             unmeasured=sorted(k for k, t_ in tiles.items() if t_['level'] == 'unmeasured'),
                             spread_defects=sorted(k for k, t_ in tiles.items() if t_['spread_defect']),
                             spread_unmeasured=sorted(k for k, t_ in tiles.items() if not t_['spread_ps'])))
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
    ctp = {}
    for c in ('ss', 'ff', 'tt'):
        f = case / f'{master}_{c}.lib'
        if f.exists():
            t_ = f.read_text()
            mn = re.search(r'timing_type : min_clock_tree_path;.*?values\("([-\d.]+)', t_, re.S)
            mx = re.search(r'timing_type : max_clock_tree_path;.*?values\("([-\d.]+)', t_, re.S)
            if mn and mx:
                ctp[c] = round((float(mn.group(1)) + float(mx.group(1))) / 2, 1)
    if all(c in ctp for c in ('ss', 'ff', 'tt')):
        # the routed view's own clock tree (write_timing_model min / max_clock_tree_path, mean): the insertion the die
        #   STA actually sees through the view's arcs (the calibrate CTS-only measurement is pre-route / pre-ECO)
        return ctp, 'view Liberty clock_tree_path (min+max)/2'
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
    pj = case / 'placeholder_masters.json'
    ph_all = set(json.loads(pj.read_text())['masters']) if pj.exists() else set()
    for k, s_ in sinks.items():
        if 'tt' not in s_.get('entry_ps', {}):        # placeholder / sheet-target sink: TT entry interpolated
            s_['entry_ps'] = dict(s_['entry_ps'], tt=round((s_['entry_ps']['ss'] + s_['entry_ps']['ff']) / 2, 3))
        ins, src = view_insertion(case, s_['master'], measured or {})
        if not ins and s_['master'] in ph_all:      # die --placeholder-all: the bundled recipe's own insertion (mid)
            ins, src = dict(RELAY_INS), 'placeholder recipe (analytic, hfd_ph_<corner>.lib)'
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
         'set ot_clock_missing {}', 'set ot_clock_bound 0', 'set ot_dom [dict create]', 'set ot_lat {}', 'set ot_level_clocks [dict create]', 'set ot_early 0', 'set ot_unmeasured 0', 'set ot_etm_corrected 0']
    for key, s in sorted(sinks.items()):
        pin = key if '[' in s['port'] else key + '[0]'
        level = s.get('level', 'unmeasured')
        conservative = level != 'common' and not SKEW_ALL
        suffix = '__early_tap' if level == 'early_tap' else '__unmeasured'
        clk = s['domain'] + (suffix if conservative else '')
        # die-gaps 2026-10-08: the r25 kit left 22 view clocks unbound (paths untimed): the hub quarters hfd_hc /
        # hfd_sfu / hfd_su enter their clock on ck0..ck7 (one die net) and the SerDes / host PHY macros on 'clk', while
        # the die model names every sink port 'ck'.  Fallbacks: <inst>/clk, then <inst>/ck? (all taps, same entry).
        inst = key.rsplit('/', 1)[0]
        L.append(f'set p [get_pins -quiet {{{pin}}}]; foreach alt {{{{{key}}} {{{inst}/clk}} {{{inst}/ck?}} {{{inst}/ck?[0]}}}} '
                 f'{{ if {{![llength $p]}} {{ set p [get_pins -quiet $alt] }} }}; '
                 f'if {{![llength $p]}} {{ lappend ot_clock_missing {{{pin}}} }} else {{ dict lappend ot_dom {clk} $p; '
                 f'dict set ot_level_clocks {clk} {s["domain"]}; '
                 f'foreach pp $p {{ lappend ot_lat [list {clk} {s["entry_ps"][corner] / 1000:.6f} '
                 f'{s["entry_ps"][corner] / 1000:.6f} $pp] }}'
                 + (' ; incr ot_early [llength $p]' if conservative and level == 'early_tap' else
                    ' ; incr ot_unmeasured [llength $p]' if conservative else '') + ' }')
    for d, per in PERIOD_PS.items():
        for clk in (d, d + '__early_tap', d + '__unmeasured'):
            L.append(f'if {{[dict exists $ot_dom {clk}]}} {{ create_clock -name {clk} -period {per / 1000:.6f} [dict get $ot_dom {clk}] }}')
    # Actual OpenSTA 3.1.0 probes with a published hbfd_rly8 ETM show
    # propagated source-clock timing is byte-identical with clock-tree groups
    # present or stripped. Preserve physical phi-R; adding those tree values
    # here would introduce a second insertion instead of compensating one.
    L += ['foreach e $ot_lat { lassign $e d early late p; '
          'set_clock_latency -source -early -clock $d $early $p; '
          'set_clock_latency -source -late -clock $d $late $p; incr ot_clock_bound }',
          'set_propagated_clock [all_clocks]',
          # die clock delivery rule (owner 2026-10-13 09:25, el1013-pinreg-audit.log): every clock pin is delivered at
          #   phi - R (entry = region flop target - the view's own insertion, compose()); a hop inside one clock level
          #   (R <= 300 ps) is budgeted 60 ps + SKEW 90, a hop with either endpoint on an early tap (R > 300 ps) 60 +
          #   SKEW 150.  --skew-all restores the older uniform 60 + 150 on every endpoint.
          f'set_clock_uncertainty -setup {0.210 if SKEW_ALL else 0.150:.3f} [all_clocks]',
          'set_clock_uncertainty -hold 0.025 [all_clocks]',
          # Pair constraints cover early launch -> common capture as well as the reverse.
          # Missing insertion is not evidence of a common level: use 210 ps in both directions.
          # Preserve 210 ps on early -> early until a shared early trunk is qualified.
          'dict for {a da} $ot_level_clocks { dict for {b db} $ot_level_clocks { '
          'if {$da eq $db && ([string match *__early_tap $a] || [string match *__early_tap $b] || [string match *__unmeasured $a] || [string match *__unmeasured $b])} { '
          'set_clock_uncertainty -setup -from [get_clocks $a] -to [get_clocks $b] 0.210 } } }',
          # mesochronous domains: no synchronous timing between different die clocks (crossings are FIFO / forwarded)
          'set cl [all_clocks]',
          'dict for {a da} $ot_level_clocks { dict for {b db} $ot_level_clocks { '
          'if {$da ne $db} { set_false_path -from [get_clocks $a] -to [get_clocks $b] } } }',
          f'puts "OT_CLOCK_CONTEXT corner={corner} bound=$ot_clock_bound missing=[llength $ot_clock_missing] early_tap_pins=$ot_early unmeasured_pins=$ot_unmeasured etm_corrected_pins=$ot_etm_corrected"',
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


PAD_SCALE = dict(ff=1.0, tt=1.4, ss=1.9)    # a hold-pad delay cell's delay at TT / SS relative to FF (ASAP7 BUF chains)


# OpenROAD has no set_annotated_delay (OpenSTA's Tcl wrapper is not loaded; run_grt_sta.tcl died on it 2026-10-08), but
# it carries the SWIG primitive under it: sta::set_arc_delay edge arc scene min_max delay.  ot_pad adds the pad to the
# CURRENT wire-arc delay (driver -> the listed load pin, i.e. set_annotated_delay -net -incremental) on that corner's
# scene only, so it rides on the GRT parasitics of the same session; probed on ASAP7 BUFx2 (+50 ps at FF, TT unchanged).
OT_PAD_PROC = r"""proc ot_pad {l sc ps} {
  set n 0
  set scene [sta::find_scene $sc]
  foreach d [get_pins -quiet -of_objects [get_nets -of_objects $l] -filter "direction==output"] {
    foreach v [$d vertices] {
      set it [$v out_edge_iterator]
      while {[$it has_next]} {
        set e [$it next]
        if {[$e role] ne "wire" || [$e to_pin] ne $l} continue
        foreach arc [$e timing_arcs] { foreach mm {min max} {
          sta::set_arc_delay $e $arc $scene $mm [expr {[$e arc_delay $arc $scene $mm] + $ps * 1e-12}] } }
        incr n
      }
      $it finish
    }
  }
  return $n
}
"""


def hold_pads(path, corner):
    """die-level hold padding (rule H1, die links): a delay on the die net into each listed load pin (the relay input,
    or the receiving block pin for a relay -> block hop), sized at FF; the same cells cost PAD_SCALE x at TT / SS
    setup, so every corner is timed with them.  Modelled as an incremental wire-arc annotation (ot_pad above): an
    ideal delay (no slew / load change, no pad area), disclosed as such."""
    if not path:
        return ''
    pads = json.loads(Path(path).read_text())
    L = [f'# die hold pads (tools/hbm_die_relay_sta.py --hold-pads), corner {corner}', OT_PAD_PROC,
         'sta::worst_slack -max', 'set ot_npad 0; set ot_nmiss 0']
    for pin, ps in sorted(pads.items()):
        L.append(f'set l [get_pins -quiet {{{pin}}}]; if {{[llength $l]}} {{ set k [ot_pad $l {corner} '
                 f'{ps * PAD_SCALE[corner]:.3f}]; if {{$k}} {{ incr ot_npad $k }} else {{ incr ot_nmiss }} }} else {{ incr ot_nmiss }}')
    L.append(f'puts "OT_HOLD_PADS corner={corner} pins={len(pads)} arcs_padded=$ot_npad missing=$ot_nmiss"')
    return '\n'.join(L) + '\n'


def report(corner, tag=''):
    k = 'min' if corner == 'ff' else 'max'
    sfx = f'_{tag}' if tag else ''
    tg = f' pads={tag}' if tag else ''
    return f'''
puts "OT_WNS corner={corner}{tg} ns=[sta::worst_slack -corner {corner} -{k}] tns_ns=[sta::total_negative_slack -corner {corner} -{k}]"
set f [open /out/paths_{corner}{sfx}.txt w]
set n 0
foreach pe [find_timing_paths -path_delay {k} -corner {corner} -group_path_count 200000 -endpoint_path_count 1 -slack_max 0.015] {{
  puts $f "[get_full_name [get_property $pe startpoint]] [get_full_name [get_property $pe endpoint]] [get_property $pe slack]"
  incr n
}}
close $f
puts "OT_FAIL_ENDPOINTS corner={corner}{tg} n=$n"
report_checks -path_delay {k} -corner {corner} -group_path_count 10 -format full_clock_expanded -digits 4 -fields {{slew cap input_pins}}
puts OT_DONE
'''


# ASAP7 platform layer RC (flow/platforms/asap7/setRC.tcl, the values estimate_parasitics uses in every die case):
# kOhm/um and pF/um per routing layer.  The cap sensitivity re-issues them with capacitance x k (resistance and vias
# unchanged) and re-runs estimate_parasitics -global_routing on the SAME global route.
ASAP7_LAYER_RC = dict(M1=(7.04175e-02, 1e-10), M2=(2.97127e-02, 1.74942e-01), M3=(3.12870e-02, 1.55554e-01),
                      M4=(1.80365e-02, 1.78475e-01), M5=(1.89935e-02, 1.64264e-01), M6=(1.18796e-02, 1.87426e-01),
                      M7=(1.25096e-02, 1.62979e-01), M8=(8.44765e-03, 1.03962e-01), M9=(8.89556e-03, 9.28446e-02))


def sensitivity(sinks, ocv, cap_scales):
    """hbmdie-v10-sta (2026-10-12) post-nominal bounds in the same GRT session, RAW (no die hold pads):
    (1) OCV bound: set_timing_derate -early (1-ocv) -late (1+ocv) on cells and nets (the repo convention of
        tools/s81/die_sens.sh, 0.95 / 1.05), on nominal GRT parasitics;
    (2) GRT-vs-DRT wire-cap error bar: every routing layer's capacitance per um x k (k = 1.40 median, 2.44 p95 of
        the DRT/GRT net-C ratio measured on 3,189 internal nets, results/physical/die_region_drt_1012/README.md),
        estimate_parasitics -global_routing re-run on the same route; pin / view-model caps unchanged, so this is the
        wire part only (the measured gap is per-unit-length coupling C, wire length agrees within 3 %);
    (3) the p95 cap case again with the OCV derate (worst bound).
    Each case re-applies the corner's clock constraints and prints, per case, TT setup and FF hold:
      OT_SENS case=<name> corner=tt|ff wns_ns=.. tns_ns=.. fail=<endpoints with slack < 0>"""
    if not ocv and not cap_scales:
        return ''

    def rc(k):
        return '\n'.join(f'set_layer_rc -layer {l} -resistance {r:.6e} -capacitance {c * k:.6e}'
                          for l, (r, c) in ASAP7_LAYER_RC.items()) + '\nestimate_parasitics -global_routing\n'

    def rep(name):
        out = []
        for c, k in (('tt', 'max'), ('ff', 'min')):
            out.append(constraints(sinks, c) + f'''set n 0
foreach pe [find_timing_paths -path_delay {k} -corner {c} -group_path_count 200000 -endpoint_path_count 1 -slack_max 0.0] {{ incr n }}
set w [sta::worst_slack -corner {c} -{k}]; set t [sta::total_negative_slack -corner {c} -{k}]
puts "OT_SENS case={name} corner={c} wns_ns=$w tns_ns=$t fail=$n"
''')
        return '\n'.join(out)
    der = (f'set_timing_derate -early {1 - ocv:.3f}\nset_timing_derate -late {1 + ocv:.3f}\n' if ocv else '')
    L = ['\n# ---- hbmdie-v10-sta sensitivity (raw, no pads): see tools/hbm_die_relay_sta.py sensitivity() ----',
         'puts OT_SENS_BEGIN']
    if ocv:
        L += [der, rep(f'ocv{ocv:g}_c1.00'), 'unset_timing_derate']
    for k in cap_scales:
        L += [rc(k), rep(f'c{k:.2f}')]
    if ocv and cap_scales:
        L += [der, rep(f'ocv{ocv:g}_c{max(cap_scales):.2f}'), 'unset_timing_derate']
    L += [rc(1.0), 'puts OT_SENS_DONE']
    return '\n'.join(L) + '\n'


# ASAP7 setRC.tcl: the placement-parasitic die cases estimate every die net on M7's per-um RC (set_wire_rc -layer M7)
M7_RC = ASAP7_LAYER_RC['M7']


def place_sens(sinks, cases):
    """hbmdie-v10-sta (2026-10-12): bounds on the PLACEMENT-parasitic die STA (the case's estimate_parasitics -placement,
    every net on M7 per-um RC), one session after the nominal TT setup / FF hold.  cases = [(name, r_k, c_k, ocv)]:
    the M7 per-um resistance x r_k and capacitance x c_k (set_layer_rc, then set_wire_rc -layer M7, re-estimate) and
    set_timing_derate -early 1-ocv -late 1+ocv on cells and nets.  Wire-cap points: C x1.40 / x2.44 (GRT-vs-DRT net-C
    median / p95, results/physical/die_region_drt_1012); detour point: R and C x d, d = the GRT of record's routed
    wirelength / placement HPWL (tools/hbm_die_relay_sta.py detour).  Prints per case and corner
      OT_SENS case=<name> corner=tt|ff wns_ns=.. tns_ns=.. fail=<endpoints with slack < 0>"""
    r0, c0 = M7_RC
    L = ['\n# ---- placement-parasitic sensitivity (tools/hbm_die_relay_sta.py place_sens) ----', 'puts OT_SENS_BEGIN']
    for name, rk, ck, ocv in cases:
        L.append(f'set_layer_rc -layer M7 -resistance {r0 * rk:.6e} -capacitance {c0 * ck:.6e}')
        L += ['set_wire_rc -signal -layer M7', 'set_wire_rc -clock -layer M7', 'estimate_parasitics -placement']
        L.append(f'set_timing_derate -early {1 - ocv:.3f}\nset_timing_derate -late {1 + ocv:.3f}' if ocv else 'unset_timing_derate')
        for c, k in (('tt', 'max'), ('ff', 'min')):
            L.append(constraints(sinks, c) + f'''set n 0
foreach pe [find_timing_paths -path_delay {k} -corner {c} -group_path_count 200000 -endpoint_path_count 1 -slack_max 0.0] {{ incr n }}
puts "OT_SENS case={name} corner={c} r_k={rk:.3f} c_k={ck:.3f} ocv={ocv:g} wns_ns=[sta::worst_slack -corner {c} -{k}] tns_ns=[sta::total_negative_slack -corner {c} -{k}] fail=$n"
''')
    L += ['unset_timing_derate', 'puts OT_SENS_DONE']
    return '\n'.join(L) + '\n'


def detour(grt_csv, hpwl_csv):
    """routed / HPWL wirelength of the GRT of record: report_wire_length -global_route file ('grt: net total_wl pins') vs the
    same case's placement HPWL per net (hpwl.csv: net,hpwl_um); totals over nets present in both, and the median"""
    def rd(path):
        out = {}
        for ln in Path(path).read_text().splitlines():      # 'grt: <net> <total_wl um> <#pins>' or '<net> <hpwl um>'
            t = ln.replace(',', ' ').split()
            if t and t[0] == 'grt:':
                t = t[1:]
            try:
                out[t[0]] = float(t[1])
            except (IndexError, ValueError):
                continue
        return out
    g, h = rd(grt_csv), rd(hpwl_csv)
    both = [(g[n], h[n]) for n in g if n in h and h[n] > 0]
    r = sorted(a / b for a, b in both)
    return dict(nets=len(both), grt_um=round(sum(a for a, _ in both), 1), hpwl_um=round(sum(b for _, b in both), 1),
                detour_total=round(sum(a for a, _ in both) / max(1e-9, sum(b for _, b in both)), 4),
                detour_median=round(r[len(r) // 2], 4) if r else None,
                detour_p90=round(r[int(len(r) * 0.9)], 4) if r else None)


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
    ap.add_argument('--case', required=False)
    ap.add_argument('--clock-context', help='clock_context.json from tools/hbm_die_clock_context.py')
    ap.add_argument('--budgets', action='store_true')
    ap.add_argument('--hold-pads', help='JSON {load pin: FF pad ps} (die-level hold padding)')
    ap.add_argument('--measured', help='measured_insertion.json (closure-loop calibrate) for view insertion')
    ap.add_argument('--ocv', type=float, default=0.05,
                    help='OCV bound on the GRT session: set_timing_derate -early 1-x -late 1+x (cells + nets), 0 = off')
    ap.add_argument('--place-sens', action='store_true',
                    help='write run_sta_place.tcl: placement-parasitic TT setup / FF hold + OCV / wire-cap / detour bounds')
    ap.add_argument('--detour', type=float, default=0.0, help='GRT routed/HPWL factor for the place-sens detour point')
    ap.add_argument('--detour-of', nargs=2, metavar=('GRT_CSV', 'HPWL_CSV'), help='print the detour factor and exit')
    ap.add_argument('--cap-scales', default='1.40,2.44',
                    help='GRT-vs-DRT wire-capacitance sensitivity (results/physical/die_region_drt_1012: DRT/GRT net C '
                         'median +40 %%, p95 +144 %%); empty = off')
    ap.add_argument('--skew-all', action='store_true', help='uniform 60 + 150 ps setup uncertainty (pre-rule budget)')
    a = ap.parse_args()
    global SKEW_ALL
    SKEW_ALL = a.skew_all
    if a.detour_of:
        print(json.dumps(detour(*a.detour_of)))
        return
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
    dr = delivery_record(case, sinks, measured)
    (case / 'clock_delivery.json').write_text(json.dumps(dr, indent=1) + '\n')
    print(json.dumps(dict(clock_delivery=dr['summary'])))
    (case / 'relay_clock_context.json').write_text(json.dumps(dict(view_sinks=sinks0, relay_sinks=added, relays_without_domain=nodom,
                                                                   relay_internal_ps=RELAY_INS), indent=0))
    base = (case / 'run.tcl').read_text()
    prefix = base.partition('set_cmd_units -time ns')[0]
    assert 'estimate_parasitics' in prefix, 'case run.tcl has no parasitics step before the clock boundary'
    for c in ('ss', 'ff'):
        (case / f'run_clock_{c}.tcl').write_text(prefix + constraints(sinks, c) + hold_pads(a.hold_pads, c) + report(c))
    ttp, tt_fallback = tt_prefix(prefix, case)
    (case / 'run_clock_tt.tcl').write_text(ttp + constraints(sinks, 'tt') + hold_pads(a.hold_pads, 'tt') + report('tt'))
    (case / 'tt_fallback.json').write_text(json.dumps(tt_fallback) + '\n')
    if a.place_sens:
        caps = [float(x) for x in a.cap_scales.split(',') if x.strip()]
        cases = [(f'ocv{a.ocv:g}', 1.0, 1.0, a.ocv)] if a.ocv else []
        cases += [(f'c{k:.2f}', 1.0, k, 0.0) for k in caps]
        if a.detour:
            cases += [(f'detour{a.detour:.3f}', a.detour, a.detour, 0.0)]
        if a.ocv and caps:
            cases += [(f'ocv{a.ocv:g}_c{max(caps):.2f}', 1.0, max(caps), a.ocv)]
        nom = constraints(sinks, 'tt') + report('tt').replace('puts OT_DONE', '') + constraints(sinks, 'ff') + \
            report('ff').replace('puts OT_DONE', '')
        (case / 'run_sta_place.tcl').write_text(ttp + nom + place_sens(sinks, cases) + 'puts OT_DONE\n')
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
    # with pads: each corner is reported raw (paths_<c>_nopad.txt) and then with the pads (paths_<c>.txt), one GRT
    def corner_block(c, last):
        r = report(c, 'nopad').replace('puts OT_DONE', '') + hold_pads(a.hold_pads, c) if a.hold_pads else ''
        t = report(c, 'pad' if a.hold_pads else '')
        t = t.replace('/out/paths_' + c + '_pad.txt', '/out/paths_' + c + '.txt')
        return constraints(sinks, c) + r + (t if last else t.replace('puts OT_DONE', ''))
    sens = sensitivity(sinks, a.ocv, [float(x) for x in a.cap_scales.split(',') if x.strip()])
    (case / 'run_grt_sta.tcl').write_text(gp + corner_block('tt', False) + corner_block('ff', False) + corner_block('ss', True)
                                          + sens)
    # STA-only on an existing GRT checkpoint: guides cannot feed estimate_parasitics (GRT-0008), so the session
    # re-runs the same global route (deterministic, same layers / adjustments) -- written only to a scratch odb
    (case / 'run_grt_sta_only.tcl').write_text((case / 'run_grt_sta.tcl').read_text().replace(
        'write_db /out/ckpt_grt.odb', '').replace('write_guides /out/route.guide', '').replace(
        'report_wire_length -net * -global_route -file /out/wirelength_grt.csv', ''))
    print(json.dumps(dict(planned_sinks=len(ctx['sinks']), relay_sinks=len(added), relays_without_domain=len(nodom))))


if __name__ == '__main__':
    main()
