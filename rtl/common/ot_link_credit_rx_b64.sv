`timescale 1ns/1ps
// Opt-in SRAM successor to ot_link_credit_rx (OREG0, WFREE1/2 semantics).
// Legacy source is untouched. l_* landing, credit/fault flags and visible edges
// match the legacy receiver. Same-depth local reset copies must cover the head
// forwarding flags; caller expands its existing relay, adding no release stage.
module ot_link_credit_rx_b64 #(
 parameter integer W=553, DEPTH=8, WFREE=1, NS=(W+15)/16, MUT=0, LOCAL_HIT=0, LOCAL_POP=0
)(input wire clk,rst_n,input wire [NS-1:0] head_rst_n,
 input wire l_valid,input wire [W-1:0] l_data,(* keep *) output reg l_credit,
 output wire o_valid,input wire o_ready,output wire [W-1:0] o_data,output reg fault);
 localparam integer AW=(DEPTH>1)?$clog2(DEPTH):1, CW=$clog2(DEPTH+1);
 reg v_q,nz_r; reg [W-1:0] d_q; reg [AW-1:0] wp,rp; reg [CW-1:0] n;
 assign o_valid=nz_r;
 wire pop=o_valid&&o_ready, full=n==CW'(DEPTH);
 wire pop_count,pop_addr;
 generate if(LOCAL_POP!=0) begin:g_local_pop
  // CORE_CRED12 AW4 grows the shared pop cone to42 mapped loads. Independent
  // kept predicates retain the same edge while bounding count and address cones.
  (* keep=1 *) ot_link_credit_rx_b64_pop u_count(.a(o_valid),.b(o_ready),.q(pop_count));
  (* keep=1 *) ot_link_credit_rx_b64_pop u_addr(.a(o_valid),.b(o_ready),.q(pop_addr));
 end else begin:g_legacy_pop
  assign pop_count=pop;assign pop_addr=pop;
 end endgenerate
 wire wr=v_q&&(!full || ((WFREE==0)&&pop));
 wire [CW-1:0] nnext=n+CW'(wr)-CW'(pop_count);
 wire [AW-1:0] rnext=pop_addr ? ((rp==AW'(DEPTH-1))?'0:rp+1'b1):rp;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin v_q<=0;wp<=0;rp<=0;n<=0;l_credit<=0;fault<=0;nz_r<=0;end
  else begin
   v_q<=l_valid; l_credit<=pop;
   if(v_q&&full&&!pop) fault<=1;
   if(wr) wp<=(wp==AW'(DEPTH-1))?'0:wp+1'b1;
   rp<=rnext; n<=nnext; nz_r<=nnext!=0;
  end
 always @(posedge clk) d_q<=l_data;
 ot_sram_showahead_b64 #(.W(W),.AW(AW),.WREG(1),.NS(NS),.MUT(MUT),.LOCAL_HIT(LOCAL_HIT)) u_head(
  .clk(clk),.rst_n(head_rst_n),.we(wr),.wa(wp),.wd(d_q),.ra(rnext),.q(o_data));
`ifndef SYNTHESIS
 initial if(DEPTH<2 || DEPTH>32 || WFREE<0 || WFREE>2) $fatal(1,"credit SRAM unsupported shape");
`endif
endmodule

(* keep_hierarchy="yes" *) module ot_link_credit_rx_b64_pop(input wire a,b,output wire q);
 assign q=a&&b;
endmodule
