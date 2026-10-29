# ---- DIE-QC-36 KITS BTAB QC-014 (B) (12.17(3) pair with (A)): V1d run form from the V1c ROUTED DB without the V1d M4
# body adjustment; pre_b.tcl = clock FIXED + signal rip + b_strip.tcl (E-strip M5 obstruction + M3 corridor reserve
# 0.30); eco_b.tcl = V1d FF-only routed-RC ECO + planned repeaters (planned_rep.tcl) before repair_design.
override export PRE_GLOBAL_ROUTE_TCL = /work/pre_b.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/eco_b.tcl
