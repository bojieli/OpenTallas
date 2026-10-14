set ::env(OT_GATE_SIGNOFF_SDC) /src/physical/ref_tile/dsfd_gth_rw_clockleaf/signoff.sdc
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
read_db $base/4_1_cts.odb
if {[file exists $base/4_cts.sdc]} { read_sdc $base/4_cts.sdc } else { read_sdc $base/3_place.sdc }
foreach lib [[ord::get_db] getLibs] {
 foreach m [$lib getMasters] {if {[regexp {^(OR3|OR4|OR5|AND4|AOI21|AOI221|OAI21|BUF)} [$m getName]]} {puts "AVAILABLE_MASTER [$m getName] [$m getWidth] [$m getHeight]"}}
}
exit
