# DIE-CLOCK: per-hop clock arrival of forwarded-clock relay chains (F1 hop accounting on a die ODB).
#
# Source in an OpenROAD session that has the die read (read_db / link) with liberty loaded, clocks created and
# set_propagated_clock + parasitics estimated (TT or FF libs).  Env:
#   OT_FCLK_TSV   die_repeaters.fclk.tsv (fclk_net, src, load, ...) from tools/die_repeaters/fclk_audit.tcl
#   OT_FCLK_OUT   output TSV: net  station  ck_pin  arr_max  arr_min
# For every station (src and loads of each fclk net) it writes the propagated arrival at the station flop's clock pin.
# tools/die_clock/fclk_hops.py turns that into per-hop deltas (consecutive stations of a chain) and the verdict.
set ot_seen [dict create]
set fo [open $::env(OT_FCLK_OUT) w]
set fi [open $::env(OT_FCLK_TSV) r]
gets $fi hdr
while {[gets $fi line] >= 0} {
  set f [split $line "\t"]
  set net [lindex $f 0]
  foreach st [list [lindex $f 1] [lindex $f 2]] {
    if {[dict exists $ot_seen $st]} { continue }
    dict set ot_seen $st 1
    set inst [get_cells -quiet [string map {[ \\[ ] \\]} $st]]
    if {$inst eq ""} { continue }
    foreach p [get_pins -quiet -of_objects $inst] {
      if {[get_property $p is_clock] || [string match {*/CLK} [get_full_name $p]] || [string match {*/clk*} [get_full_name $p]]} {
        set am [get_property $p arrival_max_rise]
        set an [get_property $p arrival_min_rise]
        puts $fo "$net\t$st\t[get_full_name $p]\t$am\t$an"
      }
    }
  }
}
close $fi
close $fo
puts "OT_FCLK_HOPS_DONE [dict size $ot_seen]"
