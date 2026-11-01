`timescale 1ns/1ps
module tb_head;
 parameter integer MUT=0;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,cfg_we=0;reg[15:0]cfg_bank=0;reg[6:0]cfg_row=0;reg[255:0]cfg_data=0;
 reg[9:0] l_fault=0,l_valid=0;
 reg old_cfg_we;always @(posedge clk)old_cfg_we<=cfg_we;
 wire[279:0]a,b;
 old_ot_hbm_su_programme_pghead gold(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),.l_fault(l_fault),.l_valid(l_valid),.o_we(a[279:270]),.o_any(a[269]),.o_bank(a[268:264]),.o_row(a[263:257]),.o_data(a[256:1]),.fault(a[0]));
 ot_hbm_su_programme_pghead #(.NATIVE_PIN(1)) dut(.clk(clk),.rst_n(rst_n),.cfg_we(MUT?old_cfg_we:cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),.l_fault(l_fault),.l_valid(l_valid),.o_we(b[279:270]),.o_any(b[269]),.o_bank(b[268:264]),.o_row(b[263:257]),.o_data(b[256:1]),.fault(b[0]));
 integer cycles=0,bad=0,cwe_bad=0,known=0,unknown=0,j,k;
 always @(posedge clk)begin
  #0.001;cycles=cycles+1;
  if(gold.c_we===1'b0 || gold.c_we===1'b1)if(dut.c_we!==gold.c_we)cwe_bad=cwe_bad+1;
  for(j=0;j<280;j=j+1)begin
   if(a[j]===1'b0 || a[j]===1'b1)begin known=known+1;if(a[j]!==b[j])bad=bad+1;end
   else unknown=unknown+1;
  end
 end
 initial begin
  for(k=0;k<512;k=k+1)begin
   @(negedge clk);
   cfg_we=(k%3)!=0;cfg_bank=32*(k%11)+(k%32);cfg_row=k%128;cfg_data={8{32'h12345678^k}};
   l_valid=(k%7==0)?10'b1111111111:0;l_fault=(k%61==0)?1:0;
   if(k==1 || k==106 || k==259)rst_n=1;
   if(k==105)begin rst_n=0;#0.4165;rst_n=1;end
   if(k==258)begin #0.1;rst_n=0;#0.08;rst_n=1;end
  end
  @(negedge clk);
  $display("HEAD_RESULT MUT=%0d cycles=%0d mismatches=%0d cwe_mismatches=%0d known=%0d unknown=%0d",MUT,cycles,bad,cwe_bad,known,unknown);
  if(bad==0 && cwe_bad==0)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
