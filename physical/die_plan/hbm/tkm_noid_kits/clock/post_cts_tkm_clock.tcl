# F4 only rewires local flop clock leaves; no legacy tap-input alignment.
source /work/f4_chain_leaf.tcl
# Balance means after F4 has finished, preserving the selected graph/topology.
ot_dtsh::closed_loop {*}$::ot_dtsh::cl_args measure_sinks _sink
ot_dtsh::audit
ot_hbmentry::check
