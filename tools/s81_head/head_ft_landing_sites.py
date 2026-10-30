#!/usr/bin/env python3
"""Kit-only HEAD placement experiment: place existing FT stages after CA input rings.
No RTL, plan, latency or clock changes. Intended only for a fresh kit copy.
"""
import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('kit',type=Path);a=p.parse_args()
f=a.kit/'face_flops.tcl';s=f.read_text();marker='close $ff_out\nputs "OT_FACE_FLOPS'
assert s.count(marker)==1
patch=r'''
# HEAD local experiment: CA input rings interrupt ff_from_in's buffer-only walk.
# Resolve the already-existing canonical u_ft_<slot>_s<j> flop directly; distribute
# all k captures AFTER the ring, including the last capture at the output face.
set head_ft_cells 0
foreach hi [$ff_blk getInsts] {
 set hn [$hi getName]
 if {![regexp {^u_ft_(.+)_s([0-9]+)/((q\\?\[([0-9]+)\\?\])|eq)\$_[A-Z0-9_]+$} $hn -> hs hj hsig hq hb]} continue
 if {![dict exists $ff_ft $hs]} {error "HEAD_FT unknown slot $hs"}
 lassign [dict get $ff_ft $hs] hk hfin hfout hregs
 if {$hj >= $hk} {error "HEAD_FT stage outside table $hn"}
 set hin [format {%s_i[%d]} $hs [expr {$hb eq ""?64:$hb}]]
 set hout [format {%s_o[%d]} $hs [expr {$hb eq ""?64:$hb}]]
 set hbi [$ff_blk findBTerm $hin];set hbo [$ff_blk findBTerm $hout]
 if {$hbi eq "NULL" || $hbo eq "NULL"} {error "HEAD_FT missing bit port $hn $hin $hout"}
 set ha [$hbi getBBox];set hz [$hbo getBBox]
 set hp [ff_zroute [expr {([$ha xMin]+[$ha xMax])/2}] [expr {([$ha yMin]+[$ha yMax])/2}] [expr {([$hz xMin]+[$hz xMax])/2}] [expr {([$hz yMin]+[$hz yMax])/2}] $hfin $hfout]
 set hl 0
 for {set hi2 0} {$hi2+3 < [llength $hp]} {incr hi2 2} {set hl [expr {$hl+abs([lindex $hp $hi2]-[lindex $hp $hi2+2])+abs([lindex $hp $hi2+1]-[lindex $hp $hi2+3])}]}
 set hxy [ff_point_at $hp [expr {$hl*double($hj+1)/$hk}]]
 set hgot [ff_put_near $hi [lindex $hxy 0] [lindex $hxy 1]]
 if {$hgot eq ""} {error "HEAD_FT no legal site $hn"}
 puts $ff_out "$hn\thead_ft$hj\t[expr {[lindex $hgot 0]/double($ff_dbu)}]\t[expr {[lindex $hgot 1]/double($ff_dbu)}]\t$hin"
 incr head_ft_cells
}
if {$head_ft_cells==0} {error "HEAD_FT experiment matched zero sequential cells"}
puts "HEAD_FT_AFTER_LANDING placed $head_ft_cells existing flops; zero RTL/cycle changes"
'''
s=s.replace(marker,patch+'\n'+marker);f.write_text(s)
print(f)
