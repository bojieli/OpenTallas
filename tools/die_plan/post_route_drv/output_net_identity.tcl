# Keep a moved output BTerm distinct from the net that used to carry its name.
# write_verilog otherwise aliases the old driver back onto the new output,
# creating a cycle through an inserted output delay buffer.
# Only internal net names change; instances, connectivity and metal stay fixed.
proc ot_output_net_identity {} {
  set block [ord::get_db_block]
  set changed 0
  foreach bt [$block getBTerms] {
    if {[$bt getIoType] ne "OUTPUT"} continue
    set name [$bt getName]
    set actual [$bt getNet]
    set old [$block findNet $name]
    if {$old eq "NULL" || $old eq $actual} continue
    if {[llength [$old getBTerms]]} {error "OT_OUTPUT_NET_IDENTITY conflicting BTerm net $name"}
    set replacement ot_export_internal_[$old getId]
    if {[$block findNet $replacement] ne "NULL"} {error "OT_OUTPUT_NET_IDENTITY duplicate $replacement"}
    $old rename $replacement
    if {[$old getName] ne $replacement || [$bt getNet] ne $actual} {error "OT_OUTPUT_NET_IDENTITY rename failed $name"}
    puts "OT_OUTPUT_NET_IDENTITY $name -> $replacement output_net=[$actual getName]"
    incr changed
  }
  puts "OT_OUTPUT_NET_IDENTITY renamed=$changed"
  return $changed
}
