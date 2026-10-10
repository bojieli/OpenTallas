# Read-only preflight of primitive MY legality in a retained hard-block ODB.
# This does not qualify route/power/track reflection or change an exported LEF.
read_db $::env(OT_AUDIT_ODB)
set block [ord::get_db_block]
set seen [dict create]
foreach inst [$block getInsts] {
    set master [$inst getMaster]
    set name [$master getName]
    dict incr seen $name
}
set bad 0
set total 0
foreach name [lsort [dict keys $seen]] {
    set master [[ord::get_db] findMaster $name]
    if {[catch {$master getSymmetryY} allowed]} {
        puts "UNPROVEN $name [dict get $seen $name] $allowed"
        incr bad
    } else {
        puts "MASTER $name count=[dict get $seen $name] symmetryY=$allowed"
        if {!$allowed} {incr bad}
    }
    incr total [dict get $seen $name]
}
puts "PRIMITIVE_MY_PREFLIGHT instances=$total unique=[dict size $seen] unproven_or_disallowed=$bad"
puts "SCOPE primitive orientation only; no route/track/power/signoff or abstract symmetry qualification"
if {$bad} {exit 3}
exit 0
