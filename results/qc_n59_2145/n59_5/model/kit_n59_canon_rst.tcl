# PATH-QC-N59-5: Codex driver-keep canonicalisation, then the STANDARD keep hook physical/common_flow/ot_keep_regs.tcl
# (per-bit techmap + keep on every cell driving a keep wire, then ot_rst_copies.tcl because OT_RST_COPIES_MAX is set;
# GEOM-REVIEW-11 23:44 fix (2)).  Sourcing ot_rst_copies.tcl alone (N59-4 rstB, N59-5 first synth) split the loads but
# the vector rst_cp_* cells had keep only as multi-bit cells: techmap split them without keep and opt_merge folded every
# family back to copy [0] (10 rst_cp flops in 1_2_yosys.v; rstB reset census 3901 pins > 405 um).
source /work/n59_keep_replicas.tcl
source /work/cf/ot_keep_regs.tcl
