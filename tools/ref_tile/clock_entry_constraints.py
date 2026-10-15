"""Fail-closed clock delivery for hard entries and opt-in local glue CTS roots.

An ETM already contains clock insertion in its launch/check arcs. Source latency
compensates that reference once; it must never be added back to the ETM arcs.
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
import child_lint
import direct_macro_clock_entries

MODES = ("entries", "hybrid_entries", "multiple_cts_roots")

CORNERS = ('tt', 'ff', 'ss')
ENTRY_DOMAIN_API_VERSION = 1


def signoff_period(spec):
    """Opt-in leaf signoff period; all existing profiles retain their ABI."""
    route = spec.get('route', {})
    value = route.get('signoff_period_ps', 833.333)
    if 'signoff_period_ps' in route and spec.get('clock') != 'multiple_cts_roots':
        raise ValueError('signoff_period_ps requires multiple_cts_roots leaf timing ownership')
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError('signoff_period_ps must be finite and positive')
    if 'signoff_period_ps' in route:
        physical = route.get('period_ps', 770)
        if isinstance(physical, bool) or not isinstance(physical, (int, float)) or not math.isfinite(physical) or physical <= 0 or physical > value:
            raise ValueError('route period must be finite, positive and no greater than signoff_period_ps')
    return float(value)


def related_data(spec):
    """Explicit opt-in to ordinary STA across related leaf roots."""
    policy = spec.get('clock_data_paths', 'independent')
    relationship = spec.get('clock_relationship')
    if policy == 'independent':
        if relationship is not None:
            raise ValueError('independent leaf datapaths do not consume a clock_relationship declaration')
        return False
    if policy != 'related_same_frequency' or relationship != dict(kind='same_pll_fixed_phase', ratio=[1, 1], phase_ps=0):
        raise ValueError('related leaf datapaths require explicit same_pll_fixed_phase ratio1/1 phase0 relationship')
    return True


def domains(spec):
    """Explicit related PLL /3 and /4 clock domains. No exception policy."""
    declared = spec.get('clock_entry_domains')
    leaf = spec.get('clock') == 'multiple_cts_roots'
    if leaf:
        signoff_period(spec)
        related_data(spec)
    if leaf and (spec.get('kind') != 'tile' or declared is None or len(spec.get('clock_ports', [])) < 2):
        raise ValueError('multiple_cts_roots requires a leaf tile, at least two roots and explicit IO domains')
    if declared is None:
        return {'core': dict(ratio=[1, 1], ports=list(spec['clock_ports']),
                             inputs=['*'], outputs=['*'])}
    if not isinstance(declared, dict) or 'core' not in declared:
        raise ValueError('entries: explicit domains require core ratio1/1')
    owners = {}
    out = {}
    for name, data in declared.items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name):
            raise ValueError('entries: invalid domain name')
        if set(data) - {'ratio', 'ports', 'inputs', 'outputs'}:
            raise ValueError('entries: unsupported domain policy (no clock exceptions)')
        ratio = data.get('ratio')
        if ratio not in ([1, 1], [4, 3]):
            raise ValueError('entries: only related CK1/1 and CKV4/3 are supported')
        if leaf and (ratio != [1, 1] or len(data.get('ports', [])) != 1):
            raise ValueError('multiple_cts_roots requires one actual related samefrequency phase0 root per domain')
        if name == 'core' and ratio != [1, 1]:
            raise ValueError('entries: core ratio must be1/1')
        for field in ('ports', 'inputs', 'outputs'):
            if not isinstance(data.get(field), list) or any(not isinstance(x, str) for x in data[field]):
                raise ValueError(f'entries: {name}.{field} must be an explicit string list')
        if leaf and any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x) for f in ('inputs', 'outputs') for x in data[f]):
            raise ValueError('multiple_cts_roots requires literal base IO names, no wildcard domains')
        if not data['ports']:
            raise ValueError(f'entries: {name} needs at least one actual entry port')
        for port in data['ports']:
            if port in owners:
                raise ValueError(f'entries: duplicate domain clock port {port}')
            owners[port] = name
        out[name] = data
    if set(owners) != set(spec['clock_ports']):
        raise ValueError('entries: domain clock coverage differs from actual source ports')
    if owners[spec['clock_port']] != 'core':
        raise ValueError('entries: primary clock_port must belong to core')
    return out


def virtual_clock(domain):
    return 'core_clk' if domain == 'core' else f'ot_io_{domain}'


def clocks(spec, period):
    if spec.get('clock') not in MODES:
        return f"create_clock -name core_clk -period {period} [get_ports {spec['clock_port']}]\n"
    ds = domains(spec)
    owners = {p: name for name, d in ds.items() for p in d['ports']}
    lines = [f'# OT_CLOCK_ENTRY_DOMAIN_API_VERSION {ENTRY_DOMAIN_API_VERSION}']
    for name, d in ds.items():
        value = period * d['ratio'][0] / d['ratio'][1]
        lines.append(f"create_clock -name {virtual_clock(name)} -period {value:.9f}")
    for i, port in enumerate(spec['clock_ports']):
        ratio = ds[owners[port]]['ratio']
        value = period * ratio[0] / ratio[1]
        lines.append(f"create_clock -name ot_entry_{i} -period {value:.9f} [get_ports {{{port}}}]")
    return '\n'.join(lines) + '\n'


def generate(spec, root):
    if spec.get('clock') not in MODES:
        return ''
    ds = domains(spec)
    direct = direct_macro_clock_entries.load(spec, root)
    roots = list(spec['clock_ports']) if spec.get('clock') == 'multiple_cts_roots' else (spec.get('clock_cts_roots', []) if spec.get('clock') == 'hybrid_entries' else [])
    if spec.get('clock') == 'hybrid_entries' and (not isinstance(roots, list) or not roots or
            not all(isinstance(p, str) for p in roots) or len(set(roots)) != len(roots) or not set(roots) < set(spec['clock_ports'])):
        raise ValueError('hybrid_entries requires a nonempty proper subset of distinct clock_cts_roots')
    refs, counts = {}, {}
    for child in spec.get('children', []):
        view = Path(root) / child['view']
        master = view.name
        counts[master] = counts.get(master, 0) + int(child.get('count', 1))
        if master in refs:
            continue
        record = json.loads((view / 'insertion.json').read_text())
        pins = record.get('clock_measurements')
        if not pins:
            pin = record.get('lib_clock_pin')
            if not pin:
                # Legacy exports have one routed root named ck and one actual
                # Liberty clock pin named clk. Only a unique pin can bind it.
                clocks = child_lint.clock_insertion((view / f'{master}_tt.lib').read_text())
                if len(clocks) != 1 or not record.get('clock'):
                    raise ValueError(f'{view}: ambiguous routed clock pin association')
                pin = next(iter(clocks))
            pins = {pin: record}
        if len(pins) > 1 and spec.get('clock_entry_domains') is None:
            raise ValueError(f'{view}: multi-clock child requires explicit entry domain/ratio/IO mapping')
        refs[master] = {}
        for pin, measured in pins.items():
            refs[master][pin] = {}
            for corner in CORNERS:
                lib = view / f'{master}_{corner}.lib'
                if not lib.is_file():
                    raise ValueError(f'{lib}: missing bound child ETM')
                clocks = child_lint.clock_insertion(lib.read_text())
                if pin not in clocks or set(clocks) != set(pins):
                    raise ValueError(f'{lib}: routed/Liberty clock pin association mismatch')
                data = measured.get(corner, {})
                b = data.get('boundary', {})
                values = [float(b[k]) for k in ('min', 'mean', 'max')]
                if not b.get('n') or data.get('errors') or not all(math.isfinite(x) for x in values):
                    raise ValueError(f'{view}/{pin}/{corner}: missing real routed boundary reference')
                if not values[0] <= values[1] <= values[2]:
                    raise ValueError(f'{view}/{pin}/{corner}: inconsistent boundary reference')
                refs[master][pin][corner] = values
    expected = sum(counts[m] * len(refs[m]) for m in refs) + len(direct['entries'])
    if expected != len(spec['clock_ports']) - len(roots):
        raise ValueError(f'entries: {expected} bound child clock pins, {len(spec["clock_ports"]) - len(roots)} hard source ports')
    rows = []
    for master, pins in refs.items():
        for pin, corners in pins.items():
            row = ' '.join(f'{c} {{{" ".join(map(str, corners[c]))}}}' for c in CORNERS)
            rows.append(f'{{{master}/{pin}}} {{{row}}}')
    domain_rows = []
    owner_rows = []
    for name, d in ds.items():
        patterns = lambda names: ' '.join('{' + n + '}' for n in names)
        domain_rows.append("{" + name + "} {clock " + virtual_clock(name) + " io_budget_ps " + str(round(signoff_period(spec) * d["ratio"][0] / d["ratio"][1] * 0.2, 3)) + " inputs {" + patterns(d["inputs"]) + "} outputs {" + patterns(d["outputs"]) + "}}")
        owner_rows.extend(f"{{{p}}} {{{name}}}" for p in d['ports'])
    body = LEAF_BODY if spec.get('clock') == 'multiple_cts_roots' else BODY
    if direct['entries']:
        body = direct_body(body, direct)
    return (f'# OT_CLOCK_ENTRY_DOMAIN_API_VERSION {ENTRY_DOMAIN_API_VERSION}\n'
            '# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.\n'
            + (('set ::ot_ce_leaf_roots 1\nset ::ot_ce_related_data ' + str(int(related_data(spec))) + '\n') if spec.get('clock') == 'multiple_cts_roots' else '') +
            'set ::ot_ce_refs [dict create ' + ' '.join(rows) + ']\n'
            'set ::ot_ce_counts [dict create ' + ' '.join(f'{{{m}}} {n}' for m, n in counts.items()) + ']\n'
            'set ::ot_ce_domains [dict create ' + ' '.join(domain_rows) + ']\n'
            'set ::ot_ce_source_domains [dict create ' + ' '.join(owner_rows) + ']\n'
            'set ::ot_ce_explicit_domains ' + str(int(spec.get('clock_entry_domains') is not None)) + '\n'
            'set ::ot_ce_cts_roots {' + ' '.join('{' + p + '}' for p in roots) + '}\n'
            'set ::ot_ce_ports {' + ' '.join('{' + p + '}' for p in spec['clock_ports']) + '}\n' + body)


BODY = r'''
proc ot_ce_corner {} {
  if {[info exists ::ot_ioref_scene] && $::ot_ioref_scene eq "BC"} { return ff }
  if {[info exists ::ot_ce_corner]} { return $::ot_ce_corner }
  # WC is a scene label, not an actual library corner: option-B overlays WC
  # with TT. Bind the reference to actual loaded child Liberty objects.
  set found {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    set libcells [get_lib_cells -quiet -of_objects $cell]
    if {![llength $libcells]} { error "OT_ENTRIES: $master has no loaded Liberty association" }
    foreach lc $libcells {
      set full [get_full_name $lc]
      if {![regexp -nocase {_(tt|ff|ss)/} $full -> corner]} { error "OT_ENTRIES: unknown actual child Liberty corner $full" }
      dict set found [string tolower $corner] 1
    }
  }
  if {[dict size $found] == 1} { return [lindex [dict keys $found] 0] }
  # A multi-mode database needs its actual setup corner or BC scene shim.
  if {[info exists ::env(OT_MM_SETUP_CORNER)]} {
    switch -nocase -- $::env(OT_MM_SETUP_CORNER) {
      TC - tt {set corner tt} BC - ff {set corner ff} WC - ss {set corner ss}
      default { error "OT_ENTRIES: unknown actual setup corner" }
    }
    if {[dict exists $found $corner]} { return $corner }
  }
  error "OT_ENTRIES: ambiguous actual loaded child corners [dict keys $found]"
}
# get_property pin arrival_max_rise is a DATA arrival query. On a clock-only
# macro pin it returns an infinity sentinel even with a finite propagated clock
# path. Read the actual rising clock path in the current analysis scene instead.
proc ot_ce_finite {value} {
  return [expr {[string is double -strict $value] && ![regexp -nocase {inf|nan} $value]}]
}
proc ot_ce_clock_wire {pin clock} {
  set scene [get_property [sta::cmd_scene] name]
  set clock_name [get_full_name $clock]
  set values {}
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    set paths [$vertex path_iterator rise max]
    while {[$paths has_next]} {
      set path [$paths next]
      # OpenSTA's Path tag identifies scene, rise/max, clock and propagation.
      # Match the complete fixed fields, never accept another scene's path.
      set tag [$path tag]
      if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne "^max" ||
          [lindex $tag 3] ne $clock_name || [lindex $tag 4] ne "^" ||
          [string first "(clock prop)" $tag] < 0} continue
      set arrival [sta::time_sta_ui [$path arrival]]
      if {![ot_ce_finite $arrival]} {
        $paths finish
        error "OT_ENTRIES: nonfinite propagated clock arrival on [get_full_name $pin] scene=$scene clock=$clock_name"
      }
      lappend values $arrival
    }
    $paths finish
  }
  if {[llength $values] != 1} {
    # Synthesis/floorplan have no extracted entry wire. This is solely a finite
    # pre-CTS diagnostic reference; routed gates must measure a clock path.
    if {![llength $values] && [info exists ::ot_ref_pre_cts] && $::ot_ref_pre_cts &&
        (![info exists ::ot_ce_require_wire] || !$::ot_ce_require_wire)} {
      puts "OT_ENTRIES PRE_CTS_ZERO_WIRE [get_full_name $pin] scene=$scene"
      return 0.0
    }
    error "OT_ENTRIES: missing unique finite propagated clock arrival on [get_full_name $pin] scene=$scene clock=$clock_name"
  }
  return [lindex $values 0]
}
# Match ck_insertion.py's exported insertion.json boundary population: input
# timing endpoints plus output timing launch registers, intersected with this root.
proc ot_ce_boundary_pins {pins} {
  set regs {}; set boundary {}
  foreach pin $pins { dict set regs [regsub {/[^/]+$} [get_full_name $pin] {}] $pin }
  set inputs [all_inputs -no_clocks]
  if {[llength $inputs]} {
    foreach path [find_timing_paths -path_delay max -from $inputs -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] {
      set name [regsub {/[^/]+$} [get_full_name [get_property $path endpoint]] {}]
      if {[dict exists $regs $name]} { dict set boundary $name [dict get $regs $name] }
    }
  }
  if {[llength [all_outputs]]} {
    foreach path [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] {
      set name [regsub {/[^/]+$} [get_full_name [get_property $path startpoint]] {}]
      if {[dict exists $regs $name]} { dict set boundary $name [dict get $regs $name] }
    }
  }
  return [dict values $boundary]
}
proc ot_ce_apply {} {
  set corner [ot_ce_corner]
  set clk [get_clocks core_clk]
  if {[llength $clk] != 1} { error "OT_ENTRIES: core_clk missing" }
  # Wires-only parents have no CTS tree to set this flag for us.
  # Ideal clocks silently report zero network arrival despite real entry wires.
  set_propagated_clock [get_clocks ot_entry_*]
  set sources {}; set names {}
  foreach c [get_clocks ot_entry_*] {
    foreach p [get_property $c sources] { lappend sources $p; lappend names [get_full_name $p] }
  }
  if {[lsort $names] ne [lsort $::ot_ce_ports]} { error "OT_ENTRIES: source clock coverage differs from spec" }
  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }
  sta::worst_slack_cmd max
  set rows {}; set seen {}; set counts {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    dict incr counts $master
    foreach pin [get_pins -quiet -of_objects $cell] {
      set key "$master/[get_property $pin lib_pin_name]"
      if {![dict exists $::ot_ce_refs $key]} continue
      set ports [get_ports -quiet -of_objects [get_nets -quiet -of_objects $pin]]
      if {[llength $ports] != 1} { error "OT_ENTRIES: [get_full_name $pin] lacks one direct top clock port" }
      set port [lindex $ports 0]; set name [get_full_name $port]
      if {$name ni $::ot_ce_ports || $name in $::ot_ce_cts_roots || [dict exists $seen $name]} { error "OT_ENTRIES: duplicate or undeclared source $name" }
      dict set seen $name 1
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set wire [ot_ce_clock_wire $pin $clock]
      if {![ot_ce_finite $wire]} { error "OT_ENTRIES: nonfinite entry wire clock arrival on [get_full_name $pin]" }
      if {abs($wire) < 1.0e-9 && [info exists ::ot_ce_require_wire] && $::ot_ce_require_wire} {
        # A zero arrival is admissible only if actual source and child pin are
        # physically coincident. Missing parasitics/ideal clocks cannot qualify.
        if {![llength [info commands ord::get_db_block]]} { error "OT_ENTRIES: zero wire lacks physical source/pin proof" }
        set block [ord::get_db_block]
        set bt [$block findBTerm $name]
        set it [$block findITerm [get_full_name $pin]]
        if {$bt eq "NULL" || $it eq "NULL"} { error "OT_ENTRIES: missing physical source/child clock pin" }
        set pb [$bt getBBox]; set ib [$it getBBox]
        set distance [expr {(abs(([$pb xMin]+[$pb xMax])-([$ib xMin]+[$ib xMax])) + abs(([$pb yMin]+[$pb yMax])-([$ib yMin]+[$ib yMax]))) / 2.0 / [$block getDbUnitsPerMicron]}]
        if {$distance > 0.001} { error "OT_ENTRIES: zero clock wire arrival despite $distance um source/pin separation on $name" }
        puts "OT_ENTRIES ZERO_WIRE_PROVEN $name [get_full_name $pin] distance=$distance"
      }
      lassign [dict get $::ot_ce_refs $key $corner] lo mean hi
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set ttmean [lindex [dict get $::ot_ce_refs $key tt] 1]
      set domain [dict get $::ot_ce_source_domains $name]
      set vc [get_clocks [dict get $::ot_ce_domains $domain clock]]
      if {abs([get_property $vc period]-[get_property $clock period])>0.001} { error "OT_ENTRIES: domain/source period mismatch $name" }
      lappend rows [list $port $pin $wire $lo $mean $hi $clock $ttmean $domain]
    }
  }
  dict for {m n} $::ot_ce_counts {
    if {![dict exists $counts $m] || [dict get $counts $m] != $n} { error "OT_ENTRIES: bound child count mismatch $m" }
  }
  # Each glue root owns a real CTS tree. Measure every propagated standard-cell
  # clock sink in the current scene; never substitute a declared/common phase.
  foreach name $::ot_ce_cts_roots {
    set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
    set pins [all_registers -clock [get_full_name $clock] -clock_pins]
    if {![llength $pins]} { error "OT_HYBRID: glue root $name has no actual sequential clock sinks" }
    set arrivals {}; set measured {}; set total 0.0
    foreach pin $pins {
      set cell [get_cells -of_objects $pin]
      set master [get_property $cell ref_name]
      if {[dict exists $::ot_ce_counts $master]} { error "OT_HYBRID: CTS root $name reaches a hard child" }
      set arrival [ot_ce_clock_wire $pin $clock]
      lappend arrivals $arrival
      dict set measured [get_full_name $pin] $arrival
      set total [expr {$total + $arrival}]
    }
    set arrivals [lsort -real $arrivals]
    set lo [lindex $arrivals 0]; set hi [lindex $arrivals end]
    set tree_mean [expr {$total / [llength $arrivals]}]
    set mean $tree_mean
    if {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire && $mean <= 0} {
      error "OT_HYBRID: glue root $name lacks a positive actual propagated CTS insertion"
    }
    if {[llength $arrivals] > 15000 && ($tree_mean > 300 || $hi-$lo > 80)} {
      error "OT_HYBRID: glue root $name exceeds measured large-root insertion/spread limits"
    }
    set boundary [ot_ce_boundary_pins $pins]
    set scope boundary
    if {![llength $boundary]} { set boundary $pins; set scope all_internal_only }
    set arrivals {}; set total 0.0
    foreach pin $boundary {
      set arrival [dict get $measured [get_full_name $pin]]
      lappend arrivals $arrival; set total [expr {$total + $arrival}]
    }
    set arrivals [lsort -real $arrivals]
    set lo [lindex $arrivals 0]; set hi [lindex $arrivals end]
    set mean [expr {$total / [llength $arrivals]}]
    if {[llength $pins] > 15000 && $mean > 300} {
      error "OT_HYBRID: glue root $name exceeds boundary insertion limit"
    }
    set domain [dict get $::ot_ce_source_domains $name]
    lappend rows [list [get_ports $name] [lindex $pins 0] 0 $lo $mean $hi $clock $mean $domain]
    dict set seen $name 1
    puts "OT_HYBRID CTS_MEASURE $corner $name sinks=[llength $pins] reference_scope=$scope boundary_sinks=[llength $boundary] min=$lo mean=$mean max=$hi all_mean=$tree_mean"
  }
  if {[dict size $seen] != [llength $::ot_ce_ports]} { error "OT_ENTRIES: incomplete actual child/source coverage" }
  set ref 0
  foreach row $rows { lassign $row p pin wire lo mean hi; set ref [expr {max($ref, $wire + $mean)}] }
  set low {}; set high {}; set lowclocks {}; set highclocks {}; set domain_low {}; set domain_high {}
  foreach row $rows {
    lassign $row p pin wire lo mean hi clock ttmean domain
    # Physical source level includes the entry wire, not just the hard
    # child's internal insertion. Only a TT scene measures the TT wire.
    # Other physical scenes conservatively reserve the deep pair budget;
    # they must not guess TT wire delay from FF/SS or an ideal zero arrival.
    set deep [expr {$ttmean > 300}]
    set level_basis "zero-wire diagnostic"
    if {$corner eq "tt"} {
      set deep [expr {$ttmean + $wire > 300}]
      set level_basis "TT timing-graph entry arrival + child R (physical proof required for route/signoff)"
    } elseif {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire} {
      set deep 1
      set level_basis "TT wire level not measured in this scene; conservative210ps setup"
    }
    if {$deep} { lappend highclocks $clock } else { lappend lowclocks $clock }
    puts "OT_ENTRIES LEVEL [get_full_name $p] deep=$deep basis=$level_basis"
    set latency [expr {$ref - $wire - $mean}]
    if {![ot_ce_finite $ref] || ![ot_ce_finite $latency]} { error "OT_ENTRIES: nonfinite reference/source latency on [get_full_name $p]" }
    set_clock_latency -source $latency $clock
    lappend low [expr {$ref + $lo - $mean}]; lappend high [expr {$ref + $hi - $mean}]
    dict lappend domain_low $domain [expr {$ref + $lo - $mean}]
    dict lappend domain_high $domain [expr {$ref + $hi - $mean}]
    puts "OT_ENTRIES COMP $corner [get_full_name $p] -> [get_full_name $pin] wire=$wire R=$mean latency=$latency phi=$ref"
  }
  # Every entry is synchronous and related. Reserve die skew on internal hops;
  # no asynchronous groups, false paths or ETM insertion add-back.
  set_clock_uncertainty -setup 150 -from [get_clocks ot_entry_*] -to [get_clocks ot_entry_*]
  # H1 authoritative pair_check.HOLD_TREE =50ps hold margin+50ps die skew.
  # Tile-local25ps uncertainty is not the composed pair margin.
  set_clock_uncertainty -hold 100 -from [get_clocks ot_entry_*] -to [get_clocks ot_entry_*]
  # Each deep tile has its own earlier trunk tap. The authoritative TREE
  # pair budget uses150ps die skew when either reference exceeds300ps,
  # including deep-to-deep pairs (pair_check.SKEW_DEEP).
  if {[llength $highclocks]} {
    set_clock_uncertainty -setup 210 -from $highclocks -to [get_clocks ot_entry_*]
    set_clock_uncertainty -setup 210 -from [get_clocks ot_entry_*] -to $highclocks
  }
  # Preserve measured boundary spread: balancing the mean does not erase the
  # earliest/latest physical boundary arrivals or change ETM setup/hold arcs.
  set lmin [lindex [lsort -real $low] 0]; set lmax [lindex [lsort -real $high] end]
  unset_input_delay [all_inputs]; unset_output_delay [all_outputs]
  set sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  set covered_in {}; set covered_out {}
  dict for {domain info} $::ot_ce_domains {
    if {![dict exists $domain_low $domain]} { error "OT_ENTRIES: domain $domain has no actual child clock pins" }
    set dlmin [lindex [lsort -real [dict get $domain_low $domain]] 0]
    set dlmax [lindex [lsort -real [dict get $domain_high $domain]] end]
    set vc [get_clocks [dict get $info clock]]
    set budget [dict get $info io_budget_ps]
    set inputs {}; set outputs {}
    foreach pattern [dict get $info inputs] {
      foreach p [get_ports -quiet $pattern -filter "direction == input"] {
        set n [get_full_name $p]
        if {$n in $::ot_ce_ports} continue
        if {[dict exists $covered_in $n]} { error "OT_ENTRIES: input $n has duplicate IO domains" }
        dict set covered_in $n $domain; lappend inputs $p
      }
    }
    foreach pattern [dict get $info outputs] {
      foreach p [get_ports -quiet $pattern -filter "direction == output"] {
        set n [get_full_name $p]
        if {[dict exists $covered_out $n]} { error "OT_ENTRIES: output $n has duplicate IO domains" }
        dict set covered_out $n $domain; lappend outputs $p
      }
    }
    if {[llength $inputs]} {
      set_input_delay [expr {$budget+$dlmax+$sk}] -max -clock $vc $inputs
      set_input_delay [expr {$dlmin-$hki}] -min -clock $vc $inputs
    }
    if {[llength $outputs]} {
      set_output_delay [expr {$budget-$dlmax+$sk}] -max -clock $vc $outputs
      set_output_delay [expr {-$dlmin-$hk}] -min -clock $vc $outputs
    }
    if {[info exists ::env(OT_IO_INTER)] && $::env(OT_IO_INTER) ne ""} {
      foreach pattern [split $::env(OT_IO_INTER) ","] {
        foreach p [get_ports -quiet $pattern] {
          set n [get_full_name $p]
          if {[dict exists $covered_in $n] && [dict get $covered_in $n] eq $domain} {
            set_input_delay [expr {$budget+$dlmax+150}] -max -clock $vc $p
          }
          if {[dict exists $covered_out $n] && [dict get $covered_out $n] eq $domain} {
            set_output_delay [expr {$budget-$dlmax+150}] -max -clock $vc $p
          }
        }
      }
    }
    puts "OT_ENTRIES DOMAIN $domain [get_property $vc period]ps IO[llength $inputs]/[llength $outputs] boundary=$dlmin..$dlmax"
  }
  if {[dict size $covered_in] != [llength [all_inputs -no_clocks]] || [dict size $covered_out] != [llength [all_outputs]]} {
    error "OT_ENTRIES: incomplete actual IO domain coverage (resets must also have a domain)"
  }
  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"
}
ot_ce_apply
'''


LEAF_OWNERSHIP = r'''
# A multi-root leaf contains independent synchronous datapaths. Domain declarations
# are checked against the real synthesized timing graph, not trusted as metadata.
proc ot_ce_leaf_ownership {inputs outputs} {
  set expected {}
  dict for {domain info} $::ot_ce_domains {lappend expected [dict get $info clock]}
  for {set i 0} {$i < [llength $::ot_ce_ports]} {incr i} {lappend expected ot_entry_$i}
  set actual {}
  foreach c [all_clocks] {lappend actual [get_full_name $c]}
  if {[lsort $actual] ne [lsort $expected]} {error "OT_MULTI_ROOT: undeclared clock alias or relationship"}
  set cells {}; set clocks {}; set crossing_pairs {}; set domain_roots {}
  foreach root $::ot_ce_cts_roots {
    set domain [dict get $::ot_ce_source_domains $root]
    dict set domain_roots $domain $root
    set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $root]]
    foreach pin [all_registers -clock [get_full_name $clock] -clock_pins] {
      set cell [get_full_name [get_cells -of_objects $pin]]
      if {[dict exists $cells $cell]} { error "OT_MULTI_ROOT: duplicate clock ownership $cell" }
      dict set cells $cell $domain
    }
  }
  foreach pin [all_registers -clock_pins] {
    set cell [get_full_name [get_cells -of_objects $pin]]
    if {![dict exists $cells $cell]} { error "OT_MULTI_ROOT: unowned register $cell" }
  }
  # OpenSTA's -data_pins population includes asynchronous clear/preset
  # controls. Classify these from the actual loaded Liberty sequential arcs,
  # never from port names or reset_ports. They retain recovery/removal timing;
  # only ordinary synchronous D/control paths require data-domain ownership.
  set async_pins {}
  foreach pin [all_registers -async_pins] {dict set async_pins [get_full_name $pin] 1}
  foreach pin [all_registers -data_pins] {
    if {[dict exists $async_pins [get_full_name $pin]]} continue
    set cell [get_full_name [get_cells -of_objects $pin]]
    set expected [dict get $cells $cell]
    foreach start [get_fanin -flat -startpoints_only -to $pin] {
      set ports [get_ports -quiet [get_full_name $start]]
      if {[llength $ports]} {
        set name [get_full_name $start]
        if {![dict exists $inputs $name] || [dict get $inputs $name] ne $expected} {
          error "OT_MULTI_ROOT: input $name has wrong domain for $cell"
        }
      } else {
        set source [get_full_name [get_cells -quiet -of_objects $start]]
        if {![dict exists $cells $source]} {
          error "OT_MULTI_ROOT: unowned data path $source -> $cell"
        }
        set source_domain [dict get $cells $source]
        if {$source_domain ne $expected} {
          if {!$::ot_ce_related_data} {error "OT_MULTI_ROOT: cross-domain data path $source -> $cell requires explicit related profile"}
          dict set crossing_pairs [list $source_domain $expected] 1
        }
      }
    }
  }
  dict for {name domain} $outputs {
    foreach start [get_fanin -flat -startpoints_only -to [get_ports $name]] {
      set source [get_full_name [get_cells -quiet -of_objects $start]]
      if {![dict exists $cells $source] || [dict get $cells $source] ne $domain} {
        error "OT_MULTI_ROOT: output $name has wrong or unregistered source domain $source"
      }
    }
  }
  dict for {pair unused} $crossing_pairs {
    lassign $pair source_domain target_domain
    set source_root [dict get $domain_roots $source_domain]
    set target_root [dict get $domain_roots $target_domain]
    set from [all_registers -clock ot_entry_[lsearch -exact $::ot_ce_ports $source_root] -clock_pins]
    set to {}
    foreach pin [all_registers -clock ot_entry_[lsearch -exact $::ot_ce_ports $target_root] -data_pins] {
      if {![dict exists $async_pins [get_full_name $pin]]} {lappend to $pin}
    }
    foreach kind {max min} {
      set paths [find_timing_paths -from $from -to $to -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
      if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
        error "OT_MULTI_ROOT: related crossing lacks actual finite $kind STA path $source_domain -> $target_domain"
      }
      puts "OT_MULTI_ROOT RELATED_PATH $source_domain -> $target_domain $kind slack=[get_property [lindex $paths 0] slack] (ordinary synchronous timing retained)"
    }
  }
  puts "OT_MULTI_ROOT OWNERSHIP PASS roots=[llength $::ot_ce_cts_roots] registers=[dict size $cells] inputs=[dict size $inputs] outputs=[dict size $outputs] async_control_pins=[dict size $async_pins]"
}
'''


def leaf_body():
    """Extend the proven hard-entry timing algorithm without changing legacy SDC bytes."""
    body = BODY
    substitutions = [
        ('  set found {}\n  foreach cell [get_cells -quiet -hierarchical *] {\n    set master [get_property $cell ref_name]\n    if {![dict exists $::ot_ce_counts $master]} continue\n',
         r'''  set found {}; set clock_cells {}
  # Physical-only taps/endcaps have no Liberty association. The clock corner
  # belongs to actual sequential clock sinks, not every physical instance.
  foreach pin [all_registers -clock_pins] {
    set cell [get_cells -quiet -of_objects $pin]
    if {[llength $cell] != 1 || $cell eq "NULL"} {error "OT_MULTI_ROOT: clock sink lacks one actual sequential cell"}
    dict set clock_cells [get_full_name $cell] $cell
  }
  if {![dict size $clock_cells]} {error "OT_MULTI_ROOT: no actual sequential cells for corner inference"}
  foreach cell [dict values $clock_cells] {
    set master [get_property $cell ref_name]
'''),
        ('    if {![llength $libcells]} { error "OT_ENTRIES: $master has no loaded Liberty association" }\n',
         '    if {![llength $libcells] || "NULL" in $libcells} { error "OT_MULTI_ROOT: actual sequential cell $master has no loaded Liberty association" }\n'),
        ('      if {![regexp -nocase {_(tt|ff|ss)/} $full -> corner]} { error "OT_ENTRIES: unknown actual child Liberty corner $full" }\n',
         '      if {![regexp -nocase {_(tt|ff|ss)/|_(tt|ff|ss)_} $full -> corner alt]} { error "OT_ENTRIES: unknown actual Liberty corner $full" }\n      if {$corner eq ""} {set corner $alt}\n'),
        ('      foreach p [get_ports -quiet $pattern -filter "direction == input"] {\n',
         '      set match [get_ports -quiet $pattern -filter "direction == input"]\n      if {$::ot_ce_leaf_roots && ![llength $match]} {set match [get_ports -quiet [format {%s\\[*\\]} $pattern] -filter "direction == input"]}\n      if {$::ot_ce_leaf_roots && ![llength $match]} {error "OT_MULTI_ROOT: unknown input $pattern"}\n      foreach p $match {\n'),
        ('      foreach p [get_ports -quiet $pattern -filter "direction == output"] {\n',
         '      set match [get_ports -quiet $pattern -filter "direction == output"]\n      if {$::ot_ce_leaf_roots && ![llength $match]} {set match [get_ports -quiet [format {%s\\[*\\]} $pattern] -filter "direction == output"]}\n      if {$::ot_ce_leaf_roots && ![llength $match]} {error "OT_MULTI_ROOT: unknown output $pattern"}\n      foreach p $match {\n'),
        ('  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"\n',
         '  if {$::ot_ce_leaf_roots} { ot_ce_leaf_ownership $covered_in $covered_out }\n  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"\n'),
    ]
    for old, new in substitutions:
        if body.count(old) != 1:
            raise ValueError("clock-entry body changed; revalidate multi-root extension")
        body = body.replace(old, new)
    return LEAF_OWNERSHIP + body


LEAF_BODY = leaf_body()


def direct_body(body, direct):
    """Add explicitly bound raw-memory pin references without changing ETM semantics."""
    marker = '  # Each glue root owns a real CTS tree.'
    hook = r'''  foreach row [ot_ce_direct_rows $corner] {
    set name [get_full_name [lindex $row 0]]
    if {[dict exists $seen $name]} {error "OT_DIRECT_MACRO: duplicate hard-source ownership $name"}
    dict set seen $name 1
    lappend rows $row
  }
'''
    if body.count(marker) != 1:
        raise ValueError('clock entry body changed; revalidate direct macro extension')
    body = body.replace(marker, hook + marker)
    # A parent with only direct raw SRAMs has no routed ETM master from which
    # to identify the current scene; use its actual linked SRAM libraries too.
    marker = '    if {![dict exists $::ot_ce_counts $master]} continue'
    if body.count(marker) != 2:
        raise ValueError('clock entry corner body changed; revalidate direct macro extension')
    body = body.replace(marker, '    if {![dict exists $::ot_ce_counts $master] && $master ni $::ot_ce_direct_masters} continue', 1)
    masters = sorted({e['master'] for e in direct['entries']})
    return ('set ::ot_ce_direct_masters {' + ' '.join(masters) + '}\n'
            + direct['bindings_tcl'] + body)
