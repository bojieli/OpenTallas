`timescale 1fs/1fs
// Functional successor projection only, never substitute for selected flattened GI.
module tb_qwen_head_xpf37_control;
reg ck=0;always #416500 ck=~ck;
reg rst_n=0,pw_v=0,start=0,stop=0,su_issue=0;reg[9:0]pw_addr=0;reg[63:0]pw_data=0;
reg[3:0]sl=0;reg[8:0]pc=0;wire[15:0]ob;wire ofault;
qfd_dv_typed_su_observer #(.ENABLE(1)) obs(.ck(ck),.rst_n(rst_n),.su_issue(su_issue),.cmd_user(2'd0),.su_pidx(pc),.cmd_slice(sl),.observation(ob),.fault(ofault));
wire cv,cc,cs;wire[1:0]ci;wire[187:0]cd;wire[2:0]cn;wire[5:0]stage;wire[31:0]stop_cycle;wire[11:0]base;wire present,lready,lfault;
qfd_dv_xpf_seg_loader loader(.clk(ck),.rst_n(rst_n),.stage_active(active),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),.cfg_clear(cc),.cfg_v(cv),.cfg_seal(cs),.cfg_index(ci),.cfg_data(cd),.cfg_count(cn),.stage(stage),.stop_cycle(stop_cycle),.base(base),.present(present),.image_ready(lready),.fault(lfault));
wire ready,fault,active;wire[71:0]xpf;wire[31:0]cycle;
ot_qfd_xpf_static_schedule #(.N(3)) mon(.clk(ck),.rst_n(rst_n),.cfg_v(cv),.cfg_index(ci),.cfg_data(cd),.cfg_clear(cc),.cfg_seal(cs),.cfg_count(cn),.start(start),.stop(stop),.stage(stage),.me_issue(1'b0),.me_pc(12'd0),.su_issue(ob[15]),.su_pc({3'd0,ob[8:0]}),.cp_issue(1'b0),.cp_pc(12'd0),.image_ready(ready),.xpf(xpf),.fault(fault),.active(active),.cycle(cycle));
reg[63:0]pw[0:1023];reg[71:0]gold[0:0];integer mut=0,arms=0,seen=0;
always @(negedge ck)if(rst_n)begin
 if(xpf[0])begin if(xpf!==gold[0])$fatal(1,"XPF_SOURCE_FIELDS");arms++;end
 if(ob[15])seen++;
end
initial begin
 if(!$value$plusargs("MUT=%d",mut))mut=0;
 $readmemh("input/program.memh",pw);$readmemh("input/xpf72.memh",gold);
 repeat(8)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);
 for(integer i=0;i<1024;i++)begin pw_v=1;pw_addr=i;pw_data=pw[i];@(negedge ck);end
 pw_v=0;repeat(16)@(negedge ck);
 if(!lready||!ready||lfault||fault||cn!=1||base!=28||stage!=37||stop_cycle!=400)$fatal(1,"REAL_XPF_LOADER_ABI");
 start=1;@(negedge ck);start=0;
 for(integer t=0;t<400;t++)begin
  su_issue=t>=128&&t<=150&&t%2==0;sl=(t-128)/2;pc=t==128?17:16;
  if(mut==1&&t==128)pc=16;
  if(mut==2&&t==130)pc=17;
  @(negedge ck);
 end
 su_issue=0;stop=1;@(negedge ck);stop=0;repeat(8)@(negedge ck);
 $display("XPF37_SUMMARY mut=%0d arms=%0d seen=%0d fault=%0d loader=%0d observer=%0d",mut,arms,seen,fault,lfault,ofault);
 if(lfault||ofault||arms!=1||seen!=12||fault!=(mut!=0))$fatal(1,"XPF37_CONTROL_VERDICT");
 $display("PASS_HEAD_XPF37_CONTROL_COMPONENT");$finish;
end
endmodule
