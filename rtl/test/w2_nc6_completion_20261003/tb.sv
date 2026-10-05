`timescale 1ps/1ps
module tb;
 localparam NC=6,AW=34,TW=32,GW=4,PW=35;
 reg clk=0;always #500 clk=~clk;
 reg rst_n=0,admission_stop=0,rearm_v=0,provider_fenced=0,reset_fenced=0;
 wire rearm_rdy,idle,fault;
 reg [5:0] cv=0,cwe=0,cr=0,cwr=0;wire[5:0] cready,rv,wv;
 reg [6*AW-1:0] ca=0;reg [6*TW-1:0] ct=0;reg[6*GW-1:0] cg=0;reg[6*256-1:0] cd=0;
 wire[6*TW-1:0] rt,wt;wire[6*GW-1:0] rg,wg;wire[6*256-1:0] rd;
 wire pv,pwe;reg pr=0;wire[AW-1:0] pa;wire[PW-1:0] pt;wire[GW-1:0] pg;wire[255:0] pd;
 reg prv=0,pwv=0;wire prr,pwr;reg[PW-1:0] prt=0,pwt=0;reg[GW-1:0] prg=0,pwg=0;reg[255:0] prd=0;
 wire disabled_pv,disabled_fault;
 ot_hdc_qwen_pc_exact_completion #(.OPT_EXACT(1)) dut(
  .clk(clk),.rst_n(rst_n),.admission_stop(admission_stop),.rearm_v(rearm_v),.provider_fenced(provider_fenced),.reset_fenced(reset_fenced),.rearm_rdy(rearm_rdy),.idle(idle),
  .c_req_v(cv),.c_req_we(cwe),.c_req_rdy(cready),.c_req_addr(ca),.c_req_tag(ct),.c_req_gen(cg),.c_req_data(cd),
  .c_rsp_v(rv),.c_rsp_rdy(cr),.c_rsp_tag(rt),.c_rsp_gen(rg),.c_rsp_data(rd),.c_wr_done_v(wv),.c_wr_done_rdy(cwr),.c_wr_done_tag(wt),.c_wr_done_gen(wg),
  .p_req_v(pv),.p_req_rdy(pr),.p_req_we(pwe),.p_req_addr(pa),.p_req_tag(pt),.p_req_gen(pg),.p_req_data(pd),
  .p_rsp_v(prv),.p_rsp_rdy(prr),.p_rsp_tag(prt),.p_rsp_gen(prg),.p_rsp_data(prd),
  .p_wr_done_v(pwv),.p_wr_done_ready(pwr),.p_wr_done_tag(pwt),.p_wr_done_gen(pwg),.fault(fault));
 ot_hdc_qwen_pc_exact_completion disabled(
  .clk(clk),.rst_n(rst_n),.admission_stop(admission_stop),.rearm_v(1'b0),.provider_fenced(1'b0),.reset_fenced(1'b0),
  .c_req_v(cv),.c_req_we(cwe),.c_req_addr(ca),.c_req_tag(ct),.c_req_gen(cg),.c_req_data(cd),.c_rsp_rdy(cr),.c_wr_done_rdy(cwr),
  .p_req_v(disabled_pv),.p_req_rdy(pr),.p_rsp_v(prv),.p_rsp_tag(prt),.p_rsp_gen(prg),.p_rsp_data(prd),
  .p_wr_done_v(pwv),.p_wr_done_tag(pwt),.p_wr_done_gen(pwg),.fault(disabled_fault));
 integer cycles=0,scenario=0,case_pass_count=0;reg took_req,took_read,took_write;reg[5:0] took_client_read,took_client_write;
 task step;
  begin
   #1;took_req=pv&&pr;took_read=prv&&prr;took_write=pwv&&pwr;
   took_client_read=rv&cr;took_client_write=wv&cwr;
   @(posedge clk);#1;cycles=cycles+1;
   if(disabled_pv||disabled_fault)$fatal(1,"defaultoff violated");
   // Component-owned counters must conserve real accepted local debt.
   for(integer c=0;c<6;c=c+1)begin
    integer count;count=0;for(integer s=0;s<16;s=s+1)if(dut.state[c][s]!=0)count=count+1;
    if(integer'(dut.outstanding[c])!=count)$fatal(1,"debt count mismatch c%0d",c);
   end
   @(negedge clk);
  end
 endtask
 task cold;
  begin
   // Scenario boundary only: synthetic provider explicitly discards all copies.
   // This is not a runtime reset/recovery proof for an attached backend.
   rst_n=0;cv=0;cwe=0;cr=0;cwr=0;pr=0;prv=0;pwv=0;
   admission_stop=0;rearm_v=0;provider_fenced=0;reset_fenced=0;
   step();step();rst_n=1;step();scenario=scenario+1;
  end
 endtask
 task issue(input integer c,input reg write_flag,input reg[31:0] t,input reg[3:0] g);
  integer n;
  begin
   cv[c]=1;cwe[c]=write_flag;ct[c*32+:32]=t;cg[c*4+:4]=g;ca[c*34+:34]=34'(c*32);cd[c*256+:256]=256'(t);pr=1;n=0;
   do begin step();n=n+1;if(n>8||fault)$fatal(1,"request admission");end while(!took_req);
   cv[c]=0;
  end
 endtask
 task read_return(input integer c,input reg[31:0] t,input reg[3:0] g);
  integer n;
  begin prv=1;prt={3'(c),t};prg=g;prd=256'(t)^256'h12345678;n=0;
   do begin step();n=n+1;if(n>8)$fatal(1,"read input held forever");end while(!took_read);
   prv=0;
  end
 endtask
 task write_return(input integer c,input reg[31:0] t,input reg[3:0] g);
  begin pwv=1;pwt={3'(c),t};pwg=g;step();if(!took_write)$fatal(1,"write input not accepted");pwv=0;end
 endtask
 task expect_fault;
  begin step();step();if(!fault||pv||rv||wv||prr||pwr)$fatal(1,"bad completion not quarantined");end
 endtask
 task drain_read(input integer c,input reg[31:0] t,input reg[3:0] g);
  begin
   step();if(!rv[c]||rt[c*32+:32]!=t||rg[c*4+:4]!=g||rd[c*256+:256]!=(256'(t)^256'h12345678))$fatal(1,"read identity/data");
   repeat(3)begin step();if(!rv[c]||rt[c*32+:32]!=t)$fatal(1,"held read changed");end
   cr[c]=1;step();if(!took_client_read[c])$fatal(1,"read acceptance");cr[c]=0;
  end
 endtask
 task pass(input string name);
  begin case_pass_count=case_pass_count+1;$display("CASE_PASS %s cycle=%0d",name,cycles);end
 endtask
 initial begin
  @(negedge clk);
  cold();
  // Full original32/gen4 including occupied KV5; stall a frozen request.
  cv[5]=1;cwe[5]=0;ct[5*32+:32]=32'hfedcba98;cg[5*4+:4]=15;ca[5*34+:34]=34'h1234;cd[5*256+:256]=256'h9876;
  step();repeat(4)begin step();if(!pv||pt!={3'd5,32'hfedcba98}||pg!=15||pa!=34'h1234||pd!=256'h9876)$fatal(1,"heldrequest");end
  pr=1;step();if(!took_req)$fatal(1,"request missed");cv=0;
  read_return(5,32'hfedcba98,15);drain_read(5,32'hfedcba98,15);if(!idle)$fatal(1,"healthy read not idle");pass("heldrequest_read_KV5");
  cold();issue(2,1,32'hffffffff,7);write_return(2,32'hffffffff,7);
  step();step();if(!wv[2])$fatal(1,"WR L3 missing");
  repeat(4)begin step();if(!wv[2]||wt[2*32+:32]!=32'hffffffff||wg[2*4+:4]!=7||dut.outstanding[2]!=1)$fatal(1,"heldWR changed");end
  cwr[2]=1;step();cwr=0;if(!took_client_write[2]||!idle)$fatal(1,"WR retirement");pass("heldwrite_ready");
  cold();for(integer t=0;t<16;t=t+1)issue(0,0,32'(t),1);
  cv[0]=1;ct[0+:32]=99;cg[0+:4]=1;repeat(4)begin step();if(pv||took_req)$fatal(1,"17th credit accepted");end
  cv=0;read_return(0,15,1);drain_read(0,15,1);issue(0,0,99,1);for(integer t=0;t<15;t=t+1)begin read_return(0,32'(t),1);drain_read(0,32'(t),1);end
  read_return(0,99,1);drain_read(0,99,1);if(!idle)$fatal(1,"full table final drain");pass("full16_oldcredit_no_bypass_outoforder");
  cold();issue(0,0,1,1);issue(0,0,2,1);issue(0,0,3,1);
  read_return(0,1,1);step();read_return(0,2,1);
  prv=1;prt={3'd0,32'd3};prg=1;prd=256'd3^256'h12345678;
  repeat(4)begin step();if(prr||took_read||!rv[0]||rt[0+:32]!=1)$fatal(1,"backend read backpressure");end
  cr[0]=1;step();cr=0;
  do step();while(!took_read);prv=0;
  drain_read(0,2,1);drain_read(0,3,1);if(!idle)$fatal(1,"held return drain");pass("held_backend_read_and_finite_query");
  cold();cv[0]=1;ct[0+:32]=123;cg[0+:4]=2;pr=0;step();step();
  admission_stop=1;step();if(pv)$fatal(1,"stop did not cancel unaccepted holder");cv=0;
  provider_fenced=1;reset_fenced=1;rearm_v=1;#1;if(!rearm_rdy)$fatal(1,"unaccepted reservation not retired");step();rearm_v=0;pass("stop_cancels_only_unaccepted_holder");
  cold();cv[0]=1;ct[0+:32]=42;cg[0+:4]=3;pr=0;step();
  pr=1;prv=1;prt={3'd0,32'd42};prg=3;prd=42;step();cv=0;prv=0;
  expect_fault();if(dut.outstanding[0]!=1)$fatal(1,"sameedge false return lost debt");pass("sameedge_issue_return_refused");
  cold();issue(4,1,111,4);write_return(4,111,4);write_return(4,111,4);expect_fault();pass("duplicate_write_ack");
  cold();issue(1,0,44,3);cv[1]=1;ct[32+:32]=44;cg[4+:4]=3;expect_fault();pass("duplicate_live_request");
  cold();issue(1,0,44,3);read_return(1,45,3);expect_fault();pass("validcode_wrongtag");
  cold();issue(1,0,44,3);read_return(1,44,2);expect_fault();pass("wronggeneration");
  cold();issue(1,1,44,3);read_return(1,44,3);expect_fault();pass("wrongdirection");
  cold();issue(1,0,44,3);read_return(7,44,3);expect_fault();pass("invalidclient");
  cold();issue(1,0,44,3);read_return(1,44,3);drain_read(1,44,3);read_return(1,44,3);expect_fault();pass("duplicate_retired_return");
  cold();issue(1,1,44,3);admission_stop=1;provider_fenced=1;reset_fenced=1;rearm_v=1;expect_fault();
  if(dut.outstanding[1]!=1)$fatal(1,"rearm erased accepted debt");pass("rearm_live_debt_refused");
  cold();admission_stop=1;rearm_v=1;expect_fault();pass("unfenced_wrap_refused");
  cold();issue(3,0,88,15);read_return(3,88,15);drain_read(3,88,15);
  admission_stop=1;provider_fenced=1;reset_fenced=1;rearm_v=1;
  #1;if(!rearm_rdy)$fatal(1,"positive empty fenced rearm");step();rearm_v=0;admission_stop=0;
  issue(3,0,88,0);read_return(3,88,0);drain_read(3,88,0);pass("fenced_generation15_to0");
  // No installed generation oracle: tests verify stale mismatched return after
  // producer-selected wrap, not impossible detection of samekey ABA after fence.
  read_return(3,88,15);expect_fault();pass("reset_stale_old_generation");
  cold();issue(0,0,7,1);read_return(0,7,1);step();if(!rv[0])$fatal(1,"setup held read");
  write_return(4,99,1);cr[0]=1;step();if(took_client_read[0]||dut.outstanding[0]!=1||!fault)$fatal(1,"bad query released good debt");pass("badquery_blocks_simultaneous_release");
  $display("COMPONENT_PASS cases=%0d cycles=%0d NC6 MAX16 period_ps1000",case_pass_count,cycles);$finish;
 end
 // Fixture finite functional watchdog, not an imposed process/resource cap.
 initial begin repeat(2000)@(posedge clk);$fatal(1,"fixture did not terminate");end
endmodule
