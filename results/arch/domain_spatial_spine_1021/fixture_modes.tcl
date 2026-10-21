# This runner uses real loaded Liberty, real placed databases and real clock
# sources. No mock STA/Liberty getter or synthetic accepted clock is installed.
source /w/load.tcl
set mode $::env(DSP_FIXTURE_MODE)
if {$mode eq "collector"} {puts "FIXTURE_COLLECTOR PASS"; exit}

proc must_reject {label body} {
    if {![catch {uplevel 1 $body} message]} {error "CAUSAL_ESCAPE $label"}
    if {![string match "OT_DOMAIN_SPINE*" $message]} {
        error "NON_ADMISSION_ERROR $label $message"
    }
    puts "CAUSAL_CAUGHT $label $message"
}

if {$mode eq "causals"} {
    set saved $::ot_dsp_roots
    set ::ot_dsp_roots [lrange $saved 0 end-1]
    must_reject missing_root {ot_dsp::admit}
    set ::ot_dsp_roots [concat $saved [list [lindex $saved 0]]]
    must_reject duplicate_root {ot_dsp::admit}
    set ::ot_dsp_roots [lreplace $saved end end impossible_source_root]
    must_reject root_mismatch {ot_dsp::admit}
    set ::ot_dsp_roots $saved
    set block [ord::get_db_block]
    set b0 [$block findBTerm [lindex $saved 0]]
    set b1 [$block findBTerm [lindex $saved 1]]
    set n0 [$b0 getNet]; set n1 [$b1 getNet]
    $b1 connect $n0
    must_reject actual_shared_root_net {ot_dsp::admit}
    $b1 connect $n1
    # Choose a genuine connected clock contact using its actual Liberty role,
    # not a guessed name, a dummy sink, or a fabricated is_clock return value.
    set selected ""
    foreach it [$n0 getITerms] {
        if {![$it isInputSignal]} continue
        set inst [$it getInst]
        set m [[$inst getMaster] getName]
        set pn [[$it getMTerm] getName]
        foreach cell [get_lib_cells -quiet "*/$m"] {
            foreach lp [get_lib_pins -quiet -of_objects $cell] {
                if {[get_property $lp name] eq $pn && [get_property $lp is_clock]} {set selected $it; break}
            }
            if {$selected ne ""} break
        }
        if {$selected ne ""} break
    }
    if {$selected eq ""} {error "fixture has no real Liberty clock contact to mutate"}
    set previous [$selected getNet]
    set foreign [odb::dbNet_create $block dsp_causal_unowned_clock]
    $selected connect $foreign
    must_reject actual_unowned_clock_contact {ot_dsp::admit}
    $selected connect $previous
    odb::dbNet_destroy $foreign
    ot_dsp::admit
    puts "FIXTURE_CAUSALS PASS restored_real_design"
    exit
}

if {$mode ne "engine"} {error "unsupported fixture mode $mode"}
# The production generated wrapper retains clock_entries/raw/landed checks and
# the current FRAME timing basis around the unchanged canonical aab engine.
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
clock_tree_synthesis
estimate_parasitics -placement
if {![info exists ::ot_sp_ports] || [lsort $::ot_sp_ports] ne [lsort $::ot_dsp_roots]} {
    error "canonical engine did not build exactly the existing roots"
}
check_placement -verbose
write_db /w/engine.odb
write_sdc /w/engine.sdc
puts "FIXTURE_ENGINE_EXECUTED real_spines=[llength $::ot_sp_ports] cells=[llength $::ot_sp_all_insts]"
puts "NOT_A_GATE_VERDICT: ROOT must judge actual reach/spread/STA and paired evidence"
