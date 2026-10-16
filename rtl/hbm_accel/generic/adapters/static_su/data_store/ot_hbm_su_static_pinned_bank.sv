`timescale 1ns/1ps
`default_nettype none
// Physical leaf boundary: sample at n, actual SRAM read/write at n+1,
// registered data/return pins at n+2. Payload is not reset. The compiler
// prices both read edges and the +1 write commit; there is no retry path.
module ot_hbm_su_static_pinned_bank #(
 parameter integer READERS=6,RB=9,MUT_COHERENCE=0,MUT_RETURN=0,
 // RD_ROOT 1 (H-SU 10-15, bank clock7 r7): the read-side output registers (read_data, read_return) take their own
 // related root clk_rd entering at the read face, so no register-clock net crosses the SRAM columns
 parameter integer RD_ROOT=0,
 // WS_ROOT (H-SU 10-15, bank r10b): clock of the 18 word-select flops (ks), which sit at each SRAM column's pin edge.
 // 0 = clk (r9: the clk tree then spans every macro column, R 196.6 / spread 74.7 -> native capture 224 > 190);
 // 1 = clk_rd (r10 gate: clk_rd insertion 308.7 / spread 57.1, the E-face read root then spans the columns);
 // 2 = clk_ws, the interior root: ks plus (PIN_RST) the mid-tile return-valid stage r_macro, so clk stays at the
 //     W-face pin registers and clk_rd at the E-face ones (r10b gate with r_macro on clk / rst_r on clk_rd: clk spread
 //     42.8, clk_rd 174.5 / spread 64.2 -- one stray sink each). clk_ws reaches no pin.
 parameter integer WS_ROOT=0,
 // PIN_RST 1 (bank r10): rst_n is a synchronous data input registered at the W face like every other input
 // (r_pin/w_pin gate on it directly, so the first command after release is taken on the same edge as before); the
 // internal return-valid stage gates on the registered copy rst_w; r_return needs no reset of its own (its only source
 // r_macro is cleared). Requires >= 3 clock edges in reset;
 // reset is entered from idle (a read sampled before the asserting edge may still return within 2 edges).
 parameter integer PIN_RST=0,
 parameter integer MUT_RESET=0 // bench mutant: a write issued during reset lands (reset gate dropped on w_pin)
)(
 input wire clk,rst_n,
 input wire clk_rd, // same serial clock as clk (related root); used only when RD_ROOT=1
 input wire clk_ws, // same serial clock as clk (related root); used only when WS_ROOT=2
 input wire[READERS-1:0]clk_macro, // six distinct physical roots; phase-compensated to clk
 input wire[READERS-1:0]read_v,input wire[READERS*RB-1:0]read_addr,
 output reg[READERS*32-1:0]read_data,output wire[READERS-1:0]read_return,
 input wire write_v,input wire[RB-1:0]write_addr,input wire[31:0]write_data
);
 reg[READERS-1:0]r_pin,r_macro,r_return,r_late;
 reg[READERS*RB-1:0]a_pin;
 reg w_pin;reg[RB-1:0]wa_pin;reg[31:0]wd_pin;
 wire[READERS*32-1:0]raw_data;
 wire c_rd=(RD_ROOT!=0)?clk_rd:clk;
 always @(posedge clk)begin
  a_pin<=read_addr;wa_pin<=write_addr;wd_pin<=write_data;
 end
 always @(posedge c_rd)read_data<=raw_data;
 wire c_ws=(WS_ROOT==2)?clk_ws:(WS_ROOT==1)?c_rd:clk;
 if(PIN_RST!=0)begin:g_pin_rst
  reg rst_w;
  always @(posedge clk)begin
   rst_w<=rst_n;
   r_pin<=read_v&{READERS{rst_n}};
   w_pin<=write_v&&(rst_n||MUT_RESET!=0);
  end
  always @(posedge c_ws)r_macro<=r_pin&{READERS{rst_w}};
  always @(posedge c_rd)begin
   r_return<=r_macro;
   r_late<=r_return;
  end
 end else begin:g_async_rst
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin r_pin<=0;r_macro<=0;w_pin<=0;end
   else begin r_pin<=read_v;r_macro<=r_pin;w_pin<=write_v;end
  end
  always @(posedge c_rd or negedge rst_n)begin
   if(!rst_n)begin r_return<=0;r_late<=0;end
   else begin r_return<=r_macro;r_late<=r_return;end
  end
 end
 assign read_return=MUT_RETURN!=0?r_late:r_return;
 ot_hbm_su_static_replicated_bank #(.READERS(READERS),.RB(RB),.MUT_COHERENCE(MUT_COHERENCE))u_data(
  .clk(c_ws),.clk_macro(clk_macro),.read_v(r_pin),.read_addr(a_pin),.read_data(raw_data),
  .write_v(w_pin),.write_addr(wa_pin),.write_data(wd_pin));
endmodule
`default_nettype wire
