set P /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach l [glob $P/asap7sc7p5t_*RVT_TT_*.lib*] {
  if {![string match *FAKE* $l]} { read_liberty $l }
}
read_liberty /work/macros/ot_sram_1r1w_32x128_m1_tt.lib
set R [glob /work/run/results/asap7/*/base]
read_db $R/3_place.odb
read_sdc $R/3_place.sdc
set ::env(OT_PV_CONTROL_REGIONS) 4
set ::env(RESULTS_DIR) /work/pre_review
source /work/pv_pair_taps.tcl
