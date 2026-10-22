`timescale 1ns/1ps
// Opt-in successor; zero edge change, no resettable state, four real SRAMs.
module qfd_dv_s5_btab_safe (
    input  wire           ck,
    input  wire           bt_re,
    input  wire [8:0]     bt_word,
    output wire [255:0]   bt_q,
    input  wire           tw_we,
    input  wire [1:0]     tw_kind,
    input  wire [23:0]    tw_addr,
    input  wire [1023:0]  tw_data
);
    wire bt_w = tw_we && tw_kind == 2'd2;
    wire [4*256-1:0] bt_rd;
    genvar bk;
    generate for (bk = 0; bk < 4; bk = bk + 1) begin : g_btb
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ck), .r_ce_in(bt_re && bt_word[1:0] == bk[1:0]), .r_addr_in(bt_word[8:2]),
            .rd_out(bt_rd[bk*256 +: 256]), .w_ce_in(bt_w), .w_addr_in(tw_addr[8:2]),
            .wd_in(tw_data[256*bk +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // Four shared decodes, each feeds sixteen distinct kept select copies (max16).
    // Each copy controls sixteen bits. The mux precedes the existing capture edge:
    // q[n+1] = rd[n][bank[n-1]], identical to btcap[n+1][t2_bank[n+1]].
    wire [3:0] bank_oh = 4'b0001 << bt_word[1:0];
    genvar g;
    generate for (g=0;g<16;g=g+1) begin : g_read
        wire [3:0] sel;
        qfd_dv_s5_btab_sel_copy #(.ID(g)) u_sel (.ck(ck),.d(bank_oh),.q(sel));
        reg [15:0] q;
        wire [15:0] pick;
`ifdef OT_S5_BTAB_MUT
        assign pick = (bt_rd[256*0+16*g+:16] & {16{sel[1]}}) |
                      (bt_rd[256*1+16*g+:16] & {16{sel[0]}}) |
                      (bt_rd[256*2+16*g+:16] & {16{sel[3]}}) |
                      (bt_rd[256*3+16*g+:16] & {16{sel[2]}});
`else
        assign pick = (bt_rd[256*0+16*g+:16] & {16{sel[0]}}) |
                      (bt_rd[256*1+16*g+:16] & {16{sel[1]}}) |
                      (bt_rd[256*2+16*g+:16] & {16{sel[2]}}) |
                      (bt_rd[256*3+16*g+:16] & {16{sel[3]}});
`endif
        always @(posedge ck) q <= pick;
        assign bt_q[16*g+:16] = q;
    end endgenerate
endmodule

(* keep_hierarchy = 1 *)
module qfd_dv_s5_btab_sel_copy #(parameter integer ID=0)(input wire ck,input wire [3:0] d,output reg [3:0] q);
    (* keep = 1 *) wire [3:0] distinct = d;
    always @(posedge ck) q <= distinct;
endmodule
