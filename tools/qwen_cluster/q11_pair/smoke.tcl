foreach p [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] {read_liberty $p}
foreach p [glob /src/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_*x64_m1/*_tt.lib] {read_liberty $p}
read_db /work/fixture.odb
read_sdc /src/physical/ref_tile/qfd_coll_split_q11a/clock.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set blk [ord::get_db_block]
set raw [[$blk findBTerm clk] getNet]
set original [dict create]; set data {}
foreach inst [$blk getInsts] {
  if {[string match clkbuf_sp_* [$inst getName]]} {error "Q11 smoke fixture is already clock-spined"}
  foreach it [$inst getITerms] {
    set net [$it getNet]
    if {$net eq "NULL" || $net eq ""} continue
    if {$net eq $raw && [$it getIoType] eq "INPUT"} {dict set original $it 1} elseif {[$net getSigType] ni {POWER GROUND CLOCK}} {lappend data [list $it $net]}
  }
}
set cells_before [llength [$blk getInsts]]
set ::env(OT_SPINE_PORT) clk
set ::env(OT_SPINE_SYM) 1
set ::env(OT_SPINE_MACRO_LEAF) 1
set ::env(OT_SPINE_TREE_PAD) 1
set ::env(OT_SPINE_SAFE_BALANCE) 1
set ::env(OT_SPINE_TOL_PS) 10
# Connectivity/construction smoke only. Normal gate retains full balancing.
set ::env(OT_SPINE_ITERS) 0
source /src/physical/common_flow/clock_spine.tcl
source /src/physical/ref_tile/qfd_coll_split_q11a/spine_ins.tcl
source /src/tools/qwen_cluster/q11_pair/clock_pair.tcl
if {![ot_clock_spine clk]} {error "Q11 smoke did not construct a clock tree"}
set covered [dict create]
dict for {leaf members} $::ot_sp_members {
  foreach it $members {
    if {![dict exists $original $it] || [dict exists $covered $it]} {error "Q11 clock endpoint lost/duplicated"}
    dict set covered $it 1
    if {[[$it getNet] getSigType] ne "CLOCK"} {error "Q11 clock endpoint is not on a CLOCK net"}
  }
}
if {[dict size $original] != [dict size $covered]} {error "Q11 incomplete clock coverage"}
foreach row $data {lassign $row it net; if {[$it getNet] ne $net} {error "Q11 changed a functional data connection"}}
puts "Q11_SMOKE_PASS original_clock_pins=[dict size $original] preserved_data_connections=[llength $data] buffers_added=[expr {[llength [$blk getInsts]]-$cells_before}] leaves=[dict size $::ot_sp_members]"
write_db /work/q11_smoke.odb
exit
