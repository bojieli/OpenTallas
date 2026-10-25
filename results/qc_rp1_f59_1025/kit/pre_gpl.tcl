# PATH-QC-RP1-F59 PRE_GLOBAL_PLACE (GEOM-REVIEW F6 amend on f58, SRAMIF recipe): pin registers at their faces
# (face_flops.tcl, unchanged), then the per-bank macro-interface registers (RTL MIF=1: u_rce/u_ra/u_we/u_wa/u_wd per SRAM,
# decode in front) and the rd_out capture registers anchored FIRM at their SRAM pin edge (main physical/common_flow/
# macro_pin_flops.tcl, unchanged; anchor_row_packing.tcl legalises).  f58's mif_anchor.tcl clone step is retired (MIF=1
# gives every SRAM its own registers in RTL).  Released for DPL by pre_dpl.tcl.
source /work/face_flops.tcl
source /work/cf/macro_pin_flops.tcl
