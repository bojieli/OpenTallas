`timescale 1ns/1ps
module tb_s81_embed_static_issue;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,start=0;reg [16:0] token=0;
 wire qv,ov,fault;wire [13:0] qm;wire [11:0] qr;wire [8:0] qi,oi;wire [511:0] od;
 reg [1:0] v=0;reg [13:0] m[0:1];reg [11:0] r[0:1];
 integer n=0,j=0,cycles=0,expected=0,romn=0,mut=0;
 ot_s81_embed_static_issue dut(.clk(clk),.rst_n(rst_n),.start(start),.token(token),
 .req_v(qv),.req_macro(qm),.req_row(qr),.req_idx(qi),.rsp_v(v[1]),
 .rsp_macro(m[1]^(mut?14'b1:14'b0)),.rsp_row(r[1]),.rsp_d(256'h1234),
 .rom_v(ov),.rom_idx(oi),.rom_d(od),.fault(fault));
 always @(posedge clk)begin v<={v[0],qv};m[0]<=qm;m[1]<=m[0];r[0]<=qr;r[1]<=r[0];end
 always @(negedge clk)begin
   cycles=cycles+1;
   if(qv)begin
     expected=token*320+n;
     if({qm[13:2],qm[1],qr,qm[0]}!==26'(expected) || qi!=n)$fatal(1,"address mismatch");
     n=n+1;
   end
   if(ov)begin if(oi!=romn || od[31:0]!==32'h12340000)$fatal(1,"return mismatch");romn=romn+1;end
 end
 initial begin
   if($test$plusargs("mutant"))mut=1;
   repeat(4)@(negedge clk);rst_n=1;
   for(j=0;j<6;j=j+1)begin
      case(j)0:token=0;1:token=12;2:token=32319;3:token=32320;4:token=128799;5:token=129279;endcase
      n=0;romn=0;@(negedge clk);start=1;@(negedge clk);start=0;
      repeat(326)@(negedge clk);
      if(n!=320 || romn!=320)$fatal(1,"count mismatch");
   end
   if(fault)$fatal(1,"fixed ROM identity contract violated");
   $display("STATIC_ISSUE PASS boundary tokens/cross-bank/all320words");$finish;
 end
endmodule
