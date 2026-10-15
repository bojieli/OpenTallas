// el1011-hbm-sfu 2026-10-12: listed FIRST in the ot_su12_sfu lane-cluster (tools/ref_tile kind=cluster) sources so the
// lane instantiates ot_hdc_v41x_sfu_chain as its hard child (no parameter overrides) and the chain RTL body is
// excluded from the cluster synthesis.  Simulation / benches do not read this file (same words, chain as RTL).
`define OT_SFU_CHAIN_HARD
