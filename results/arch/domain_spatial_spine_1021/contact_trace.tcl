# Observation only: record the production validator's actual inputs before it
# decides admission. No clock roles, design objects or acceptance rules change.
proc dsp_contact_trace {command operation} {
    lassign $command validator roots rootnets contacts nonclock
    set netroots {}
    dict for {root net} $rootnets {dict set netroots $net $root}
    set block [ord::get_db_block]
    set file [open /w/actual_contacts.tsv w]
    puts $file "terminal\troot\tmaster\tpin\tactual_net"
    foreach contact $contacts {
        lassign $contact terminal net
        set slash [string last / $terminal]
        set name [string range $terminal 0 [expr {$slash-1}]]
        set pin [string range $terminal [expr {$slash+1}] end]
        set inst [$block findInst $name]
        set master [expr {$inst eq "NULL" ? "MISSING" : [[$inst getMaster] getName]}]
        set root [expr {[dict exists $netroots $net] ? [dict get $netroots $net] : "UNOWNED"}]
        set netname [expr {$net in {NULL {}} ? "DISCONNECTED" : [$net getName]}]
        puts $file "$terminal\t$root\t$master\t$pin\t$netname"
    }
    close $file
    puts "ACTUAL_CONTACT_TRACE rows=[llength $contacts] nonclock=[llength $nonclock]"
}
trace add execution ot_dsp::validate enter dsp_contact_trace
