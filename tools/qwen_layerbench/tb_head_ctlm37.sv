`timescale 1ns/1fs
module tb_head_ctlm37;
reg ck=0;always #0.416500 ck=~ck;reg rst_n=0;
reg pw_v=0,dw_v=0,start=0,rng=0;reg[9:0]pw_addr=0,first=0;reg[2:0]dw_addr=0;reg[63:0]dw_data=0,desc[0:7];reg[1:0]user_id=0;reg[5:0]stage=0;
wire[2:0]load,ready,fault,done;wire[5:0]ts[0:2],fc[0:2];wire[1:0]tu[0:2];wire[3:0]running[0:2];wire[115:0]cmd[0:2];
`define PORT(I) .ck(ck),.rst_n(rst_n),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(64'd0),.dw_v(dw_v),.dw_addr(dw_addr),.dw_data(dw_data),.start(start),.stage(stage),.start_user(user_id),.start_rng(rng),.start_first(first),.start_cnt(10'd1),.cmd(cmd[I]),.table_load(load[I]),.table_stage(ts[I]),.table_user(tu[I]),.image_ready(ready[I]),.running_u(running[I]),.done(done[I]),.fault(fault[I]),.fault_code(fc[I])
qfd_dv_cmd_cal_mu #(.NU(4),.CTX_DW(1),.UFOLD(1),.CALENDAR_ROM(1),.TABLE_ROM(1),.UVM_STRIDE(4096),.PIDX_STRIDE(128),.CALREG(7)) original(`PORT(0));
qfd_dv_cmd_cal_mu_head37 #(.NU(4),.CTX_DW(1),.UFOLD(1),.CALENDAR_ROM(1),.TABLE_ROM(1),.UVM_STRIDE(4096),.PIDX_STRIDE(128),.CALREG(7)) off0(`PORT(1));
qfd_dv_cmd_cal_mu_head37 #(.HEAD_STAGE37(1),.NU(4),.CTX_DW(1),.UFOLD(1),.CALENDAR_ROM(1),.TABLE_ROM(1),.UVM_STRIDE(4096),.PIDX_STRIDE(128),.CALREG(7)) on1(`PORT(2));
integer s,u,k,idx,existing=1,active=0,requests=0,headrequests=0,cycles=0;
always @(negedge ck)if(rst_n)begin
 cycles=cycles+1;
 if(existing)begin
  if({load[0],ts[0],tu[0],ready[0],fault[0],fc[0],done[0],running[0],cmd[0]}!=={load[1],ts[1],tu[1],ready[1],fault[1],fc[1],done[1],running[1],cmd[1]}||
     {load[0],ts[0],tu[0],ready[0],fault[0],fc[0],done[0],running[0],cmd[0]}!=={load[2],ts[2],tu[2],ready[2],fault[2],fc[2],done[2],running[2],cmd[2]})$fatal(1,"CTLM_DEFAULT_LOCKSTEP");
 end
 if(active&&load[2])begin
  if(ts[2]!==6'(s)||tu[2]!==2'(u))$fatal(1,"CTLM_WRONG_REQUEST stage%0d/%0d user%0d/%0d",ts[2],s,tu[2],u);
  if(existing)requests=requests+1;else headrequests=headrequests+1;
 end
 if(!existing&&(load[0]||load[1]))$fatal(1,"CTLM_OFF_ACCEPTED_37");
end
initial begin
 $readmemh("dw.hex",desc);
 repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);
 for(k=0;k<1024;k=k+1)begin pw_v=1;pw_addr=10'(k);@(negedge ck);end
 pw_v=0;
 for(k=0;k<8;k=k+1)begin dw_v=1;dw_addr=3'(k);dw_data=desc[k];@(negedge ck);end
 dw_v=0;repeat(128)@(negedge ck);
 if(ready!==3'b111||fault!==0)$fatal(1,"CTLM_IMAGE_READY %b %b",ready,fault);
 for(s=1;s<=36;s=s+1)for(u=0;u<4;u=u+1)begin
  active=1;stage=6'(s);first=10'(868+4*(s-1));rng=1;user_id=2'(u);start=1;@(negedge ck);start=0;
  repeat(64)@(negedge ck);active=0;
  if(fault!==0||running[2]!==0)$fatal(1,"CTLM_EXISTING_LOAD_FAULT");
 end
 if(requests!=144)$fatal(1,"CTLM_EXISTING_COVERAGE %0d",requests);
 existing=0;s=37;
 for(u=0;u<4;u=u+1)begin
  active=1;stage=37;first=1012;rng=1;user_id=2'(u);
  if($test$plusargs("MUT_USER")&&u==1)user_id=0;
  start=1;@(negedge ck);start=0;repeat(64)@(negedge ck);active=0;
 end
 if(headrequests!=4||!fault[0]||!fault[1]||fault[2]||!fc[0][4]||!fc[1][4])$fatal(1,"CTLM_37_COVERAGE requests%0d faults%b fc%h/%h/%h",headrequests,fault,fc[0],fc[1],fc[2]);
 $display("NATIVE_CTLM37_PASS oldloads144 headloads4 nent1013 sharedrange1012 defaultoffreject cycles%0d",cycles);$finish;
end
endmodule
