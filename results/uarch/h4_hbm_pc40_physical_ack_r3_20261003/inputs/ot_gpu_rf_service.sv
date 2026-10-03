`timescale 1ns/1ps
module ot_gpu_rf_service #(parameter integer ACK_ID=0) (
 input wire clk, rst_n,
 input wire rd_valid, output wire rd_ready,
 input wire [8:0] rd_a, rd_b,
 output reg rsp_valid, input wire rsp_ready,
 output reg [4095:0] rsp_a, rsp_b,
 input wire wr_valid, output wire wr_ready,
 input wire [8:0] wr_addr, input wire [4095:0] wr_data,
 output reg ack_valid, input wire ack_ready,
 input wire [45:0] wr_owner,output wire [45:0] ack_owner,
 output wire [8:0] ack_slot,output wire ack_identity_fault
);
function automatic [71:0] w4_encode(input [54:0] payload);
 reg [63:0] data;reg [71:0] c;reg parity;integer p,k,j;
 begin
  data={9'b0,payload};c=0;j=0;
  for(p=1;p<=71;p=p+1) if((p&(p-1))!=0)begin c[p-1]=data[j];j=j+1;end
  for(k=1;k<=64;k=k*2)begin parity=0;for(p=1;p<=71;p=p+1)if((p&k)!=0)parity=parity^c[p-1];c[k-1]=parity;end
  c[71]=^c[70:0];w4_encode=c;
 end
endfunction
function automatic [55:0] w4_decode(input [71:0] word);
 reg [71:0] c;reg [63:0] data;reg parity,bad;integer p,k,j,syndrome;
 begin
  c=word;syndrome=0;
  for(k=1;k<=64;k=k*2)begin parity=0;for(p=1;p<=71;p=p+1)if((p&k)!=0)parity=parity^c[p-1];if(parity)syndrome=syndrome+k;end
  bad=0;
  if((^c)==1'b1)begin if(syndrome>0&&syndrome<=71)c[syndrome-1]=~c[syndrome-1];else if(syndrome>71)bad=1;end
  else if(syndrome!=0)bad=1;
  data=0;j=0;for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin data[j]=c[p-1];j=j+1;end
  if(data[63:55]!=0)bad=1;
  w4_decode={bad,data[54:0]};
 end
endfunction

generate if(ACK_ID==0)begin:g_original
 assign ack_owner=0;assign ack_slot=0;assign ack_identity_fault=0;
 ot_gpu_rf_service_W4_original u_original(.clk(clk),
.rst_n(rst_n),
.rd_valid(rd_valid),
.rd_ready(rd_ready),
.rd_a(rd_a),
.rd_b(rd_b),
.rsp_valid(rsp_valid),
.rsp_ready(rsp_ready),
.rsp_a(rsp_a),
.rsp_b(rsp_b),
.wr_valid(wr_valid),
.wr_ready(wr_ready),
.wr_addr(wr_addr),
.wr_data(wr_data),
.ack_valid(ack_valid),
.ack_ready(ack_ready));
end else begin:g_identity

 reg read_pending, prefer_write;
 reg write_pending;reg [54:0] accepted_identity;reg [71:0] protected_ACK;
 wire [55:0] decoded_ACK=w4_decode(protected_ACK);
 assign ack_identity_fault=ack_valid && decoded_ACK[55];
 assign ack_owner=ack_valid && !decoded_ACK[55] ? decoded_ACK[54:9] : 46'd0;
 assign ack_slot=ack_valid && !decoded_ACK[55] ? decoded_ACK[8:0] : 9'd0;
 reg [1:0] page_a, page_b;
 wire idle = rst_n && !read_pending && !rsp_valid && !ack_valid && !write_pending;
 assign rd_ready = idle && (!wr_valid || !prefer_write);
 assign wr_ready = idle && (!rd_valid || prefer_write);
 wire read_go = rd_valid && rd_ready;
 wire write_go = wr_valid && wr_ready;
 wire [4095:0] words_a [0:3];
 wire [4095:0] words_b [0:3];
 genvar p,b;
 for(p=0;p<4;p=p+1) begin:g_page
  for(b=0;b<16;b=b+1) begin:g_bank
   ot_sram_1r1w_128x256_m1_r2c2 u_operand_a (
    .clk(clk),.r_ce_in(read_go && rd_a[8:7]==p),.r_addr_in(rd_a[6:0]),.rd_out(words_a[p][b*256+:256]),
    .w_ce_in(write_go && wr_addr[8:7]==p),.w_addr_in(wr_addr[6:0]),.wd_in(wr_data[b*256+:256]),
    .w_mask_in({256{1'b1}}),.rr_en(2'b00),.rr_addr(12'd0),.cr_en(2'b00),.cr_sel(16'd0));
   ot_sram_1r1w_128x256_m1_r2c2 u_operand_b (
    .clk(clk),.r_ce_in(read_go && rd_b[8:7]==p),.r_addr_in(rd_b[6:0]),.rd_out(words_b[p][b*256+:256]),
    .w_ce_in(write_go && wr_addr[8:7]==p),.w_addr_in(wr_addr[6:0]),.wd_in(wr_data[b*256+:256]),
    .w_mask_in({256{1'b1}}),.rr_en(2'b00),.rr_addr(12'd0),.cr_en(2'b00),.cr_sel(16'd0));
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   read_pending<=0; rsp_valid<=0; ack_valid<=0; write_pending<=0;accepted_identity<=0;protected_ACK<=0; prefer_write<=0; page_a<=0;page_b<=0;
  end else begin
   read_pending<=read_go;
   if(read_go) begin page_a<=rd_a[8:7];page_b<=rd_b[8:7];prefer_write<=1;end
   if(read_pending) begin rsp_a<=words_a[page_a];rsp_b<=words_b[page_b];rsp_valid<=1;end
   else if(rsp_valid && rsp_ready) rsp_valid<=0;
   if(write_go) begin accepted_identity<={wr_owner,wr_addr};write_pending<=1;prefer_write<=0;end
   if(write_pending) begin protected_ACK<=w4_encode(accepted_identity);ack_valid<=1;write_pending<=0;end
   else if(ack_valid && ack_ready && !decoded_ACK[55]) ack_valid<=0;
  end
 end

end endgenerate
endmodule
`timescale 1ns/1ps
// Finite aligned RF provider. 512 vectors of 128 FP32 lanes, two physical
// 1R1W operand copies. No read-during-write semantics are assumed. Response
// registers lease all banks until consumption; mirrored ACK is registered
// after both copies' write edge. Persistent competing read/write alternate.
module ot_gpu_rf_service_W4_original (
 input wire clk, rst_n,
 input wire rd_valid, output wire rd_ready,
 input wire [8:0] rd_a, rd_b,
 output reg rsp_valid, input wire rsp_ready,
 output reg [4095:0] rsp_a, rsp_b,
 input wire wr_valid, output wire wr_ready,
 input wire [8:0] wr_addr, input wire [4095:0] wr_data,
 output reg ack_valid, input wire ack_ready
);
 reg read_pending, prefer_write;
 reg [1:0] page_a, page_b;
 wire idle = rst_n && !read_pending && !rsp_valid && !ack_valid;
 assign rd_ready = idle && (!wr_valid || !prefer_write);
 assign wr_ready = idle && (!rd_valid || prefer_write);
 wire read_go = rd_valid && rd_ready;
 wire write_go = wr_valid && wr_ready;
 wire [4095:0] words_a [0:3];
 wire [4095:0] words_b [0:3];
 genvar p,b;
 generate for(p=0;p<4;p=p+1) begin:g_page
  for(b=0;b<16;b=b+1) begin:g_bank
   ot_sram_1r1w_128x256_m1_r2c2 u_operand_a (
    .clk(clk),.r_ce_in(read_go && rd_a[8:7]==p),.r_addr_in(rd_a[6:0]),.rd_out(words_a[p][b*256+:256]),
    .w_ce_in(write_go && wr_addr[8:7]==p),.w_addr_in(wr_addr[6:0]),.wd_in(wr_data[b*256+:256]),
    .w_mask_in({256{1'b1}}),.rr_en(2'b00),.rr_addr(12'd0),.cr_en(2'b00),.cr_sel(16'd0));
   ot_sram_1r1w_128x256_m1_r2c2 u_operand_b (
    .clk(clk),.r_ce_in(read_go && rd_b[8:7]==p),.r_addr_in(rd_b[6:0]),.rd_out(words_b[p][b*256+:256]),
    .w_ce_in(write_go && wr_addr[8:7]==p),.w_addr_in(wr_addr[6:0]),.wd_in(wr_data[b*256+:256]),
    .w_mask_in({256{1'b1}}),.rr_en(2'b00),.rr_addr(12'd0),.cr_en(2'b00),.cr_sel(16'd0));
  end
 end endgenerate
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   read_pending<=0; rsp_valid<=0; ack_valid<=0; prefer_write<=0; page_a<=0;page_b<=0;
  end else begin
   read_pending<=read_go;
   if(read_go) begin page_a<=rd_a[8:7];page_b<=rd_b[8:7];prefer_write<=1;end
   if(read_pending) begin rsp_a<=words_a[page_a];rsp_b<=words_b[page_b];rsp_valid<=1;end
   else if(rsp_valid && rsp_ready) rsp_valid<=0;
   if(write_go) begin ack_valid<=1;prefer_write<=0;end
   else if(ack_valid && ack_ready) ack_valid<=0;
  end
 end
endmodule
