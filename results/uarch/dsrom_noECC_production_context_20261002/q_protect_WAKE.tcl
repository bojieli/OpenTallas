# Eight source-owned cells in emitted Verilog; preserve through physical optimization.
set w0 [get_cells -hierarchical -regexp {^_278359_$}]
if {[llength $w0] != 1} {error "Missing unique mapped WAKE cell 0"}
set_dont_touch $w0
set w1 [get_cells -hierarchical -regexp {^_278360_$}]
if {[llength $w1] != 1} {error "Missing unique mapped WAKE cell 1"}
set_dont_touch $w1
set w2 [get_cells -hierarchical -regexp {^_278361_$}]
if {[llength $w2] != 1} {error "Missing unique mapped WAKE cell 2"}
set_dont_touch $w2
set w3 [get_cells -hierarchical -regexp {^_278362_$}]
if {[llength $w3] != 1} {error "Missing unique mapped WAKE cell 3"}
set_dont_touch $w3
set w4 [get_cells -hierarchical -regexp {^_278363_$}]
if {[llength $w4] != 1} {error "Missing unique mapped WAKE cell 4"}
set_dont_touch $w4
set w5 [get_cells -hierarchical -regexp {^_278364_$}]
if {[llength $w5] != 1} {error "Missing unique mapped WAKE cell 5"}
set_dont_touch $w5
set w6 [get_cells -hierarchical -regexp {^_278365_$}]
if {[llength $w6] != 1} {error "Missing unique mapped WAKE cell 6"}
set_dont_touch $w6
set w7 [get_cells -hierarchical -regexp {^_278366_$}]
if {[llength $w7] != 1} {error "Missing unique mapped WAKE cell 7"}
set_dont_touch $w7
