`timescale 1ps/1fs
module tb;
reg clk=0; always #416.5 clk=~clk;
reg rst_n=0; reg [279:0] rt=0;
wire [2:0] ov,oe,ff; wire[31:0] ot[0:2],od[0:2];
gold_cap_tr a(.clk(clk),.rst_n(rst_n),.rt(rt),.o_v(ov[0]),.o_t(ot[0]),.o_d(od[0]),.o_e(oe[0]),.fault(ff[0]));
ot_s81sl_cap_tr b(.clk(clk),.rst_n(rst_n),.rt(rt),.o_v(ov[1]),.o_t(ot[1]),.o_d(od[1]),.o_e(oe[1]),.fault(ff[1]));
mut_cap_tr c(.clk(clk),.rst_n(rst_n),.rt(rt),.o_v(ov[2]),.o_t(ot[2]),.o_d(od[2]),.o_e(oe[2]),.fault(ff[2]));
integer k,j,mism=0,mut=0,seed=91821,resets=0;
initial begin
  for(k=0;k<12000;k=k+1) begin
    @(negedge clk);
    rst_n = k>=80 && !((k%853)>=400 && (k%853)<480);
    if(!rst_n) resets=resets+1;
    for(j=0;j<280;j=j+1) rt[j]=$urandom(seed)&1;
    @(posedge clk); #1;
    if({a.rv_q,a.l_v,a.l_e,a.l_f} !== {b.rv_q,b.l_v,b.l_e,b.l_f} ||
       {ov[0],ot[0],od[0],oe[0],ff[0]} !== {ov[1],ot[1],od[1],oe[1],ff[1]}) begin
       mism=mism+1;if(mism<5)$display("MISM k=%0d rv=%h/%h",k,a.rv_q,b.rv_q);
    end
    if(a.rv_q !== c.rv_q)mut=mut+1;
  end
  $display("CAP_TR_FACE cycles=%0d mism=%0d mutant=%0d reset_edges=%0d",k,mism,mut,resets);
  if(mism || mut==0)$fatal(1,"CAP_TR_FACE_FAIL");
  $display("CAP_TR_FACE_PASS");$finish;
end
endmodule
