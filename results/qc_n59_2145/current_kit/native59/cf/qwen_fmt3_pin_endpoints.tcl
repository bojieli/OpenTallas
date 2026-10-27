# Opt-in audit after generated hops.tcl: bind literal BTerms to actual DFFs.
# Coordinates are micrometres in this strip's local frame, never legacy offsets.
set ot_ep_file [open /work/pin_endpoints.tsv w]
puts $ot_ep_file "port\tdirection\tinstance\tmaster\tpin_x_um\tpin_y_um\tcell_x_um\tcell_y_um\tplacement"
set ot_ep_count 0
set ot_ep_dbu [$::ot_blk getDbUnitsPerMicron]
foreach ot_ep_i [$::ot_blk getInsts] {
    if {![string match *DFF* [[$ot_ep_i getMaster] getName]]} { continue }
    foreach ot_ep_it [$ot_ep_i getITerms] {
        set ot_ep_dir ""
        if {[$ot_ep_it isOutputSignal]} {
            set ot_ep_dir q
        } elseif {[[$ot_ep_it getMTerm] getName] eq "D"} {
            set ot_ep_dir d
        }
        if {$ot_ep_dir eq ""} { continue }
        set ot_ep_bt [::ot_net_port [$ot_ep_it getNet] $ot_ep_dir]
        if {$ot_ep_bt eq ""} { continue }
        set ot_ep_bb [$ot_ep_bt getBBox]
        lassign [$ot_ep_i getLocation] ot_ep_x ot_ep_y
        puts $ot_ep_file [join [list [$ot_ep_bt getName] $ot_ep_dir [$ot_ep_i getName] \
            [[$ot_ep_i getMaster] getName] \
            [expr {([$ot_ep_bb xMin]+[$ot_ep_bb xMax])/2.0/$ot_ep_dbu}] \
            [expr {([$ot_ep_bb yMin]+[$ot_ep_bb yMax])/2.0/$ot_ep_dbu}] \
            [expr {$ot_ep_x/double($ot_ep_dbu)}] [expr {$ot_ep_y/double($ot_ep_dbu)}] \
            [$ot_ep_i getPlacementStatus]] "\t"]
        incr ot_ep_count
    }
}
close $ot_ep_file
if {$ot_ep_count == 0} { error "FMT3 pin endpoint audit found no registered boundary" }
puts "FMT3 pin endpoint audit: $ot_ep_count actual port/register bindings"
