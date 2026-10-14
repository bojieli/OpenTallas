`timescale 1ns/1ps
module tb_s81ph_gather_reset_cmd;
 reg ck=0,ckv=0;always #3 ck=~ck;always #4 ckv=~ckv;
 reg rst=0,rsv=0;reg [159:0] fv=0;reg [84:0] cmd=0;reg [11:0] fc=0;
 wire [162:0] raw_tc,tc;wire [7:0] raw_rc,rc;wire [23:0] ts;wire [15:0] cs;wire [11:0] fcd;
 wire [10:0] xgo;wire [8:0] done;wire [1:0] st;
 dsfd_gth_strip strip(.ck_r({ckv,{132{ck}}}),.rst(rst),.rsv(rsv),.tst_i(24'h555555),.cs_i(16'd0),.rc_i(raw_rc),.tc_i(raw_tc),.fcd_i(fc),.tst_o(ts),.cs_o(cs),.rc_o(rc),.tc_o(tc),.fcd_o(fcd));
 dsfd_gth_ctl ctl(.ck(ck),.ckv(ckv),.rst(rst),.rsv(rsv),.f_vm(fv),.tst(ts),.cs(cs),.c_cmd(cmd),.c_done(done),.c_st(st),.f_cd(fcd),.t_xgo(xgo),.tc(raw_tc),.rc(raw_rc));
 integer off,phase,q,epoch=0,fail=0,pass=0;reg saw_x,saw_d;reg [9:0] ph;reg [6:0] tag;
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
  $display("RESET_CMD SUMMARY pass=%0d fail=%0d",pass,fail);
  if(fail)$fatal(1,"reset/start contract loses early command");
  $display("RESET_CMD_GATE PASS");$finish;
 end
endmodule
