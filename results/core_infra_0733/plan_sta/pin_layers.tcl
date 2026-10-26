read_db /work/source.odb
set f [open /work/master_pin_layers.tsv w]
foreach name {BUFx2_ASAP7_75t_R BUFx3_ASAP7_75t_R BUFx4_ASAP7_75t_R BUFx4f_ASAP7_75t_R BUFx5_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx10_ASAP7_75t_R BUFx12_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx16f_ASAP7_75t_R BUFx24_ASAP7_75t_R DFFHQNx1_ASAP7_75t_R DFFHQNx2_ASAP7_75t_R DFFASRHQNx1_ASAP7_75t_R DFFLQNx1_ASAP7_75t_R ot_sram_1r1w_1024x256_m2_r2c2} {
 set master [[ord::get_db] findMaster $name]
 if {$master eq "NULL"} {error "MISSING_PHYSICAL_MASTER $name"}
 foreach pin {A Y CLK clk} {
  set mt [$master findMTerm $pin]
  if {$mt eq "NULL"} continue
  set layers {}
  foreach mp [$mt getMPins] {
   foreach box [$mp getGeometry] {
    set layer [$box getTechLayer]
    if {$layer ne "NULL" && [$layer getRoutingLevel]>0} {lappend layers [$layer getRoutingLevel]}
   }
  }
  puts $f [list $name $pin [lsort -integer -unique $layers]]
 }
}
close $f
