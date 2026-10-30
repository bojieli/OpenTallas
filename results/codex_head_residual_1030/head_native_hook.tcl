# Explicit hd_tile native8 opt-in. Source after cland_place_ff definition, before group calls.
rename cland_place_ff cland_place_ff_default
proc cland_place_ff {prefix rect tag} {
 if {$prefix ne "u_cland_i"} {return [cland_place_ff_default $prefix $rect $tag]}
 if {[llength $rect] != 4} {error "HEAD_NATIVE8 malformed band rectangle"}
 if {$rect ne "12.96 708.48 47.52 1008.512"} {
  foreach a $rect b {12.96 708.48 47.52 1008.512} {if {abs($a-$b)>0.00001} {error "HEAD_NATIVE8 requires exact approved band.i"}}
 }
 set ::env(OT_GEOM_OUT) /work/head_native_live.tsv
 uplevel #0 {source /work/head_native_tools/geom_dump.tcl}
 set cmd [list python3 /work/head_native_pack.py --kit /work --dump /work/head_native_live.tsv --geom-tools /work/head_native_tools --out /work/head_native_generated]
 if {[file exists /work/head_native_private_write_comb.enabled]} {lappend cmd --private-write-comb}
 puts [exec {*}$cmd]
 uplevel #0 {source /work/head_native_generated/native_ring_layout.tcl}
 return 2941
}
