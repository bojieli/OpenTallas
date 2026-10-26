# Native59 placement publications are real physical copies.  A kept wire
# alone keeps its name, but opt_merge may still merge its driving flop.
# Transfer the RTL keep contract to the process-generated cells before
# the first synthesis optimisation (ORFS SYNTH_CANONICALIZE_TCL).
yosys proc
yosys attrmvcp -copy -attr keep
