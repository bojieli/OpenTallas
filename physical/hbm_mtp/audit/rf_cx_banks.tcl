# Mandatory post-synthesis, before global placement. Actual OpenDB instances
# and library MTerm directions establish independent timing-control groups.
if {![info exists ::env(OT_RF_CX_AUDITOR)]} {error "OT_RF_CX_AUDITOR missing"}
if {![info exists ::env(OT_RF_CX_AUDIT_DIR)]} {error "OT_RF_CX_AUDIT_DIR missing"}
file mkdir $::env(OT_RF_CX_AUDIT_DIR)
set graph [file join $::env(OT_RF_CX_AUDIT_DIR) mapped_bank_graph.tsv]
set report [file join $::env(OT_RF_CX_AUDIT_DIR) mapped_bank_audit.json]
set block [ord::get_db_block]
if {$block == "NULL"} {error "RF bank audit requires loaded mapped database"}
set fp [open $graph w]
foreach inst [$block getInsts] {
    set master [$inst getMaster]
    foreach iterm [$inst getITerms] {
        set net [$iterm getNet]
        if {$net == "NULL"} {continue}
        set mt [$iterm getMTerm]
        # Supply pins do not participate in data/control timing cones.
        set sigtype [$mt getSigType]
        if {$sigtype == "POWER" || $sigtype == "GROUND"} {continue}
        puts $fp [join [list [$inst getName] [$master getName] [$mt getName] [$mt getIoType] [$net getName]] "\t"]
    }
}
close $fp
if {[catch {exec python3 $::env(OT_RF_CX_AUDITOR) $graph $report 2>@1} message]} {
    puts stderr $message
    error "RF -cx mapped bank topology audit FAILED; preserve graph and report"
}
puts $message
