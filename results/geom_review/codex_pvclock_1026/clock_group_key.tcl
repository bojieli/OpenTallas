# Read actual CTS connectivity, so post-CTS cell moves cannot change group labels.
set pt_blk [ord::get_db_block]
set fh [open $R/ot_pv_taps.json r]
set pv_json [read $fh]
close $fh
set pv_tap_groups {}
foreach {whole tap group} [regexp -all -inline {"(ot_pv_tap_[0-9]+)": \{"group": "([^"]+)"} $pv_json] {
  dict set pv_tap_groups $tap $group
}
if {[dict size $pv_tap_groups] == 0} { error "PV clock-group map empty" }
proc ot_pv_key {name} {
  global pt_blk pv_tap_groups
  set inst [$pt_blk findInst $name]
  if {$inst eq "NULL" || $inst eq ""} {
    set inst [$pt_blk findInst [string map [list {[} {\[} {]} {\]}] $name]]
  }
  if {$inst eq "NULL" || $inst eq ""} { error "PV clock-group missing ODB instance $name" }
  set net ""
  foreach it [$inst getITerms] {
    if {[[$it getMTerm] getName] in {CLK clk CK ck}} { set net [$it getNet]; break }
  }
  set seen {}
  for {set depth 0} {$depth < 64} {incr depth} {
    if {$net eq "NULL" || $net eq "" || [dict exists $seen [$net getName]]} break
    dict set seen [$net getName] 1
    set next ""
    foreach it [$net getITerms] {
      if {[[$it getMTerm] getIoType] ne "OUTPUT"} continue
      set driver [$it getInst]
      if {[dict exists $pv_tap_groups [$driver getName]]} { return [dict get $pv_tap_groups [$driver getName]] }
      if {![regexp {^(BUF|INV|CLKBUF|DLY)} [[$driver getMaster] getName]]} {
        error "PV clock-group non-buffer driver [$driver getName]"
      }
      foreach pin [$driver getITerms] {
        if {[[$pin getMTerm] getIoType] eq "INPUT" && [$pin getSigType] in {SIGNAL CLOCK}} {
          set next [$pin getNet]; break
        }
      }
      break
    }
    set net $next
  }
  error "PV clock-group could not reach a regional tap from $name"
}
