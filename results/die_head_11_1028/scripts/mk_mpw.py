"""add one DFFHQNx1 sink per clock tap (at the tap pin xy) so OpenSTA min_pulse_width checks real register clock pins"""
import re, sys
D = sys.argv[1]
v = open(f"{D}/combo.v").read(); t = open(f"{D}/duty.tcl").read()
taps = re.findall(r"assign\s+(t_\w+)\s*=\s*(\w+)\s*;", v)
xy = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(r"place_pin -pin_name (t_\w+) -layer \w+ -location \{([\d.]+) ([\d.]+)\}", t)}
inst = "".join(f"  DFFHQNx1_ASAP7_75t_R mpw_{p} (.CLK({n}), .D(1'b0), .QN());\n" for p, n in taps)
i = v.index("endmodule", v.index("module die_combo")); v = v[:i] + inst + v[i:]
open(f"{D}/combo_mpw.v", "w").write(v)
pl = "".join(f"ot_place mpw_{p} {xy[p][0]:.3f} {max(0.0, xy[p][1]-2.0):.3f} R0\n" for p, _ in taps if p in xy)
t = t.replace("read_verilog /out/combo.v", "read_verilog /out/combo_mpw.v")
k = t.index('puts "OT_T clockplaced'); t = t[:k] + pl + t[k:]
t = t.replace("report_check_types -min_pulse_width -verbose > /out/mpw_$::env(CORNER).rpt",
              "report_check_types -min_pulse_width -verbose > /out/mpw_$::env(CORNER).rpt\nreport_check_types -min_pulse_width -violators > /out/mpw_viol_$::env(CORNER).rpt")
t = t.replace("report_pulse_width_checks >> /out/mpw_$::env(CORNER).rpt\n", "")
open(f"{D}/mpw.tcl", "w").write(t); print(len(taps), "sinks", len(xy), "placed")
