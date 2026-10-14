`timescale 1ns/1ps
// Exact original wrapper face flops, moved into an independent hard root. PHY routing stays in the core.
module hfd_lk_ep_face #(parameter integer MUT_FACE=0)(input wire clk, input wire rst_n,
    inout wire [1119:0] f_lk,
    output wire core_t_v, output wire [544:0] core_t_flit, output wire core_r_cr, output wire [23:0] core_session,
    input wire t_cr, r_v, input wire [544:0] r_flit, input wire fault, locked);
    reg  [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg [1:0] rw;                              // [0] input-side registers, [1] output-side registers
    always @(posedge clk) rw <= {2{rs[1]}};

    reg [23:0] session;                                   // pin register (changes only under the coordinated reset)
    always @(posedge clk) session <= f_lk[1117:1094];
    // el1011-hbm-lkep: centre-channel floorplan -> the core sits ~900 um from the east-face pins: pin flop + 2 relay stages
    // each way (every hop < ~350 um).  +1 edge on t_v / r_cr, +2 on r_v / t_cr: the die credit loop grows by 3 edges
    // (TXQ 32 covers it; tb_lk_rate FS models the face stages).
    reg            t_v_q, r_cr_q, t_v_r, r_cr_r, t_v_s, r_cr_s;
    reg  [544:0]   t_f_q, t_f_r, t_f_s;
    always @(posedge clk or negedge rw[0]) if (!rw[0]) begin t_v_q <= 1'b0; r_cr_q <= 1'b0; t_v_r <= 1'b0; r_cr_r <= 1'b0; t_v_s <= 1'b0; r_cr_s <= 1'b0; end
                                           else begin t_v_q <= f_lk[0]; r_cr_q <= f_lk[546]; t_v_r <= t_v_q; r_cr_r <= r_cr_q; t_v_s <= t_v_r; r_cr_s <= r_cr_r; end
    always @(posedge clk) begin t_f_q <= f_lk[545:1]; t_f_r <= t_f_q; t_f_s <= t_f_r; end



    reg            r_v_o, t_cr_o, fault_q, locked_q, r_v_m1, r_v_m2, t_cr_m1, t_cr_m2;
    reg  [544:0]   r_flit_o, r_flit_m1, r_flit_m2;
    always @(posedge clk or negedge rw[1]) if (!rw[1]) begin r_v_o <= 1'b0; t_cr_o <= 1'b0; fault_q <= 1'b0; locked_q <= 1'b0;
                                                             r_v_m1 <= 1'b0; r_v_m2 <= 1'b0; t_cr_m1 <= 1'b0; t_cr_m2 <= 1'b0; end
                                           else begin r_v_m1 <= r_v; r_v_m2 <= r_v_m1; r_v_o <= r_v_m2; t_cr_m1 <= t_cr; t_cr_m2 <= t_cr_m1;
                                                      t_cr_o <= t_cr_m2; fault_q <= fault; locked_q <= locked; end
    always @(posedge clk) begin r_flit_m1 <= r_flit; r_flit_m2 <= r_flit_m1; r_flit_o <= r_flit_m2; end
    assign f_lk[547] = r_v_o;
    assign f_lk[1092:548] = r_flit_o ^ (MUT_FACE != 0 ? 545'd1 : 545'd0);
    assign f_lk[1093] = t_cr_o;
    assign f_lk[1119:1118] = {locked_q, fault_q};

    assign core_t_v = t_v_s;
    assign core_t_flit = t_f_s;
    assign core_r_cr = r_cr_s;
    assign core_session = session;
endmodule
