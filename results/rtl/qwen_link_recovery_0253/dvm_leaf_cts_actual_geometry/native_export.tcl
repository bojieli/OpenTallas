read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_TT_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_TT_*] {if {![string match *FAKE* $l]} {read_liberty $l}}
read_db /work/routes/gate/work/orfs/results/asap7/opentallas_ot_qfd_xs_leaf_asap7_ref_gate/base/4_1_cts.odb
read_sdc /work/routes/gate/work/orfs/results/asap7/opentallas_ot_qfd_xs_leaf_asap7_ref_gate/base/4_cts.sdc
set ::ot_ce_corner tt
read_sdc /work/src/physical/ref_tile/qfd_xs_leaf_m6_138/signoff.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
write_timing_model -library_name ot_qfd_xs_leaf_tt /out/ot_qfd_xs_leaf_tt.lib
write_def /out/actual_cts.def
write_abstract_lef /out/actual_cts.lef
exit
