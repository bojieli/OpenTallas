read_db /w/routes/hdie_pc_ctrl_cfg_cfg_h4_pcidqq_28e23d021/work/orfs/results/asap7/opentallas_ot_hbm_svc_pc_ctrl_leaf_cfg_asap7_ref_hdie_pc_ctrl_cfg_cfg_h4_pcidqq_28e23d021/base/5_1_grt-failed.odb
set ::env(MAX_ROUTING_LAYER) M5
set ::env(OT_MEG_MODE) remove
source /src/physical/common_flow/macro_edge_via_guard.tcl
set ::env(OT_MEG_DEPTH_UM) 48
set ::env(OT_MEG_MODE) add
source /src/physical/common_flow/macro_edge_via_guard.tcl
set_routing_layers -signal M2-M6
set_routing_layers -clock M2-M6
set_global_routing_layer_adjustment M6 1.0
set_wire_rc -signal -layer M3
set_wire_rc -clock -layer M4
global_route -congestion_iterations 30 -congestion_report_file /out/congestion.rpt -verbose -allow_congestion
write_db /out/h6_no_overflight.odb
