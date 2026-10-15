# Candidate fixture ONLY. ck_master is an unresolved physical boundary,
# never an ideal-source waiver for the full die. No false/multicycle paths.
# Registered divider Q outputs require propagated generated clocks + CTS.
create_clock -name master -period 0.277777778 -waveform {0 0.138888889} [get_ports ck_master]
# master edges are numbered rising1 falling2 rising3 falling4 ...
# /3 rises master E0, falls E1, rises E3: edge indices 1,3,7.
create_generated_clock -name stream -source [get_ports ck_master] -edges {1 3 7} [get_ports ck_stream]
# /4 rises E0, falls E2, rises E4: edge indices 1,5,9.
create_generated_clock -name serial -source [get_ports ck_master] -edges {1 5 9} [get_ports ck_serial]
set_clock_uncertainty -setup 0.060 [get_clocks {master stream serial}]
set_clock_uncertainty -hold 0.025 [get_clocks {master stream serial}]
# Explicit required delivered minimum pulse widths, including reset behavior.
# Actual library limits may be tighter and must ALSO be checked at SS/FF.
set_min_pulse_width -high 0.277777778 [get_clocks {stream serial}]
set_min_pulse_width -low 0.277777778 [get_clocks {stream serial}]
# Actual source jitter/duty error, macro CK minpulse, clock insertion/skew,
# reset recovery/removal and pin electrical loads remain external obligations.
