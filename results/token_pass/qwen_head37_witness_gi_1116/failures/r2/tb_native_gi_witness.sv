`timescale 1ns/1ps
// Actual TT GI region integration. LP/HR regions are excluded, never stubbed.
module tb_native_gi_witness;
`include "component_constants.svh"
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[74:0]pw=0;reg[186:0]dh=0;
reg[1:0]dh_user=0;reg[82:0]auth=0;
wire[115:0]cmd;wire[16:0]status;wire[61:0]dcs;
wire cal_ready;wire[15:0]observation;wire observer_fault;
wire[9:0]ag5=$test$plusargs("NO_ME_RETIRE") ? 10'b1000000000:10'd0;
wire[37:0]event_face;
qfd_tt_ctlm_dv_gi_hp13 #(.HEAD_STAGE37(1),.STAGE_ME(1),.NU(4),
 .UVM_STRIDE(4096),.PIDX_STRIDE(128),.PRIVATE_CALR(1),.F16WTN(1),
 .OPSEG(0),.CTX_SRC(0),.FCTX(0)) dut(
 .ck(ck),.rst_n(rst_n),.pw(pw),.f16_auth(auth),.f16_obs(event_face),.f16_st(status),
 .dh(dh),.dh_user(dh_user),.init_u0(1'b0),.ctx_x(129'd0),.mu_fault(1'b0),
 .ss5(107'd0),.ag5(ag5),.fab(1'b0),.cmd(cmd),.cal_image_ready(cal_ready),.dcs(dcs));
wire actual_su=cmd[0]&&cmd[3:1]==1;
wire selected_issue=actual_su&&!($test$plusargs("DROP_OBS")&&cmd[115:112]==0&&cmd[12:11]==1);
qfd_dv_typed_su_observer #(.ENABLE(1)) observer(.ck(ck),.rst_n(rst_n),
 .su_issue(selected_issue),.cmd_user(cmd[12:11]),.su_pidx(cmd[12:4]),
 .cmd_slice(cmd[115:112]),.observation(observation),.fault(observer_fault));
// Component-only context carrier: real typed observer register + selected host
// stage/token identity. The final die context transport is not qualified here.
wire[15:0]epoch=(16'h100+16'(observation[14:13]))^
 (($test$plusargs("BAD_EPOCH")&&observation[14:13]==2&&observation[12:9]==0)?16'd1:16'd0);
assign event_face={observation,6'd37,epoch};
qfd_head37_witness_trace probe(.ck(ck),.rst_n(rst_n),
 .start({dut.u_start,2'(dut.u_user),dut.u_stage,dut.u_tokid}),.obs(event_face));
reg[63:0]image[0:1023],desc[0:7];
integer k,u,cycles=0,commands=0,groups=0,retires=0;
integer next_group[0:3];reg[3:0]group_users=0,retired_users=0;
integer start_edge[0:3];integer last_observation[0:3];
always@(posedge ck)begin
 cycles<=cycles+1;
 if(rst_n&&dut.u_start)begin
  start_edge[dut.u_user]=cycles;
  $display("GI_ACCEPTED_START edge%0d user%0d token%0d",cycles,dut.u_user,dut.u_tokid);
 end
 if(rst_n&&actual_su)begin
  commands<=commands+1;
  if(cmd[12:4]!==9'(16+128*cmd[12:11])||cmd[115:112]>=12)$fatal(1,"NATIVE_COMMAND_IDENTITY");
 end
 if(rst_n&&event_face[37])begin
  last_observation[event_face[36:35]]=cycles;
  $display("GI_OBS edge%0d user%0d slice%0d delta%0d",cycles,event_face[36:35],event_face[34:31],cycles-start_edge[event_face[36:35]]);
 end
 if(rst_n&&dut.c_done)begin
  retires<=retires+1;retired_users[dut.c_done_user]=1;
  $display("GI_REAL_RETIRE edge%0d user%0d me_retired%0d lastobs%0d",cycles,dut.c_done_user,!dut.ag_stn_busy,last_observation[dut.c_done_user]);
 end
end
always@(negedge ck)if(rst_n)begin
 if(status[9])begin
  if(!$test$plusargs("OLD_DATES")&&!$test$plusargs("DROP_OBS")&&!$test$plusargs("BAD_EPOCH")&&!$test$plusargs("NO_ME_RETIRE"))begin
   if(status[15:12]!==4'(next_group[status[11:10]]))$fatal(1,"PARENT_GROUP_ORDER");
   next_group[status[11:10]]=next_group[status[11:10]]+1;
  end
  groups=groups+1;group_users[status[11:10]]=1;
  $display("GI_GROUP edge%0d user%0d group%0d",cycles,status[11:10],status[15:12]);
 end
 if(dcs[2])$fatal(1,"REAL_CALENDAR_FAULT code%h",dut.c_fcode);
end
initial begin
 if($test$plusargs("OLD_DATES"))$readmemh("stale_pw.hex",image);
 else $readmemh("component_pw.hex",image);
 $readmemh("dw.hex",desc);
 for(k=0;k<4;k=k+1)begin next_group[k]=13;start_edge[k]=-1;last_observation[k]=-1;end
 auth={3'b000,COMPONENT_DIGEST,16'd8};
 repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);
 for(k=0;k<1024;k=k+1)begin
  pw={1'b1,10'(k),image[k]};
  dh[118]=1;dh[117:108]=10'(k);dh[107:44]=image[k];
  @(negedge ck);
 end
 pw=0;dh=0;
 for(k=0;k<8;k=k+1)begin
  dh[186]=1;dh[185:183]=3'(k);dh[182:119]=desc[k];@(negedge ck);
 end
 dh=0;auth={3'b011,COMPONENT_DIGEST,16'd8};repeat(128)@(negedge ck);
 if(!cal_ready||!status[0]||status[16])$fatal(1,"GI_INSTALL_READY cal%0d status%h",cal_ready,status);
 for(u=0;u<4;u=u+1)begin
  dh_user=2'(u);dh[42]=1;dh[41:36]=37;dh[35:18]=18'h100+18'(u);dh[17:0]=18'(u);
  @(negedge ck);dh=0;
  repeat(360)@(negedge ck);
 end
 if(commands!=48||retires!=4||retired_users!=15||observer_fault)$fatal(1,"NATIVE_PARENT_COMMAND_RETIRE_COVERAGE cmd%0d ret%0d users%h",commands,retires,retired_users);
 if($test$plusargs("OLD_DATES")||$test$plusargs("DROP_OBS")||$test$plusargs("BAD_EPOCH")||$test$plusargs("NO_ME_RETIRE"))begin
  if(!status[16]||!dcs[1])$fatal(1,"NATIVE_PARENT_MUTANT_NOT_CAUGHT status%h dcs%h",status,dcs);
  $display("NATIVE_GI_WITNESS_MUTANT_CAUGHT groups%0d faultreturned1",groups);
 end else begin
  if(status[16]||dcs[1]||status[4:1]!=0||groups!=8||group_users!=15)$fatal(1,"NATIVE_GI_WITNESS_STATUS status%h groups%0d users%h dcs%h",status,groups,group_users,dcs);
  $display("NATIVE_GI_15RECORD_COMPONENT_PASS commands48 groups8 retired4 users4 active0 output_edges2 parent_extra0");
 end
 $finish;
end
endmodule
