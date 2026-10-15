# Regression for subtree-common clock-spine padding (OT_SPINE_TREE_PAD=1): the delay a subtree needs in common is inserted
# once at the subtree node; every leaf still receives exactly its own need along its root path; the latest leaf gets none.
source physical/common_flow/clock_spine.tcl
proc check {condition message} { if {![uplevel 1 [list expr $condition]]} { error $message } }
# tree: R -> (A -> (l0 l1 l2 via B)), (C -> (l3 l4));  A = {l0, B}, B = {l1, l2}
set ::ot_sp_kids [dict create R {A C} A {l0 B} B {l1 l2} C {l3 l4}]
set ::parent [dict create A R C R l0 A B A l1 B l2 B l3 C l4 C]
set ::pads [dict create]
proc ot_sp_pad {n c} { dict incr ::pads $n $c }
proc path_sum {n} { set s 0; while {1} { if {[dict exists $::pads $n]} { incr s [dict get $::pads $n] }; if {![dict exists $::parent $n]} break; set n [dict get $::parent $n] }; return $s }
set need [dict create l0 5 l1 7 l2 9 l3 0 l4 2]
set np [ot_sp_tree_pad R $need]
dict for {l c} $need { check {[path_sum $l] == $c} "leaf $l got [path_sum $l] pads, needs $c" }
check {![dict exists $::pads R]} "the root must not be padded while one leaf needs none"
check {[dict get $::pads A] == 5 && [dict get $::pads B] == 2 && [dict get $::pads l2] == 2 && [dict get $::pads l4] == 2} "common delay not hoisted: $::pads"
check {![dict exists $::pads l0] && ![dict exists $::pads l1] && ![dict exists $::pads C]} "pads on nodes that need none: $::pads"
check {$np == 11} "pad cells $np, expected 11 (per-leaf padding would use 23)"
# negative control: per-leaf padding of the same need uses 23 cells
set ::pads [dict create]; dict for {l c} $need { if {$c > 0} { ot_sp_pad $l $c } }
set s 0; dict for {n c} $::pads { incr s $c }; check {$s == 23} "per-leaf reference count $s"
puts "clock_spine_tree_pad PASS: 11 pad cells serve needs 5/7/9/0/2 (per-leaf 23)"
