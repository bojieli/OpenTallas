# Fixed hybrid-raw record phase. No callback, target override or protected-net unlock.
namespace eval ot_srt {
  variable source_root [file normalize [file join [file dirname [info script]] ../..]]
}
proc ot_srt::fail {message} {error "OT_SPINE_RECORD_TAP $message"}
proc ot_srt::keys {value expected} {
  if {[lsort [dict keys $value]] ne [lsort $expected]} {ot_srt::fail "unknown/missing typed fields"}
}
proc ot_srt::plan {} {
  if {![info exists ::ot_sp_record_taps_v1]} {ot_srt::fail "missing source plan"}
  set p $::ot_sp_record_taps_v1
  ot_srt::keys $p {version model records}
  if {[dict get $p version] ne "1" || [dict get $p model] ne "hybrid_raw" || ![dict size [dict get $p records]]} {
    ot_srt::fail "unsupported plan version/model"
  }
  return $p
}
proc ot_srt::unchanged {} {
  if {![info exists ::ot_srt::frozen] || [ot_srt::plan] ne $::ot_srt::frozen} {ot_srt::fail "unadmitted or changed plan"}
  if {[dict create buf [ot_sp_env OT_LRT_BUF BUFx4_ASAP7_75t_R] limit [ot_sp_env OT_LRT_MAX 64] batch [ot_sp_env OT_LRT_BATCH 0]] ne $::ot_srt::knobs} {
    ot_srt::fail "changed existing tap configuration"
  }
}
proc ot_srt::admit {rootnets contacts} {
  set p [ot_srt::plan]
  if {[info exists ::ot_srt::frozen]} {
    ot_srt::unchanged
    if {[dict size $::ot_srt::done] || [info exists ::ot_srt::active]} {ot_srt::fail "admission after builder phase"}
  }
  set knobs [dict create buf [ot_sp_env OT_LRT_BUF BUFx4_ASAP7_75t_R] limit [ot_sp_env OT_LRT_MAX 64] batch [ot_sp_env OT_LRT_BATCH 0]]
  if {[dict get $knobs buf] ne "BUFx4_ASAP7_75t_R"
      || ![string is integer -strict [dict get $knobs limit]] || [dict get $knobs limit] < 1
      || [dict get $knobs batch] ni {0 1}} {ot_srt::fail "unsupported existing tap configuration"}
  set buffer [[ord::get_db] findMaster [dict get $knobs buf]]
  if {$buffer in {NULL {}} || [$buffer getWidth] <= 0 || [$buffer getHeight] <= 0} {ot_srt::fail "missing tap buffer footprint"}
  set inputs {}; set outputs {}
  foreach mt [$buffer getMTerms] {
    if {[$mt getSigType] in {POWER GROUND}} continue
    if {[$mt getIoType] eq "INPUT"} {lappend inputs [$mt getName]} elseif {[$mt getIoType] eq "OUTPUT"} {lappend outputs [$mt getName]} else {ot_srt::fail "unsupported buffer terminal"}
  }
  if {$inputs ne "A" || $outputs ne "Y"} {ot_srt::fail "unsupported tap buffer ports"}
  set nets {}; set owners {}; set seen {}; set hashes {}; set expected {}
  dict for {root net} $rootnets {dict set nets $net $root}
  foreach contact $contacts {
    lassign $contact path net
    if {[dict exists $owners $path] || ![dict exists $nets $net]} {ot_srt::fail "ambiguous/unowned contact $path"}
    dict set owners $path [dict get $nets $net]
  }
  dict for {identity row} [dict get $p records] {
    ot_srt::keys $row {instance master raw ref source_key owner_rule targets files}
    foreach key {instance master raw ref} {
      if {![regexp {^[A-Za-z_][A-Za-z0-9_.\[\]]*$} [dict get $row $key]]} {ot_srt::fail "unsupported exact identity"}
    }
    set raw "[dict get $row instance]/[dict get $row raw]"
    set ref "[dict get $row instance]/[dict get $row ref]"
    if {$identity ne $raw || $raw eq $ref || [dict exists [dict get $p records] $ref]
        || [dict get $row owner_rule] ne "same_declared_root"} {ot_srt::fail "invalid raw/reference identity"}
    if {![dict exists $owners $raw] || ![dict exists $owners $ref]
        || [dict get $owners $raw] ne [dict get $owners $ref]} {ot_srt::fail "wrong-owner raw/reference $identity"}
    set inst [[ord::get_db_block] findInst [dict get $row instance]]
    if {$inst in {NULL {}} || [[$inst getMaster] getName] ne [dict get $row master]} {ot_srt::fail "master/instance mismatch $identity"}
    set key [dict get $row source_key]
    if {$key ne "[dict get $row master]/[dict get $row raw]" || [dict exists $expected $key]} {ot_srt::fail "duplicate/source-key mismatch"}
    if {![info exists ::ot_lrt_targets] || ![dict exists $::ot_lrt_targets $key]} {ot_srt::fail "missing existing landed target"}
    set legacy [dict get $::ot_lrt_targets $key]
    ot_srt::keys [dict get $row targets] {tt ff ss}
    if {[dict get $legacy ref] ne [dict get $row ref]} {ot_srt::fail "changed reference"}
    foreach corner {tt ff ss} {
      set target [dict get $row targets $corner]
      if {![string is double -strict $target] || [regexp -nocase {inf|nan} $target]
          || $target != [dict get $legacy $corner]} {ot_srt::fail "changed/nonfinite record target"}
    }
    if {[dict size [dict get $row files]] != 7} {ot_srt::fail "incomplete source witness"}
    dict for {relative hash} [dict get $row files] {
      if {[file pathtype $relative] ne "relative" || ".." in [file split $relative]
          || ![regexp {^[0-9a-f]{64}$} $hash]} {ot_srt::fail "unsupported source witness"}
      set file [file join $::ot_srt::source_root $relative]
      if {![file isfile $file]} {ot_srt::fail "missing source witness $relative"}
      if {![dict exists $hashes $relative]} {
        if {[catch {exec sha256sum -- $file} result] || ![regexp {^([0-9a-f]{64}) } $result -> actual]} {ot_srt::fail "unreadable source witness"}
        dict set hashes $relative $actual
      }
      if {[dict get $hashes $relative] ne $hash} {ot_srt::fail "changed source witness $relative"}
    }
    dict set expected $key 1
  }
  if {[lsort [dict keys $expected]] ne [lsort [dict keys $::ot_lrt_targets]]} {ot_srt::fail "unrepresented existing target"}
  if {[info exists ::ot_srt::frozen] && ($owners ne $::ot_srt::owners || $rootnets ne $::ot_srt::rootnets)} {
    ot_srt::fail "changed pre-builder ownership admission"
  }
  set ::ot_srt::owners $owners
  set ::ot_srt::rootnets $rootnets
  set ::ot_srt::frozen $p
  set ::ot_srt::knobs $knobs
  set ::ot_srt::done {}
  puts "OT_SPINE_RECORD_TAP ADMITTED [dict size [dict get $p records]] source targets"
}
proc ot_srt::selected {it} {
  if {![info exists ::ot_srt::active]} {ot_srt::fail "tap outside builder phase"}
  set path "[[$it getInst] getName]/[[$it getMTerm] getName]"
  return [expr {[dict exists [dict get $::ot_srt::frozen records] $path]
                && [dict get $::ot_srt::owners $path] eq $::ot_srt::active}]
}
proc ot_srt::owned_net {net} {
  if {$net eq "NULL" || [$net isDoNotTouch]} {ot_srt::fail "missing/already protected tap net"}
  if {$net eq [dict get $::ot_srt::rootnets $::ot_srt::active]} {return}
  foreach b $::ot_sp_insts {if {[[$b findITerm $::ot_sp_out] getNet] eq $net} {return}}
  ot_srt::fail "net outside current builder ownership"
}
proc ot_srt::create {it bm name x y} {
  if {![ot_srt::selected $it]} {ot_srt::fail "wrong-owner construction"}
  if {[$bm getName] ne "BUFx4_ASAP7_75t_R" || $::ot_sp_in ne "A" || $::ot_sp_out ne "Y"} {ot_srt::fail "unsupported typed tap buffer"}
  set old [$it getNet]
  ot_srt::owned_net $old
  lassign [ot_sp_buf $name $x $y $old $bm] nn lx ly b
  set keys {}; set sw $::ot_sp_sw
  set count [expr {int(ceil(double([$bm getWidth]) / $sw))}]
  for {set n -1} {$n <= $count} {incr n} {lappend keys "$ly,[expr {$lx + $n * $sw}]"}
  dict set ::ot_srt::claims $b $keys
  dict set ::ot_srt::objects $b [list $nn $old]
  $it disconnect
  $it connect $nn
  return [list $b $nn $old]
}
proc ot_srt::backout {it b nn old} {
  if {![ot_srt::selected $it] || ![dict exists $::ot_srt::objects $b]
      || [dict get $::ot_srt::objects $b] ne [list $nn $old] || [$it getNet] ne $nn} {ot_srt::fail "wrong-owner backout"}
  ot_srt::owned_net $nn
  $it disconnect
  $it connect $old
  set i [lsearch -exact $::ot_sp_insts $b]
  if {$i < 0} {ot_srt::fail "missing allocator object"}
  set ::ot_sp_insts [lreplace $::ot_sp_insts $i $i]
  incr ::ot_sp_nbuf -1
  odb::dbInst_destroy $b
  odb::dbNet_destroy $nn
  dict unset ::ot_srt::claims $b
  dict unset ::ot_srt::objects $b
  set ::ot_sp_used $::ot_srt::base_used
  dict for {object keys} $::ot_srt::claims {foreach key $keys {dict set ::ot_sp_used $key 1}}
}
proc ot_srt::apply {root} {
  ot_srt::unchanged
  if {[info exists ::ot_srt::active] || [dict exists $::ot_srt::done $root]} {ot_srt::fail "duplicate/overlapping builder phase"}
  set selected {}
  dict for {path row} [dict get $::ot_srt::frozen records] {
    if {[dict get $::ot_srt::owners $path] eq $root} {lappend selected $path}
  }
  if {![llength $selected]} {return 0}
  if {![dict exists $::ot_srt::rootnets $root] || [[dict get $::ot_srt::rootnets $root] isDoNotTouch]} {ot_srt::fail "wrong/already finalized root"}
  set before {}
  dict for {path owner} $::ot_srt::owners {
    if {$owner eq $root} {dict set before $path [[[ord::get_db_block] findITerm $path] getNet]}
  }
  set ::ot_srt::active $root
  set ::ot_srt::base_used $::ot_sp_used
  set ::ot_srt::claims {}; set ::ot_srt::objects {}
  set width $::ot_sp_cw
  try {
    foreach path $selected {
      set row [dict get $::ot_srt::frozen records $path]
      foreach contact [list $path "[dict get $row instance]/[dict get $row ref]"] {
        ot_srt::owned_net [[[ord::get_db_block] findITerm $contact] getNet]
      }
    }
    ot_lrt_tap
    dict for {path previous} $before {
      set now [[[ord::get_db_block] findITerm $path] getNet]
      if {$path ni $selected && $now ne $previous} {ot_srt::fail "changed non-target clock contact $path"}
    }
    set endpoints {}
    foreach path $selected {
      set row [dict get $::ot_srt::frozen records $path]
      set ref "[dict get $row instance]/[dict get $row ref]"
      dict set endpoints $path [dict create net [[[ord::get_db_block] findITerm $path] getNet] ref $ref refnet [[[ord::get_db_block] findITerm $ref] getNet]]
    }
    dict set ::ot_srt::done $root [dict create phase applied endpoints $endpoints objects $::ot_srt::objects]
  } finally {
    set ::ot_sp_cw $width
    unset -nocomplain ::ot_srt::active
  }
  return 1
}
proc ot_srt::protected {root} {
  ot_srt::unchanged
  if {![dict exists $::ot_srt::done $root]} {return}
  if {[dict get $::ot_srt::done $root phase] ne "applied"} {ot_srt::fail "duplicate finalization"}
  set topology [list [dict get $::ot_srt::rootnets $root]]
  foreach b $::ot_sp_insts {
    lappend topology $b [[$b findITerm $::ot_sp_out] getNet]
    if {![$b isDoNotTouch] || ![[[$b findITerm $::ot_sp_out] getNet] isDoNotTouch]} {ot_srt::fail "unprotected final builder topology"}
  }
  if {![[dict get $::ot_srt::rootnets $root] isDoNotTouch]} {ot_srt::fail "unprotected root"}
  dict set ::ot_srt::done $root topology $topology
  dict set ::ot_srt::done $root phase protected
}
proc ot_srt::verify {} {
  ot_srt::unchanged
  if {[info exists ::ot_srt::active] || [info exists ::ot_srt::consumed]} {ot_srt::fail "premature/duplicate completion consumption"}
  set ideal {}
  foreach c [all_clocks] {if {![get_property $c is_propagated]} {lappend ideal $c}}
  if {[llength $ideal]} {set_propagated_clock $ideal}
  try {
    estimate_parasitics -placement
    dict for {path row} [dict get $::ot_srt::frozen records] {
      set owner [dict get $::ot_srt::owners $path]
      if {![dict exists $::ot_srt::done $owner] || [dict get $::ot_srt::done $owner phase] ne "protected"
          || ![dict exists $::ot_srt::done $owner endpoints $path]} {ot_srt::fail "missing protected completion $path"}
      foreach object [dict get $::ot_srt::done $owner topology] {
        if {![$object isDoNotTouch]} {ot_srt::fail "changed final builder protection"}
      }
      set receipt [dict get $::ot_srt::done $owner endpoints $path]
      set it [[ord::get_db_block] findITerm $path]
      set ref [[ord::get_db_block] findITerm [dict get $receipt ref]]
      if {[$it getNet] ne [dict get $receipt net] || [$ref getNet] ne [dict get $receipt refnet]
          || ![[$it getNet] isDoNotTouch]} {ot_srt::fail "changed completed endpoint $path"}
      dict for {b pair} [dict get $::ot_srt::done $owner objects] {
        if {![$b isDoNotTouch] || ![[lindex $pair 0] isDoNotTouch]} {ot_srt::fail "changed final tap protection"}
      }
      set cell [get_cells -quiet [dict get $row instance]]
      set rawpin [get_pins -quiet $path]
      set refpin [get_pins -quiet [dict get $receipt ref]]
      if {[llength $cell] != 1 || [llength $rawpin] != 1 || [llength $refpin] != 1} {ot_srt::fail "missing final STA endpoints"}
      set corner [ot_lrt_corner $cell]
      set actual [expr {[ot_lrt_wire $rawpin] - [ot_lrt_wire $refpin]}]
      puts "OT_SPINE_RECORD_TAP REMEASURE $path owner=$owner corner=$corner raw-ref=$actual target=[dict get $row targets $corner] (existing RAW_PIN check remains verdict)"
    }
    set ::ot_srt::consumed 1
  } finally {
    if {[llength $ideal]} {unset_propagated_clock $ideal}
  }
}
