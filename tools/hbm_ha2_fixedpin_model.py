#!/usr/bin/env python3
"""Full-shape h2 physical-only pin successor, before implementation."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def model():
    pins=json.loads((ROOT/'results/physical/hbm_ha2_pin_binding_20261007/h2_placed_signal_pins.json').read_text())['pins']
    names={p['name'] for p in pins}
    groups=[]; mapped=[]
    for j,start in enumerate((160.044,580.044)):
        group=[f'h_v[{j}]',f'h_r[{j}]']+[f'h_d[{j*544+i}]' for i in range(544)]
        assert set(group)<=names
        for i,n in enumerate(group): mapped.append(dict(name=n,layer='M5',x_um=round(start+i*.144,6),y_um=.042,face='S'))
        groups.append(dict(injector=j,pins=len(group),start_um=start,end_um=round(start+545*.144,6),span_um=545*.144,
          neighbor_station_reserved_um=[start-5,-100,start+545*.144+5,0],reservation_is_not_implemented_station=True))
    rest=sorted(names-{p['name'] for p in mapped})
    # All remaining pins use opposite/side faces, leaving entire south edge clear.
    cuts=(2304,1316,len(rest)-3620); pos=0
    for face,count in zip(('N','E','W'),cuts):
        assert count*.144<(840 if face=='N' else 480)-20
        for i,n in enumerate(rest[pos:pos+count]):
            v=round(10.044+i*.144,6)
            mapped.append(dict(name=n,layer='M5' if face=='N' else 'M4',x_um=v if face=='N' else (839.958 if face=='E' else .042),y_um=479.958 if face=='N' else v,face=face))
        pos+=count
    assert len(mapped)==len(names)==6028
    assert len({(p['x_um'],p['y_um']) for p in mapped})==6028
    return dict(status='candidate-not-adopted',die_um=[840,480],area_um2=403200,area_delta_um2=0,rtl_cycles_added=0,
      compute_change=0,memory_port_change=0,replicas=1,new_mux_demux_or_fanout=0,
      injector_bytes_per_accepted_fast_cycle=68,injector_core_rows_per_fast_cycle=.5,
      boundary_bits=1092,track_pitch_um=.048,pin_pitch_tracks=3,pin_pitch_um=.144,
      groups=groups,remaining_pins=len(rest),remaining_face_counts=dict(zip(('N','E','W'),cuts)),
      single_user_latency_delta_cycles=0,station_credit_latency='owned separately by actual TU truecredit stream; not waived',
      qualification='Fixed-pin successor only. Real receiver station, extracted full-shape SS/FF>=15ps DRC0 and parent clock/interface binding pending.',pins=mapped)
def emit():
    m=model(); out=ROOT/'results/uarch/hbm_ha2_fixedpins_20261007';out.mkdir(parents=True,exist_ok=True)
    (out/'model.json').write_text(json.dumps(m,indent=2)+'\n')
    p=ROOT/'physical/hbm_ha2_fixedpins_20261007';p.mkdir(parents=True,exist_ok=True)
    t=['# Model-generated full-shape h2 fixed signal pins. Pin centers use the native .048um track lattice.', 'set expected_pins 6028']
    t += ['place_pin -pin_name {%s} -layer %s -location {%.6f %.6f}'%(v['name'],v['layer'],v['x_um'],v['y_um']) for v in m['pins']]
    (p/'pins.tcl').write_text('\n'.join(t)+'\n')
    a=['# Read-only audit after read_db; checks real routed pin boxes against candidate binding.',
       'set b [ord::get_db_block]', 'set dbu [$b getDbUnitsPerMicron]', 'set checked 0']
    a.append('set expected {')
    a += ['  {{%s} %s %.6f}' % (v['name'],v['face'],v['x_um'] if v['face'] in ('N','S') else v['y_um']) for v in m['pins']]
    a.append('}')
    a.extend(r"""
foreach row $expected {
 lassign $row name face coord
 set term [$b findBTerm $name]
 if {$term eq "NULL"} {error "missing fixed pin $name"}
 set match 0
 foreach pin [$term getBPins] {
  foreach box [$pin getBoxes] {
   set xl [expr {[$box xMin]/double($dbu)}]
   set xh [expr {[$box xMax]/double($dbu)}]
   set yl [expr {[$box yMin]/double($dbu)}]
   set yh [expr {[$box yMax]/double($dbu)}]
   if {$face eq "N" || $face eq "S"} {
    set got [expr {($xl+$xh)/2.}]
    set edge [expr {$face eq "N" ? abs($yh-480.) : abs($yl)}]
   } else {
    set got [expr {($yl+$yh)/2.}]
    set edge [expr {$face eq "E" ? abs($xh-840.) : abs($xl)}]
   }
   set layer [[$box getTechLayer] getName]
   set expected_layer [expr {$face eq "N" || $face eq "S" ? "M5" : "M4"}]
   set dx [expr {$xh-$xl}]
   set dy [expr {$yh-$yl}]
   set width [expr {$expected_layer eq "M5" ? $dx : $dy}]
   set depth [expr {$expected_layer eq "M5" ? $dy : $dx}]
   set track [expr {($got-0.012)/0.048}]
   set track_error [expr {abs($track-round($track))}]
   if {abs($got-$coord)<0.0011 && $edge<0.0011 && $layer eq $expected_layer && abs($width-0.024)<0.0011 && abs($depth-0.084)<0.0011 && $track_error<0.0011} {set match 1}
  }
 }
 if {!$match} {error "fixed pin moved or wrong face: $name $face $coord"}
 incr checked
}
if {$checked!=6028} {error "wrong pin count $checked"}
puts "HA2_FIXED_PIN_CHECK_PASS count=$checked"
""".strip().splitlines())
    (p/'check_pins.tcl').write_text('\n'.join(a)+'\n')

if __name__=='__main__':emit()
