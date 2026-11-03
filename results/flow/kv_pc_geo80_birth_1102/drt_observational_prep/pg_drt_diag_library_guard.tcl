# ALL loaded physical masters, including unused libraries. Native metadata only.
proc ot_pg_drt_diag_library_inventory {} {
  # Finite getString vocabulary from pinned6cb dbTypes.cpp; unknowns refuse.
  set known_types [list {BLOCK} {BLOCK BLACKBOX} {BLOCK SOFT} {CORE} {CORE ANTENNACELL} {CORE FEEDTHRU} {CORE SPACER} {CORE TIEHIGH} {CORE TIELOW} {CORE WELLTAP} {COVER} {COVER BUMP} {ENDCAP} {ENDCAP BOTTOMEDGE} {ENDCAP BOTTOMLEFT} {ENDCAP BOTTOMRIGHT} {ENDCAP LEFTBOTTOMCORNER} {ENDCAP LEFTBOTTOMEDGE} {ENDCAP LEFTEDGE} {ENDCAP LEFTTOPCORNER} {ENDCAP LEFTTOPEDGE} {ENDCAP POST} {ENDCAP PRE} {ENDCAP RIGHTBOTTOMCORNER} {ENDCAP RIGHTBOTTOMEDGE} {ENDCAP RIGHTEDGE} {ENDCAP RIGHTTOPCORNER} {ENDCAP RIGHTTOPEDGE} {ENDCAP TOPEDGE} {ENDCAP TOPLEFT} {ENDCAP TOPRIGHT} {PAD} {PAD AREAIO} {PAD INOUT} {PAD INPUT} {PAD OUTPUT} {PAD POWER} {PAD SPACER} {RING}]
  set out {}
  foreach lib [[ord::get_db] getLibs] {
    foreach master [$lib getMasters] {
      set raw_type [$master getType]
      set type [string toupper [string map {_ { }} [string trim $raw_type]]]
      regsub -all {\s+} $type { } type
      # Fail closed on an unknown representation, including a wrapped pointer.
      if {$type ni $known_types} {
        error "DRT_DIAG_UNKNOWN_MASTER_TYPE lib=[$lib getName] master=[$master getName] type=$raw_type"
      }
      if {$type eq "CORE ANTENNACELL"} {
        error "DRT_DIAG_ANTENNA_MASTER_REQUIRES_NEW_SCOPE lib=[$lib getName] master=[$master getName]"
      }
      lappend out [list [$lib getName] [$master getName] $raw_type]
    }
  }
  puts "DRT_DIAG_ALL_LOADED_MASTER_CENSUS count=[llength $out] core_antennacell=0"
  return [lsort $out]
}
