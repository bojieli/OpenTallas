#!/usr/bin/env python3
"""Generate read-only TT/FF probes for one pinned CFIFO output-drive candidate.

This is a sizing experiment on the preserved routed parasitics. It does not
write a changed database and cannot establish routed closure or legal placement.
The probe prints the area model before swapping two cells in memory. Numerical
RTL, pipeline cycles, bandwidth, ports, fanout and external timing are unchanged.
"""
import argparse
from pathlib import Path

PROBE = r'''
set ot_block [ord::get_db_block]
set ot_db [ord::get_db]
set ot_area 0.0
foreach ot_i [$ot_block getInsts] {
    set ot_m [$ot_i getMaster]
    set ot_area [expr {$ot_area + double([$ot_m getWidth])*[$ot_m getHeight]}]
}
set ot_changes {}
set ot_delta 0.0
foreach {ot_name ot_old ot_new} {
    _092097_ INVx3_ASAP7_75t_R INVx6_ASAP7_75t_R
    output730 BUFx3_ASAP7_75t_R BUFx6_ASAP7_75t_R
} {
    set ot_i [$ot_block findInst $ot_name]
    set ot_m [$ot_db findMaster $ot_new]
    if {$ot_i eq "NULL" || $ot_i eq "" || $ot_m eq "NULL" || $ot_m eq ""} {
        error "missing pinned instance or candidate master: $ot_name $ot_new"
    }
    set ot_before [$ot_i getMaster]
    if {[$ot_before getName] ne $ot_old} {error "pinned master mismatch: $ot_name"}
    set ot_a0 [expr {double([$ot_before getWidth])*[$ot_before getHeight]}]
    set ot_a1 [expr {double([$ot_m getWidth])*[$ot_m getHeight]}]
    set ot_delta [expr {$ot_delta + $ot_a1 - $ot_a0}]
    lappend ot_changes $ot_i $ot_m
    puts "OT_MODEL_CELL $ot_name $ot_old $ot_new old_area_dbu2=$ot_a0 new_area_dbu2=$ot_a1"
}
puts "OT_MODEL total_area_dbu2=$ot_area delta_area_dbu2=$ot_delta relative_delta=[expr {$ot_delta/$ot_area}] changed_instances=2 replicas=1 added_cycles=0 added_bits_per_cycle=0 added_ports=0 added_fanout=0 added_mac_per_cycle=0"
puts "OT_BASE_SETUP [sta::worst_slack_cmd max]"
puts "OT_BASE_HOLD [sta::worst_slack_cmd min]"
foreach {ot_i ot_m} $ot_changes {$ot_i swapMaster $ot_m}
puts "OT_PROBE_SETUP [sta::worst_slack_cmd max]"
puts "OT_PROBE_HOLD [sta::worst_slack_cmd min]"
report_checks -path_delay max -to [all_outputs] -group_path_count 2 -format full_clock_expanded
report_checks -path_delay min -to [all_outputs] -group_path_count 2 -format full_clock_expanded
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundle", type=Path)
    a = p.parse_args()
    for compatibility, corner in (("ss", "tt"), ("ff", "ff")):
        source = a.bundle / "meas" / f"meas_{compatibility}.tcl"
        tcl = source.read_text()
        marker = f'puts "OT_CORNER {corner}"'
        if tcl.count(marker) != 1:
            raise ValueError(f"wrong actual corner in {source}")
        tcl = tcl.replace(marker, PROBE + "\n" + marker)
        (a.bundle / "meas" / f"rd_drive_{corner}.tcl").write_text(tcl)


if __name__ == "__main__":
    main()
