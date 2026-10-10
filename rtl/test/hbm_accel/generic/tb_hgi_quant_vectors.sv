`timescale 1ns/1ps
module tb_hgi_quant_vectors;
 reg clk=0;always #0.4166665 clk=~clk;
 reg rst_n=0,v=0;reg [127:0] hdr=0;reg [1023:0] x=0;
 wire vo,fault,df;wire [511:0] y;
 ot_hgi_quant_decode dut(clk,rst_n,v,1'b1,1'b0,hdr,x,vo,y,fault,df);
 reg [1023:0] ins[0:511];reg [511:0] outs[0:511],expected[0:1535];
 integer op,k,count,sent=0,received=0,n8=49,n4=49,n4e=50,unused;
 string vectors="results/hgi_generic/cf_qdq_d61ca29fc";
 always @(negedge clk) if(rst_n&&vo)begin
 if(df||fault||y !== expected[received])$fatal(1,"CF-QDQ golden mismatch op=%0d output=%0d got=%h expected=%h fault=%b",op,received,y,expected[received],fault);
 received=received+1;
 end
 initial begin
 unused=$value$plusargs("VECTORS=%s",vectors);unused=$value$plusargs("N8=%d",n8);unused=$value$plusargs("N4=%d",n4);unused=$value$plusargs("N4E=%d",n4e);
 repeat(5)@(negedge clk);rst_n=1;
 for(op=4;op<=6;op=op+1)begin
 case(op)
 4:begin $readmemh({vectors,"/fp8_e8m0.in.hex"},ins,0,n8-1);$readmemh({vectors,"/fp8_e8m0.out.hex"},outs,0,n8-1);end
 5:begin $readmemh({vectors,"/fp4_e8m0.in.hex"},ins,0,n4-1);$readmemh({vectors,"/fp4_e8m0.out.hex"},outs,0,n4-1);end
 6:begin $readmemh({vectors,"/fp4_e4m3.in.hex"},ins,0,n4e-1);$readmemh({vectors,"/fp4_e4m3.out.hex"},outs,0,n4e-1);end
 endcase
 count=op==6?n4e:(op==5?n4:n8);
 for(k=0;k<count;k=k+1)begin
 @(posedge clk);#0.01;hdr=0;hdr[127:124]=4;hdr[123:118]=op;hdr[71:64]=16;v=1;x=ins[k];expected[sent]=outs[k];sent=sent+1;
 end
 @(posedge clk);#0.01;v=0;repeat(30)@(negedge clk);
 end
 if(received!=sent)$fatal(1,"CF-QDQ lost outputs %0d",received);
 $display("CF-QDQ GOLDEN PASS outputs=%0d",received);$finish;
 end
endmodule
