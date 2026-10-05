proc ot_capture {tag} {
    orfs_write_db /diag/${tag}.odb
    orfs_write_sdc /diag/${tag}.sdc
    set block [ord::get_db_block]
    set f [open /diag/${tag}_instances.tsv w]
    puts $f "name\tmaster\tx\ty"
    foreach inst [$block getInsts] {
        puts $f "[$inst getName]\t[[$inst getMaster] getName]\t[$inst getLocation]"
    }
    close $f
    foreach corner {WC BC} {
        foreach delay {min max} {
            if {[catch {
                report_checks -corner $corner -path_delay $delay -format full_clock_expanded -group_path_count 88570 -endpoint_path_count 1 -slack_max 0 -digits 6 > /diag/${tag}_${corner}_${delay}.rpt
            } msg]} {puts "CAPTURE_REPORT_ERROR $tag $corner $delay $msg"}
        }
    }
}
