`timescale 1ns/1ps
module tb_static_ownership #(parameter integer MUT=0,GMUT=0);
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,we=0,go=0,host=1,upstream=1;
 reg[1:0]addr=0;reg[31:0]data=0,drained=32'hffffffff,gfault=0;
 wire mode,valid,reserved,active,done,configured,fault;wire[31:0]cycle;wire[7:0]code;
 qkd_static_kv_ownership_calendar #(.MUT(MUT))dut(
 .ck(ck),.rst_n(rst_n),.cfg_we(we),.cfg_addr(addr),.cfg_data(data),.go(go),
 .host_quiet(host),.upstream_quiet(upstream),.group_drained(drained),.group_fault(gfault),
 .native_mode(mode),.ownership_valid(valid),.native_reserved(reserved),.active(active),.done(done),.configured(configured),
 .cycle(cycle),.fault(fault),.fault_code(code));
 reg[3:0]ci=0,ri=0,ch=0,fh=0,rh=0,cf=0,rf=0,cfh=0,rfh=0,foh=0,fgh=0,fhh=0;
 reg uq=0,uf=0;wire guard_idle,guard_fault;
 qkd_static_kv_drain_guard4 #(.MUT(GMUT)) guard(
 .ck(ck),.rst_n(rst_n),.ctrl_idle_core(ci),.ring_idle_core(ri),
 .ctrl_idle_hbm(ch),.front_idle_hbm(fh),.ring_idle_hbm(rh),
 .ctrl_fault_core(cf),.ctrl_completion_fault_core(4'b0),.ctrl_intake_fault_core(4'b0),.ring_fault_core(rf),.ctrl_fault_hbm(cfh),.ctrl_output_fault_hbm(4'b0),.ctrl_calendar_fault_hbm(4'b0),.ring_fault_hbm(rfh),
 .front_fault_overflow_hbm(foh),.front_fault_go_hbm(fgh),.front_hold_hbm(fhh),
 .upstream_quiet(uq),.upstream_fault(uf),.drained(guard_idle),.fault(guard_fault));
 task tick;begin @(posedge ck);#1;end endtask
 task bootword(input[1:0]a,input[31:0]d);begin
  @(negedge ck);we=1;addr=a;data=d;tick();@(negedge ck);we=0;tick();tick();
 end endtask
 task reset_all;begin
  @(negedge ck);rst_n=0;we=0;go=0;host=1;upstream=1;drained=32'hffffffff;gfault=0;
  ci=0;ri=0;ch=0;fh=0;rh=0;cf=0;rf=0;cfh=0;rfh=0;foh=0;fgh=0;fhh=0;uq=0;uf=0;
  repeat(5)tick();@(negedge ck);rst_n=1;repeat(5)tick();
 end endtask
 task boot;begin bootword(0,4);bootword(1,14);bootword(2,20);bootword(3,32'h514b564d);
  if(!configured||!valid||fault)$fatal(1,"boot did not seal");end endtask
 task start;begin @(negedge ck);go=1;tick();@(negedge ck);go=0;tick();
  if(!active||cycle!=0||!reserved)$fatal(1,"go pin/accepted start age mismatch");end endtask
 task normal_case;integer i;begin reset_all();boot();start();
  for(i=1;i<=20;i=i+1)begin tick();
   if(mode!==(i>=4&&i<14))$fatal(1,"fixed mode edge differs cycle=%0d mode=%0d",i,mode);
   if(fault||!valid)$fatal(1,"valid static programme faulted cycle=%0d code=%h",i,code);
   if(cycle!=i)$fatal(1,"timeline moved");
   if(reserved!==(i<20))$fatal(1,"reservation admission window differs");
  end
  if(active||!done)$fatal(1,"fixed deadline differs");
 end endtask
 task host_busy_case;integer i;begin reset_all();boot();start();
  @(negedge ck);host=0;
  for(i=1;i<=4;i=i+1)tick();
  if(!fault||valid||!code[3])$fatal(1,"dirty HOST handover accepted");
 end endtask
 task dirty_leave_case;integer i;begin reset_all();boot();start();
  for(i=1;i<=14;i=i+1)begin
   if(i==7)begin @(negedge ck);drained[0]=0;end
   tick();if(i<14&&fault)$fatal(1,"idle observation rescheduled valid native interval");
  end
  if(!fault||valid||!code[4])$fatal(1,"unpaid native debt accepted at compiled leave");
 end endtask
 task source_fault_case;integer i;begin reset_all();boot();start();
  repeat(6)tick();@(negedge ck);gfault[4]=1;repeat(3)tick();
  if(!fault||valid||!code[5])$fatal(1,"native source fault ignored");
 end endtask
 task unsealed_case;begin reset_all();
  @(negedge ck);go=1;repeat(3)tick();
  if(!fault||valid||!code[2])$fatal(1,"unsealed go accepted");
 end endtask
 task malformed_case;begin reset_all();bootword(0,10);bootword(1,9);bootword(2,20);bootword(3,32'h514b564d);
  if(!fault||valid||!code[1])$fatal(1,"unordered image accepted");
 end endtask
 task guard_case;begin reset_all();
  repeat(8)tick();if(guard_idle)$fatal(1,"zero idle inputs produced drained");
  @(negedge ck);ci=15;ri=15;ch=15;fh=15;rh=15;uq=1;
  repeat(2)tick();if(guard_idle)$fatal(1,"crossing/stability stages bypassed");
  repeat(4)tick();if(!guard_idle||guard_fault)$fatal(1,"all real observations did not drain");
  @(negedge ck);rh[2]=0;repeat(4)tick();if(guard_idle)$fatal(1,"single unpaid HBM ring ignored");
  @(negedge ck);rh=15;repeat(6)tick();if(!guard_idle)$fatal(1,"drain did not recover");
  @(negedge ck);fhh[1]=1;repeat(4)tick();if(!guard_fault||guard_idle)$fatal(1,"late PHY hold lost");
  @(negedge ck);fhh=0;repeat(6)tick();if(!guard_fault||guard_idle)$fatal(1,"fault was not sticky");
 end endtask
 integer which=-1;
 initial begin
  if($value$plusargs("CASE=%d",which))begin end
  if(which==-1||which==0)normal_case();
  if(which==-1||which==1)host_busy_case();
  if(which==-1||which==2)dirty_leave_case();
  if(which==-1||which==3)source_fault_case();
  if(which==-1||which==4)unsealed_case();
  if(which==-1||which==5)malformed_case();
  if(which==-1||which==6)guard_case();
  $display("PASS ownership fixed edges, explicit invalid handovers and both-domain guard; MUT=%0d CASE=%0d",MUT,which);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
