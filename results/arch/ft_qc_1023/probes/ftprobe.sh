#!/bin/bash
# FT-QC 10-23: read-only what-if GRT probe of the r50 Qwen compute floorplan (congestion_iterations 0, NO-PDN, clocks special,
# recipe b = M4-M5 0.30 / M6-M8 0.10 / M9 0.05, coarse 4.8 um tiles; same as SQC-QDIE5 grt_probe_np.sh 'bs').
# usage: ODB OUT VARIANT   VARIANT: p4 = p2 + slice2 OBS M1-M7 full (real slice contract) | p0 = baseline | p1 = b16 OBS M1-M7 (M8/M9 open) | p2 = p1 + qfd_rst_rep* removed
#                                   p3 = p2 + landh0 removed (landing halves pushed into clusters)
I=$1; O=$2; V=$3; mkdir -p $O; zcat $(dirname $0)/b16_ft.lef.gz > $O/b16_ft.lef
cat > $O/grt_probe.tcl <<T
set_thread_count 16
read_db /in/in.odb
set b [ord::get_db_block]; set db [ord::get_db]
set V $V
if {\$V ne "p0"} {
  read_lef /work/b16_ft.lef
  set nm [\$db findMaster qfd_c_b16_dv_ft]; set ns 0
  foreach i [\$b getInsts] { if {[[\$i getMaster] getName] eq "qfd_c_b16_dv"} { \$i swapMaster \$nm; incr ns } }
  puts "OT_FT_SWAP \$ns"
}
if {\$V eq "p4"} {
  foreach i [\$b getInsts] { set mn [[\$i getMaster] getName]; if {\$mn eq "qfd_dv_slice2_e" || \$mn eq "qfd_dv_slice2_w"} { \$i swapMaster [\$db findMaster \${mn}_ft] } }
  puts "OT_FT_SLICE_SWAP"
}
if {\$V eq "p2" || \$V eq "p3" || \$V eq "p4"} {
  set nd 0
  foreach i [\$b getInsts] { set mn [[\$i getMaster] getName]
    if {[string match qfd_rst_rep* \$mn] || (\$V eq "p3" && [string match qfd_landh0_* \$mn])} { odb::dbInst_destroy \$i; incr nd } }
  puts "OT_FT_DEL \$nd"
}
set p [expr {4.8/15.0}]
foreach ln {M2 M3} { odb::dbTrackGrid_destroy [\$b findTrackGrid [[ord::get_db_tech] findLayer \$ln]]
  make_tracks \$ln -x_offset 0.009 -x_pitch \$p -y_offset 0.009 -y_pitch \$p }
set_routing_layers -signal M4-M9 -clock M4-M9
set_global_routing_layer_adjustment M2-M3 0.50
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M8 0.10
set_global_routing_layer_adjustment M9 0.05
set nck 0; foreach n [\$b getNets] { if {[\$n getSigType] == "CLOCK" || [string match n_clk_* [\$n getName]]} { \$n setSpecial; incr nck } }; puts "OT_PROBE_SKIP_CLOCK nets=\$nck"
set t0 [clock seconds]
global_route -congestion_iterations 0 -allow_congestion -verbose -congestion_report_file /work/grt_congestion_probe.rpt
puts "OT_GRT_PROBE_S [expr {[clock seconds]-\$t0}]"
T
docker run --rm --name ftqc-probe-$V-$$ --cpus=16 --memory=${PROBE_MEM:-120}g --memory-swap=${PROBE_MEM:-120}g -v $O:/work -v $I:/in/in.odb:ro -w /work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -no_init -exit /work/grt_probe.tcl > /work/probe.log 2>&1"
rc=$?; echo "PROBE_EXIT $rc $(date -Is)" > $O/probe.exit
python3 /tmp/ftqc_summ.py $O > $O/summary.txt 2>&1
exit $rc
