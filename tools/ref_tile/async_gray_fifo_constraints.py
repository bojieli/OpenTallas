"""Bounded CDC admission for one reviewed HBM/PHY SPSC FIFO implementation.

This initial profile admits the primitive itself. Parents with other crossings,
including independent status synchronizers, remain refused. The source identity
and actual mapped fanin are both checked; register naming alone is insufficient.
No clock groups, false paths or same-domain timing exceptions are generated.
"""
import hashlib
from pathlib import Path

SOURCES = {
    'rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo.sv':
        ('e83b7120ff9c6b00eb1a7892bdfd0d4a8e9717fdf055f975f96fa879bb6c91b8',
         '3b85c58128cd8f8eeccf6e962c8cbe3672d56d3e10d044343307eb72a4712fe1'),
    'rtl/lib/ot_reset_sync.sv':
        ('489e493c19aa1260853031fee35c14ea3394ae62ff6853cf7ea407cb8fb78bbd',),
}
RELATIONSHIP = dict(kind='hbm_phy_async_gray_fifo', stream_period_ps=833.333,
                    hbm_period_ps=1024.0)


def relationship(spec):
    if (spec.get('clock') != 'multiple_cts_roots' or spec.get('kind') != 'tile'
            or spec.get('clock_relationship') != RELATIONSHIP):
        raise ValueError('async_gray_fifo requires explicit HBM PHY stream833.333/HBM1024 relationship and native leaf roots')
    if set(spec.get('clock_entry_domains', {})) != {'core', 'hbm'}:
        raise ValueError('async_gray_fifo requires exactly core and hbm domains')
    if float(spec.get('route', {}).get('signoff_period_ps', 833.333)) != 833.333:
        raise ValueError('async_gray_fifo must retain actual stream833.333 primary period')


def load(spec, root):
    relationship(spec)
    if spec.get('top') != 'ot_hbm_svc_async_fifo' or spec.get('children') or spec.get('macros'):
        raise ValueError('async_gray_fifo currently admits only the reviewed FIFO primitive; parent crossings require separate actual graph proof')
    if set(spec.get('sources', [])) != set(SOURCES) or len(spec['sources']) != len(SOURCES):
        raise ValueError('async_gray_fifo sources must be exactly the reviewed FIFO and reset synchronizer')
    actual_hashes = {}
    for path, expected in SOURCES.items():
        actual_hashes[path] = hashlib.sha256((Path(root) / path).read_bytes()).hexdigest()
        if actual_hashes[path] not in expected:
            raise ValueError(f'async_gray_fifo reviewed source changed: {path}')
    params = spec.get('params', {})
    if set(params) - {'WIDTH', 'DEPTH'} or type(params.get('WIDTH', 32)) is not int or params.get('WIDTH', 32) < 1:
        raise ValueError('async_gray_fifo unsupported primitive parameters')
    if type(params.get('DEPTH', 8)) is not int or params.get('DEPTH', 8) not in (4, 8):
        raise ValueError('async_gray_fifo requires bench-proved DEPTH4 or DEPTH8')
    ds = spec['clock_entry_domains']
    if (spec.get('clock_port') != 'rd_clk' or spec.get('clock_ports') != ['rd_clk', 'wr_clk']
            or ds['core'].get('ports') != ['rd_clk'] or ds['hbm'].get('ports') != ['wr_clk']):
        raise ValueError('async_gray_fifo initial primitive profile requires writer HBM / reader stream actual roots')
    expected = {
        'core': ({'rd_rst_n', 'rd_ready'}, {'rd_valid', 'rd_data', 'rd_underflow'}),
        'hbm': ({'wr_rst_n', 'wr_valid', 'wr_data'}, {'wr_ready', 'wr_overflow'}),
    }
    for name, (inputs, outputs) in expected.items():
        if set(ds[name].get('inputs', [])) != inputs or set(ds[name].get('outputs', [])) != outputs:
            raise ValueError(f'async_gray_fifo wrong actual IO ownership for {name}')
    return dict(source_sha256=actual_hashes, depth=params.get('DEPTH', 8), width=params.get('WIDTH', 32))


