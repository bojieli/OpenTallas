`timescale 1ns/1ps
module tb_svc_merge_h4;
 parameter integer MUT=0;
 localparam integer ML=5,DP=8,FP=4;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,iv=0,ifin=0;reg[ML-1:0]iblk=0;reg[255:0]iy=0;reg[7:0]if_=0;
 wire rv,dv;wire[255:0]ry,dy;wire[7:0]rf,df;
 ot_hdc_v41x_attn_merge_x #(.H(8),.DPT(DP),.MLEV(ML),.FPL(FP),.F12(1)) ref_m
 (.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(rv),.oy(ry),.of_(rf));
 generate if(MUT==0)begin:g_pos
 ot_s81_svc_merge_h8_split #(.DPT(DP),.MLEV(ML),.FPL(FP),.F12(1)) dut
 (.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(dv),.oy(dy),.of_(df));
 end else begin:g_mut
 wire[1:0]v;
 ot_s81_svc_merge_h4 lo(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy[127:0]),.if_(if_[3:0]),.ov(v[0]),.oy(dy[127:0]),.of_(df[3:0]));
 // Negative control breaks the high provider's cloned block tags.
 ot_s81_svc_merge_h4 hi(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk^5'd1),.iy(iy[255:128]),.if_(if_[7:4]),.ov(v[1]),.oy(dy[255:128]),.of_(df[7:4]));
 assign dv=v[0];
 end endgenerate
 integer checks=0,errors=0,outputs=0,expected=0;integer h,job,b,r,nblocks,k;
 reg[31:0]rng=32'h51c4a9e7;
 always @(posedge clk)begin
 #1;if(rst_n)begin
  checks=checks+1;
  if(rv!==dv)errors=errors+1;
  if(rv)begin outputs=outputs+1;if(ry!==dy||rf!==df)errors=errors+1;end
 end
 end
 task beat(input integer block_n,input integer row_n,input integer last_n);
 begin
 @(negedge clk);iv=1;iblk=block_n;ifin=last_n;
 for(integer j=0;j<8;j=j+1)begin
 rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
 // Finite varied exponents, signs and mantissas, including cancellation.
 iy[32*j+:32]={rng[31],8'(120+(j+block_n+row_n)%14),rng[22:0]};
 if_[j]=((j+block_n+row_n+job)%29==0);
 end
 end endtask
 initial begin
 repeat(4)@(negedge clk);rst_n=1;
 for(job=0;job<8;job=job+1)begin
 case(job%4)0:nblocks=1;1:nblocks=3;2:nblocks=4;3:nblocks=20;endcase
 expected=expected+DP;
 for(b=0;b<nblocks;b=b+1)begin
  for(r=0;r<DP;r=r+1)begin
   beat(b,r,b==nblocks-1);
   if((r+job)%5==2)begin @(negedge clk);iv=0;end
  end
 end
 @(negedge clk);iv=0;
 repeat(1+ML*FP+8)@(negedge clk);
 end
 repeat(30)@(negedge clk);
 if(MUT==0)begin if(errors||outputs!=expected)$fatal(1,"FAIL checks=%0d errors=%0d outputs=%0d expected=%0d",checks,errors,outputs,expected);$display("PASS H8_vs_2H4 checks=%0d outputs=%0d latency=%0d",checks,outputs,1+ML*FP);end
 else begin if(!errors)$fatal(1,"MUTANT ESCAPED");$display("CAUGHT H4_tag_mutant errors=%0d checks=%0d outputs=%0d",errors,checks,outputs);end
 $finish;
 end
endmodule
