# DIE-QC-36 KITS BTAB QC-014 (A): planned repeaters (same net list as (B); names missing after the re-place are
# reported as MISS), then legalize + PG connect before global routing.
source /work/planned_rep.tcl
global_connect
detailed_placement
check_placement -verbose
