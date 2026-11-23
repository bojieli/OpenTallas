`timescale 1ns/1ps
// btab_s4r (FAM-QC-HCST-R3, COORD/FIX-LEDGER rc97): qfd_dv_s5_btab_s4 + ONE read-pipeline stage (+1 cycle on bt_q).
// SRAM rd_out is captured straight into a 1024-bit stage register (no logic between macro Q and flop), then the
// existing bank AND-OR select and q capture run from that register. Select copies get a second delay so the
// select stays aligned with its data. Latency contract: q(t+1) of s4 appears at t+2 here.
module qfd_dv_s5_btab_s4r (
 input wire ck,bt_re,input wire [8:0]bt_word,
 output wire [127:0]bt_ql,bt_qh,
 input wire tw_we,input wire [1:0]tw_kind,input wire [23:0]tw_addr,input wire [511:0]tw_lo,tw_hi
);
    wire [1023:0] tw_data = {tw_hi,tw_lo};
    wire bt_w = tw_we && tw_kind == 2'd2;
    wire [1023:0] bt_rd;
    reg  [1023:0] rd_q;
    genvar bk;
    generate for (bk = 0; bk < 4; bk = bk + 1) begin : g_btb
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ck), .r_ce_in(bt_re && bt_word[1:0] == bk[1:0]), .r_addr_in(bt_word[8:2]),
            .rd_out(bt_rd[bk*256 +: 256]), .w_ce_in(bt_w), .w_addr_in(tw_addr[8:2]),
            .wd_in(tw_data[256*bk +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    always @(posedge ck) rd_q <= bt_rd;                    // new stage: macro Q -> flop, no logic
    wire [3:0] bank_oh = 4'b0001 << bt_word[1:0];
    wire [255:0] bt_q;
    genvar g;
    generate for (g=0;g<16;g=g+1) begin : g_read
        wire [3:0] sel;
        qfd_dv_s5_btab_sel_copy2 #(.ID(g)) u_sel (.ck(ck),.d(bank_oh),.q(sel));   // 2-stage select
        reg [15:0] q;
        wire [15:0] pick = (rd_q[256*0+16*g+:16] & {16{sel[0]}}) | (rd_q[256*1+16*g+:16] & {16{sel[1]}}) |
                           (rd_q[256*2+16*g+:16] & {16{sel[2]}}) | (rd_q[256*3+16*g+:16] & {16{sel[3]}});
        always @(posedge ck) q <= pick;
        assign bt_q[16*g+:16] = q;
    end endgenerate
    assign bt_ql = bt_q[127:0];
    assign bt_qh = bt_q[255:128];
endmodule

(* keep_hierarchy = 1 *)
module qfd_dv_s5_btab_sel_copy2 #(parameter integer ID=0)(input wire ck,input wire [3:0] d,output reg [3:0] q);
    (* keep = 1 *) wire [3:0] distinct = d;
    reg [3:0] m;
    always @(posedge ck) begin m <= distinct; q <= m; end
endmodule
