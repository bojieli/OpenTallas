"""DIE-HEAD-33 V-A kit patch (kit-local, placement only): ring band ff order by data-cone input-pin coordinate (+ffp)."""
import sys
from pathlib import Path
kit, ffp = Path(sys.argv[1]), Path(sys.argv[2])
p = kit / "landing_placement.tcl"; t = p.read_text()
rep = [
 ("  {u_cland_i {17.28000 708.48000 47.52000 1008.51200} ring:i@1.8037+ffr}\n",
  "  {u_cland_i {17.28000 708.48000 47.52000 1008.51200} ring:i@1.8037+ffp}\n"),
 ("proc cland_place_ff {prefix rect tag} {\n", ffp.read_text() + "proc cland_place_ff {prefix rect tag} {\n"),
 ("  lappend ffs [list [cland_ffkey $nm [string match {ring:*+ffr} $tag]] $i]\n",
  "  lappend ffs [list [cland_ffkey $nm [string match {ring:*+ffr} $tag]] $i]; lappend ffi $i\n"),
 (" set ffs {};set comb 0;set need 0.0\n", " set ffs {};set ffi {};set comb 0;set need 0.0\n"),
 (" if {![llength $ffs]} { return 0 }\n",
  " if {![llength $ffs]} { return 0 }\n if {[string match {ring:*+ffp} $tag]} { set ffs [cland_ffp_keys $ffi]; puts \"OT_CLAND_FFP $prefix: [llength $ffs] ring flops keyed by data-cone input pin y\" }\n"),
 (" if {[string match {ring:*+ff} $tag] || [string match {ring:*+ffr} $tag]} {\n",
  " if {[string match {ring:*+ff} $tag] || [string match {ring:*+ffr} $tag] || [string match {ring:*+ffp} $tag]} {\n"),
]
for a, b in rep:
    assert t.count(a) == 1, a
    t = t.replace(a, b)
p.write_text(t); print("patched", p)
