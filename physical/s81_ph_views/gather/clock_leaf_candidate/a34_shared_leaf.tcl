# Keep a direct stage pair on one genuine local clock leaf. This changes the
# physical clock network, never the clock, period, uncertainty or RTL cycles.
proc s81_a34_shared_leaf {} {
 set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
 set actual {}
 foreach i [$b getInsts] {dict set actual [string map {\\ ""} [$i getName]] $i}
 set count 0
 foreach root {0 1 2 3} {
  set pair {}
  foreach stage {3 4} {
   set name [format {u_l.g_r[%d].u_root.a%d_v$_DFF_PN0_} $root $stage]
   if {![dict exists $actual $name]} {error "S81_A34 missing actual register $name"}
   lappend pair [dict get $actual $name]
  }
  lassign $pair a z
  lassign [$a getLocation] ax ay;lassign [$z getLocation] zx zy
  set distance [expr {(abs($ax-$zx)+abs($ay-$zy))/double($dbu)}]
  if {$distance>20} {error "S81_A34 refuses nonlocal clock pair root$root $distance um"}
  set ap [$a findITerm CLK];set zp [$z findITerm CLK]
  set an [$ap getNet];set zn [$zp getNet]
  if {$an eq "NULL" || $zn eq "NULL" || [$an getSigType] ne "CLOCK" || [$zn getSigType] ne "CLOCK"} {error "S81_A34 requires two real clock pins"}
  if {$an ne $zn} {$zp disconnect;$zp connect $an}
  puts "S81_A34 root$root shared clock [$an getName] a3_to_a4=$distance um original_a4=[$zn getName]"
  incr count
 }
 if {$count!=4} {error "S81_A34 requires four actual stage pairs"}
}
rename clock_tree_synthesis s81_a34_original_cts
proc clock_tree_synthesis {args} {
 uplevel 1 [list s81_a34_original_cts {*}$args]
 s81_a34_shared_leaf
}
