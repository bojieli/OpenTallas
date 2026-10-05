`timescale 1ns/1ps
// Physical SCREEN wrapper of ot_qwen_kv_land_merge (characterization only, never instantiated in a
// design): every input and the grant output pass a register, so the routed timing is the element's own
// register-to-register paths (request -> grant, the two write stages) without block-boundary IO budgets.
module ot_qwen_kv_land_merge_screen #(parameter integer NSRC = 12, PW = 7, LW = 7, DW = 512) (
    input  wire clk, rst_n,
    input  wire [PW-1:0] rr_n, input wire [NSRC-1:0] s_v, input wire [NSRC*PW-1:0] s_port, input wire [NSRC*LW-1:0] s_loc,
    input  wire [NSRC-1:0] s_isk, s_ktail, input wire [NSRC*2-1:0] s_sel, input wire [NSRC*256-1:0] s_beat,
    input  wire [127:0] tail_lm, output reg [NSRC-1:0] s_grant_q,
    input  wire tok_v, input wire [LW-1:0] tok_loc, input wire [DW-1:0] tok_data, tok_mask,
    output wire kvw_ce, output wire [LW-1:0] kvw_addr, output wire [DW-1:0] kvw_data, kvw_mask
);
    reg [PW-1:0] rr_q; reg [NSRC-1:0] v_q, isk_q, kt_q; reg [NSRC*PW-1:0] port_q; reg [NSRC*LW-1:0] loc_q;
    reg [NSRC*2-1:0] sel_q; reg [NSRC*256-1:0] beat_q; reg [127:0] lm_q; reg tok_q; reg [LW-1:0] tl_q; reg [DW-1:0] td_q, tm_q;
    wire [NSRC-1:0] g;
    always @(posedge clk) begin
        rr_q <= rr_n; v_q <= s_v; port_q <= s_port; loc_q <= s_loc; isk_q <= s_isk; kt_q <= s_ktail; sel_q <= s_sel;
        beat_q <= s_beat; lm_q <= tail_lm; tok_q <= tok_v; tl_q <= tok_loc; td_q <= tok_data; tm_q <= tok_mask; s_grant_q <= g;
    end
    ot_qwen_kv_land_merge #(.NSRC(NSRC), .PW(PW), .LW(LW), .DW(DW)) u (
        .clk(clk), .rst_n(rst_n), .rr_n(rr_q), .s_v(v_q), .s_port(port_q), .s_loc(loc_q), .s_isk(isk_q), .s_ktail(kt_q),
        .s_sel(sel_q), .s_beat(beat_q), .tail_lm(lm_q), .s_grant(g), .tok_v(tok_q), .tok_loc(tl_q), .tok_data(td_q),
        .tok_mask(tm_q), .kvw_ce(kvw_ce), .kvw_addr(kvw_addr), .kvw_data(kvw_data), .kvw_mask(kvw_mask));
endmodule
