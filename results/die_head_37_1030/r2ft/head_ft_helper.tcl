# HEAD local experiment: CA input rings interrupt ff_from_in's buffer-only walk.
# Resolve the already-existing canonical u_ft_<slot>_s<j> flop directly; distribute
# all k captures AFTER the ring, including the last capture at the output face.
set head_ft_cells 0
set head_ft_maxbit {}
foreach hbt [$ff_blk getBTerms] {
 if {![regexp {^(.+)_i\[([0-9]+)\]$} [$hbt getName] -> hs hb]} continue
 if {![dict exists $ff_ft $hs]} continue
 if {![dict exists $head_ft_maxbit $hs] || $hb>[dict get $head_ft_maxbit $hs]} {dict set head_ft_maxbit $hs $hb}
}
foreach hi [$ff_blk getInsts] {
 set hn [$hi getName]
 if {![regexp {^u_ft_(.+)_s([0-9]+)/((q\\?\[([0-9]+)\\?\])|eq)\$_[A-Z0-9_]+$} $hn -> hs hj hsig hq hb]} continue
 if {![dict exists $ff_ft $hs]} {error "HEAD_FT unknown slot $hs"}
 lassign [dict get $ff_ft $hs] hk hfin hfout hregs
 if {$hj >= $hk} {error "HEAD_FT stage outside table $hn"}
 set hin [format {%s_i[%d]} $hs [expr {$hb eq ""?[dict get $head_ft_maxbit $hs]:$hb}]]
 set hout [format {%s_o[%d]} $hs [expr {$hb eq ""?[dict get $head_ft_maxbit $hs]:$hb}]]
 set hbi [$ff_blk findBTerm $hin];set hbo [$ff_blk findBTerm $hout]
 if {$hbi eq "NULL" || $hbo eq "NULL"} {error "HEAD_FT missing bit port $hn $hin $hout"}
 set ha [$hbi getBBox];set hz [$hbo getBBox]
 set hp [ff_zroute [expr {([$ha xMin]+[$ha xMax])/2}] [expr {([$ha yMin]+[$ha yMax])/2}] [expr {([$hz xMin]+[$hz xMax])/2}] [expr {([$hz yMin]+[$hz yMax])/2}] $hfin $hfout]
 set hl 0
 for {set hi2 0} {$hi2+3 < [llength $hp]} {incr hi2 2} {set hl [expr {$hl+abs([lindex $hp $hi2]-[lindex $hp $hi2+2])+abs([lindex $hp $hi2+1]-[lindex $hp $hi2+3])}]}
 set hprogress [expr {$hk==4 ? 0.1725+$hj*(1.0-0.1725)/($hk-1) : double($hj+1)/$hk}]
 set hxy [ff_point_at $hp [expr {$hl*$hprogress}]]
 set hgot [ff_put_near $hi [lindex $hxy 0] [lindex $hxy 1]]
 if {$hgot eq ""} {error "HEAD_FT no legal site $hn"}
 puts $ff_out "$hn\thead_ft$hj\t[expr {[lindex $hgot 0]/double($ff_dbu)}]\t[expr {[lindex $hgot 1]/double($ff_dbu)}]\t$hin"
 incr head_ft_cells
}
if {$head_ft_cells==0} {error "HEAD_FT experiment matched zero sequential cells"}
puts "HEAD_FT_AFTER_LANDING placed $head_ft_cells existing flops; zero RTL/cycle changes"
