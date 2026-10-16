# Temporary conservative OBS only during pdngen. Never edit or replace original masters.
namespace eval ot_pdn_bbox { variable swaps {}; variable aliases {}; variable signatures {}; variable originals {} }
proc ot_pdn_bbox::signature {master} {
  set terms {}
  foreach term [$master getMTerms] {
    set shapes {}
    foreach pin [$term getMPins] {
      foreach box [$pin getGeometry] {
        if {[$box isVia]} { error "PDN bbox: unsupported pin via in [$master getName]" }
        lappend shapes [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax] [$box getLayerMask]]
      }
    }
    lappend terms [list [$term getName] [$term getIoType] [$term getSigType] [lsort $shapes]]
  }
  return [list [$master getWidth] [$master getHeight] [$master getOrigin] [lsort $terms]]
}
proc ot_pdn_bbox::obstructions {master} {
  set result {}
  foreach box [$master getObstructions] {
    if {[$box isVia]} {error "PDN bbox: unsupported obstruction via"}
    lappend result [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax] [$box getLayerMask]]
  }
  return [lsort $result]
}
proc ot_pdn_bbox::conservative {master alias} {
  set cover [dict create]
  foreach box [$alias getObstructions] {
    set layer [[$box getTechLayer] getName]
    if {[dict exists $cover $layer]} {error "PDN bbox: duplicate obstruction layer $layer"}
    dict set cover $layer [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
  }
  foreach box [$master getObstructions] {
    set layer [[$box getTechLayer] getName]
    if {![dict exists $cover $layer]} {error "PDN bbox: missing obstruction layer $layer"}
    lassign [dict get $cover $layer] x0 y0 x1 y1
    if {$x0 > [$box xMin] || $y0 > [$box yMin] || $x1 < [$box xMax] || $y1 < [$box yMax]} {
      error "PDN bbox: obstruction coverage shrank [$master getName]/$layer"
    }
  }
}
proc ot_pdn_bbox::begin {dir} {
  variable swaps; variable aliases; variable signatures; variable originals
  if {[llength $swaps]} {error "PDN bbox: already active"}
  set masters [dict create]
  foreach inst [[ord::get_db_block] getInsts] {
    set master [$inst getMaster]
    # A new assumed PHY access contract reserves two narrow M5 power columns.
    # Bounding those OBS would close the declared access. Keep the small exact
    # PHY obstruction set unchanged while other masters use conservative aliases.
    if {[file exists $dir/assumed_phy_pg_access.json] &&
        [regexp {^ot_q(fd_serdes_112g_x12|fd_ucie_x64|kvd_ucie_x64)_phy} [$master getName]]} {continue}
    if {[llength [$master getObstructions]]} {dict set masters [$master getName] $master}
  }
  if {![dict size $masters]} {puts "OT_PDN_BBOX BEGIN masters=0 instances=0 (exact PHY OBS preserved)"; return}
  set stamp [clock clicks]
  set exported $dir/pdn_original_$stamp.lef
  write_lef $exported
  set file [open $dir/pdn_bbox_names.txt w]
  foreach name [lsort [dict keys $masters]] {puts $file $name}
  close $file
  # One alias library per begin: restore destroys the alias masters but OpenDB keeps their (now empty) library, and
  # read_lef -library names the library after the file, so a second begin (KV preflight begin/restore/begin) with a
  # fixed file name fails 'ODB-0229 library already exists' -> 'missing alias' (kvs8-codex-1338 resume 17:20).
  set aliaslef $dir/pdn_bbox_masters_$stamp.lef
  exec python3 $dir/pdn_bbox_obs.py $exported $dir/pdn_bbox_names.txt $aliaslef
  read_lef -library $aliaslef
  dict for {name master} $masters {
    set alias [[ord::get_db] findMaster OT_PDN_BBOX_$name]
    if {$alias == "NULL" || $alias == ""} {error "PDN bbox: missing alias $name"}
    lappend aliases $alias
    set sig [signature $master]
    if {$sig ne [signature $alias]} {error "PDN bbox: pin/outline mismatch $name"}
    conservative $master $alias
    dict set signatures $name [list $sig [obstructions $master]]
    dict set originals $name $master
  }
  foreach inst [[ord::get_db_block] getInsts] {
    set master [$inst getMaster]; set name [$master getName]
    if {![dict exists $masters $name]} {continue}
    set alias [[ord::get_db] findMaster OT_PDN_BBOX_$name]
    lappend swaps [list $inst $master]
    if {![$inst swapMaster $alias]} {error "PDN bbox: swap failed [$inst getName]"}
  }
  puts "OT_PDN_BBOX BEGIN masters=[dict size $masters] instances=[llength $swaps]"
}
proc ot_pdn_bbox::restore {} {
  variable swaps; variable aliases; variable signatures; variable originals
  foreach pair $swaps {
    lassign $pair inst master
    if {![$inst swapMaster $master]} {error "PDN bbox: restore failed [$inst getName]"}
  }
  dict for {name master} $originals {
    if {[list [signature $master] [obstructions $master]] ne [dict get $signatures $name]} {
      error "PDN bbox: original pin/OBS geometry changed $name"
    }
  }
  set swaps {}
  foreach alias $aliases {odb::dbMaster_destroy $alias}
  set aliases {}; set signatures {}; set originals {}
  puts "OT_PDN_BBOX RESTORED original masters (detailed OBS never changed)"
}
