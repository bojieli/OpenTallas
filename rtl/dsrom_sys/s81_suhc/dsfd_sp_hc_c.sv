`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_hc_c (s81die-1011/ctrl, 2026-10-11): the HC slab master under the die command plane (--ctrl-adapters,
// physical/s81_ctrl/die_ctrl_bindings.json engine hc = 2).  = dsfd_sp_hc (s81-suhc-1011: ot_s81_engine_adapter QD 8 +
// ot_s81_hc_core, gate tools/s81_suhc/hc_gate.py PASS) behind the *_c die-pin convention of the other slab masters
// (ot_s81_slab_ep): c_cmd = {v, descriptor 84} from dsfd_stage_seq c2 (pin flop), c_done = {v, tag 8} to d2 and
// c_st = {online, fault} to s2 (output flops).  One stream clock (ck) for the controller and the slab (stream_1p2
// under --suhc-1011; the adapter's pulse CDC stays and runs synchronous).
// f_inp is the die dependency net of the HC (head descriptor's VM operands present: the VM row-completion event of the
// producing stage, s81-ctl); it is a die pin, never tied here.  Latency vs dsfd_sp_hc: +1 cycle each way.
// DSFD_SUHC_STATIC_ISSUE (S-BIND 2026-10-15, owner static-cycle rule 2026-10-14T18:59): the die build has NO f_inp pin;
// the slab issues on the compiler-scheduled command edge (operands present by the static schedule, as the VM /
// selector engines' e_inputs_present 1).  Without the define the historical ready-driven f_inp pin remains (benches).
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_hc_c #(
    parameter integer NG = 256, D = 5120, S_RD = 2, S_WR = 8, S_RT = 4, HIER = 0, HALF = 0, CSPLIT = 0, TAIL_SPLIT = 0, MUT = 0, AMUT = 0,
    // pass-through of the slab's remaining structural parameters (defaults = dsfd_sp_hc's own: no change unless set)
    parameter integer HEAD_ROWS = 10, CNL_PIN = 0, CHAIN_STEP = 4,
    parameter integer PIPE = 1, PIPE_PD = 40,            // POST issue-order done (hierarchical slab; see ot_s81_hc_cseq)
    parameter integer NTREE = 0, NT_K = 67               // NORM tree variant (dsfd_sp_hc NTREE; default 0 = unchanged)
) (
    output wire [TFW-1:0] t_tf0,t_tf1,t_tf2,
    input wire [TRW-1:0] f_tr0,f_tr1,f_tr2,
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,                    // async die reset (active low)
    input  wire [84:0]         c_cmd,
    output reg  [8:0]          c_done,
    output reg  [1:0]          c_st,
`ifndef DSFD_SUHC_STATIC_ISSUE
    input  wire [0:0]          f_inp,
`endif
    input  wire                y_v,
    output wire                y_rdy,
    input  wire [NG*32-1:0]    y_d,
    output wire [S_RD-1:0]     rq_v,
    output wire [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output wire [S_WR-1:0]     wq_v,
    output wire [S_WR*14-1:0]  wq_row,
    output wire [S_WR*16-1:0]  wq_mask,
    output wire [S_WR*512-1:0] wq_d
);
    localparam integer TFW=(72+16*S_RD)+((S_RD*512>((NG/8+2)/3)*8*32)?S_RD*512:((NG/8+2)/3)*8*32)+S_RD+5+129;
    localparam integer TRW=S_RT+24*S_RT+8+512*S_RT+S_RT+4;
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
    dsfd_sp_hc #(.NG(NG), .D(D), .S_RD(S_RD), .S_WR(S_WR), .MUT(MUT), .AMUT(AMUT),.S_RT(S_RT),.HIER(HIER),.HALF(HALF),.CSPLIT(CSPLIT),.TAIL_SPLIT(TAIL_SPLIT),
                 .HEAD_ROWS(HEAD_ROWS),.CNL_PIN(CNL_PIN),.CHAIN_STEP(CHAIN_STEP),.PIPE(PIPE),.PIPE_PD(PIPE_PD),.NTREE(NTREE),.NT_K(NT_K)) u_hc (
        .t_tf0(t_tf0),.t_tf1(t_tf1),.t_tf2(t_tf2),.f_tr0(f_tr0),.f_tr1(f_tr1),.f_tr2(f_tr2),
        .cck(ck[0]), .crs(rn), .sk(ck[0]), .srs(rn), .c_cmd_v(cv_q), .c_cmd_d(cd_q), .c_done_v(dv), .c_done_tag(dt),
        .inp(`ifdef DSFD_SUHC_STATIC_ISSUE 1'b1 `else f_inp[0] `endif), .y_v(y_v), .y_rdy(y_rdy), .y_d(y_d), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v), .rs_d(rs_d),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .flt(flt), .online(onl), .fcode(fcode));
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin c_done <= 9'd0; c_st <= 2'b00; end
        else begin c_done <= {dv, dt}; c_st <= {onl, flt}; end
endmodule
