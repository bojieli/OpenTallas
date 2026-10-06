`timescale 1ns/1ps
module tb_wfc_producers;
 reg clk=0,rst_n=1,cold_fenced=0,cmd_v=0;reg [1:0] cmd_op=0;reg [9:0] cmd_user=0;
 reg [20:0] cmd_pos=0,cmd_token=0;reg [3:0] cmd_block=0;reg [15:0] cmd_epoch=5;reg [13:0] cmd_entry=12;
 wire cmd_ready;wire [9:0] users;wire [20:0] plen,glen;wire [15:0] epoch;wire [13:0] entry;
 reg pr_re=0;reg [9:0] pr_user=0;reg [20:0] pr_pos=0;reg [3:0] pr_blk=0;
 wire [20:0] pr_q;wire pr_qk,active,initializing,pfault;
 ot_dsrom_wfc_cfg_prompt #(.ENABLE(1)) p(.clk(clk),.rst_n(rst_n),.cold_fenced(cold_fenced),
 .cmd_v(cmd_v),.cmd_op(cmd_op),.cmd_user(cmd_user),.cmd_pos(cmd_pos),.cmd_token(cmd_token),.cmd_block(cmd_block),.cmd_epoch(cmd_epoch),.cmd_entry(cmd_entry),.cmd_ready(cmd_ready),
 .cfg_users(users),.cfg_prompt_len(plen),.cfg_gen_len(glen),.stage_epoch(epoch),.stage_entry(entry),
 .pr_re(pr_re),.pr_user(pr_user),.pr_pos(pr_pos),.pr_blk(pr_blk),.pr_q(pr_q),.pr_qk(pr_qk),.active(active),.initializing(initializing),.fault(pfault));
 reg request_v=0;wire request_ready;reg [46:0] id={16'd5,10'd865,21'd7};reg [20:0] request_token=21'd1123;
 reg [3:0] command_v=0,retire_v=0,fence_v=0;wire [3:0] command_ready;
 reg [187:0] command_identity=0,retire_identity=0,fence_identity=0;
 reg [83:0] command_token=0;reg [27:0] command_home=0,retire_home=0;
 reg [55:0] command_entry=0,command_pc=0,retire_entry=0;reg [15:0] command_unit=0;
 reg [23:0] retire_visibility=0;reg [19:0] fence_visibility=0;reg [3:0] quiet=0,drained=0,retire_fault=0;
 reg result_v=0,accepted=0;wire stage_v,pending,sfault,token_valid,handoff;
 wire [46:0] out_id;wire [20:0] out_token;wire [31:0] out_value;
 ot_dsrom_wfc_whole_stage #(.ENABLE(1),
 .BOOK0("results/uarch/dsrom_wfc_producers_20261005/book/rank0.viamap.hex"),
 .BOOK1("results/uarch/dsrom_wfc_producers_20261005/book/rank1.viamap.hex"),
 .BOOK2("results/uarch/dsrom_wfc_producers_20261005/book/rank2.viamap.hex"),
 .BOOK3("results/uarch/dsrom_wfc_producers_20261005/book/rank3.viamap.hex")) s(
 .clk(clk),.rst_n(rst_n),.request_v(request_v),.request_ready(request_ready),.request_identity(id),.request_token(request_token),.request_entry(14'd12),.configured_epoch(16'd5),
 .command_v(command_v),.command_ready(command_ready),.command_identity(command_identity),.command_token(command_token),.command_home(command_home),.command_entry(command_entry),.command_pc(command_pc),.command_unit(command_unit),
 .retire_v(retire_v),.retire_identity(retire_identity),.retire_home(retire_home),.retire_entry(retire_entry),.retire_visibility(retire_visibility),.retire_quiet(quiet),.retire_capture_drained(drained),.retire_fault(retire_fault),
 .fence_v(fence_v),.fence_identity(fence_identity),.fence_visibility(fence_visibility),
 .result_v(result_v),.result_identity(id),.result_token(21'd77889),.result_value(32'h3f810203),.whole_stage_accepted(accepted),
 .whole_stage_v(stage_v),.whole_stage_identity(out_id),.whole_stage_next_token(out_token),.whole_stage_value(out_value),.token_result_valid(token_valid),.stage_handoff(handoff),.pending(pending),.fault(sfault));
 reg [71:0] books[0:3][0:166];reg [71:0] load0[0:166],load1[0:166],load2[0:166],load3[0:166];integer cycles=0,commands=0,retires=0,reads=0,mode=0;
 task tick;begin #0.416667;clk=1;#0.416667;clk=0;cycles=cycles+1;end endtask
 task write_token(input integer op,u,pos,tok,blk);begin
  if(!cmd_ready)$fatal(1,"real command admission unavailable");
  cmd_op=2'(op);cmd_user=10'(u);cmd_pos=21'(pos);cmd_token=21'(tok);cmd_block=4'(blk);cmd_v=1;tick();cmd_v=0;
 end endtask
 task read_token(input integer u,pos,blk,tok,known);begin
  pr_user=10'(u);pr_pos=21'(pos);pr_blk=4'(blk);pr_re=1;tick();
  if(pr_qk!==1'(known)||(known&&pr_q!==21'(tok)))$fatal(1,"actual SRAM reply wrong user=%0d pos=%0d block=%0d got=%0d known=%0b",u,pos,blk,pr_q,pr_qk);
  pr_re=0;tick();reads=reads+1;
 end endtask
 initial begin
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank0.hex",load0);
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank1.hex",load1);
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank2.hex",load2);
  $readmemh("results/uarch/dsrom_wfc_producers_20261005/book/rank3.hex",load3);
  for(integer i=0;i<167;i=i+1)begin books[0][i]=load0[i];books[1][i]=load1[i];books[2][i]=load2[i];books[3][i]=load3[i];end
  tick();rst_n=0;tick();rst_n=1;
  if(mode==1||mode==2||mode==3)begin
   request_v=1;tick();request_v=0;tick();
   if(mode==2)begin rst_n=0;tick();rst_n=1;tick();if(!sfault||stage_v||!pending)$fatal(1,"warm reset erased accepted whole-stage debt");end
   else if(mode==3)begin fence_v=15;fence_identity={4{id}};fence_visibility={20{1'b1}};tick();if(!sfault||stage_v)$fatal(1,"early fence admitted completion");end
   else begin
    command_v=1;command_identity[0+:47]=id;command_token[0+:21]=request_token;command_home[0+:7]=books[0][0][6:0];command_entry[0+:14]=books[0][0][20:7];command_pc[0+:14]=books[0][0][34:21]+1;command_unit[0+:4]=books[0][0][38:35];tick();if(!sfault||stage_v)$fatal(1,"wrong native PC accepted");
   end
   $display("PASS WFC whole-stage negative MODE=%0d pending-preserved=%0b",mode,pending);$finish;
  end
  while(initializing)tick();
  for(integer u=0;u<866;u=u+1)for(integer pos=0;pos<3;pos=pos+1)write_token(0,u,pos,100+u*3+pos,0);
  write_token(2,866,3,30,0);
  while(!active&&!pfault)tick();
  if(pfault||users!=866||plen!=3||glen!=30||epoch!=5||entry!=12)$fatal(1,"full866 config/prompt admission failed");
  read_token(0,0,0,100,1);read_token(865,2,15,2697,1);
  write_token(1,865,31,77881,4);read_token(865,31,4,77881,1);read_token(865,31,5,0,0);
  write_token(1,865,31,77882,5);read_token(865,31,4,0,0);read_token(865,31,5,77882,1);read_token(865,39,5,0,0);write_token(1,865,21'h1fffff,123456,7);read_token(865,21'h1fffff,7,123456,1);read_token(865,31,5,0,0);
  if(mode==4)begin
   // Physical array columns bit*4+address%4; actual SRAM codeword fault.
   p.g_live.g_bank[0].u_prompt.arr[0][0]=~p.g_live.g_bank[0].u_prompt.arr[0][0];
   read_token(0,0,0,100,1);
   if(pfault)$fatal(1,"single mutable SRAM bit was not corrected");
   p.g_live.g_bank[0].u_prompt.arr[0][4]=~p.g_live.g_bank[0].u_prompt.arr[0][4];
   pr_re=1;pr_user=0;pr_pos=0;pr_blk=0;tick();if(pr_qk)$fatal(1,"double error released prompt");tick();if(!pfault)$fatal(1,"double mutable SRAM error did not poison");
   $display("PASS WFC prompt SECDED actual single repair/double refusal");$finish;
  end
  if(mode==5)begin rst_n=0;tick();rst_n=1;tick();if(!pfault||!active||pr_qk)$fatal(1,"warm reset forgot programmed active cfg");$display("PASS WFC cfg warm reset retains accepted run");$finish;end
  request_v=1;tick();request_v=0;tick();
  for(integer n=0;n<167;n=n+1)begin
   if(command_ready!=15)$fatal(1,"literal next command lacks book read readiness n=%0d",n);
   for(integer rank=0;rank<4;rank=rank+1)begin
    command_identity[47*rank+:47]=id;command_token[21*rank+:21]=request_token;
    command_home[7*rank+:7]=books[rank][n][6:0];command_entry[14*rank+:14]=books[rank][n][20:7];command_pc[14*rank+:14]=books[rank][n][34:21];command_unit[4*rank+:4]=books[rank][n][38:35];
   end
   command_v=15;tick();command_v=0;commands=commands+4;
   if(books[0][n][39])begin
    if(stage_v)$fatal(1,"fragment END asserted whole stage");
    for(integer rank=0;rank<4;rank=rank+1)begin retire_identity[47*rank+:47]=id;retire_home[7*rank+:7]=books[rank][n][6:0];retire_entry[14*rank+:14]=books[rank][n][20:7];end
    retire_visibility={24{1'b1}};quiet=15;drained=15;retire_v=15;tick();retire_v=0;retires=retires+4;
   end
   if(n%7==0)tick();
   if(sfault)$fatal(1,"literal command/receipt rejected n=%0d",n);
  end
  if(stage_v)$fatal(1,"whole stage skipped final visibility/result");
  fence_v=15;fence_identity={4{id}};fence_visibility={20{1'b1}};tick();fence_v=0;
  result_v=1;tick();result_v=0;
  if(!stage_v||!handoff||token_valid||out_id!=id||out_token!=77889||out_value!=32'h3f810203)$fatal(1,"actual retained handoff result missing");
  repeat(9)begin tick();if(!stage_v||out_id!=id||out_token!=77889||out_value!=32'h3f810203)$fatal(1,"stalled result changed");end
  accepted=1;tick();accepted=0;if(stage_v||pending||sfault)$fatal(1,"real whole-stage ACK failed");
  $display("PASS WFC producers full866/14realSRAM cfg=%0d/%0d/%0d promptreads=%0d literalcommands=%0d retirements=%0d layer19wholehandoff cycles=%0d",users,plen,glen,reads,commands,retires,cycles);$finish;
 end
endmodule
