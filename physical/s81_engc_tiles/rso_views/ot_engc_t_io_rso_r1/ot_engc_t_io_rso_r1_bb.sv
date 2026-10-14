// Physical symbol derived from actual matching TT/FF/SS ETM pins.
// Use source RTL for simulation; native slot/source binding remains open.
(* blackbox, keep_hierarchy *) module ot_engc_t_io_rso_r1 (
    input wire [84:0] c_cmd,
    output wire [8:0] c_done,
    output wire [1:0] c_st,
    output wire [2:0] cfg_o,
    input wire ck,
    input wire [2:0] f_cfg,
    input wire [15:0] f_vm,
    input wire jf_i,
    output wire [17:0] jn_o,
    input wire [7:0] perr_i,
    output wire [7:0] r0_a,
    output wire [5:0] r0_oh,
    output wire [7:0] r1_a,
    output wire [5:0] r1_oh,
    output wire [7:0] r2_a,
    output wire [5:0] r2_oh,
    input wire [255:0] rd0,
    input wire [255:0] rd1,
    input wire [63:0] rd2,
    input wire [7:0] rdy_i,
    output wire rso,
    input wire rst,
    output wire [531:0] t_vm,
    output wire [3:0] vrel_o,
    input wire werr_i,
    input wire [15:0] wn_i
);
endmodule
