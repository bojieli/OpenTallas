#!/bin/bash
# Report the worst repaired path into registers matching each regex from a screen's rep.odb. Usage: kv_paths.sh <screen work dir> <regex>...
W=$1; shift
{ echo "read_db /o/rep.odb"; grep "^read_liberty" $W/screen.tcl
  sed -n '/^create_clock/,/^set_max_fanout/p' $W/screen.tcl
  echo "source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl"; echo "estimate_parasitics -placement"
  for rx in "$@"; do echo "set pins {}; foreach c [all_registers -cells] { if {[regexp -- {$rx} [get_full_name \$c]]} { foreach pn [get_pins -of_objects \$c -filter \"direction==input\"] { if {[get_property \$pn lib_pin_name] eq \"D\"} { lappend pins \$pn } } } }"
    echo "puts \"=== $rx\"; report_checks -to \$pins -path_delay max -group_path_count 1 -fields {fanout slew} -digits 1"; done
} > $W/paths.tcl
docker run --rm -v $W:/o openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /o/paths.tcl" 2>&1 | grep -v "^\[WARNING\|^OpenROAD\|^Features\|^This program\|^license" 
