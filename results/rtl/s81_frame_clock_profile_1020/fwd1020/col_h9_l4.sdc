# Opt-in external writer clocks; actual hard-view combinational arcs propagate forwarded phase.
# No false paths, multicycles, core-domain assignment or generated insertion is added.
if {[llength [get_ports -quiet {xk[0]}]] != 1} {error "missing external lane root"}
create_clock -name ot_frame_xk0 -period 833.333 [get_ports {xk[0]}]
if {[llength [get_ports -quiet {xk[1]}]] != 1} {error "missing external lane root"}
create_clock -name ot_frame_xk1 -period 833.333 [get_ports {xk[1]}]
if {[llength [get_ports -quiet {xk[2]}]] != 1} {error "missing external lane root"}
create_clock -name ot_frame_xk2 -period 833.333 [get_ports {xk[2]}]
if {[llength [get_ports -quiet {xk[3]}]] != 1} {error "missing external lane root"}
create_clock -name ot_frame_xk3 -period 833.333 [get_ports {xk[3]}]
