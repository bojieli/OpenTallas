`timescale 1ns/1ps
module tb_qwen_dspark_s7_control;
 reg clk=0,rst=0,sv=0,cr=0,dv=0,rr=0,fenced=1,trunc3=0;
 always #0.555555 clk=~clk;
 reg [63:0] sid=0,did=0;reg [7:0] dseq=0;reg [17:0] dtok=0;reg [143:0] targets=0;reg [3:0] dn=0,ctx=3;
 wire sr,cv,rv,fault;wire [4:0] op;wire [2:0] layer,slot;wire [3:0] positions,commitn,rn;wire [17:0] token,pos,bonus,rpos;wire [63:0] cid,rid;wire [7:0] seq;
 ot_qwen_dspark_s7_control #(.ENABLE(1)) dut(.clk(clk),.rst_n(rst),.start_v(sv),.start_r(sr),.start_id(sid),.start_token(18'd77),.start_pos(18'd8190),
  .context_n(ctx),.truncate3(trunc3),.allcopy_fenced(fenced),.cmd_v(cv),.cmd_r(cr),.cmd_op(op),.cmd_layer(layer),.cmd_slot(slot),.cmd_positions(positions),.cmd_commit_n(commitn),
  .cmd_token(token),.cmd_pos(pos),.cmd_id(cid),.cmd_sequence(seq),.done_v(dv),.done_id(did),.done_sequence(dseq),.done_token(dtok),.done_targets(targets),.done_n(dn),.done_fault(1'b0),
  .result_v(rv),.result_r(rr),.result_id(rid),.result_n(rn),.result_bonus(bonus),.result_pos(rpos),.fault(fault));
 task automatic reset;
  begin @(negedge clk);rst=0;sv=0;dv=0;cr=0;rr=0;fenced=1;repeat(3)@(negedge clk);rst=1;repeat(3)@(negedge clk);end
 endtask
 integer mode,prefix,g,j,commands,gathers,tests=0;
 reg [4:0] heldop;reg [7:0] heldseq;
 initial begin
  reset();
  for(mode=0;mode<2;mode=mode+1)begin
   g=(mode==0)?7:3;trunc3=mode!=0;
   for(prefix=0;prefix<=g;prefix=prefix+1)begin
    sid=sid+1;ctx=4'(prefix+1);
    @(negedge clk);if(!sr)$fatal(1,"start credit absent");sv=1;@(negedge clk);sv=0;commands=0;gathers=0;
    while(!rv)begin
     if(fault)$fatal(1,"unexpected control fault");
     if(cv)begin
      heldop=op;heldseq=seq;did=cid;dseq=seq;
      repeat(2)begin @(negedge clk);if(!cv||op!==heldop||seq!==heldseq||cid!==sid)$fatal(1,"dispatch hold/identity changed");end
      if(op>=5&&op<=8&&positions!=7)$fatal(1,"S3 incorrectly substituted for fullS7");
      if(op==13)begin gathers=gathers+1;dtok=18'(100+slot);end
      if(op==14)begin
       if(positions!=g+1||gathers!=7)$fatal(1,"not all7 drafter slots executed");
       for(j=0;j<8;j=j+1)targets[j*18+:18]=18'(j<prefix?100+j:900+j);
       dn=4'(g+1);
      end
      if(op==15)begin if(commitn!=prefix+1)$fatal(1,"prefix accept wrong");dn=commitn;end
      cr=1;@(negedge clk);cr=0;repeat(2)@(negedge clk);dv=1;@(negedge clk);dv=0;commands=commands+1;
     end else @(negedge clk);
    end
    if(commands!=54||rn!=prefix+1||rid!==sid||rpos!=8190+prefix+1||bonus!==18'(900+prefix))$fatal(1,"nativeaccept result wrong prefix=%0d",prefix);
    repeat(4)begin @(negedge clk);if(!rv||rn!=prefix+1||sr)$fatal(1,"result stalled lease lost");end
    rr=1;@(negedge clk);rr=0;tests=tests+1;
   end
  end
  reset();sid=55;ctx=3;sv=1;@(negedge clk);sv=0;@(negedge clk);cr=1;did=sid+1;dseq=seq;@(negedge clk);cr=0;dv=1;@(negedge clk);dv=0;@(negedge clk);
  if(!fault||cv||sr||rv)$fatal(1,"wrong cohort completion not quarantined");
  reset();dv=1;did=55;dseq=0;@(negedge clk);dv=0;@(negedge clk);
  if(!fault||cv||sr||rv)$fatal(1,"unsolicited completion not quarantined");
  $display("QWEN_S7_CONTROL_PASS accept_cases=%0d commands_each=54 drafter_always7=1 retained_context1to8=1 cohort_hold=1 wrongID_unsolicited_negative=1",tests);
  $finish;
 end
endmodule
