source /out/timing_libs.tcl
foreach c {TT FF} {ot_lib_load $c /out/actual_${c}.libraries.json}
puts EXACT_LIBRARY_PROBE_PASS
