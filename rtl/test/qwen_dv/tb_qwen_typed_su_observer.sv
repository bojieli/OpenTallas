`timescale 1ns/1ps
module tb_qwen_typed_su_observer;
 reg ck=0,rst_n=0;always #5 ck=~ck;
 reg issue=0;reg[1:0]user_id=0;reg[8:0]pc=0;reg[3:0]slice=0;
 wire[15:0]typed,legacy;wire fault,legacy_fault;
 qfd_dv_typed_su_observer #(.ENABLE(1)) t(.ck(ck),.rst_n(rst_n),.su_issue(issue),.cmd_user(user_id),.su_pidx(pc),.cmd_slice(slice),.observation(typed),.fault(fault));
 qfd_dv_typed_su_observer l(.ck(ck),.rst_n(rst_n),.su_issue(issue),.cmd_user(user_id),.su_pidx(pc),.cmd_slice(slice),.observation(legacy),.fault(legacy_fault));
 string file;integer fd,rv,u,n=0,mut=0;reg[115:0]cmd;reg[15:0]expect_t,expect_l,observed;
 initial begin
  if(!$value$plusargs("EVENTS=%s",file))$fatal(1,"EVENTS");rv=$value$plusargs("MUT=%d",mut);
  repeat(3)@(negedge ck);rst_n=1;fd=$fopen(file,"r");
  while(!$feof(fd))begin
   rv=$fscanf(fd,"%d %h\n",u,cmd);
   if(rv==2)begin
    @(negedge ck);issue=cmd[0]&&cmd[3:1]==1;user_id=u;pc=cmd[12:4];slice=cmd[115:112];
    if(!issue)$fatal(1,"not actual source SU");
    expect_t={1'b1,2'(u),cmd[115:112],cmd[12:4]};
    expect_l={u==0,u==0,2'd2,3'd0,cmd[12:4]};
    @(posedge ck);#1;observed=typed^((mut==1)?16'h2000:16'd0);
    if(observed!==expect_t||legacy!==expect_l||fault||legacy_fault)$fatal(1,"TYPED_SU_OBSERVER_FAIL n%0d",n);
    n++;
   end
  end
  $fclose(fd);
  @(negedge ck);issue=0;@(posedge ck);#1;if(typed[15]||legacy[15])$fatal(1,"valid not cleared");
  @(negedge ck);issue=1;slice=12;@(posedge ck);#1;if(!fault||legacy_fault)$fatal(1,"unsupported unicast guard");
  $display("TYPED_SU_OBSERVER_PASS source_events=%0d typed_users=4 default_legacy_exact=1 register_stages=1 invalid_slice_fault=1",n);$finish;
 end
endmodule
