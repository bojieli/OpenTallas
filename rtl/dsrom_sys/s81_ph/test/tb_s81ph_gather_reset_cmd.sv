`timescale 1ns/1ps
module tb_s81ph_gather_reset_cmd;
 reg ck=0,ckv=0;always #3 ck=~ck;always #4 ckv=~ckv;
 reg rst=0,rsv=0;reg [159:0] fv=0;reg [84:0] cmd=0;reg [11:0] fc=0;
 wire [7:0] ready;wire [162:0] raw_tc,tc;wire [7:0] raw_rc,rc;wire [23:0] ts;wire [15:0] cs;wire [11:0] fcd;
 wire [10:0] xgo;wire [8:0] done;wire [1:0] st;
 dsfd_gth_strip strip(.ck_r({ckv,{132{ck}}}),.rst(rst),.rsv(rsv),.tst_i(24'h555555),.cs_i(16'd0),.ready_i(8'hFF),.rc_i(raw_rc),.tc_i(raw_tc),.fcd_i(fc),.tst_o(ts),.cs_o(cs),.ready_o(ready),.rc_o(rc),.tc_o(tc),.fcd_o(fcd));
 dsfd_gth_ctl ctl(.ck(ck),.ckv(ckv),.rst(rst),.rsv(rsv),.f_vm(fv),.tst(ts),.cs(cs),.roots_ready(ready),.c_cmd(cmd),.c_done(done),.c_st(st),.f_cd(fcd),.t_xgo(xgo),.tc(raw_tc),.rc(raw_rc));
 integer off,phase,q,epoch=0,fail=0,pass=0,b,k,rsv_off;
 reg tgl;reg [9:0] sent_ph[0:8];reg [6:0] sent_tag[0:8];reg saw_x,saw_d;reg [9:0] ph;reg [6:0] tag;
 task idle(input integer n);begin repeat(n)@(negedge ck);end endtask
 initial begin
  for(phase=0;phase<6;phase=phase+1)begin
   if(phase==3)continue; // avoid ambiguous exact coincident reset release/clock edge
   for(off=1;off<=6;off=off+1)begin
    rst=0;rsv=0;cmd=0;fv=0;fc=0;idle(10);
    if(tc[0] || done[8] || xgo[10] || rc!=0)$fatal(1,"old-epoch output during reset");
    #phase;rst=1;rsv=1;epoch=epoch+1;ph=epoch;tag=epoch;
    if(off>1)begin repeat(off-1)@(posedge ck);#0.1;end
    cmd={1'b1,1'b0,66'd0,ph,tag};@(posedge ck);#0.1;cmd=0;
    // phase payload deliberately follows reset/rc release; early command must survive.
    idle(100);@(negedge ckv);fv={100'd0,ph,47'd0,2'b00,1'b1};@(negedge ckv);fv=0;
    saw_x=0;saw_d=0;
    for(q=0;q<400;q=q+1)begin
     @(negedge ck);
     if(xgo[10])begin
      if(xgo[9:0]!==ph)$fatal(1,"old-epoch/wrong-phase xgo");saw_x=1;
      @(negedge ckv);fc={1'b1,1'b0,ph};
     end
     if(done[8])begin
      if(done[7:0]!=={1'b0,tag})$fatal(1,"old-epoch/wrong-tag done");saw_d=1;
     end
    end
    if(saw_x&&saw_d)begin pass=pass+1;$display("RESET_CMD PASS offset=%0d phase=%0d epoch=%0d",off,phase,epoch);end
    else begin fail=fail+1;$display("RESET_CMD FAIL lost_command offset=%0d phase=%0d epoch=%0d xgo=%b done=%b",off,phase,epoch,saw_x,saw_d);end
   end
  end
  // QD8 is the documented producer credit limit, including both pin stages.
  // Exercise eight real commands at successive first edges before any done,
  // then an illegal ninth command: sticky fault and no ninth start/done.
  for(rsv_off=0;rsv_off<8;rsv_off=rsv_off+1)begin
   for(b=8;b<=9;b=b+1)begin
    rst=0;rsv=0;cmd=0;fv=0;fc=0;tgl=0;idle(10);
    rst=1;
    fork
     begin #rsv_off;rsv=1;end
     begin
      for(k=0;k<b;k=k+1)begin
       epoch=epoch+1;sent_ph[k]=epoch;sent_tag[k]=epoch%128;
       cmd={1'b1,1'b0,66'd0,sent_ph[k],sent_tag[k]};@(posedge ck);#0.1;
      end
      cmd=0;
     end
    join
    idle(100);
    if(b==9 && !st[0])$fatal(1,"ninth command was silently accepted/dropped without sticky fault");
    if(b==8 && st[0])$fatal(1,"legal eight-credit burst raised fault");
    for(k=0;k<8;k=k+1)begin
     @(negedge ckv);fv={100'd0,sent_ph[k],47'd0,2'b00,1'b1};@(negedge ckv);fv=0;
     saw_x=0;saw_d=0;
     for(q=0;q<400;q=q+1)begin
      @(negedge ck);
      if(xgo[10])begin
       if(saw_x || xgo[9:0]!==sent_ph[k])$fatal(1,"burst reorder/duplicate/wrong phase");
       saw_x=1;@(negedge ckv);tgl=~tgl;fc={tgl,1'b0,sent_ph[k]};
      end
      if(done[8])begin
       if(saw_d || done[7:0]!=={1'b0,sent_tag[k]})$fatal(1,"burst wrong epoch/duplicate tag");saw_d=1;
      end
     end
     if(!saw_x || !saw_d)begin fail=fail+1;$display("BURST FAIL n=%0d rsv_offset=%0d job=%0d",b,rsv_off,k);end
    end
    if(b==9)begin
     @(negedge ckv);fv={100'd0,sent_ph[8],47'd0,2'b00,1'b1};@(negedge ckv);fv=0;
     repeat(400)begin @(negedge ck);if(xgo[10] || done[8])$fatal(1,"uncredited ninth job emitted start/done");end
     if(!st[0])$fatal(1,"credit fault not sticky");
    end
    if(!fail)begin pass=pass+1;$display("BURST PASS n=%0d rsv_offset=%0d accepted8completed8 ninth_fault=%b",b,rsv_off,st[0]);end
   end
  end
  $display("RESET_CMD SUMMARY pass=%0d fail=%0d",pass,fail);
  if(fail)$fatal(1,"reset/start contract loses early command");
  $display("RESET_CMD_GATE PASS");$finish;
 end
endmodule
