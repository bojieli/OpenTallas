set ::env(OT_GATE_SIGNOFF_SDC) /src/physical/ref_tile/dsfd_gth_rw/signoff.sdc
# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain $plat/lib/NLDM/*RVT_SS*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    set w [string map {_tt.lib _ss.lib} $w]
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}
read_db /work/results/asap7/opentallas_dsfd_gth_rw_asap7_ref_gate/base/3_2_place_iop.odb
set ::env(RESULTS_DIR) /probe
set ::env(OT_IOHOLD_IN) 1
set ::env(OT_INHOLD_DRV) BUFx4f_ASAP7_75t_R
set ::env(OT_OFLOP_HOPS) 8
set ::env(OT_OFLOP_COLS) 4
set ::env(OT_OFLOP_ALLOW_NONE) 1
set ::env(S81_MIDPOINT_REPORT) /probe/assigned_anchor.tsv
source /probe/assigned.tcl
source /probe/leaf_iohold.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
source /probe/anchor.tcl
exit
