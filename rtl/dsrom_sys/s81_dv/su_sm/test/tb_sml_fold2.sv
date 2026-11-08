`timescale 1ns/1ps
module tb_sml_fold2;
 parameter integer MUT=0;
 reg clk=0,rst=0;always #1 clk=~clk;
 reg cv=0,sv=0,mv=0;reg[6:0]nv=0;
 reg[31:0]scale=32'h3e800000,sink=32'h3f000000,nmb=32'hbf800000;
 reg[63:0]s=0;
 wire[1:0]mxv,ev,es,el;wire[63:0]mx,e;
 wire fmxv,fev,fes,fel,fault;wire[63:0]fmx,fe;
 genvar g;
 generate for(g=0;g<2;g=g+1)begin:R
 ot_s81_su_sml u(.clk(clk),.rst_in(rst),.sk_en(g==0),.i_cv(cv),.i_nv(nv),.i_scale(scale),.i_sink(sink),
 .i_sv(sv),.i_s(s[32*g+:32]),.i_mv(mv),.i_nmb(nmb),.o_mxv(mxv[g]),.o_mx(mx[32*g+:32]),
 .o_ev(ev[g]),.o_es(es[g]),.o_el(el[g]),.o_e(e[32*g+:32]));
 end endgenerate
 ot_s81_su_sml_fold2 #(.MUT(MUT)) D(.clk(clk),.rst_in(rst),.sk_en(1'b1),.i_cv(cv),.i_nv(nv),.i_scale(scale),.i_sink(sink),
 .i_sv(sv),.i_s(s),.i_mv(mv),.i_nmb(nmb),.o_mxv(fmxv),.o_mx(fmx),.o_ev(fev),.o_es(fes),.o_el(fel),.o_e(fe),.o_fault(fault));
 reg[33:0]q0[$],q1[$];reg[31:0]qm0[$],qm1[$];reg[63:0]qfm[$];integer err=0,checks=0;
 reg[33:0]x;reg[31:0]a,b;
 always @(negedge clk)if(rst)begin
  if(ev[0])q0.push_back({es[0],el[0],e[31:0]});
  if(ev[1])q1.push_back({es[1],el[1],e[63:32]});
  if(mxv[0])qm0.push_back(mx[31:0]);if(mxv[1])qm1.push_back(mx[63:32]);
  if(fev)begin
   if(q0.size()==0)begin $display("missing lower reference");err++;end
   else begin x=q0.pop_front();if(x!=={fes,fel,fe[31:0]})begin $display("lower mismatch %h %h",x,{fes,fel,fe[31:0]});err++;end checks++;end
   if(!fes)begin
    if(q1.size()==0)begin $display("missing upper reference");err++;end
    else begin x=q1.pop_front();if(x!=={fes,fel,fe[63:32]})begin $display("upper mismatch %h %h",x,{fes,fel,fe[63:32]});err++;end checks++;end
   end
  end
  if(fmxv)qfm.push_back(fmx);
 end
 task tick;begin @(posedge clk);#0.1;end endtask
 function automatic[31:0]score(input integer k);
  if(k%11==0)score=32'hff800000;else score={1'($urandom),8'(123+$urandom%5),23'($urandom)};
 endfunction
 integer j,k,seed=1108;
 initial begin
 seed=$urandom(seed);repeat(4)tick;rst=1;repeat(8)tick;
 for(j=0;j<4;j++)begin
  nv=(j==0)?1:(j==1)?2:(j==2)?8:40;
  cv=1;tick;cv=0;repeat(6)tick;
  for(k=0;k<nv;k++)begin sv=1;s={score(k+1),score(k)};tick;sv=0;repeat(2)tick;end
  repeat(30)tick;mv=1;tick;mv=0;repeat(300)tick;
 end
 while(qfm.size()>0 && qm0.size()>0 && qm1.size()>0)begin
 a=qm0.pop_front();b=qm1.pop_front();s=qfm.pop_front();if(s!=={b,a})begin $display("max mismatch %h %h",s,{b,a});err++;end checks++;
 end
 if(qfm.size()!=0)err++;
 if(q0.size()!=0||q1.size()!=0||qm0.size()!=0||qm1.size()!=0||fault)begin $display("leftover/fault %d %d %b",q0.size(),q1.size(),fault);err++;end
 if(err)$fatal(1,"FOLD2 FAIL checks%0d errors%0d MUT%0d",checks,err,MUT);
 $display("FOLD2 PASS checks%0d MUT%0d",checks,MUT);$finish;
 end
endmodule
