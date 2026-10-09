source /src/physical/dsrom_markov_lookup_localcapture/capture_anchor.tcl
source /src/physical/dsrom_markov_lookup_localcapture/electrical_env.tcl
# Measured master1.62x0.27um:258buffers add112.8492um2 before internal repair.
# One insertion at placement only; subsequent CTS/GRT hooks restore the load.
buffer_ports -outputs -buffer_cell BUFx24_ASAP7_75t_R -max_utilization 60 -verbose
