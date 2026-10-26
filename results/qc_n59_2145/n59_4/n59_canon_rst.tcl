# PATH-QC-N59-4 trial: Codex driver-keep canonicalisation, then the standard regional reset-copy split
# (physical/common_flow/ot_rst_copies, main cfea7b3a1): native59 rst_cp_* families held N kept identical copies but every
# load stayed on copy [0] (current3 census: 4040 reset pins > 405 um), because SYNTH_CANONICALIZE_TCL replaced ot_keep_regs.tcl.
source /work/n59_keep_replicas.tcl
source /work/ot_rst/ot_rst_copies.tcl
