`timescale 1ns/1ps
`default_nettype none
module banked_calendar_case #(parameter integer W=135,XW=46,MUT=0)(output reg finished=0);
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,cfg_we=0,start_v=0;
 reg [10:0] cfg_addr=0,start_base=0;
 reg [11:0] start_limit=0;
 reg [255:0] cfg_data=0;
 reg [15:0] start_loops=0;
 reg [XW-1:0] start_ctx=0;
 wire [W-1:0] oc,nc;
 wire [XW-1:0] ox,nx;
 wire [15:0] oi,ni;
 wire ol,nl,ov,nv,oa,na,od,nd,ofault,nfault;
 wire [31:0] oo,no;
 ot_smh_calendar_static_x #(.W(W),.AW(11),.XW(XW)) old_master(
  .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),.start_ctx(start_ctx),
  .calendar(oc),.calendar_ctx(ox),.calendar_iter(oi),.calendar_lastit(ol),.calendar_v(ov),.ordinal(oo),.active(oa),.done(od),.fault(ofault));
 ot_smh_calendar_banked_native #(.W(W),.AW(11),.XW(XW),.MUT(MUT)) dut(
  .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),.start_ctx(start_ctx),
  .calendar(nc),.calendar_ctx(nx),.calendar_iter(ni),.calendar_lastit(nl),.calendar_v(nv),.ordinal(no),.active(na),.done(nd),.fault(nfault));
 function automatic [W-1:0] payload(input integer pc);
  for(integer b=0;b<W;b=b+1) payload[b]=((pc*13+b*7+(pc>>(b%11)))>>(b%5))&1;
 endfunction
 function automatic [255:0] protected_word(input integer pc);
  reg [255:0] z;
  begin z=0;z[255:240]=16'hc7a1;z[234:224]=11'(pc);z[W-1:0]=payload(pc);protected_word=z;end
 endfunction
 reg [W-1:0] cq[0:1];reg [XW-1:0] xq[0:1];reg [15:0] iq[0:1];
 reg lq[0:1],vq[0:1],dq[0:1],aq[0:1];reg [31:0] oq[0:1];
 integer cycle=0,warm=0,matched=0,old_seen=0,done_seen=0,runs=0,expected_total=0;
 integer gold_base=0,gold_len=0,gold_loops=0,run_seen=0;
 reg [XW-1:0] gold_ctx=0;
 reg valid_phase=0,bad_phase=0;
 always @(posedge clk) begin
  #1; cycle=cycle+1;
  if(cycle>20000)$fatal(1,"BANKED_FAIL watchdog W=%0d",W);
  if(!rst_n)begin
   warm=0;
   for(integer j=0;j<2;j=j+1)begin cq[j]=0;xq[j]=0;iq[j]=0;lq[j]=0;vq[j]=0;dq[j]=0;oq[j]=0;aq[j]=0;end
  end else begin
   if(warm>=8)begin
    if(nv!==vq[1] || nd!==dq[1])$fatal(1,"BANKED_FAIL timing W=%0d cycle=%0d valid=%b/%b done=%b/%b",W,cycle,nv,vq[1],nd,dq[1]);
    if(valid_phase && ((oa && !na) || (na && !(oa || aq[0] || aq[1]))))
     $fatal(1,"BANKED_FAIL active envelope W=%0d cycle=%0d old=%b new=%b",W,cycle,oa,na);
    if(vq[1])begin
     if(nc!==cq[1] || nx!==xq[1] || ni!==iq[1] || nl!==lq[1] || no!==oq[1])
      $fatal(1,"BANKED_FAIL tuple W=%0d cycle=%0d ordinal=%0d/%0d iter=%0d/%0d ctx=%h/%h data=%h/%h",W,cycle,no,oq[1],ni,iq[1],nx,xq[1],nc,cq[1]);
     if(valid_phase)matched=matched+1;
    end
    if(valid_phase && (ofault || nfault))$fatal(1,"BANKED_FAIL fault W=%0d cycle=%0d old=%b new=%b",W,cycle,ofault,nfault);
   end
   if(valid_phase && ov)begin
    if(run_seen>=gold_len*gold_loops || oc!==payload(gold_base+(run_seen%gold_len)) || oo!==32'(run_seen) ||
       ox!==gold_ctx || oi!==16'(run_seen/gold_len) || ol!==(run_seen/gold_len==gold_loops-1))
      $fatal(1,"BANKED_FAIL independent reference W=%0d cycle=%0d seen=%0d ordinal=%0d",W,cycle,run_seen,oo);
    run_seen=run_seen+1;old_seen=old_seen+1;
   end
   if(valid_phase && nd)done_seen=done_seen+1;
   aq[1]=aq[0];aq[0]=oa;
   cq[1]=cq[0];xq[1]=xq[0];iq[1]=iq[0];lq[1]=lq[0];vq[1]=vq[0];dq[1]=dq[0];oq[1]=oq[0];
   cq[0]=oc;xq[0]=ox;iq[0]=oi;lq[0]=ol;vq[0]=ov;dq[0]=od;oq[0]=oo;
   warm=warm+1;
  end
 end
 task automatic idle(input integer edges);
  repeat(edges)@(negedge clk);
 endtask
 task automatic reset;
  begin @(negedge clk);rst_n=0;cfg_we=0;start_v=0;valid_phase=0;idle(4);rst_n=1;idle(10);end
 endtask
 task automatic write_word(input integer addr,input [255:0] word256);
  begin @(negedge clk);cfg_we=1;cfg_addr=11'(addr);cfg_data=word256;end
 endtask
 task automatic launch(input integer base,lim,loops,input [XW-1:0] context_bits);
  begin
   @(negedge clk);gold_base=base;gold_len=lim-base;gold_loops=loops;gold_ctx=context_bits;run_seen=0;
   expected_total=expected_total+(lim-base)*loops;runs=runs+1;
   start_base=11'(base);start_limit=12'(lim);start_loops=16'(loops);start_ctx=context_bits;start_v=1;
   @(negedge clk);start_v=0;
  end
 endtask
 task automatic run_case(input integer base,lim,loops,input [XW-1:0] context_bits);
  integer target_done;
  begin target_done=done_seen+1;launch(base,lim,loops,context_bits);
   wait(done_seen==target_done);@(negedge clk);
   if(run_seen!=(lim-base)*loops)$fatal(1,"BANKED_FAIL count W=%0d",W);
   idle(4);
  end
 endtask
 integer pair_start,prior_done;
 reg [255:0] badword;
 initial begin
  reset();
  // Every address gets a full256-bit protected word, including both macro banks.
  for(integer a=0;a<2048;a=a+1)write_word(a,protected_word(a));
  @(negedge clk);cfg_we=0;idle(6);valid_phase=1;
  run_case(1024,1031,1,XW'(43));
  run_case(2044,2048,3,{XW{1'b1}});
  run_case(1022,1027,5,XW'(64'h2d35ac78e19b));
  run_case(0,2048,1,XW'(64'h136b9d725ae3));
  // Tight legal spacing: old N+3, plus2 new tail edges; N=4 gives9.
  prior_done=done_seen;launch(1022,1026,1,XW'(43));pair_start=cycle;
  idle(7); // launch returns one edge after GO; next launch adds one edge: gap9.
  launch(2044,2048,1,{XW{1'b1}});
  wait(done_seen==prior_done+2);@(negedge clk);idle(5);
  if(matched!=expected_total || old_seen!=expected_total || done_seen!=runs)
   $fatal(1,"BANKED_FAIL totals W=%0d matched=%0d old=%0d expected=%0d done=%0d runs=%0d",W,matched,old_seen,expected_total,done_seen,runs);
  $display("BANKED_VALID_PASS W=%0d XW=%0d words=%0d runs=%0d gap=9",W,XW,matched,runs);
  // Fault isolation: each corruption starts from a clean reset, no stale fault.
  for(integer kind=0;kind<4;kind=kind+1)begin
   reset();badword=protected_word(1024);
   case(kind)0:badword[255]=~badword[255];1:badword[239]=1;2:badword[224]=~badword[224];3:badword[W]=1;endcase
   write_word(1024,badword);@(negedge clk);cfg_we=0;idle(6);
   launch(1024,1025,1,XW'(43));idle(16);
   if(!ofault || !nfault)$fatal(1,"BANKED_FAIL protection W=%0d kind=%0d old=%b new=%b",W,kind,ofault,nfault);
  end
  // Balanced reset must also clear sticky fault and cancel an occupied pipeline.
  reset();
  launch(0,100,3,XW'(43));idle(4);reset();if(ofault || nfault || ov || nv || od || nd)$fatal(1,"BANKED_FAIL reset W=%0d",W);
  write_word(1024,protected_word(1024));@(negedge clk);cfg_we=0;idle(6);valid_phase=1;
  run_case(1024,1025,7,XW'(43));
  $display("BANKED_PROFILE_PASS W=%0d XW=%0d MUT=%0d protection=4 reset=6",W,XW,MUT);finished=1;
 end
endmodule
module tb_banked_calendar #(parameter integer MUT=0);
 wire svg_done,xc_done;
 banked_calendar_case #(.W(135),.XW(46),.MUT(MUT)) svg(.finished(svg_done));
 banked_calendar_case #(.W(173),.XW(5),.MUT(MUT)) xc(.finished(xc_done));
 initial begin wait(svg_done&&xc_done);$display("BANKED_CALENDAR PASS MUT=%0d profiles=2",MUT);$finish;end
endmodule
`default_nettype wire
