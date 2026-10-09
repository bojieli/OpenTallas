`timescale 1ns/1ps
`ifndef MUTANT
`define MUTANT 0
`endif
module tb_hgi_quant_decode;
 reg clk=0;always #0.4166665 clk=~clk;
 reg rst_n=0,v=0,gen=0,fp4=0;reg [127:0] hdr=0;reg [1023:0] x=0;
 wire vo,fault,df;wire [511:0] y;
 ot_hgi_quant_decode #(.MUTANT(`MUTANT)) dut(clk,rst_n,v,gen,fp4,hdr,x,vo,y,fault,df);
 wire av,af,bv,bf;wire [511:0] ay,by;wire [255:0] q;wire signed [9:0] e;
 wire legal=hdr[127:124]==4 && (hdr[123:118]==4||hdr[123:118]==5||(hdr[123:118]==6&&hdr[71:64]==16));
 wire take=v&&(!gen||legal);wire e4=gen&&hdr[123:118]==6;
 ot_hfd_actquant_m #(.MR(1),.MLAT(6)) refa(clk,rst_n,take&&!e4,gen ? hdr[123:118]==5 : fp4,x,av,q,e,ay,af);
 ot_hgi_fp4qdq refb(clk,rst_n,take&&e4,x,bv,by,bf);
 reg [14:0] rv=0,rf=0;reg [511:0] ry[0:14];integer i,cyc,n=0,decodes=0;reg [31:0] rnd;
 always @(posedge clk) begin
  if(!rst_n) begin rv<=0;rf<=0;end
  else begin rv<={rv[13:0],bv};rf<={rf[13:0],bf};end
  ry[0]<=by;for(i=1;i<15;i=i+1)ry[i]<=ry[i-1];
 end
 always @(negedge clk) if(rst_n) begin
  if(vo !== (av|rv[14]))$fatal(1,"VALID mismatch");
  if(vo) begin
   n=n+1; if(av&&rv[14])$fatal(1,"OUTPUT COLLISION n=%0d",n);
   if(y !== (rv[14]?ry[14]:ay) || fault !== (rv[14]?rf[14]:af))$fatal(1,"ARITHMETIC mismatch output %0d",n);
  end
  if(df !== (v&&gen&&!legal))$fatal(1,"DECODE mismatch");
  if(df)decodes=decodes+1;
 end
 initial begin
 repeat(5)@(negedge clk);rst_n=1;
 for(cyc=0;cyc<6000;cyc=cyc+1)begin
 @(posedge clk);#0.01;
 v=cyc%11!=0;gen=cyc>=1000;fp4=cyc%2;hdr=0;hdr[127:124]=4;hdr[123:118]=4+cyc%3;hdr[71:64]=16;
 if(cyc%101==0&&gen)hdr[123:118]=63;
 for(i=0;i<32;i=i+1)begin
 rnd=$urandom;
 case(cyc%13)
 0:x[i*32+:32]=0;
 1:x[i*32+:32]=32'h80000000;
 2:x[i*32+:32]={rnd[31],8'd0,rnd[22:0]};
 3:x[i*32+:32]={rnd[31],8'd254,rnd[22:0]};
 4:x[i*32+:32]={rnd[31],8'd127,rnd[22:20],20'd0};
 default:x[i*32+:32]={rnd[31],8'd100+rnd[5:0],rnd[22:0]};
 endcase
 end
 end
 @(posedge clk);#0.01;v=0;repeat(40)@(negedge clk);
 if(n<5000||decodes==0)$fatal(1,"COVERAGE outputs=%0d illegal=%0d",n,decodes);
 $display("CF-QDQ LOCKSTEP PASS outputs=%0d illegal_decode=%0d mutant=%0d",n,decodes,`MUTANT);$finish;
 end
endmodule
