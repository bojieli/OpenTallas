# Remove only our marked GPL density guide before detailed legalization.
uplevel #0 {
 set count 0
 foreach b [[ord::get_db_block] getBlockages] {
  set tag [odb::dbStringProperty_find $b codex_prompt_rx_spread]
  if {$tag ne "NULL" && $tag ne "" && [$tag getValue] eq "north_gpl_only"} {
   odb::dbBlockage_destroy $b
   incr count
  }
 }
 puts "PROMPT_RX_SPREAD_RELEASE removed $count marked GPL guides"
 if {$count != 1} {error "expected exactly one prompt GPL guide"}
}
