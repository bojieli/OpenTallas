`timescale 1ns/1ps
module tb_svc7_full_chunk;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,iv=0;reg[143:0]b=0;reg[2:0]bank=0,wbank=0;
 reg[7:0]we=0;reg[127:0]wd=0;
 wire ov;wire[31:0]y;wire[2:0]fault_parts;
`ifdef SVC7_FULL_BOUNDED
 ot_s81svc7_chunk_bounded dut(.*);
`else
 ot_s81svc7_chunk dut(.*);
`endif
 reg[143:0]bp;reg[2:0]bk,wb;reg[7:0]wp;reg[127:0]data;
 always @(posedge clk)begin bp<=b;bk<=bank;wb<=wbank;wp<=we;data<=wd;end
 wire[143:0]sk_b;wire[23:0]sk_bank;
 genvar k;
 generate for(k=0;k<8;k=k+1)begin:g_refskew
  localparam integer D=k<2?0:5*(k-1);
  ot_hdc_v41x_dly #(.W(21),.D(D))u(.clk(clk),.d({bk,bp[k*18+:18]}),.q({sk_bank[k*3+:3],sk_b[k*18+:18]}));
 end endgenerate
 wire[31:0]gy;wire gf;
 // Independently existing original head datapath: same arithmetic function,
 // different product/add cuts (native mul6+pin1 versus original mul_s7).
 ot_hdc_v41x_attn_hdp_s #(.TD(8),.NBANK(5),.BW(3),.FPL(5),.FML(7),.F12(1))gold(
  .clk(clk),.rst_n(rst_n),.we(wp),.wbank(wb),.wd(data),.sk_bank(sk_bank),.sk_b(sk_b),.y(gy),.f(gf));
 reg r0,r1;reg[42:0]vh;
 always @(posedge clk)begin r0<=rst_n;r1<=r0;end
 always @(posedge clk or negedge r1)if(!r1)vh<=0;else vh<={vh[41:0],iv};
`ifdef SVC7_FULL_CALLER
 // EXACT existing hgrp caller qualification (caller_contract657d97ee2):
 // rawLOCALreset immediately clears parentvalid, not a delayed reference.
 // Original hdp has NOvalidport. Experimental chunkov is diagnostic only.
 wire contract_v;
 ot_hdc_v41x_vdly #(.D(43))u_contract(.clk(clk),.rst_n(rst_n),.d(iv),.q(contract_v));
 wire control_check=rst_n;
 wire expected_v=contract_v;
 wire data_check=contract_v;
`else
 wire control_check=1'b1;
 wire expected_v=vh[42];
 wire data_check=ov;
`endif
 integer cyc=0,age=0,checks=0,errors=0,valids=0,j;
 always @(negedge clk)begin
  if(cyc>=4)begin
   checks=checks+1;
   if((control_check&&ov!==expected_v) || (data_check&&({y,|fault_parts}!={gy,gf})))begin
    errors=errors+1;$display("SVC7_FULL_MISMATCH cyc=%0d v=%b/%b y=%h/%h f=%b/%b",cyc,ov,expected_v,y,gy,|fault_parts,gf);
   end
   if(ov)valids=valids+1;
  end
  rst_n=(cyc>=12&&!(cyc>=711&&cyc<717)&&!(cyc>=2033&&cyc<2039));
  if(!rst_n)age=0;else age=age+1;
  // Existing configuration protocol: all five banks are written before iv.
  iv=rst_n&&age>4&&cyc>=40&&($urandom_range(0,7)!=0);
  we=0;
  if((cyc>=20&&cyc<25)||(cyc>=1000&&cyc<1005))begin
   we=8'hff;wbank=cyc>=1000?cyc-1000:cyc-20;
  end
  bank=$urandom_range(0,4);
  for(j=0;j<8;j=j+1)begin
   wd[j*16+:16]=$urandom;wd[j*16+7+:8]=8'h7e;
   b[j*18+:18]=$urandom;b[j*18+7+:8]=8'h7e;b[j*18+16+:2]=0;
  end
  if(cyc%29==0)b[18*$urandom_range(0,7)+16]=1;
  if(cyc%97==0)b[18*$urandom_range(0,7)+:16]=16'h7fc1;
  if(cyc%101==0)b[18*$urandom_range(0,7)+17]=1;
  cyc=cyc+1;
  if(cyc==7000)begin
   $display("SVC7_FULL checks=%0d valid=%0d errors=%0d verdict=%s",checks,valids,errors,errors==0?"PASS":"FAIL");
   if(errors||valids<1000)$fatal(1,"SVC7_FULL_FAIL");$finish;
  end
 end
endmodule
