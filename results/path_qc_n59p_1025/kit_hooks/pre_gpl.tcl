# PATH-QC-N59-PROTO native59 STN prototype: face (pin) registers at their faces, then the QB_STN stations on the
# pin -> SRAM-face paths (n59_stations.tcl), then the macro-pin flops (write-face replicas u_wc / u_wd, read-port u_rm,
# rd_out captures u_rdq) anchored FIRM at their SRAM pins (main physical/common_flow/macro_pin_flops.tcl @ 2cf25f6d7).
source /work/face_flops.tcl
source /work/n59_stations.tcl
source /work/cf/macro_pin_flops.tcl
