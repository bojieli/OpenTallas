# Explicit preservation of an existing registered reset provider, before CTS.
# This checker never reconnects a pin, places a cell or changes RTL.
namespace eval ot_rp {}
proc ot_rp::need {ok why} { if {!$ok} { error "OT_RESET_PROVIDER $why" } }
proc ot_rp::inst {blk name} {
  set i [$blk findInst $name]
  need [expr {$i ne "NULL"}] "missing exact instance $name"
  return $i
}
proc ot_rp::pin {i name} {
  set p [$i findITerm $name]
  need [expr {$p ne "NULL" && [$p getNet] ne "NULL"}] "missing/undriven [$i getName]/$name"
  return $p
}
proc ot_rp::trace {net anchor expected clock models flop_model} {
  set seen {}; set stages {}; set buffers {}; set parity 0
  while {$net ne $anchor} {
    need [expr {$net ne "NULL" && ![dict exists $seen [$net getName]]}] "missing net or lineage loop"
    dict set seen [$net getName] 1
    set drivers {}
    foreach p [$net getITerms] {
      if {[[$p getMTerm] getIoType] eq "OUTPUT"} { lappend drivers $p }
    }
    need [expr {[llength $drivers] == 1}] "lineage net [$net getName] has [llength $drivers] drivers"
    set p [lindex $drivers 0]; set i [$p getInst]; set name [$i getName]
    set master [[$i getMaster] getName]; set port [[$p getMTerm] getName]
    if {[dict exists $models $master]} {
      set m [dict get $models $master]
      need [expr {$port eq [dict get $m output]}] "unexpected buffer output $name/$port"
      set input [pin $i [dict get $m input]]
      set parity [expr {$parity ^ [dict get $m inverted]}]
      lappend buffers [list $name $master $port [$net getName]]
      set net [$input getNet]
    } elseif {$master eq [dict get $flop_model master]} {
      need [expr {[llength $stages] < [llength $expected]}] "too many registered provider stages"
      set want [lindex $expected [llength $stages]]
      need [expr {$name eq $want}] "wrong registered stage $name; expected $want"
      need [expr {$port eq [dict get $flop_model output]}] "wrong registered output $name/$port"
      need [expr {[[pin $i [dict get $flop_model clock]] getNet] eq $clock}] "wrong provider stage clock $name"
      set parity [expr {$parity ^ [dict get $flop_model inverted]}]
      lappend stages $name
      set net [[pin $i [dict get $flop_model data]] getNet]
    } else { error "OT_RESET_PROVIDER unsupported lineage driver $name ($master)/$port" }
  }
  need [expr {$stages eq $expected}] "registered lineage depth/identity mismatch"
  return [dict create stages $stages parity $parity buffers $buffers]
}
proc ot_reset_provider_preserve {blk c} {
  foreach k {provider provider_master provider_pin provider_clock source_clock_net sinks sink_master sink_pin sink_clock stages buffers flop libraries tap_net tap_parity tap_key} {
    ot_rp::need [dict exists $c $k] "missing contract field $k"
  }
  ot_rp::need [expr {[dict size [dict get $c libraries]] > 0}] "native library identity missing"
  dict for {path digest} [dict get $c libraries] {
    ot_rp::need [file readable $path] "native library unavailable $path"
    ot_rp::need [expr {[lindex [exec sha256sum -- $path] 0] eq $digest}] "native library changed $path"
  }
  set clock [$blk findNet [dict get $c source_clock_net]]
  ot_rp::need [expr {$clock ne "NULL"}] "source clock net unavailable"
  set provider [ot_rp::inst $blk [dict get $c provider]]
  ot_rp::need [expr {[[$provider getMaster] getName] eq [dict get $c provider_master]}] "provider master changed"
  ot_rp::need [expr {[[ot_rp::pin $provider [dict get $c provider_clock]] getNet] eq $clock}] "provider clock source changed"
  set anchor [[ot_rp::pin $provider [dict get $c provider_pin]] getNet]
  set models [dict get $c buffers]; set fm [dict get $c flop]
  # Verify the provider's upstream reset against the exact declared delivered
  # tap through only library-qualified buffers. A private FF here is an error.
  set upstream [ot_rp::trace [[ot_rp::pin $provider rst] getNet] [dict get $c tap_net] {} $clock $models $fm]
  ot_rp::need [expr {[dict get $upstream parity] == [dict get $c tap_parity]}] "provider reset tap polarity changed"
  set expected [lreverse [dict get $c stages]]
  ot_rp::need [expr {[llength $expected] > 0 && [llength [lsort -unique $expected]] == [llength $expected]}] "empty/duplicate provider stage contract"
  set sinks [dict get $c sinks]
  ot_rp::need [expr {[llength $sinks] > 0 && [llength [lsort -unique $sinks]] == [llength $sinks]}] "empty/duplicate provider sinks"
  set receipts {}
  foreach name $sinks {
    set i [ot_rp::inst $blk $name]
    ot_rp::need [expr {[[$i getMaster] getName] eq [dict get $c sink_master]}] "sink master changed $name"
    ot_rp::need [expr {[[ot_rp::pin $i [dict get $c sink_clock]] getNet] eq $clock}] "sink clock source changed $name"
    set p [ot_rp::pin $i [dict get $c sink_pin]]; set before [$p getNet]
    set r [ot_rp::trace $before $anchor $expected $clock $models $fm]
    ot_rp::need [expr {[dict get $r parity] == 0}] "provider-to-sink reset polarity changed $name"
    ot_rp::need [expr {[$p getNet] eq $before}] "checker changed sink connection $name"
    dict set receipts $name [dict create net [$before getName] source [dict get $c provider] pin [dict get $c provider_pin] offset_cycles [llength $expected] stages [dict get $r stages] buffers [dict get $r buffers]]
    puts "OT_RESET_PROVIDER PRESERVED $name.[dict get $c sink_pin] <- [dict get $c provider].[dict get $c provider_pin] +[llength $expected] clocks; connection unchanged"
  }
  # No claim about provider-internal stages, absolute release, asynchronous
  # assertion, post-CTS timing root relation or downstream signoff is made.
  return [dict create status PRESERVED provider_offset_cycles [llength $expected] tap [dict get $c tap_key] provider_internal_cycles NOT_QUALIFIED absolute_release_cycles NOT_RUN sinks $receipts]
}
