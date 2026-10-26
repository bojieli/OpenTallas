source /work/tap_balance.tcl
estimate_parasitics -placement
# FF hold gate runs before any timing repair; repair occurs at GRT.
detailed_placement
check_placement -verbose
estimate_parasitics -placement
