(* blackbox *) module ot_sram_1r1w_64x512_m1_r2c2(input clk,r_ce_in,w_ce_in,input[5:0]r_addr_in,w_addr_in,input[511:0]wd_in,w_mask_in,output[511:0]rd_out,input[1:0]rr_en,cr_en,input[11:0]rr_addr,input[17:0]cr_sel); endmodule
module ot_hep_rx_leaf #(parameter integer W = 306, parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          we,
    input  wire [5:0]    wa,
    input  wire [5:0]    ra,
    input  wire [W-1:0]  din,
    output reg  [W-1:0]  dout
);
    reg wq; reg [5:0] aq; reg [W-1:0] dq;
    wire [511:0] mr;
`ifdef OT_HEP_RAM_F6
    // Physical profile: retain the existing per-leaf capture flops instead of merging
    // identical payload/address captures across distant SRAM interfaces. No new edge.
    (* keep *)
`endif
    always @(posedge ck) begin wq <= we; aq <= wa; dq <= din; end
    ot_sram_1r1w_64x512_m1_r2c2 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in({{(512-W){1'b0}}, dq}),
        .w_mask_in({{(512-W){1'b0}}, {W{1'b1}}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
`ifdef OT_HEP_RAM_F6
    (* keep *)
`endif
    always @(posedge ck) dout <= mr[W-1:0] ^ (MUT != 0 ? {{(W-1){1'b0}}, 1'b1} : {W{1'b0}});
endmodule

module top(input ck,we,input[5:0]wa,ra,input[305:0]din,output[305:0]o0,o1); ot_hep_rx_leaf a(.ck(ck),.we(we),.wa(wa),.ra(ra),.din(din),.dout(o0)); ot_hep_rx_leaf b(.ck(ck),.we(we),.wa(wa),.ra(ra),.din(din),.dout(o1)); endmodule
