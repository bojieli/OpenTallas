`timescale 1ns/1ps
// ot_dsrom_engram_prefetch_h (el1011-ds-misc, 2026-10-11): the Engram prefetch buffer of ot_dsrom_engram_prefetch
// (8 slots x 24 columns x 8 beats x 512 b, eight SECDED72 words per beat, compact1536 addressing into 6 groups of 3
// 256x256 SRAMs; the top 192 bits of each bank-2 row are spare), rebuilt as a registered SRAM array for the
// 1188 x 432 um eng_SE outline of dsfd_engram_c.
//
// Why: the flat original read 18 macros spread over the outline through ONE combinational stage
// (6:1 x 576 b group mux -> 8 SECDED decoders -> |ue -> out_ue): pre-route reg2reg WNS -1569 ps; the write side drove
// 18 macros from one address / data register (-1141 ps).
//
// Structure (floorplan in physical/s81_ph_views/engram_c_h/macro_place.tcl: macros placed BY BANK, so each bank's
// 6:1 group select is local to one macro column; every macro has its own access registers in its left channel):
//   write  W1 wr_q / wa_q / wd_q (encode, as before)                                   -- next to the sink's write port
//          W2 per-bank copy {data lane, address, group one-hot & valid}                -- one per bank column
//          W3 per-macro {w_ce, w_addr, data}                                            -- in the macro's channel
//          the macro commits at the 4th edge after wr_v (the original: the 2nd); wr_pending covers W1..W3.
//   read   R1 per-bank copy {address, group one-hot & valid}
//          R2 per-macro {r_ce, r_addr}                       -> macro samples at the 3rd edge
//          R3 per-macro capture of rd_out (no logic before it) + select
//          R4 per-bank pair select (3 of 6)   R5 per-bank 3:1 select   R6 relay toward the VM pins
//          R7 SECDED decode registered (data, per-lane ce / ue)            R8 out_v / out_data / |ce / |ue
//          out_v follows rd_v by 9 cycles (the original: 2).  The VM consumes out_v (valid-tagged), not a fixed delay.
// Replicated registers are ot_v41_kreg instances (keep_hierarchy): Yosys opt_merge would fold identical copies.
module ot_dsrom_engram_prefetch_h #(
    parameter [71:0] READ_INJECT = 72'd0 // simulation exactness only, default off
) (
    input wire ck,rst_n,
    input wire wr_v,
    input wire [10:0] wr_addr, // {slot3,column5,beat3}; column<24
    input wire [511:0] wr_data,
    output wire wr_pending,
    input wire rd_v,
    input wire [10:0] rd_addr,
    output reg out_v,
    output reg [511:0] out_data,
    output reg out_ce,out_ue,
    output reg fault
);
    localparam integer NG = 6, NB = 3;
    wire wr_ok=wr_addr[7:3]<24;
    wire rd_ok=rd_addr[7:3]<24;
    wire [10:0] wr_compact=({8'd0,wr_addr[10:8]}<<7)+({8'd0,wr_addr[10:8]}<<6)+{3'd0,wr_addr[7:0]};
    wire [10:0] rd_compact=({8'd0,rd_addr[10:8]}<<7)+({8'd0,rd_addr[10:8]}<<6)+{3'd0,rd_addr[7:0]};
    wire [575:0] encoded;
    genvar lane,group,bank;
    generate for(lane=0;lane<8;lane=lane+1) begin:g_encode
        ot_s81_secded_enc72 u_enc(.d(wr_data[64*lane+:64]),.c(encoded[72*lane+:72]));
    end endgenerate

    // ---------------- W1 (as the original)
    reg wr_q;
    reg [10:0] wa_q;
    reg [575:0] wd_q;
    reg werr_q, rerr_q;          // address faults registered at their own port (write side / read side), then OR-ed
    always @(posedge ck or negedge rst_n) begin
        if(!rst_n) begin wr_q<=0;fault<=0;werr_q<=0;rerr_q<=0;end
        else begin
            wr_q<=wr_v&&wr_ok;
            werr_q<=wr_v&&!wr_ok; rerr_q<=rd_v&&!rd_ok;
            if(werr_q||rerr_q||out_ue) fault<=1;
        end
    end
    always @(posedge ck) begin wa_q<=wr_compact;wd_q<=encoded;end
    wire [5:0] w1_oh = {6{wr_q}} & (6'd1 << wa_q[10:8]);
    // ---------------- R0 -> R1 select (valid folded into the group one-hot)
    wire [5:0] r0_oh = {6{rd_v&&rd_ok}} & (6'd1 << rd_compact[10:8]);

    wire [5:0] w2_oh [0:NB-1];
    wire [7:0] w2_a  [0:NB-1];
    wire [255:0] w2_d [0:NB-1];
    wire [5:0] r1_oh [0:NB-1];
    wire [7:0] r1_a  [0:NB-1];
    wire [255:0] bm  [0:NB-1];         // R5 per-bank select out
    reg  [255:0] rl  [0:NB-1];         // R6 relay
    wire [NG*NB-1:0] w3_any, sel3_all;
    generate for(bank=0;bank<NB;bank=bank+1) begin:g_bank
        localparam integer BW = (bank < 2) ? 256 : 64;
        // W2 / R1: per-bank copies
        // (TEXTBOOK class 2: datapath copies carry no reset; only the valid / select one-hots are reset)
        ot_v41_kreg #(.W(8+BW), .AR(0)) u_w2d (.clk(ck), .arst_n(rst_n),
            .d({wd_q[256*bank+:BW], wa_q[7:0]}), .q({w2_d[bank][BW-1:0], w2_a[bank]}));
        ot_v41_kreg #(.W(6), .AR(1)) u_w2v (.clk(ck), .arst_n(rst_n), .d(w1_oh), .q(w2_oh[bank]));
        if (BW < 256) begin : g_pad assign w2_d[bank][255:BW] = {(256-BW){1'b0}}; end
        ot_v41_kreg #(.W(8), .AR(0)) u_r1a (.clk(ck), .arst_n(rst_n), .d(rd_compact[7:0]), .q(r1_a[bank]));
        ot_v41_kreg #(.W(6), .AR(1)) u_r1v (.clk(ck), .arst_n(rst_n), .d(r0_oh), .q(r1_oh[bank]));
        wire [BW-1:0] cap [0:NG-1];
        wire [NG-1:0] sel3;
        for(group=0;group<NG;group=group+1) begin:g_grp
            // W3 / R2: per-macro access registers (in the macro's left channel)
            wire w3_v, r2_v; wire [7:0] w3_a, r2_a; wire [BW-1:0] w3_d; wire [255:0] rd_out;
            ot_v41_kreg #(.W(8+BW), .AR(0)) u_w3d (.clk(ck), .arst_n(rst_n),
                .d({w2_d[bank][BW-1:0], w2_a[bank]}), .q({w3_d, w3_a}));
            ot_v41_kreg #(.W(1), .AR(1)) u_w3v (.clk(ck), .arst_n(rst_n), .d(w2_oh[bank][group]), .q(w3_v));
            ot_v41_kreg #(.W(8), .AR(0)) u_r2a (.clk(ck), .arst_n(rst_n), .d(r1_a[bank]), .q(r2_a));
            ot_v41_kreg #(.W(1), .AR(1)) u_r2v (.clk(ck), .arst_n(rst_n), .d(r1_oh[bank][group]), .q(r2_v));
            wire [255:0] wd_m;
            if (BW < 256) begin : g_wpad assign wd_m = {{(256-BW){1'b0}}, w3_d}; end
            else begin : g_wfull assign wd_m = w3_d; end
            ot_sram_1r1w_256x256_m2_r2c2 u_sram(
                .clk(ck),.r_ce_in(r2_v),.r_addr_in(r2_a),.rd_out(rd_out),
                .w_ce_in(w3_v),.w_addr_in(w3_a),.wd_in(wd_m),.w_mask_in({256{1'b1}}),
                .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
            // R3: capture flops straight off the macro (no logic before them) + the select
            // (r2_v is sampled by the macro at edge 3, rd_out is captured at edge 4: the select follows one stage later)
            reg [BW-1:0] cap_q; reg sm_q, s3_q;
            always @(posedge ck) cap_q <= rd_out[BW-1:0];
            always @(posedge ck or negedge rst_n) if(!rst_n) begin sm_q <= 1'b0; s3_q <= 1'b0; end
                                                 else begin sm_q <= r2_v; s3_q <= sm_q; end
            assign cap[group] = cap_q;
            assign sel3[group] = s3_q;
            assign w3_any[NB*group+bank] = w3_v;
            assign sel3_all[NB*group+bank] = s3_q;
        end
        // R4: pairs (groups 2k / 2k+1 are vertical neighbours in the bank column)
        reg [BW-1:0] p_q [0:2]; reg [2:0] ps_q;
        integer k;
        always @(posedge ck) for (k = 0; k < 3; k = k + 1)
            p_q[k] <= (cap[2*k] & {BW{sel3[2*k]}}) | (cap[2*k+1] & {BW{sel3[2*k+1]}});
        always @(posedge ck or negedge rst_n) if(!rst_n) ps_q <= 3'd0;
            else for (k = 0; k < 3; k = k + 1) ps_q[k] <= sel3[2*k] | sel3[2*k+1];
        // R5: 3:1
        reg [BW-1:0] m_q;
        always @(posedge ck) m_q <= (p_q[0] & {BW{ps_q[0]}}) | (p_q[1] & {BW{ps_q[1]}}) | (p_q[2] & {BW{ps_q[2]}});
        if (BW < 256) begin : g_mpad assign bm[bank] = {{(256-BW){1'b0}}, m_q}; end
        else begin : g_mfull assign bm[bank] = m_q; end
        // R6: relay toward the decode / VM pins
        always @(posedge ck) rl[bank] <= bm[bank];
    end endgenerate
    assign wr_pending = wr_q | (|w2_oh[0]) | (|w3_any);

    // valid pipeline: R1 .. R7 (out_v at R8)
    reg [6:0] rv_q;
    always @(posedge ck or negedge rst_n)
        if(!rst_n) rv_q <= 7'd0; else rv_q <= {rv_q[5:0], rd_v&&rd_ok};

    // R7: decode registered
    wire [575:0] read_code = {rl[2][63:0], rl[1], rl[0]};
    wire [511:0] decoded;
    wire [7:0] ce,ue;
    generate for(lane=0;lane<8;lane=lane+1) begin:g_decode
        ot_s81_secded_dec72 u_dec(.c(read_code[72*lane+:72]^(lane==0?READ_INJECT:72'd0)),
            .d(decoded[64*lane+:64]),.ce(ce[lane]),.ue(ue[lane]));
    end endgenerate
    reg [511:0] d7_q; reg [7:0] ce7_q, ue7_q; reg v7_q;
    always @(posedge ck) d7_q <= decoded;
    always @(posedge ck or negedge rst_n)
        if(!rst_n) begin v7_q<=0; ce7_q<=0; ue7_q<=0; end
        else begin v7_q<=rv_q[6]; ce7_q<=ce & {8{rv_q[6]}}; ue7_q<=ue & {8{rv_q[6]}}; end
    // (out_data / d7_q / rl / m_q / p_q / cap_q: datapath, no reset)
    // R8: out
    always @(posedge ck or negedge rst_n) begin
        if(!rst_n) begin out_v<=0;out_ce<=0;out_ue<=0;end
        else begin out_v<=v7_q;out_ce<=v7_q&&(|ce7_q);out_ue<=v7_q&&(|ue7_q);end
    end
    always @(posedge ck) out_data<=d7_q;
endmodule
