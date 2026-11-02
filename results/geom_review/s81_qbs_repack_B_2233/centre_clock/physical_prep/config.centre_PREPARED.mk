# DISABLED candidate config; explicit ROOT physical-stage selection required.
include /work/config.mk
override export IO_CONSTRAINTS = /work/io_centre.tcl
override export MACRO_PLACEMENT_TCL = /work/macro_place_centre.tcl
# allFF native apply must complete against the new FP before invoking GPL.
# Replaces old face-only placement/release: every face is already in allFF targets.
override export PRE_GLOBAL_PLACE_TCL = /work/allFF_firm.tcl
override export PRE_DETAIL_PLACE_TCL = /work/allFF_firm.tcl
