`timescale 1ns/1ps
// Resettable ASTK relay standard. One physical stage; unlike qkd_rlys_296,
// asynchronous reset is part of the exact strip contract.
module qkd_astk_rly_296(input wire ck, input wire rst_n,
    input wire [295:0] a, output reg [295:0] b);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) b <= 296'd0;
`ifdef KVD_ASTK_RLY_MUT
        else b <= a ^ 296'd1;
`else
        else b <= a;
`endif
endmodule

// Wires-only specialization of ot_hdc_delay RESET=1. Spare input bits are
// explicit zero straps and spare outputs are private unused wires.
module qkd_astk_delay #(parameter integer W=32, D=1, RESET=1)(
    input wire clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    localparam integer C=(W+295)/296;
    wire [C*296-1:0] line [0:D];
    assign line[0]={{(C*296-W){1'b0}},d};
    genvar s,c;
    generate for(s=0;s<D;s=s+1) begin:g_stage
        for(c=0;c<C;c=c+1) begin:g_chunk
            qkd_astk_rly_296 u_r(.ck(clk),.rst_n(rst_n),
                .a(line[s][296*c+:296]),.b(line[s+1][296*c+:296]));
        end
    end endgenerate
    assign q=line[D][W-1:0];
    initial if(RESET!=1) $fatal(1,"ASTK relay requires RESET=1");
endmodule

// The only old er_die glue gate becomes a registered physical leaf.
// The stack fault output is delayed by exactly one edge; no production issue
// or result is rescheduled by this diagnostic fault path.
// PORT_REGS lands the external fault b before its merge. The local fault a
// keeps its original edge; b detection gains exactly one cycle (+2 flops: unreset data + reset validity).
module qkd_astk_fault_join #(parameter integer PORT_REGS=0)(input wire ck,rst_n,input wire a,b,output reg q);
    wire b_landed;
    generate if (PORT_REGS != 0) begin : g_fault_land
        reg bq, b_valid;
        always @(posedge ck) bq<=b;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) b_valid<=1'b0; else b_valid<=1'b1;
`ifdef KVG3_ASTK_FMUT
        assign b_landed=b;
`else
        assign b_landed=b_valid & bq;
`endif
    end else begin : g_fault_direct
        assign b_landed=b;
    end endgenerate
    always @(posedge ck or negedge rst_n)
        if(!rst_n) q<=1'b0;
        else q<=a|b_landed;
endmodule

// No-reset chain variant. The owner-chain token validity resets locally; relay
// data remains unreset exactly as ot_hdc_delay's default RESET=0.
module qkd_astk_delay_nrst #(parameter integer W=32,D=1)(
 input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] q);
 localparam integer C=(W+295)/296;
 wire [C*296-1:0] line[0:D];
 assign line[0]={{(C*296-W){1'b0}},d};
 genvar s,c;
 generate for(s=0;s<D;s=s+1) begin:g_stage
  for(c=0;c<C;c=c+1) begin:g_chunk
   qkd_rlys_296 u_r(.ck(clk),.a(line[s][296*c+:296]),.b(line[s+1][296*c+:296]));
  end
 end endgenerate
 assign q=line[D][W-1:0];
endmodule
