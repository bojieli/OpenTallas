`timescale 1ns/1ps
// Standalone experimental mechanism. No parent binding or production K is supplied.
module qfd_d8_mechanism #(parameter integer W=10, SRAM=0, ENABLE=0)(
 input wire wclk,rclk,wrst,rrst,w_en,r_en,
 input wire k0,k1,k2,k3, input wire [W-1:0] din,
 output reg [W-1:0] dout, output reg valid, output reg fault);
 wire rst=wrst|rrst;
 reg [1:0] wz,rz;
 always @(posedge wclk or posedge rst) if(rst) wz<=3; else wz<={wz[0],1'b0};
 always @(posedge rclk or posedge rst) if(rst) rz<=3; else rz<={rz[0],1'b0};
 reg [3:0] wc,rc,kq;
 reg [7:0] live;
 reg [4:0] warm;
 wire we=ENABLE && !wz[1] && w_en;
 wire re=ENABLE && !rz[1] && r_en;
 wire [3:0] expected=rc-kq;
 wire [2:0] slot=expected[2:0];
 wire ready=(&live) && warm >= ((kq==0)?5'd16:{1'b0,kq});
 wire [W+4:0] record={1'b1,(wc^4'd1),din};
 wire [W+4:0] selected;
 always @(posedge wclk or posedge rst) begin
  if(rst) begin wc<=0;live<=0;end
  else if(wz[1]) begin wc<=0;live<=0;end
  else if(we) begin wc<=wc+1'b1;live[wc[2:0]]<=1'b1;end
 end
 always @(posedge rclk or posedge rst) begin
  if(rst) begin rc<=0;kq<=0;warm<=0;end
  else if(rz[1]) begin rc<=0;kq<={k3,k2,k1,k0};warm<=0;end
  else if(re) begin rc<=rc+1'b1;if(warm<16)warm<=warm+1'b1;end
 end
 generate if(SRAM) begin: sram
  localparam B=(W+5+63)/64;
  wire [B*64-1:0] padded={{(B*64-W-5){1'b0}},record};
  wire [B*64-1:0] readword;
  for(genvar b=0;b<B;b=b+1) begin: banks
   ot_sram_1r1w2c_32x64_m1 mem(.wclk(wclk),.rclk(rclk),
    .r_ce_in(re),.r_addr_in({2'b0,slot}),.rd_out(readword[b*64+:64]),
    .w_ce_in(we),.w_addr_in({2'b0,wc[2:0]}),.wd_in(padded[b*64+:64]),.w_mask_in(64'hffffffffffffffff));
  end
  reg [3:0] pe;reg pv,pr;
  always @(posedge rclk or posedge rst) begin
   if(rst)begin pe<=0;pv<=0;pr<=0;dout<=0;valid<=0;fault<=0;end
   else if(rz[1])begin pe<=0;pv<=0;pr<=0;dout<=0;valid<=0;fault<=0;end
   else begin
    pr<=re;if(re)begin pe<=expected;pv<=ready && live[slot];end
    valid<=pr && pv && readword[W+4] && readword[W+:4]==pe;
    if(pr)begin
     if(pv && readword[W+4] && readword[W+:4]==pe)dout<=readword[W-1:0];else dout<=0;
     if(pv && (!readword[W+4] || readword[W+:4]!=pe))fault<=1;
    end
   end
  end
 end else begin: ff
  reg [W+3:0] rows[0:7];
  always @(posedge wclk) if(we)rows[wc[2:0]]<=record[W+3:0];
  assign selected={1'b1,rows[slot]};
  always @(posedge rclk or posedge rst)begin
   if(rst)begin dout<=0;valid<=0;fault<=0;end
   else if(rz[1])begin dout<=0;valid<=0;fault<=0;end
   else begin
    valid<=re && ready && live[slot] && selected[W+:4]==expected;
    if(re)begin
     if(ready && live[slot] && selected[W+:4]==expected)dout<=selected[W-1:0];else dout<=0;
     if(ready && live[slot] && selected[W+:4]!=expected)fault<=1;
    end
   end
  end
 end endgenerate
endmodule
