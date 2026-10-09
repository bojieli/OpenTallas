`timescale 1ns/1ps
// One independently readable 16word partial bank. Payload SECDED is supplied
// by the existing HCOLL64bit codec. Three real128x256 macros; all macro pins
// are driven by registers and all raw macro data is captured before decoding.
module ot_hgi_sum96_partial_bank(
 input wire clk,rst_n,input wire wr_valid,input wire [3:0] wr_tile,
 input wire [511:0] wr_data,output reg wr_ack,output reg [3:0] ack_tile,
 input wire rd_valid,input wire [3:0] rd_tile,
 output reg response_valid,output reg [511:0] response_data,
 output wire corrected,output wire uncorrectable);
 wire [575:0] encoded,raw;
 reg [575:0] wd_pin,raw_capture;
 reg [6:0] wa_pin,ra_pin;
 reg wc_pin,rc_pin;
 reg [3:0] wt;
 reg [2:0] rv;
 wire [511:0] decoded;
 wire ce,ue;
 ot_hcoll_payload_codec #(.W(512),.ECC(1)) codec(.payload(wr_data),.code(encoded),.sampled(raw_capture),.decoded(decoded),.ce(ce),.ue(ue));
 ot_hcoll_sram128 #(.W(576)) storage(.clk(clk),.r_ce(rc_pin),.r_addr(ra_pin),.rd(raw),
 .w_ce(wc_pin),.w_addr(wa_pin),.wd(wd_pin));
 always @(posedge clk or negedge rst_n) begin
 if(!rst_n)begin wc_pin<=0;rc_pin<=0;rv<=0;wr_ack<=0;response_valid<=0;end
 else begin
 wc_pin<=wr_valid;rc_pin<=rd_valid;
 rv<={rv[1:0],rd_valid};wr_ack<=wc_pin;ack_tile<=wt;
 response_valid<=rv[2]&&!ue;
 end
 end
 always @(posedge clk)begin
 wd_pin<=encoded;wa_pin<={3'b0,wr_tile};wt<=wr_tile;
 ra_pin<={3'b0,rd_tile};raw_capture<=raw;response_data<=decoded;
 end
 assign corrected=rv[2]&&ce;
 assign uncorrectable=rv[2]&&ue;
endmodule
