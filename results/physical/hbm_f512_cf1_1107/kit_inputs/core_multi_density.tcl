# Reviewed native multi-port density stage. Every input remains a distinct root;
# numeric tap ranges avoid name collisions and core_tap_align measures them all.
if {![info exists ::env(OT_DTAP_PORTS)] || ![llength $::env(OT_DTAP_PORTS)]} {
  error "MULTIPORT_CTS_HOLD: no reviewed native clock-port contract"
}
set ot_md_seen [dict create]
set ot_md_idx 0
set ::env(OT_DTAP_APPEND) 0
foreach ot_md_port $::env(OT_DTAP_PORTS) {
  set ot_md_bt [[ord::get_db_block] findBTerm $ot_md_port]
  if {$ot_md_bt eq "NULL" || [$ot_md_bt getNet] eq "NULL"} {
    error "MULTIPORT_CTS_HOLD: native clock root missing: $ot_md_port"
  }
  set ot_md_net [[$ot_md_bt getNet] getName]
  if {[dict exists $ot_md_seen $ot_md_net]} {
    error "MULTIPORT_CTS_HOLD: native clock inputs unexpectedly shorted: $ot_md_port"
  }
  dict set ot_md_seen $ot_md_net 1
  set ::env(OT_DTAP_PORT) $ot_md_port
  set ::env(OT_DTAP_ID_OFFSET) [expr {$ot_md_idx * 100000}]
  source /work/core_density_taps.tcl
  set ::env(OT_DTAP_APPEND) 1
  incr ot_md_idx
}
puts "OT_MULTIPORT_DENSITY roots $ot_md_idx layout $::env(OT_DTAP_LAYOUT) common POST_CTS alignment"
