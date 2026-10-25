# QC 2026-10-25 (GEOM-REVIEW-3 [QC-PHYS-RP1-F57] cond a/b): routed RCX report, one corner (env MC TT|FF, ODB, SPEF, SDC):
# every tap mean/min/max and, per macro, clk vs W-side / E-side interface-reg min/mean, all from ONE arrival set
# (core_taps_post.tcl report-only on the loaded SPEF, no estimate, no correction table).
set C $::env(MC)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] {read_liberty $l}
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_[string tolower $C].lib
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set ::env(OT_CTAP_EST) loaded
set ::env(OT_CTAP_REPORT_ONLY) 1
set ::env(OT_CTAP_CORR) ""
source /work/core_taps_post.tcl
