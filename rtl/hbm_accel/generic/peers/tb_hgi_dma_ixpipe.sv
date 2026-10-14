`timescale 1ns/1ps
module tb_hgi_dma_ixpipe #(parameter integer MUT=0);
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0,v=0,first=0,rb=0; reg [31:0] id=0,dw=0; reg [26:0] mul=0; reg [39:0] ab=0;
 wire vo;wire [59:0] addr;wire [31:0] dwo;wire [23:0] active;
 ot_hgi_dma_ixpipe #(.MUT(MUT)) dut(clk,rst_n,v,id,dw,mul,ab,rb,first,vo,addr,dwo,active);
 reg [59:0] expa[0:511];reg [31:0] expdw[0:511];integer sent=0,recv=0,errors=0;
 reg [59:0] baseprod,prod;reg [31:0] rng=32'h67aed145;
 always @(negedge clk) if(vo)begin
 if(recv>=sent||addr!==expa[recv]||dwo!==expdw[recv])begin errors++;if(errors<5)$display("FAIL IXP row%0d addr%h expected%h dw%h/%h",recv,addr,expa[recv],dwo,expdw[recv]);end
 recv++;
 end
 initial begin
 for(integer command=0;command<4;command++)begin
 v=0;rst_n=0;repeat(4)@(negedge clk);rst_n=1;
 rb=command[0];mul=command==0?27'h7ffffff:command==1?27'h1234560:command==2?27'd32:27'h543210;
 ab=40'hbabcdef000;first=1;
 for(integer n=0;n<100;n++)begin
 @(negedge clk); rng=(rng<<1)^((rng[31])?32'h04c11db7:0);id=n==0?32'hf1234567:n==1?32'h01234567:rng;dw=32'd156672+n*32;
 prod={28'd0,id}*{33'd0,mul};if(n==0)baseprod=prod;
 if(rb)expa[sent]={20'd0,ab}+prod-baseprod;else expa[sent]={20'd0,ab}+prod;
 expdw[sent]=dw;sent++;v=1;first=0;
 if(n%7==3)begin @(negedge clk);v=0;end
 end
 @(negedge clk);v=0;repeat(32)@(negedge clk);
 end
 if(recv!=sent)errors++;
 if(errors)$fatal(1,"FATAL IXP errors=%0d records=%0d",errors,sent);
 $display("PASS IXP records=%0d unsigned32x27 rebase_wrap destination order bubbles exact",sent);$finish;
 end
endmodule
