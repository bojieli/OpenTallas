# Read-only pin-access evidence on exact safe3 GRT geometry, including PG/vias.
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.lef
if {![file exists $base/5_1_grt.odb]} {error "PIN_ACCESS_EVIDENCE exact GRT checkpoint absent"}
read_db $base/5_1_grt.odb
set_thread_count 4
puts "PIN_ACCESS_EVIDENCE source=b30f8454c6db1309ee4ec7a154943f6c737b43f2 checkpoint=5_1_grt.odb stage=GRT actual_PG_vias=1 escape_qualification=0"
set_routing_layers -signal M2-M5
pin_access -verbose 1
puts "PIN_ACCESS_EVIDENCE COMPLETED access-only; full-channel DRT/DRC not qualified"