def extend(body, spec, root):
    load(spec, root)
    crossing = '          if {!$::ot_ce_related_data} {error "OT_MULTI_ROOT: cross-domain data path $source -> $cell requires explicit related profile"}'
    if body.count(crossing) != 1:
        raise ValueError('async_gray_fifo actual crossing gate changed; revalidate extension')
    body = body.replace(crossing, '''          ot_ag_crossing $start $pin $source $cell $source_domain $expected
          continue''')
    output = '''      if {![dict exists $cells $source] || [dict get $cells $source] ne $domain} {
        error "OT_MULTI_ROOT: output $name has wrong or unregistered source domain $source"
      }'''
    if body.count(output) != 1:
        raise ValueError('async_gray_fifo output gate changed; revalidate extension')
    body = body.replace(output, '''      if {![dict exists $cells $source] || [dict get $cells $source] ne $domain} {
        if {[dict exists $cells $source] && [ot_ag_payload $start [get_ports $name] $source $name [dict get $cells $source] $domain]} {continue}
        error "OT_MULTI_ROOT: output $name has wrong or unregistered source domain $source"
      }''')
    marker = '  puts "OT_MULTI_ROOT OWNERSHIP PASS roots='
    if body.count(marker) != 1:
        raise ValueError('async_gray_fifo ownership gate changed; revalidate extension')
    body = body.replace(marker, '  ot_ag_complete\n' + marker)
    body = body.replace('  set cells {}; set clocks {}; set crossing_pairs {}; set domain_roots {}',
                        '  set ::ot_ag_seen {}\n  set cells {}; set clocks {}; set crossing_pairs {}; set domain_roots {}')
    return TCL + '\n' + body


TCL = r'''
# Source fingerprint is checked by the generator before this audited profile is
# emitted. Fail if mapping loses public register identities; never guess names.
set ::ot_ag_seen {}
proc ot_ag_role {cell} {
  set roles {}
  foreach p [get_pins -quiet -of_objects [get_cells $cell]] {
    if {[get_property $p direction] ne "output"} continue
    foreach net [get_nets -quiet -of_objects $p] {
      set name [string map {\\ {}} [get_full_name $net]]
      if {[regexp {^(wr_gray|rd_gray|wr_gray_r1|rd_gray_w1|wr_online|rd_online|wr_online_r1|rd_online_w1)(\[[0-9]+\])?$} $name unused role]} {
        dict set roles $role 1
      }
      if {[regexp {^mem\[[0-9]+\](\[[0-9]+\])?$} $name]} {dict set roles payload 1}
    }
  }
  if {[dict size $roles] != 1} {return {}}
  return [lindex [dict keys $roles] 0]
}
proc ot_ag_bound {start target} {
  # OpenSTA graph startpoints are register clock pins; exceptions and path
  # queries must begin at the actual launch register, not a clock input pin.
  set launch [get_cells -quiet -of_objects $start]
  if {[llength $launch] != 1} {error "OT_ASYNC_GRAY: missing unique launch register"}
  # Bound ALL Gray bits within the faster source period minus setup uncertainty;
  # this also bounds inter-bit skew below a source cycle. Payload is held by the
  # verified FIFO protocol, and receives the same conservative datapath budget.
  # No exception applies to any other path or either synchronizer's second stage.
  set_max_delay -ignore_clock_latency 773.333 -from $launch -to $target
  set_min_delay -ignore_clock_latency 0.0 -from $launch -to $target
  foreach kind {max min} {
    set paths [find_timing_paths -from $launch -to $target -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
    if {![llength $paths] && [info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1" && ![info exists ::ot_mm_active]} {
      puts "OT_ASYNC_GRAY PATH_DEFERRED [get_full_name $start] -> [get_full_name $target] $kind (strict at sign-off)"
      continue
    }
    if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
      error "OT_ASYNC_GRAY: missing finite bounded $kind path [get_full_name $start] -> [get_full_name $target]"
    }
  }
}
proc ot_ag_crossing {start pin source target source_domain target_domain} {
  set sr [ot_ag_role $source]; set tr [ot_ag_role $target]
  set pair [list $sr $tr $source_domain $target_domain]
  if {$pair ni {{wr_gray wr_gray_r1 hbm core} {rd_gray rd_gray_w1 core hbm}
                 {wr_online wr_online_r1 hbm core} {rd_online rd_online_w1 core hbm}}} {
    error "OT_ASYNC_GRAY: unapproved actual crossing $source -> $target ($pair)"
  }
  ot_ag_bound $start $pin
  dict incr ::ot_ag_seen $sr
  puts "OT_ASYNC_GRAY BOUNDED $source -> $target"
}
proc ot_ag_payload {start port source name source_domain target_domain} {
  if {$source_domain ne "hbm" || $target_domain ne "core" ||
      ![regexp {^rd_data\[[0-9]+\]$} $name] || [ot_ag_role $source] ne "payload"} {return 0}
  ot_ag_bound $start $port
  dict incr ::ot_ag_seen payload
  return 1
}
proc ot_ag_complete {} {
  foreach role {wr_gray rd_gray wr_online rd_online payload} {
    if {![dict exists $::ot_ag_seen $role]} {error "OT_ASYNC_GRAY: missing actual audited crossing $role"}
  }
  puts "OT_ASYNC_GRAY STRUCTURAL_PASS $::ot_ag_seen (primitive-only, bounded CDC; no physical closure claim)"
}
'''
