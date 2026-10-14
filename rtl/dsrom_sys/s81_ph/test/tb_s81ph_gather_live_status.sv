`timescale 1ns/1ps
// Public status observations: single-cycle live/busy pulses survive, each fault
// source latches, and reset clears the epoch. Latencies are the priced contract.
module tb_s81ph_gather_live_status;
 reg ck=0; always #3 ck=~ck;
 reg ckv=0; always #4 ckv=~ckv;
 reg rst=0; reg [23:0] ts=0; reg [15:0] cs=0;
 wire [23:0] tso; wire [15:0] cso; wire [7:0] ready,rc;
 wire [162:0] tc_ctl,tc; wire [11:0] fc;
 wire [1:0] st; wire [8:0] done; wire [10:0] xgo;
 dsfd_gth_strip strip(.ck_r({ckv,{132{ck}}}),.rst(rst),.rsv(rst),.tst_i(ts),.cs_i(cs),.ready_i(8'hff),.rc_i(rc),.tc_i(tc_ctl),.fcd_i(12'd0),.tst_o(tso),.cs_o(cso),.ready_o(ready),.rc_o(),.tc_o(tc),.fcd_o(fc));
 dsfd_gth_ctl ctl(.ck(ck),.ckv(ckv),.rst(rst),.rsv(rst),.tst(tso),.cs(cso),.roots_ready(ready),.f_vm(512'd0),.c_cmd(85'd0),.c_done(done),.c_st(st),.t_xgo(xgo),.f_cd(fc),.tc(tc_ctl),.rc(rc));
 integer cases=0,errors=0,k,b;
 task tick; begin @(posedge ck); #1; end endtask
 task check(input bit okay,input integer kind,input integer bitn,input integer edge_n);begin
  if(!okay)begin errors++;if(errors<8)$display("STATUS_FAIL kind=%0d bit=%0d edge=%0d tc=%b c_st=%b",kind,bitn,edge_n,tc[162:160],st);end
 end endtask
 task epoch(input integer phase);begin
  @(negedge ck);rst=0;ts=0;cs=0; #1;
  repeat(3)tick();@(negedge ck); #(phase);rst=1;
  repeat(16)tick();check(tc[162:160]===3'b000 && !st[0],0,0,0);
 end endtask
 // kind1 trunkfault (+4 tst,+1 pin,+1 aggregate,+1 tr,+1 tc),
 // kind2 colfault adds the original cflt register; busy/live use kind1 latency.
 task pulse(input integer kind,input integer bitn);integer e,arrival;reg expected;begin
  epoch(bitn%3);@(negedge ck);
  case(kind)
   1:ts[2*bitn+1]=1;
   2:cs[2*bitn]=1;
   3:cs[2*bitn+1]=1;
   4:ts=24'h555555;
  endcase
  arrival=kind==2?9:8;
  for(e=1;e<=14;e++)begin
   tick();expected=(kind<=2)?(e>=arrival):(e==arrival);
   case(kind)
    1,2:check(tc[160]===expected && tc[162:161]===2'b00,kind,bitn,e);
    3:check(tc[161]===expected && tc[160]===1'b0 && tc[162]===1'b0,kind,bitn,e);
    4:check(tc[162]===expected && tc[161:160]===2'b00,kind,bitn,e);
   endcase
   check(st[0]===1'b0 && done===9'd0 && xgo===11'd0,kind,bitn,e);
   if(e==1)begin @(negedge ck);ts=0;cs=0;end
  end
  cases++;
 end endtask
 initial begin
  for(b=0;b<12;b++)pulse(1,b);
  for(b=0;b<8;b++)pulse(2,b);
  for(b=0;b<8;b++)pulse(3,b);
  pulse(4,0);epoch(2);
  if(errors)$fatal(1,"LIVE_STATUS FAIL cases=%0d errors=%0d",cases,errors);
  $display("LIVE_STATUS PASS %0d single-bit/pulse/reset cases; trunk/live/busy8edges columnfault9edges; c_st endpoint semantics preserved",cases);$finish;
 end
endmodule
