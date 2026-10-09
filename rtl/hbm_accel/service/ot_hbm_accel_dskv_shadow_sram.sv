`timescale 1ps/1fs
`default_nettype none
// F04/R3 opt-in actual SRAM. Logical sectors = slot*17+sector (0..135).
// One outstanding transaction; response must be consumed before another request.
// Every write replaces a complete corrected sector; byte merging belongs to caller.
module ot_hbm_accel_dskv_shadow_sram #(parameter integer ENABLE=0)(
 input wire clk,rst_n,req_v, output wire req_r,
 input wire req_write,input wire [2:0] req_slot,input wire [4:0] req_sector,
 input wire [255:0] req_data,
 output wire rsp_v,input wire rsp_r,output wire [255:0] rsp_data,
 output wire rsp_poison,output wire fault
);
 generate if(!ENABLE) begin:off
 assign req_r=0; assign rsp_v=0; assign rsp_data=0; assign rsp_poison=0; assign fault=0;
 end else begin:on
 localparam [2:0] IDLE=0,ENC=1,WRITE=2,READ=3,CAPTURE=4,DECODE=5,RESP=6;
 reg [2:0] st,st_n;
 wire state_bad=(st!=~st_n)||(st>RESP); reg [7:0] address; reg [255:0] wd,answer;
 reg poison,failed,valid_read; reg [135:0] valid_p,valid_n;
 reg [9:0] checkbits[0:135]; reg [9:0] captured_check;
 reg bank_capture;
 wire [7:0] req_address = 8'(req_slot)*8'd17 + 8'(req_sector);
 wire accept=req_v&&req_r;
 wire legal=req_sector<17;
 wire [265:0] enc_word;
 ot_secded_enc #(.K(256),.R(10)) enc(.clk(clk),.d(wd),.q(enc_word));
 wire [255:0] rd0,rd1;
 ot_sram_1r1w_128x256_m1_r2c2 bank0(
 .clk(clk),.r_ce_in(st==READ&&!state_bad&&!address[7]),.r_addr_in(address[6:0]),.rd_out(rd0),
 .w_ce_in(st==WRITE&&!state_bad&&!address[7]),.w_addr_in(address[6:0]),.wd_in(enc_word[255:0]),
 .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_sram_1r1w_128x256_m1_r2c2 bank1(
 .clk(clk),.r_ce_in(st==READ&&!state_bad&&address[7]),.r_addr_in(address[6:0]),.rd_out(rd1),
 .w_ce_in(st==WRITE&&!state_bad&&address[7]),.w_addr_in(address[6:0]),.wd_in(enc_word[255:0]),
 .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 wire dec_v,ce,ue; wire [255:0] dec_data; wire [31:0] nce,nue;
 ot_secded_dec #(.K(256),.R(10)) dec(.clk(clk),.rst_n(rst_n),.v(st==CAPTURE&&!state_bad),
 .w({captured_check,bank_capture?rd1:rd0}),.ov(dec_v),.d(dec_data),.ce(ce),.ue(ue),.n_ce(nce),.n_ue(nue));
 assign req_r=st==IDLE&&!failed&&!state_bad;
 assign rsp_v=st==RESP&&!state_bad; assign rsp_data=answer; assign rsp_poison=poison; assign fault=failed||state_bad;
 always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin
 st<=IDLE; st_n<=~IDLE; address<=0; wd<=0; answer<=0; poison<=0; failed<=0;
 valid_p<=0; valid_n<={136{1'b1}}; captured_check<=0; bank_capture<=0; valid_read<=0;
 end else if(state_bad)begin failed<=1;poison<=1;answer<=0;st<=RESP;st_n<=~RESP;end else begin
 case(st)
 IDLE:if(accept)begin
 address<=req_address; wd<=req_data; poison<=0;
 if(!legal)begin failed<=1; poison<=1; answer<=0; st<=RESP; st_n<=~RESP; end
 else if(req_write)begin st<=ENC;st_n<=~ENC;end
 else begin
 valid_read<=valid_p[req_address]&&!valid_n[req_address];
 if(valid_p[req_address]==valid_n[req_address]) failed<=1;
 st<=READ;st_n<=~READ;
 end
 end
 ENC:begin st<=WRITE;st_n<=~WRITE;end
 WRITE:begin
 checkbits[address]<=enc_word[265:256]; valid_p[address]<=1; valid_n[address]<=0;
 answer<=enc_word[255:0]; st<=RESP; st_n<=~RESP;
 end
 READ:begin captured_check<=checkbits[address]; bank_capture<=address[7]; st<=CAPTURE;st_n<=~CAPTURE; end
 CAPTURE:begin st<=DECODE;st_n<=~DECODE;end
 DECODE:if(dec_v)begin
 poison<=ue||!valid_read; answer<=(ue||!valid_read)?256'b0:dec_data;
 if(ue||!valid_read)failed<=1; st<=RESP; st_n<=~RESP;
 end
 RESP:if(rsp_r)begin st<=IDLE; st_n<=~IDLE;end
 default:begin failed<=1; poison<=1; answer<=0; st<=RESP; st_n<=~RESP; end
 endcase
 end
 end
 end endgenerate
endmodule
`default_nettype wire
