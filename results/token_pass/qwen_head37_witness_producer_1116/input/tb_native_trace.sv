`timescale 1ns/1ps
// Component calendar replay, not the final transformer programme or die transport.
module tb_native_trace;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0,pw_v=0,dw_v=0,start=0;
reg[9:0]pw_addr=0;reg[2:0]dw_addr=0;reg[63:0]dw_data=0,desc[0:7];
reg[1:0]user_id=0;wire[115:0]cmd;wire[1:0]cmd_user;
wire ready,fault,done,su_issue;wire[5:0]fault_code;wire[3:0]running;
wire[8:0]su_pidx;
qfd_dv_cmd_cal_mu_head37 #(.HEAD_STAGE37(1),.NU(4),.CTX_DW(1),.UFOLD(1),
 .CALENDAR_ROM(1),.TABLE_ROM(1),.UVM_STRIDE(4096),.PIDX_STRIDE(128),.CALREG(1)) cal(
 .ck(ck),.rst_n(rst_n),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(64'd0),
 .dw_v(dw_v),.dw_addr(dw_addr),.dw_data(dw_data),.start(start),.stage(6'd37),
 .start_user(user_id),.start_rng(1'b1),.start_first(10'd0),.start_cnt(10'd13),
 .cmd(cmd),.cmd_user(cmd_user),.image_ready(ready),.running_u(running),
 .done(done),.fault(fault),.fault_code(fault_code),.su_issue(su_issue),.su_pidx(su_pidx));
wire[15:0]observation;wire observer_fault;
wire[1:0]obs_user=$test$plusargs("MUT_USER") ? (cmd_user^2'd1):cmd_user;
wire issue_for_observer=su_issue&&!($test$plusargs("DROP_OBS")&&cmd[115:112]==11&&cmd_user==3);
qfd_dv_typed_su_observer #(.ENABLE(1)) observer(.ck(ck),.rst_n(rst_n),
 .su_issue(issue_for_observer),.cmd_user(obs_user),.su_pidx(su_pidx),
 .cmd_slice(cmd[115:112]),.observation(observation),.fault(observer_fault));
// The actual observer outputs its registered typed command. This component
// supplies the selected context's constant stage/token metadata alongside it;
// actual global stage/token transport and due dates remain a separate join.
wire[37:0]obs_face={observation,6'd37,(16'h100+16'(observation[14:13]))};
qfd_head37_witness_trace probe(.ck(ck),.rst_n(rst_n),
 .start({start,user_id,6'd37,(16'h100+16'(user_id))}),.obs(obs_face));
integer u,k,commands=0,cycles=0;
always@(posedge ck)begin
 cycles<=cycles+1;
 if(su_issue)begin
  commands<=commands+1;
  if(su_pidx!==9'(16+128*cmd_user)||cmd[115:112]>=12)$fatal(1,"ACTUAL_CALENDAR_IDENTITY");
 end
end
initial begin
 $readmemh("dw.hex",desc);
 repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);
 for(k=0;k<1024;k=k+1)begin pw_v=1;pw_addr=10'(k);@(negedge ck);end
 pw_v=0;
 for(k=0;k<8;k=k+1)begin dw_v=1;dw_addr=3'(k);dw_data=desc[k];@(negedge ck);end
 dw_v=0;repeat(128)@(negedge ck);
 if(!ready||fault||running!==0)$fatal(1,"ACTUAL_CALENDAR_BOOT %b %h %b",ready,fault_code,running);
 for(u=0;u<4;u=u+1)begin
  if(fault||running[u])$fatal(1,"UNACCEPTABLE_CONTEXT_START");
  user_id=2'(u);start=1;@(negedge ck);start=0;
  repeat(300)@(negedge ck);
  if(fault||running[u])$fatal(1,"ACTUAL_CALENDAR_RUNTIME %h %b",fault_code,running);
 end
 if(commands!=48)$fatal(1,"ACTUAL_COMMAND_COUNT %0d",commands);
 if($test$plusargs("MUT_USER"))begin
  if(!observer_fault)$fatal(1,"MUTANT_NOT_CAUGHT");
  $display("NATIVE_OBSERVER_USER_MUTANT_CAUGHT");
 end else if(observer_fault)$fatal(1,"ACTUAL_OBSERVER_FAULT");
 $display("NATIVE_CALREG1_OBSERVER_TRACE_COMPONENT_PASS48 commands cycles%0d",cycles);
 $finish;
end
endmodule
