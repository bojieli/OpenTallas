Bench-only frozen as-built OVL REFERENCE (SQC-KDIE4 10-22), used by run_kv_d2d_sfm_miter_ovlref.sh / run_kv_d2d_sfm_guard_ovlref.sh /
run_d2d_dies_ovlref.sh when OVLM=1.  Byte copies of rtl/qwen_sys/d2d_static_20261015/{ot_qwen_d2d_static,ot_qwen_d2d_dies,
ot_qwen_d2d_dies_ovl,ot_qwen_d2d_dies_sfo}.sv at origin/claude/kv-d2d3-1020 (MU-D2D-OVL 0fc36caf5 + 353123a8d: as-built
cores with OVL / SAFE_RC parameters), where the OVL SFM3 miters PASSED.  Those reference hunks never reached main: main's
ot_qwen_d2d_dies_ovl.sv instantiates qkd_d2d_static_core #(.OVL(1)) with cal_*_rx / user ports the main core lacks, so every
OVLM=1 bench failed to build (route qkd_d2d_static_ovl_sfm3_cm3-cm3-9d4637e1a NEEDS_RTL, SFO_MITER_FAIL build).
The routed DUT (ot_qwen_d2d_sfm3.sv / ot_qwen_d2d_sfm.sv / ot_qwen_d2d_safe_fo.sv) is read from the tree unchanged; the only
modules it shares with these files (ot_qwen_d2d_cal, ot_qwen_d2d_kvn_rx) are byte-identical to the tree's.  Not synthesised.
