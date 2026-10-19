# SOURCE PROTOTYPE ONLY. Not sourced by production helpers.
# Rebuild after cell insertion or any rule/region change. getInsts uses OpenDB's
# native instance regex; exact dbRegion identity is checked separately below.
# Pin patterns are deliberately
# restricted to exact literals: unsupported syntax REFUSES rather than guessing.
proc ot_pg_prepare {block} {
  set mapping [dict create]
  foreach rule [$block getGlobalConnects] {
    set pattern [$rule getPinPattern]
    if {![regexp {^\^?([A-Za-z_][A-Za-z0-9_]*)\$?$} $pattern -> pin]} {
      error "OT_PG_UNSUPPORTED_PIN_PATTERN $pattern"
    }
    set net [$rule getNet]
    if {$net eq "NULL" || [$net getSigType] ni {POWER GROUND}} {
      error "OT_PG_RULE_NET_ROLE $pattern"
    }
    set region [$rule getRegion]
    foreach inst [$rule getInsts] {
      if {$region ne "NULL" && [$inst getRegion] ne $region} continue
      set term [$inst findITerm $pin]
      if {$term eq "NULL"} continue
      set role [[$term getMTerm] getSigType]
      if {$role ni {POWER GROUND}} {
        error "OT_PG_RULE_SIGNAL_PIN [$inst getName]/$pin"
      }
      if {$role ne [$net getSigType]} {
        error "OT_PG_RULE_ROLE [$inst getName]/$pin"
      }
      set key [list [$inst getName] $pin]
      dict lappend mapping $key $net
    }
  }
  # All overlap, including differently named native voltage supplies, refuses.
  dict for {key nets} $mapping {
    set nets [lsort -unique $nets]
    if {[llength $nets] != 1} { error "OT_PG_AMBIGUOUS_DOMAIN $key" }
    dict set mapping $key [lindex $nets 0]
  }
  return $mapping
}
proc ot_pg_expected {mapping inst term} {
  set key [list [$inst getName] [[$term getMTerm] getName]]
  if {![dict exists $mapping $key]} {error "OT_PG_UNKNOWN_DOMAIN $key"}
  return [dict get $mapping $key]
}
# Census is driven by the MASTER, never by the possibly incomplete ITerm list.
proc ot_pg_master_census {inst} {
  set rows {}
  foreach mt [[$inst getMaster] getMTerms] {
    set role [$mt getSigType]
    if {$role ni {POWER GROUND}} continue
    set pin [$mt getName]
    set term [$inst findITerm $pin]
    set why ""
    if {$term eq "NULL"} {
      set why OT_PG_MISSING_ITERM
    } elseif {[$term getMTerm] ne $mt || [$term getSigType] ne $role} {
      set why OT_PG_ITERM_TYPE_MISMATCH
    }
    lappend rows [list $mt $term $why]
  }
  return $rows
}
proc ot_pg_bind_before_protect {mapping inst} {
  set pending {}
  # Preflight every terminal before changing any connection. No force or
  # temporary clearing of protection is permitted in this SOURCE prototype.
  foreach row [ot_pg_master_census $inst] {
    lassign $row mt term why
    if {$why ne ""} {error "$why [$inst getName]/[$mt getName]"}
    set expected [ot_pg_expected $mapping $inst $term]
    set actual [$term getNet]
    if {$actual ne "NULL" && $actual ne $expected} {
      error "OT_PG_WRONG_DOMAIN [$inst getName]/[[$term getMTerm] getName]"
    }
    if {$actual eq "NULL"} {lappend pending [list $term $expected]}
  }
  if {[llength $pending] && [$inst isDoNotTouch]} {
    error "OT_PG_ORDER_PROTECTED_UNBOUND [$inst getName]"
  }
  foreach pair $pending {lassign $pair term net; $term connect $net}
  foreach row [ot_pg_master_census $inst] {
    lassign $row mt term why
    if {$why ne ""} {error "$why [$inst getName]/[$mt getName]"}
    if {[$term getNet] ne [ot_pg_expected $mapping $inst $term]} {
      error "OT_PG_BIND_VERIFY [$inst getName]"
    }
  }
  return [llength $pending]
}
# Run after final global_connect, independently BEFORE/alongside PSM. This
# asserts every native PG MTerm, without clock/physical-only/name exemptions.
proc ot_pg_collect_all_native {block mapping} {
  set checked 0; set failures {}; set counts [dict create POWER 0 GROUND 0]
  foreach inst [$block getInsts] {
    foreach row [ot_pg_master_census $inst] {
      lassign $row mt term census_why
      set role [$mt getSigType]
      incr checked; dict incr counts $role
      set actual "NULL"
      if {$census_why eq ""} {set actual [$term getNet]}
      set actual_name ""; set actual_role ""
      if {$actual ne "NULL"} {set actual_name [$actual getName]; set actual_role [$actual getSigType]}
      set why ""; set expected_name ""
      if {$census_why ne ""} {
        set why $census_why
      } elseif {[catch {ot_pg_expected $mapping $inst $term} expected]} {
        set why $expected
      } else {
        set expected_name [$expected getName]
        if {$actual ne $expected} {set why OT_PG_FINAL_BINDING}
      }
      if {$why ne ""} {
        lappend failures [dict create instance [$inst getName] master [[$inst getMaster] getName] pin [$mt getName] role $role actual_net $actual_name actual_role $actual_role expected_net $expected_name reason $why]
      }
    }
  }
  return [dict create checked $checked roles $counts failures $failures failure_count [llength $failures]]
}
proc ot_pg_assert_all_native {block mapping} {
  set report [ot_pg_collect_all_native $block $mapping]
  if {[dict get $report failure_count]} {
    error "OT_PG_FINAL_FAIL count=[dict get $report failure_count] checked=[dict get $report checked] first=[lindex [dict get $report failures] 0]"
  }
  puts "OT_PG_FINAL_PASS native_pg_terminals=[dict get $report checked]"
  return [dict get $report checked]
}
