#!/usr/bin/env python3
"""Construct the complete native eight-sink clock leaf, not a parent closure.

All eight priced relay/pad cells are matched simultaneously to enclosed-contact
sites and checked against BOTH endpoint budgets. No global solver mutation.
"""
import gzip, hashlib, json, re, math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_native_relay_leaf_route_20261003'

def legal_PG_width():
    text=(BASE/'inputs/actual_tech.lef').read_text()
    layer=re.search(r'^LAYER M3\s*\n(.*?)^END M3\s*$',text,re.M|re.S)[1]
    widths=[float(v) for v in re.search(r'WIDTHTABLE\s+([0-9.\s]+);',layer)[1].split()]
    return min(v for v in widths if v>=.054), widths

def legal_PG_geometry():
    text=(BASE/'inputs/actual_tech.lef').read_text()
    layer=re.search(r'^LAYER M3\s*\n(.*?)^END M3\s*$',text,re.M|re.S)[1]
    track=float(re.search(r'PITCH\s+([0-9.]+)',layer)[1])
    width,_=legal_PG_width()
    step=round(math.ceil((2.7+width)/track)*track,9)
    return dict(track_um=track, center_step_um=step,
                spacing_um=round(step-width,9), pitch_um=round(2*step,9))

def construct(p):
    ts = p['tasks']
    if len(ts) != 8 or any(len(t['node_ids']) != 1 for t in ts):
        raise ValueError('Complete fixed eight-sink, one-relay-per-branch leaf required')
    if len({t['source_instance'] for t in ts}) != 1:
        raise ValueError('One actual native driver required')
    rc = np.array([p['RC_fF_per_um']['M8'], p['RC_fF_per_um']['M9']])
    sites = p['sites']
    a = np.array([[v['bbox_DBU'][0]+27, v['bbox_DBU'][1]+135] for v in sites])
    tree = cKDTree(a*rc)
    edges, ptr = [], [0]
    for t in ts:
        near = tree.query_ball_point(np.array(t['source_contact_DBU'])*rc,
                                    t['first_metal_budget_fF']*1000+1e-9, p=1)
        for j in sorted(near):
            last = np.sum(np.abs(a[j]+[321, 0]-t['sink_contact_DBU'])*rc)/1000
            if last <= t['relay_metal_budget_fF']+1e-12:
                edges.append(j)
        ptr.append(len(edges))
    graph = csr_matrix((np.ones(len(edges), dtype=np.int8), edges, ptr),
                       shape=(8, len(sites)))
    matching = maximum_bipartite_matching(graph, perm_type='column')
    if any(j < 0 for j in matching):
        raise ValueError('No complete eight-branch contact/site matching; no route admission')
    cells = [dict(c) for c in p['cells']]
    branches = []
    for i, j in enumerate(matching):
        t = ts[i]; v = dict(sites[int(j)])
        v['instance'] = f'relay_{i}'; v['role'] = 'existing_priced_relay_or_pad'
        cells.append(v)
        first = np.sum(np.abs(a[j]-t['source_contact_DBU'])*rc)/1000
        last = np.sum(np.abs(a[j]+[321, 0]-t['sink_contact_DBU'])*rc)/1000
        branches.append(dict(source=t['source_instance'], sink=t['destination'],
                             relay=v['instance'], first_C_fF=float(first),
                             last_C_fF=float(last), first_limit_fF=t['first_metal_budget_fF'],
                             last_limit_fF=t['relay_metal_budget_fF'],
                             source_contact=t['source_contact_DBU'], sink_contact=t['sink_contact_DBU']))
    for i, c in enumerate(cells):
        for d in cells[:i]:
            x,y,X,Y=c['bbox_DBU']; a0,b,A,B=d['bbox_DBU']
            if x<A and a0<X and y<B and b<Y:
                raise ValueError('Cell overlap')
    box=[min(c['bbox_DBU'][k] for c in cells) for k in (0,1)]
    origin=[box[0]//54*54-2160,box[1]//540*540-2160]
    end=[max(c['bbox_DBU'][k] for c in cells) for k in (2,3)]
    die=[0,0,((end[0]-origin[0]+2159)//54+1)*54/1000,
         ((end[1]-origin[1]+2159)//540+1)*540/1000]
    # The first/last follow-pin rail centres need complete via landings.
    # Preserve core row phases and all parent-relative positions, translate the
    # isolated fixture by one native row, and reserve a row outside each end.
    origin[1]-=270
    die[3]+=.54
    core=[0,.27,die[2],die[3]-.27]
    width,widths=legal_PG_width()
    pg=legal_PG_geometry()
    return dict(candidate=p['candidate'], scope=p['scope'], cells=cells,
                branches=branches, translated_origin_DBU=origin, die_um=die,
                core_um=core, PG_boundary_halo_um=.27,
                PG_boundary_fixture_area_delta_um2=.54*die[2],
                PG_boundary_fixture_not_full_parent_growth=True,
                fixed_native_cells=9, fixed_priced_relay_pad_cells=8,
                standard_cell_body_um2=8*1.08*.27+9*.378*.27,
                original_driver_fanout=8, relay_fanout=1,
                PG_M3_reserved_lanes_per_group=2, PG_M3_width_um=width,
                PG_M3_geometry=pg,
                PG_M3_legal_widths_um=widths,
                PG_M3_extra_metal_exclusion_um2=2*(width-.054)*die[3],
                tech_sha256=hashlib.sha256((BASE/'inputs/actual_tech.lef').read_bytes()).hexdigest(),
                clocks_per_cycle=1, arithmetic_MACs=0, memory_bytes_per_cycle=0,
                unchanged_global_buffer_count=68614, extra_architectural_cycles=0,
                source_parent_clock_waveform_qualified=False,
                source_reset_pins=0, reset_construction_covered=False,
                conditional_clock_leaf_route_admitted=True,
                full_parent_build_admitted=False, SSFF_qualified=False,
                component_inputs='ideal 20ps clock slew; parent waveform remains separate',
                PG='native alternating M1 rails plus ORFS physical PG; actual DRC/PG result required',
                source_sha256=hashlib.sha256((BASE/'inputs/leaf.json.gz').read_bytes()).hexdigest())

def emit(m):
    out=ROOT/'rtl/model_ready_ds_relay_20261003/ot_ds_native_relay_leaf.v'
    lines=['module ot_ds_native_relay_leaf(input clk, input [7:0] d, output [7:0] qn);',
           'wire source_y; wire [7:0] leaf_y;',
           '(* keep, dont_touch *) BUFx4_ASAP7_75t_R source_buf (.A(clk), .Y(source_y));']
    for i in range(8):
        lines += [f'(* keep, dont_touch *) BUFx4_ASAP7_75t_R relay_{i} (.A(source_y), .Y(leaf_y[{i}]));',
                  f'(* keep, dont_touch *) DFFHQNx1_ASAP7_75t_R sink_{i} (.CLK(leaf_y[{i}]), .D(d[{i}]), .QN(qn[{i}]));']
    lines += ['endmodule',
              '(* blackbox *) module BUFx4_ASAP7_75t_R(input A, output Y); endmodule',
              '(* blackbox *) module DFFHQNx1_ASAP7_75t_R(input CLK, input D, output QN); endmodule']
    out.write_text('\n'.join(lines)+'\n')
    ox,oy=m['translated_origin_DBU'];tcl=['source /src/physical/dsrom_native_relay_20261003/binding.tcl',
        'set aliases [ds_native_binding]', 'set block [ord::get_db_block]',
        'set scale [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])/1000.0}]']
    names={m['branches'][0]['source']:'source_buf'}
    names.update({b['sink']:f'sink_{i}' for i,b in enumerate(m['branches'])})
    for c in m['cells']:
        name=names.get(c['instance'],c['instance']); x,y=c['bbox_DBU'][:2]
        tcl += [f'set inst [dict get $aliases {name}]',
                f'if {{$inst == "NULL"}} {{error "Missing actual fixed instance {name}"}}',
                f'if {{[[$inst getMaster] getName] ne "{c["master"]}"}} {{error "Master changed {name}"}}',
                f'$inst setOrient {c["orientation"]}',
                f'$inst setLocation [expr {{round({x-ox}*$scale)}}] [expr {{round({y-oy}*$scale)}}]',
                '$inst setPlacementStatus LOCKED']
    tcl += ['set_dont_touch [get_cells *]', 'set_dont_touch [get_nets *]',
            'puts "DS_NATIVE_RELAY_FIXED_CENSUS_17"']
    (ROOT/'physical/dsrom_native_relay_20261003/place.tcl').write_text('\n'.join(tcl)+'\n')
    (ROOT/'physical/dsrom_native_relay_20261003/binding.tcl').write_text('''
proc ds_native_one {values label} {
  if {[llength $values] != 1} {error "Ambiguous/missing native $label"}
  return [lindex $values 0]
}
proc ds_native_pin {inst pin} {
  set it [$inst findITerm $pin]
  if {$it == "NULL"} {error "Missing native pin $pin"}
  return [$it getNet]
}
proc ds_native_binding {} {
  set block [ord::get_db_block]
  set clock [$block findBTerm clk]
  if {$clock == "NULL"} {error "Missing original clock port"}
  set cn [$clock getNet]; set sources {}
  foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] eq "BUFx4_ASAP7_75t_R" && [ds_native_pin $inst A] eq $cn} {lappend sources $inst}
  }
  set source [ds_native_one $sources clock_driver]
  set sy [ds_native_pin $source Y]
  set result [dict create source_buf $source]; set used [list $source]
  for {set i 0} {$i<8} {incr i} {
    set port [$block findBTerm [format {d[%d]} $i]]
    if {$port == "NULL"} {error "Missing original data port $i"}
    set dn [$port getNet];set sinks {}
    foreach inst [$block getInsts] {
      if {[[$inst getMaster] getName] eq "DFFHQNx1_ASAP7_75t_R" && [ds_native_pin $inst D] eq $dn} {lappend sinks $inst}
    }
    set sink [ds_native_one $sinks sink_$i]
    set sn [ds_native_pin $sink CLK]; set relays {}
    foreach inst [$block getInsts] {
      if {[[$inst getMaster] getName] eq "BUFx4_ASAP7_75t_R" && [ds_native_pin $inst A] eq $sy && [ds_native_pin $inst Y] eq $sn} {lappend relays $inst}
    }
    set relay [ds_native_one $relays relay_$i]
    dict set result sink_$i $sink;dict set result relay_$i $relay
    lappend used $sink $relay
  }
  if {[llength [lsort -unique $used]] != 17} {error "Native 17-cell ownership aliases"}
  return $result
}
'''.lstrip())
    # This component already contains its selected clock tree. Bypass automatic
    # CTS insertion, not timing checks: retain exact priced cells, propagate the
    # clock, validate placement, and produce the normal ORFS stage artifacts.
    (ROOT/'physical/dsrom_native_relay_20261003/fixed_cts.tcl').write_text('''
set_clock_transition 20 [get_clocks core_clk]
set_propagated_clock [all_clocks]
check_placement -verbose
estimate_parasitics -placement
report_metrics 4 "native fixed clock tree"
orfs_write_db $::env(RESULTS_DIR)/4_1_cts.odb
orfs_write_sdc $::env(RESULTS_DIR)/4_cts.sdc
exit
'''.lstrip())
    (ROOT/'physical/dsrom_native_relay_20261003/report.tcl').write_text('''
source /src/physical/dsrom_native_relay_20261003/binding.tcl
set aliases [ds_native_binding]
set block [ord::get_db_block]
set expected [concat source_buf {relay_0 relay_1 relay_2 relay_3 relay_4 relay_5 relay_6 relay_7 sink_0 sink_1 sink_2 sink_3 sink_4 sink_5 sink_6 sink_7}]
foreach n $expected {
  set inst [dict get $aliases $n]
  if {$inst == "NULL"} {error "Native clock instance lost: $n"}
  if {[$inst getPlacementStatus] ne "LOCKED"} {error "Native fixed instance moved: $n"}
}
report_clock_skew -setup
report_clock_skew -hold
report_check_types -max_slew -max_capacitance -max_fanout -violators
puts "DS_NATIVE_RELAY_ROUTED_CENSUS_17"
'''.lstrip())
    (ROOT/'physical/dsrom_native_relay_20261003/clock.sdc').write_text(
        'set_clock_transition 20 [get_clocks core_clk]\n')
    pg=m['PG_M3_geometry']
    (ROOT/'physical/dsrom_native_relay_20261003/pdn.tcl').write_text('''
foreach inst [[ord::get_db_block] getInsts] {$inst setDoNotTouch false}
add_global_connection -net VDD -inst_pattern .* -pin_pattern ^VDD$ -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern ^VSS$ -ground
global_connect
foreach inst [[ord::get_db_block] getInsts] {$inst setDoNotTouch true}
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name native_relay -voltage_domains CORE
add_pdn_stripe -grid native_relay -layer M1 -width 0.018 -followpins
'''.lstrip()+f'add_pdn_stripe -grid native_relay -layer M3 -width 0.090 -pitch {pg["pitch_um"]} -spacing {pg["spacing_um"]} -offset 0.54 -extend_to_boundary -allow_out_of_core\n'
        +'add_pdn_connect -grid native_relay -layers {M1 M3}\n')
    (BASE/'model.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')

if __name__ == '__main__':
    p=json.loads(gzip.decompress((BASE/'inputs/leaf.json.gz').read_bytes()))
    emit(construct(p))
