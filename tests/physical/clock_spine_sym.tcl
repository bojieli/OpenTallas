# Regression for the symmetric, insertion-aware clock-spine topology (OT_SPINE_SYM=1): bbox-centre nodes, short levels
# collapsed, a leaf with its own insertion taps the tree early enough to arrive with the latest flop leaf.
source physical/common_flow/clock_spine.tcl
proc check {condition message} { if {![uplevel 1 [list expr $condition]]} { error $message } }
proc ot_sp_free {x y} { return [list $x $y] }
set ::ot_sp_dbu 1000; set ::ot_sp_nn 0
set ::ot_sp_pos [dict create]; set ::ot_sp_cnt [dict create]; set ::ot_sp_kids [dict create]
# 16 flop leaves on a 4 x 4 grid, 200 um pitch, in a 600 x 600 um block; two clustered leaves 5 um apart (collapse)
set ids {}; set k 0
for {set i 0} {$i < 4} {incr i} { for {set j 0} {$j < 4} {incr j} {
  set id "L[incr k]"; dict set ::ot_sp_pos $id [list [expr {$i * 200000}] [expr {$j * 200000}]]; dict set ::ot_sp_cnt $id 4; lappend ids $id } }
# one slow child (500 ps inside) far from the root, one fast child (100 ps) in the far corner
dict set ::ot_sp_pos M1 {300000 300000}; dict set ::ot_sp_cnt M1 1
dict set ::ot_sp_pos M2 {600000 600000}; dict set ::ot_sp_cnt M2 1
set lins [dict create M1 500.0 M2 100.0]
set top [ot_sp_sym_build [concat $ids {M1 M2}] $lins 0 300000]
# symmetry: the first tree node below the top is the centre of the flop leaves' bounding box
set sub [lindex [dict get $::ot_sp_kids $top] 0]
check {[dict get $::ot_sp_pos $sub] eq {300000 300000}} "root node at [dict get $::ot_sp_pos $sub], expected the bbox centre"
# every flop leaf has the same estimated arrival (equal path length by construction on a regular grid)
set ts {}; foreach i $ids { lappend ts [dict get $::ot_sp_est_t $i] }
check {[tcl::mathfunc::max {*}$ts] - [tcl::mathfunc::min {*}$ts] < 1e-6} "flop leaves not equidistant: $ts"
set latest [tcl::mathfunc::max {*}$ts]
# the slow child cannot meet the flop leaves' arrival from any tap: it sits on its earliest tap, the top buffer
check {[lsearch -exact [dict get $::ot_sp_kids $top] M1] >= 0} "slow child not on the top buffer: $::ot_sp_kids"
# the fast child taps a tree node (not the top) and arrives no later than the latest flop leaf
check {[lsearch -exact [dict get $::ot_sp_kids $top] M2] < 0} "fast child wastes the top tap"
check {[dict get $::ot_sp_est_t M2] + 100.0 <= $latest} "fast child late: [dict get $::ot_sp_est_t M2] + 100 > $latest"
# every leaf is reachable exactly once
set seen {}
proc walk {n} { if {[dict exists $::ot_sp_kids $n]} { foreach c [dict get $::ot_sp_kids $n] { walk $c } } else { lappend ::seen $n } }
walk $top
check {[lsort $seen] eq [lsort [concat $ids {M1 M2}]]} "leaf set changed: $seen"
# collapse: a node within OT_SPINE_SYM_MERGE of its parent is spliced out; negative control: with merge 0 it is kept
set ::ot_sp_pos [dict create T {0 0} A {10000 0} l0 {100000 0} l1 {100000 50000} l2 {0 100000}]
set ::ot_sp_cnt [dict create T 3 A 2 l0 1 l1 1 l2 1]
set ::ot_sp_kids [dict create T {A l2} A {l0 l1}]
ot_sp_collapse T 0 8
check {[dict exists $::ot_sp_kids A]} "merge 0 must keep every node"
ot_sp_collapse T 40000 8
check {![dict exists $::ot_sp_kids A] && [lsort [dict get $::ot_sp_kids T]] eq {l0 l1 l2}} "short level not collapsed: $::ot_sp_kids"
puts "clock_spine_sym PASS: bbox-centre tree, equal flop-leaf estimates, slow child on the top tap, fast child on a tree tap, collapse"
