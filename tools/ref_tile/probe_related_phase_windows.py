#!/usr/bin/env python3
"""Generate diagnostic scalar ETMs verifying related 3:4 edge windows in STA.

This is synthetic phase calibration and never qualifies a production tile.
Both directions, rising and falling capture, and setup/hold must be present.
"""
import argparse
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--serial-period', type=float, default=1111.110666666667, help='Diagnostic mutant injection; expected windows stay fixed')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    cells = []
    for name, edge in [('rise', 'rising'), ('fall', 'falling')]:
        cells.append(f'''cell({name}) {{area:1;
 pin(C) {{direction:input;clock:true;capacitance:0;}}
 pin(D) {{direction:input;capacitance:0;
  timing() {{related_pin:"C";timing_type:setup_{edge};rise_constraint(scalar) {{values("50");}} fall_constraint(scalar) {{values("50");}}}}
  timing() {{related_pin:"C";timing_type:hold_{edge};rise_constraint(scalar) {{values("20");}} fall_constraint(scalar) {{values("20");}}}}
 }}
 pin(Q) {{direction:output;
  timing() {{related_pin:"C";timing_type:{edge}_edge;timing_sense:non_unate;
   cell_rise(scalar) {{values("100");}} cell_fall(scalar) {{values("100");}}
   rise_transition(scalar) {{values("1");}} fall_transition(scalar) {{values("1");}}
  }}
 }}
}}''')
    (a.out/'phase.lib').write_text('''library(phase) {
 delay_model:table_lookup;time_unit:"1ps";voltage_unit:"1V";current_unit:"1mA";pulling_resistance_unit:"1kohm";capacitive_load_unit(1,pf);
 nom_voltage:1;nom_temperature:25;nom_process:1;
 input_threshold_pct_rise:50;input_threshold_pct_fall:50;output_threshold_pct_rise:50;output_threshold_pct_fall:50;
 slew_lower_threshold_pct_rise:20;slew_upper_threshold_pct_rise:80;slew_lower_threshold_pct_fall:20;slew_upper_threshold_pct_fall:80;
'''+'\n'.join(cells)+'\n}\n')
    libpath = a.out/'phase.lib'
    libpath.write_text(libpath.read_text().replace(':', ' : '))
    # core rising->serial rising/falling; serial rising->core rising/falling.
    (a.out/'phase.v').write_text('''module phase(input c,s);
wire a,b;
rise core(.C(c),.Q(a));
rise serial(.C(s),.Q(b));
rise cr(.C(s),.D(a)); fall cf(.C(s),.D(a));
rise sr(.C(c),.D(b)); fall sf(.C(c),.D(b));
endmodule
''')
    (a.out/'phase.tcl').write_text('''read_liberty /probe/phase.lib
read_verilog /probe/phase.v
link_design phase
create_clock -name core -period 833.333 [get_ports c]
create_clock -name serial -period 1111.110666666667 [get_ports s]
foreach {src dst window holdwindow} {core cr 277.777666666667 0 core cf 277.777666666667 0 serial sr 277.777666666667 0 serial sf 138.888833333333 138.888833333333} {
 foreach kind {max min} {
  set paths [find_timing_paths -from [get_pins $src/Q] -to [get_pins $dst/D] -path_delay $kind -group_path_count 1]
  if {![llength $paths]} {error "missing $src->$dst $kind"}
  set slack [get_property [lindex $paths 0] slack]
  set expected [expr {$kind eq "max" ? $window-150 : 80+$holdwindow}]
  if {abs($slack-$expected)>0.02} {error "phase mismatch $src->$dst $kind got$slack expected$expected"}
  puts "PHASE_PATH $src $dst $kind slack=$slack expected=$expected"
 }
}
report_checks -path_delay max -format full_clock_expanded -group_path_count 8
report_checks -path_delay min -format full_clock_expanded -group_path_count 8
puts "PHASE_PASS synthetic diagnostic only"
exit
'''.replace('1111.110666666667', str(a.serial_period)))


if __name__ == '__main__':
    main()
