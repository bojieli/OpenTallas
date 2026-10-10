# tap_latency.py (vm8-seam): the die balances every tap leaf to REF; source latency = REF - tap mean insertion
# TT taps {"cke0": 125.6, "cke1": 160.5, "cke2": 165.5, "cke3": 119.6, "cks0": 171.3, "cks1": 105.8, "ckw0": 212.3, "ckw1": 182.8, "ckw2": 144.4, "ckw3": 115.9}
# FF taps {"cke0": 102.4, "cke1": 135.6, "cke2": 138.9, "cke3": 97.5, "cks0": 144.2, "cks1": 85.0, "ckw0": 178.8, "ckw1": 151.9, "ckw2": 121.4, "ckw3": 95.1}
if {[llength [get_libs -quiet *_FF_*]]} {
  set_clock_latency -source 76.5 [get_ports -quiet {cke0[0]}]
  set_clock_latency -source 43.2 [get_ports -quiet {cke1[0]}]
  set_clock_latency -source 40.0 [get_ports -quiet {cke2[0]}]
  set_clock_latency -source 81.3 [get_ports -quiet {cke3[0]}]
  set_clock_latency -source 34.6 [get_ports -quiet {cks0[0]}]
  set_clock_latency -source 93.8 [get_ports -quiet {cks1[0]}]
  set_clock_latency -source 0.0 [get_ports -quiet {ckw0[0]}]
  set_clock_latency -source 27.0 [get_ports -quiet {ckw1[0]}]
  set_clock_latency -source 57.4 [get_ports -quiet {ckw2[0]}]
  set_clock_latency -source 83.7 [get_ports -quiet {ckw3[0]}]
} else {
  set_clock_latency -source 86.7 [get_ports -quiet {cke0[0]}]
  set_clock_latency -source 51.8 [get_ports -quiet {cke1[0]}]
  set_clock_latency -source 46.8 [get_ports -quiet {cke2[0]}]
  set_clock_latency -source 92.6 [get_ports -quiet {cke3[0]}]
  set_clock_latency -source 41.0 [get_ports -quiet {cks0[0]}]
  set_clock_latency -source 106.5 [get_ports -quiet {cks1[0]}]
  set_clock_latency -source 0.0 [get_ports -quiet {ckw0[0]}]
  set_clock_latency -source 29.5 [get_ports -quiet {ckw1[0]}]
  set_clock_latency -source 67.9 [get_ports -quiet {ckw2[0]}]
  set_clock_latency -source 96.4 [get_ports -quiet {ckw3[0]}]
}
