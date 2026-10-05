// ---------------------------------------------------------------------------
// DS-ROM (DeepSeek-V4.1-Flash, S81) CANONICAL BASELINE flags, every adopted lever ON
// (integration checkpoint 2026-10-04; results/arch/dsrom_baseline_config_20261004/config.json).
//
// The as-built sources keep their default-off parameters (pinned files byte-identical, old
// configurations reproducible); a successor top includes this header and passes these values.
// Excluded (rejected / parked) variants are listed in config.json and have no flag here.
// ---------------------------------------------------------------------------
`ifndef DSROM_BASELINE_FLAGS_SVH
`define DSROM_BASELINE_FLAGS_SVH
// wavefront verify (rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv, S81: ot_rom_pkg_ctrl_wf_s81)
`define DSROM_BL_PKG_WAVE          1
`define DSROM_BL_PKG_WAVE_WIN      6
// re-index layers L24/L28/L32/L36: candidate-block gather + mask-drop, position-slotted lists
// (rtl/dsrom_sys/integration/ot_dsrom_reindex_chain.sv; 2^LSW >= WIN lists per stack)
`define DSROM_BL_REINDEX_KGATHER   1
`define DSROM_BL_REINDEX_MDROP     1
`define DSROM_BL_REINDEX_LSW       3
// L1 fused DSpark draft head on the S81 head argmax (rtl/dsrom_sys/integration/ot_dsrom_s81_head_amax_fh.sv)
`define DSROM_BL_HEAD_FH           1
// packed WINDOW KV load (rtl/chip/ot_dsrom_window_stream_la.sv); binding on claude/dsrom-s81-window-bind-20261004
`define DSROM_BL_WINDOW_STREAM     1
`define DSROM_BL_WINDOW_STREAM_IW  8
// per-user cross-stage staged state under WAVE: position slots >= WIN (DS-ROM correctness 2026-10-04,
// results/rtl/dsrom_correctness_20261004).  SIDE (multicast) staging: ot_rom_pkg_ctrl_wf_ps SIDE_PSL (slot = position
// mod 2^SIDE_PSL, per-(user, slot) counts, core_side_off added by the memory wrapper to staging reads); SIDE_PSH = log2
// of the stage's whole SIDE staging span (words), so 2^(SIDE_PSL + SIDE_PSH) <= 2^SIDE_USH.  Hop-relayed state
// (tools/hdc_program_v41_array.py `relay`, the S81 controller's mode) is per position by construction: no flag.
`define DSROM_BL_SIDE_PSL          3
// ROM element second-macro row decode (entry 2NSEG+1+s -> s_row[NSEG+s]): fixed in place in ot_v41_rom_elem_w10 and
// every copy (no flag; every image with an 8-segment pair must be rebuilt from the fixed source)
// S81 die configuration: one die per rank, 12 head dies (results/rtl/dsrom_s81_fulldie_20261004)
`define DSROM_BL_HEAD_DIES         12
`endif
