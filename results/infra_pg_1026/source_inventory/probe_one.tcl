set tag $::env(SNAP_TAG)
set path $::env(SNAP_FILE)
 read_db $path
 set f [open /inventory/${tag}.tsv w];set bl [ord::get_db_block];set total 0;set bumps 0;set autos 0
 foreach nn {VDD VDDPHY VSS} {set n [$bl findNet $nn];foreach bt [$n getBTerms] {
  set name [$bt getName];incr total
  if {[regexp {^(VDD|VDDPHY|VSS)_b[0-9]+$} $name]} {incr bumps} else {incr autos}
  set bb {};foreach bp [$bt getBPins] {foreach b [$bp getBoxes] {lappend bb [list [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}}
  puts $f "$name\t$nn\t[$bt getSigType]\t$bb"
 }}
 close $f;puts "SOURCE_INVENTORY $tag total=$total intended=$bumps auto=$autos"
