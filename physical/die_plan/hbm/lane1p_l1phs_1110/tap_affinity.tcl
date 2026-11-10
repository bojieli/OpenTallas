# HBM-COLLECT-1 L1P-HS 11-10 (COORD: tap affinity as in HEAD ds8c): after core_density_taps.tcl has built the density
# taps (PRE_CTS), move each listed member flop's clock pin onto the tap net of its anchor flop, so launch and capture
# of the D2L cross-tap TT setup endpoints share one tap. Clock-pin moves only: no data, reset or cell change.
# File /work/tap_affinity.tsv: "member<TAB>anchor" instance names.
namespace eval ::ot_taff {
  set blk [ord::get_db_block]
  proc ckterm {inst} {
    foreach it [$inst getITerms] {
      if {[$it isInputSignal] && [[$it getMTerm] getName] in {CLK CLKN}} { return $it }
    }
    return ""
  }
  set f /work/tap_affinity.tsv
  set moved 0; set same 0; set miss 0
  if {[file exists $f]} {
    set fh [open $f r]
    foreach ln [split [read $fh] "\n"] {
      if {$ln eq "" || [string index $ln 0] eq "#"} continue
      lassign [split $ln "\t"] m a
      set mi [$blk findInst $m]; set ai [$blk findInst $a]
      if {$mi eq "NULL" || $ai eq "NULL"} { incr miss; puts "OT_TAP_AFFINITY missing $m / $a"; continue }
      set mt [ckterm $mi]; set at [ckterm $ai]
      if {$mt eq "" || $at eq ""} { incr miss; continue }
      set an [$at getNet]
      if {[$mt getNet] eq $an} { incr same; continue }
      $mt disconnect
      $mt connect $an
      incr moved
    }
    close $fh
  }
  puts "OT_TAP_AFFINITY moved $moved same $same missing $miss"
}
