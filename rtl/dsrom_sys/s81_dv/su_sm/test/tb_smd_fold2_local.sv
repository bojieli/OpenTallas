`timescale 1ns/1ps
module tb_smd_fold2_local;
 parameter integer MUT=0;
 reg clk=0,rst=0;always #1 clk=~clk;
 reg pv=0,dv=0,csv=0;reg[4:0]csi=0;reg[63:0]csd=0;reg[31:0]den=32'h3f800000;reg[127:0]pa=0;
 wire[1:0]ov,f;wire[63:0]o;wire fov;wire[1:0]ff;wire[63:0]fo;
 genvar g;
 generate for(g=0;g<2;g++)begin:R
 ot_s81_su_smd #(.STALEDEN(0))u(.clk(clk),.rst_in(rst),.cfg_p(3'(1+4*g)),.i_pv(pv),.i_pa(pa[64*g+:64]),
 .i_dv(dv),.i_den(den),.i_csv(csv),.i_csi(csi),.i_csd(csd),.o_ov(ov[g]),.o_o(o[32*g+:32]),.o_f(f[g]));
 end endgenerate
 ot_s81_su_smd_fold2_local #(.STALEDEN(MUT))D(.clk(clk),.rst_in(rst),.cfg_p(2'd1),.i_pv(pv),.i_pa(pa),
 .i_dv(dv),.i_den(den),.i_csv(csv),.i_csi(csi),.i_csd(csd),.o_ov(fov),.o_o(fo),.o_f(ff));
 reg[31:0]q0[$],q1[$];reg[31:0]a,b;integer err=0,checks=0;
 always @(negedge clk)if(rst)begin
 if(ov[0])q0.push_back(o[31:0]);if(ov[1])q1.push_back(o[63:32]);
 if(fov)begin
  if(q0.size()==0||q1.size()==0)begin $display("missing reference");err++;end
  else begin a=q0.pop_front();b=q1.pop_front();if(fo!=={b,a})begin $display("divide mismatch %h %h",fo,{b,a});err++;end checks++;end
 end end
 task tick;begin @(posedge clk);#0.1;end endtask
 function automatic[31:0]val(input integer k);val={1'($urandom),8'(118+$urandom%14),23'($urandom)};endfunction
 integer j,k,seed=1108;
 initial begin
 seed=$urandom(seed);repeat(4)tick;rst=1;repeat(8)tick;
 for(j=0;j<3;j++)begin
 den=32'h3f800000+(j<<22);dv=1;tick;dv=0;
 for(k=0;k<32;k++)begin csv=1;csi=5'(k);csd={32'h3f000000+(k<<16),32'h3e000000+(k<<15)};tick;end
 csv=0;repeat(6)tick;
 for(k=0;k<32;k++)begin pa={val(k),val(k+1),val(k+2),val(k+3)};pv=1;tick;pv=0;tick;end
 repeat(200)tick;
 end
 if(q0.size()!=0||q1.size()!=0||(|ff)||(|f))begin $display("leftover/fault %d %d %b %b",q0.size(),q1.size(),ff,f);err++;end
 if(err)$fatal(1,"DIVFOLD2 FAIL checks%0d errors%0d MUT%0d",checks,err,MUT);
 $display("DIVFOLD2 PASS checks%0d MUT%0d",checks,MUT);$finish;
 end
endmodule
