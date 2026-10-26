`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_su_c (s81die-1011/ctrl, 2026-10-11): the SU slab master under the die command plane (--ctrl-adapters,
// physical/s81_ctrl/die_ctrl_bindings.json engine su = 1).  = dsfd_sp_su (s81-suhc-1011, main 28e66b4d4: full shape
// 3/3 exact, mutants FAIL) behind the *_c die-pin convention: c_cmd = {v, descriptor 84} from the sequencer c1 (pin
// flop), c_done = {v, tag 8} to d1 and c_st = {online, fault} to s1 (output flops); one stream clock for the
// controller side and the slab (the adapter's pulse CDC runs synchronous).  f_inp = the SU dependency net (head
// descriptor's VM operands present: the VM row-completion event), a die pin, never tied here.  +1 cycle each way.
// The hierarchical dsfd_sp_su_h replaces dsfd_sp_su with the same pins.
// DSFD_SUHC_STATIC_ISSUE (S-BIND 2026-10-15, owner static-cycle rule 2026-10-14T18:59): the die build has NO f_inp pin;
// the slab issues on the compiler-scheduled command edge (operands present by the static schedule, as the VM /
// selector engines' e_inputs_present 1).  Without the define the historical ready-driven f_inp pin remains (benches).
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_su_c #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16, SM_NVMAX = 40,
    parameter integer S_RD = 16, S_WR = 16, MUT = 0, AMUT = 0
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,                    // async die reset (active low)
    input  wire [84:0]         c_cmd,
    output reg  [8:0]          c_done,
    output reg  [1:0]          c_st,
`ifndef DSFD_SUHC_STATIC_ISSUE
    input  wire [0:0]          f_inp,
`endif
    output wire [S_RD-1:0]     rq_v,
    output wire [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output wire [S_WR-1:0]     wq_v,
    output wire [S_WR*14-1:0]  wq_row,
    output wire [S_WR*16-1:0]  wq_mask,
    output wire [S_WR*512-1:0] wq_d
);
    // the slab's fault code stays inside (diagnostic); the die fault is c_st[0] -> the sequencer's s<e> (no die sink
    // exists for a per-slab code: keeping it a pin left it unbound in the die port audit)
    wire [3:0] fcode;
    reg [1:0] rs_q;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    reg        cv_q;
    reg [83:0] cd_q;
    always @(posedge ck[0] or negedge rn) if (!rn) cv_q <= 1'b0; else cv_q <= c_cmd[84];
    always @(posedge ck[0]) cd_q <= c_cmd[83:0];
    wire dv, flt, onl;
    wire [7:0] dt;
    dsfd_sp_su #(.QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H), .SM_LPH(SM_LPH),
                 .SM_NVMAX(SM_NVMAX), .S_RD(S_RD), .S_WR(S_WR), .MUT(MUT), .AMUT(AMUT)) u_su (
        .cck(ck[0]), .crs(rn), .sk(ck[0]), .srs(rn), .c_cmd_v(cv_q), .c_cmd_d(cd_q), .c_done_v(dv), .c_done_tag(dt),
        .inp(`ifdef DSFD_SUHC_STATIC_ISSUE 1'b1 `else f_inp[0] `endif), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v), .rs_d(rs_d), .wq_v(wq_v), .wq_row(wq_row),
        .wq_mask(wq_mask), .wq_d(wq_d), .flt(flt), .online(onl), .fcode(fcode));
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin c_done <= 9'd0; c_st <= 2'b00; end
        else begin c_done <= {dv, dt}; c_st <= {onl, flt}; end
endmodule
