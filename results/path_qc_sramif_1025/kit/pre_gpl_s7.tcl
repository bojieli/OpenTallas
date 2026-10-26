# PATH-QC-SRAMIF s7 PRE_GLOBAL_PLACE (GEOM-REVIEW F6 fix, 2026-10-25): pin registers at their faces (face_flops.tcl,
# unchanged), then the per-SRAM macro-interface registers (RTL MIF=1: one rce/ra/we/wa/wd landing register set per SRAM,
# decode in front) and the rd_out capture registers anchored FIRM at their SRAM pin edge (physical/common_flow/
# macro_pin_flops.tcl, shared tool, unchanged; anchor_row_packing.tcl legalises).  Released for DPL by pre_dpl_s7.tcl.
source /work/face_flops.tcl
source /work/cf/macro_pin_flops.tcl
