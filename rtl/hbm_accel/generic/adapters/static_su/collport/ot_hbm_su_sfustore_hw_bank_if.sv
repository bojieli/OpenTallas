`timescale 1ns/1ps
`default_nettype none
// Physical SRAM interface, identical external edges to sfustore_hw_bank RD_CAP=1.
// WD/mask capture stays at the original input edge. Raw/selector capture replaces
// the post-mux rd_cap at its original edge; the mux moves before read_data's D.
// Every live macro data/mask pin can therefore own a nearby kept register.
module ot_hbm_su_sfustore_hw_bank_if #(parameter integer RD_CAP=1, MUT_IF=0)(
 input wire clk, rst_n,
 input wire read_v, input wire [8:0] read_addr, output reg [31:0] read_data,
 input wire write_v, input wire [8:0] write_addr, input wire [31:0] write_data
);
 reg r_pin,w_pin;
 reg [8:0] a_pin;
 reg [5:0] wa_pin;
 (* keep=1 *) reg [255:0] wd_pin;
 (* keep=1 *) reg [255:0] wm_pin;
 wire [255:0] raw;
 wire [2:0] ks;
 always @(posedge clk) begin
  a_pin<=read_addr;
  wa_pin<=write_addr[8:3];
  wd_pin<={8{write_data}} ^ ((MUT_IF==2)?256'd1:256'd0);
  wm_pin<=({224'd0,32'hffffffff} << {write_addr[2:0],5'd0}) ^ ((MUT_IF==1)?256'd1:256'd0);
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin r_pin<=1'b0;w_pin<=(MUT_IF==4);end
  else begin r_pin<=read_v;w_pin<=write_v;end
 if(1) begin:u_data
  for(genvar r=0;r<1;r=r+1) begin:g_read
   reg [2:0] ks_q;
   always @(posedge clk) if(r_pin) ks_q<=a_pin[2:0];
   assign ks=ks_q;
   ot_sram_1r1w_128x256_m1_r2c2 u_m(
    .clk(clk),.r_ce_in(r_pin),.r_addr_in({1'b0,a_pin[8:3]} ^ ((MUT_IF==3)?7'd1:7'd0)),
    .rd_out(raw),.w_ce_in(w_pin),.w_addr_in({1'b0,wa_pin}),.wd_in(wd_pin),.w_mask_in(wm_pin),
    .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
  end
 end
 if(RD_CAP!=0) begin:g_rd_cap
  (* keep=1 *) reg [255:0] rd_raw_cap;
  reg [2:0] ks_cap;
  always @(posedge clk) begin
   rd_raw_cap<=raw;
   ks_cap<=ks;
   read_data<=rd_raw_cap[{ks_cap,5'd0}+:32];
  end
 end else begin:g_rd_direct
  always @(posedge clk) read_data<=raw[{ks,5'd0}+:32];
 end
endmodule
`default_nettype wire
