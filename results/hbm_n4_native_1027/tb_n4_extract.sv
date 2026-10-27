`timescale 1ps/1ps
module tb_n4_extract;
 reg clk=0;initial forever begin #416 clk=1;#417 clk=0;end
 reg rst_n=0,job_v=0;reg[216:0]job=0;reg[270:0]u[0:3];
 wire[172:0]gd[0:3],cd[0:3],rootd0,rootd2;wire[270:0]n4a,n4b;
 wire gdone,gfault,gbusy,cdone,cfault,cbusy;reg mutate=0,padded=0; reg[5:0] pk4=0,pk5=0;
 ot_hnx_fused_hub #(.N4EXT(0)) gold(.clk(clk),.rst_n(rst_n),.job_v(job_v),.job(job),.done(gdone),.fault(gfault),.busy(gbusy),
 .wsc(8'd115),.pk4a(pk4),.pk4b(pk4),.pk5(pk5),.pb4a(1'b0),.pb4b(1'b0),.pb5(1'b0),
 .uq0(u[0]),.uq1(u[1]),.uq2(u[2]),.uq3(u[3]),.dq0(gd[0]),.dq1(gd[1]),.dq2(gd[2]),.dq3(gd[3]));
 ot_hnx_fused_tnode n4_left(.clk(clk),.rst_n(rst_n),.pad_k(pk4),.pad_b(1'b0),.ua(u[0]),.ub(mutate?u[2]:u[1]),.uo(n4a),.dn(rootd0),.da(cd[0]),.db(cd[1]));
 ot_hnx_fused_tnode n4_right(.clk(clk),.rst_n(rst_n),.pad_k(pk4),.pad_b(1'b0),.ua(mutate?u[1]:u[2]),.ub(u[3]),.uo(n4b),.dn(rootd2),.da(cd[2]),.db(cd[3]));
 ot_hnx_fused_hub #(.N4EXT(1)) dut(.clk(clk),.rst_n(rst_n),.job_v(job_v),.job(job),.done(cdone),.fault(cfault),.busy(cbusy),
 .wsc(8'd115),.pk4a(pk4),.pk4b(pk4),.pk5(pk5),.pb4a(1'b0),.pb4b(1'b0),.pb5(1'b0),
 .uq0(n4a),.uq1(271'd0),.uq2(n4b),.uq3(271'd0),.dq0(rootd0),.dq1(),.dq2(rootd2),.dq3());
 integer checks=0,errors=0,chunks=0,scalars=0,commands=0,finflags=0;reg active=0;
 task automatic bad(input string why);
  errors=errors+1;if(errors<6)$display("N4_EXTRACT_MISMATCH %s check=%0d gold=%h new=%h",why,checks,gold.ur,dut.ur);
 endtask
 always @(negedge clk)if(active)begin
  checks=checks+1;
  if(gold.ur[270:256]!==dut.ur[270:256])bad("UP control including independent fin/fault");
  if(gold.ur[270]&&gold.ur[255:0]!==dut.ur[255:0])bad("UP valid payload");
  if(gold.ur[270]&&gold.ur[269])begin chunks=chunks+1;if(gold.ur[31:0]!==32'h3e35517a)bad("golden IEEE pair-tree witness");end
  if(gold.ur[270]&&!gold.ur[269])scalars=scalars+1;
  if(gold.ur[258]&&gold.ur[257])finflags=finflags+1;
  for(integer q=0;q<4;q=q+1)begin
   if({gd[q][172],gd[q][32]}!=={cd[q][172],cd[q][32]})bad("DOWN validity");
   if(gd[q][172])begin commands=commands+1;if(gd[q][171:33]!==cd[q][171:33])bad("DOWN command fields");end
   if(gd[q][32]&&gd[q][31:0]!==cd[q][31:0])bad("DOWN r fields");
  end
  if({gdone,gfault,gbusy}!=={cdone,cfault,cbusy})bad("hub state outputs");
 end
 task automatic tick;@(negedge clk);#1;endtask
 initial begin
  padded=$test$plusargs("PADS");pk4=padded?4:0;pk5=padded?2:0;
  for(integer q=0;q<4;q=q+1)u[q]=0;
  repeat(5)tick;rst_n=1;repeat(80)tick;active=1;
  mutate=$test$plusargs("MUT_PAIR");job=0;job[0]=1;job[216:185]=32'h358637bd;job_v=1;tick;job_v=0;
  // Legal positive partial sums whose rounding distinguishes golden vs cross-hub pairing.
  for(integer i=0;i<32;i=i+1)begin
   for(integer t=0;t<16;t=t+1)begin
    for(integer q=0;q<4;q=q+1)u[q]=0;
    if(t==0)u[0]={1'b1,1'b1,10'd0,3'b0,224'd0,32'h3b5c19bf};
    if(t==(padded?4:0))u[1]={1'b1,1'b1,10'd0,3'b0,224'd0,32'h3dc58aba};
    if(t==(padded?2:0))u[2]={1'b1,1'b1,10'd0,3'b0,224'd0,32'h3a5b3861};
    if(t==(padded?6:0))u[3]={1'b1,1'b1,10'd0,3'b0,224'd0,32'h3d9c80fb};
    tick;
   end
  end
  for(integer q=0;q<4;q=q+1)begin
   u[q]={1'b1,1'b0,10'(q),3'b0,{8{32'h3f800000+32'(q)}}};tick;u[q]=0;repeat(19)tick;
  end
  // Fin is independent of v and must survive the moved level-four nodes.
  for(integer t=0;t<8;t=t+1)begin
   for(integer q=0;q<4;q=q+1)u[q]=0;
   if(t==0)u[0]={1'b0,1'b0,10'd0,3'b110,256'd0};
   if(t==(padded?4:0))u[1]={1'b0,1'b0,10'd0,3'b110,256'd0};
   if(t==(padded?2:0))u[2]={1'b0,1'b0,10'd0,3'b110,256'd0};
   if(t==(padded?6:0))u[3]={1'b0,1'b0,10'd0,3'b110,256'd0};
   tick;
  end
  for(integer q=0;q<4;q=q+1)u[q]=0;repeat(120)tick;active=0;
  $display("N4_EXTRACT_RESULT checks=%0d errors=%0d chunks=%0d scalars=%0d commands=%0d finflags=%0d MUT_PAIR=%0d PADS=%0d clock_ps=833",checks,errors,chunks,scalars,commands,finflags,mutate,padded);
  if(errors||chunks!=32||scalars!=4||commands<8||finflags<1)$fatal(1,"N4_EXTRACT FAIL");
  $display("N4_EXTRACT PASS");$finish;
 end
endmodule
