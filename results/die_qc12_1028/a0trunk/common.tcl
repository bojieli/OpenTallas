# DIE-QC-12 A0 trunk: libs for corner $::env(CORNER) (TT|FF) + parent placement-RC setup
set C $::env(CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] {read_liberty $f}
foreach f [glob /p/macros/*_${c}.lib] {read_liberty $f}
