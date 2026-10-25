# QC-PHYS: per-tap / macro clock arrival on f56c 5_1_grt.odb in the measure.tcl basis (fresh GRT, rc_cal 0.8/0.9)
set C $::env(MC)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] {read_liberty $l}
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_[string tolower $C].lib
read_db /work/run/results/asap7/kq_qfd_dv_s8_crh_rp1_f56c/base/5_1_grt.odb
read_sdc /work/run/results/asap7/kq_qfd_dv_s8_crh_rp1_f56c/base/5_1_grt.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
source /work/rc_cal.tcl
set_global_routing_layer_adjustment * 0.3
set_routing_layers -signal M2-M5 -clock M2-M5
set_macro_extension 2
global_route -congestion_iterations 30
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
set ::env(OT_CTAP_REPORT_ONLY) 1
set ::env(OT_CTAP_EST) grt
source /work/core_taps_post.tcl
