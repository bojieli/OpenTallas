# ROOT authorized ONE comb-only PLACE from actual anchored newFP. No CTS/GRT/route.
include /work/config.mk
override export IO_CONSTRAINTS = /work/io_centre.tcl
override export MACRO_PLACEMENT_TCL = /work/macro_place_centre.tcl
override export PRE_GLOBAL_PLACE_TCL = /work/allFF_guard_bay.tcl
override export PRE_DETAIL_PLACE_TCL = /work/allFF_guard_bay.tcl
