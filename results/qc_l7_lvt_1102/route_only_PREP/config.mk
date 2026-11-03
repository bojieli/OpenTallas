# PRIVATE route-only diagnostic PREP; original immutable inputs remain /work.
include /work/config.mk
override export OT_MM_FF_SDC = /route/vclk_ff.sdc
override export ADDITIONAL_LEFS = /work/macros/ot_sram_1r1w2c_128x64_m1.lef /work/asap7sc7p5t_28_L_1x_220121a.lef
override export PRE_DETAIL_ROUTE_TCL = /route/pre.tcl
override export POST_DETAIL_ROUTE_TCL = /route/post.tcl
