`timescale 1ns/1ps
// Routed SRAM clock/capture context, full G4W16. Still a child, not a full die proof.
module ot_hdc_v41_fh_macro_ctx #(
    parameter integer W  = 16,
    parameter integer G  = 4,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer ALAT = 0,
    parameter integer CAPTURE = 0,
    parameter integer RETURN_EXTRA = 2,
    parameter integer PROTECT_SPLIT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              s3_v_in,          // the S3 valid that enters the engine's result valid line
    input  wire [1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1-1:0] a_tag_p_in,
    input  wire [G*W*32-1:0] res_in,
    input wire [G-1:0] wr_en,
    input wire [G*AW-1:0] wr_addr,
    input wire [G*W-1:0] wr_mask,
    input wire [G*W*32-1:0] wr_data,
    output wire [G-1:0]      ra_re,
    output wire [G*AW-1:0]   ra_addr,
    input  wire              go_fus,           // a fused op with i_iwe accepted (sets iw_pend)
    input  wire [AW-1:0]     i_iaddr,
    input  wire [4:0]        busy_in,          // active, e_v, s1_v, s1b_v, s2_v (s3_v is s3_v_in)
    input  wire [G-1:0]      o_we1_in,
    input  wire [G*AW-1:0]   o_addr1_in,
    input  wire [G*W-1:0]    o_mask1_in,
    input  wire [G*W-1:0]    leaf_mask_in,
    input  wire [NW-1:0]     leaf_row_in,
    input  wire              tv_in,            // tv[0] input (r_v && r_last && r_amax, as-built)
    input  wire              ov1_in,
    input  wire [NW-1:0]     am_idx_in,
    output reg  [1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1-1:0] r_tag,
    output reg               r_v,
    output wire [(1+32+NW)*G*W-1:0] leaf,
    output reg  [G-1:0]      o_we,
    output reg  [G*AW-1:0]   o_addr,
    output reg  [G*W-1:0]    o_mask,
    output reg  [G*W*32-1:0] o_data,
    output wire              fault,
    output reg [G*W*32+G*W+G*AW+G-1:0] result_capture,
    output wire [(1+32+NW)*(G*W/2)-1:0] argmax_level1
);
    wire [G*W*32-1:0] ra_q;
    wire [G*W-1:0] mem_valid,mem_corrected,mem_poison,mem_committed;
    wire memory_fault,child_fault;
    wire [G-1:0] child_we;
    wire [(1+32+NW)*G*W-1:0] child_leaf;
    ot_hdc_v41_fh_sram_return #(.W(W),.G(G),.AW(AW),.PROTECT_SPLIT(PROTECT_SPLIT)) u_memory (
        .clk(clk),.rst_n(rst_n),.rd_en(ra_re),.rd_addr(ra_addr),.rd_data(ra_q),
        .rd_valid(mem_valid),.corrected(mem_corrected),.poisoned(mem_poison),
        .wr_en(wr_en),.wr_addr(wr_addr),.wr_mask(wr_mask),.wr_data(wr_data),
        .wr_committed(mem_committed),.fault(memory_fault));
    ot_hdc_v41_fh_ctx #(.W(W),.G(G),.IL(IL),.AW(AW),.NW(NW),.ALAT(ALAT),
        .CAPTURE(CAPTURE),.RETURN_EXTRA(RETURN_EXTRA)) u_head (
        .clk(clk),.rst_n(rst_n),.ra_re(ra_re),.ra_addr(ra_addr),.ra_q(ra_q),
        .o_we(child_we),.leaf(child_leaf),.fault(child_fault),
        .s3_v_in(s3_v_in),
        .a_tag_p_in(a_tag_p_in),
        .res_in(res_in),
        .go_fus(go_fus),
        .i_iaddr(i_iaddr),
        .busy_in(busy_in),
        .o_we1_in(o_we1_in),
        .o_addr1_in(o_addr1_in),
        .o_mask1_in(o_mask1_in),
        .leaf_mask_in(leaf_mask_in),
        .leaf_row_in(leaf_row_in),
        .tv_in(tv_in),
        .ov1_in(ov1_in),
        .am_idx_in(am_idx_in),
        .r_tag(r_tag),
        .r_v(r_v),
        .o_addr(o_addr),
        .o_mask(o_mask),
        .o_data(o_data));
    assign fault=child_fault||memory_fault;
`ifndef SYNTHESIS
    initial if(RETURN_EXTRA!=2+PROTECT_SPLIT) $fatal(1,"Protected SRAM return and head latency mismatch");
`endif
    assign o_we=fault?{G{1'b0}}:child_we;
    for(genvar l=0;l<G*W;l=l+1) begin : g_leaf_fault
        localparam integer CW=1+32+NW;
        assign leaf[l*CW+:CW]={child_leaf[l*CW+CW-1]&&!fault,child_leaf[l*CW+:CW-1]};
    end
    // Actual result-port receiving registers and the first existing argmax
    // tree level bound this child. They add loads, not production stages.
    always @(posedge clk) result_capture <= {o_we,o_addr,o_mask,o_data};
    for(genvar p=0;p<G*W/2;p=p+1) begin : g_argmax_consumer
        localparam integer CW=1+32+NW;
        wire [CW-1:0] x0=leaf[CW*(2*p)+:CW];
        wire [CW-1:0] x1=leaf[CW*(2*p+1)+:CW];
        wire x0_wins=x0[CW-1]&&(!x1[CW-1]||x0[CW-2-:32]>x1[CW-2-:32]||
            (x0[CW-2-:32]==x1[CW-2-:32]&&x0[NW-1:0]<x1[NW-1:0]));
        reg [CW-1:0] c;
        always @(posedge clk) c<=x0_wins?x0:x1;
        assign argmax_level1[CW*p+:CW]=c;
    end
endmodule
