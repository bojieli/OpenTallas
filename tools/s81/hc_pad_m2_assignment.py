#!/usr/bin/env python3
"""Assign unique actual M2 signal tracks and emit exact OpenDB BPin placement.
ASAP7 M2 Y patterns are heterogeneous; place_pin remaps legal points incorrectly.
Keep paired return input/output ordering and all M4/M5 coordinates unchanged.
"""
import hashlib,json,sys
from pathlib import Path
from pin_files import tcl
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'physical/s81_die_pins/v18'
PROC='''# Actual M2 Y tracks: six signal patterns per .270um, rail pattern omitted.
# PPL place_pin corrupts Y indexing on this heterogeneous grid; use exact boxes.
proc ot_s81_hc_exact_m2 {name location size} {
 set block [ord::get_db_block]
 set tech [ord::get_db_tech]
 set dbu [$block getDbUnitsPerMicron]
 set ly [$tech findLayer M2]
 if {$ly eq "NULL"} {error "HC exact M2: missing layer"}
 set grid [$block findTrackGrid $ly]
 if {$grid eq "NULL"} {error "HC exact M2: missing tracks"}
 lassign $location x y
 lassign $size sx sy
 set cy [expr {round($y*$dbu)}]
 if {[lsearch -exact [$grid getGridY] $cy] < 0} {error "HC exact M2: $name center $cy off native tracks"}
 set x0 [expr {round(($x-$sx/2)*$dbu)}]
 set x1 [expr {round(($x+$sx/2)*$dbu)}]
 set y0 [expr {round(($y-$sy/2)*$dbu)}]
 set y1 [expr {round(($y+$sy/2)*$dbu)}]
 set die [$block getDieArea]
 if {$x0<[$die xMin] || $x1>[$die xMax] || $y0<[$die yMin] || $y1>[$die yMax]} {error "HC exact M2: $name rectangle outside die"}
 set bt [$block findBTerm $name]
 if {$bt eq "NULL"} {error "HC exact M2: missing port $name"}
 foreach bp [$bt getBPins] {odb::dbBPin_destroy $bp}
 set bp [odb::dbBPin_create $bt]
 odb::dbBox_create $bp $ly $x0 $y0 $x1 $y1
 $bp setPlacementStatus FIRM
}
'''
def main():
 p=OUT/'ot_s81_hc_pad_fv4fd5r2.json';r=json.loads(p.read_text());old_sha=hashlib.sha256(p.read_bytes()).hexdigest()
 a=r['ports']['r_i']['per_bit'];b=r['ports']['r_o']['per_bit'];assert len(a)==len(b)==2156
 tracks=[270*k+off for k in range(368) for off in (45,81,117,153,189,225) if 9<=270*k+off<=round(r['outline_um'][1]*1000)-9]
 changes=[];last=-1
 for i,(src,dst) in enumerate(zip(a,b)):
  assert src[1:]==dst[1:],(i,src,dst)
  if src[1]!='M2':continue
  target=round(src[2]*1000)
  available=[v for v in tracks if v>=last+36]
  v=min(available,key=lambda v:(abs(v-target),v));last=v
  if v!=target:changes.append(dict(bit=i,old_um=target/1000,new_um=v/1000))
  src[2]=dst[2]=v/1000
 centers=[round(v[2]*1000) for v in a if v[1]=='M2']
 assert len(centers)==len(set(centers))==1078
 assert min(y-x for x,y in zip(centers,centers[1:]))>=36
 r['m2_delivery']={'strategy':'exact_OpenDB_BPin_boxes','actual_y_signal_pattern_dbu1000':[45,81,117,153,189,225],'pattern_step_dbu1000':270,'rail_pattern_excluded_dbu1000':270,'same_bit_r_i_r_o_same_y':True,'physical_admission':False}
 p.write_text(json.dumps(r,separators=(',',':'))+'\n')
 import contextlib,io,re
 buf=io.StringIO()
 with contextlib.redirect_stdout(buf):tcl(p,scalar=('sk','srs'))
 lines=[]
 for l in buf.getvalue().splitlines():
  if '-layer M2 ' in l:
   m=re.fullmatch(r'place_pin -pin_name \{(.*)\} -layer M2 -location \{(.*)\} -pin_size \{(.*)\} -force_to_die_boundary',l);assert m,l
   l='ot_s81_hc_exact_m2 {%s} {%s} {%s}'%m.groups()
  lines.append(l)
 (p.with_suffix('.tcl')).write_text(PROC+'\n'.join(lines)+'\n')
 report=dict(source_previous_assignment_sha256=old_sha,return_bits=2156,M2_bits_per_face=1078,min_same_layer_center_um=.036,changed_paired_bits=changes,max_shift_um=max([abs(c['new_um']-c['old_um']) for c in changes] or [0]),physical_admission=False)
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
