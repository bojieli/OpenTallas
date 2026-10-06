`timescale 1ps/1fs
// One full-shape cohort, independent pinned golden files; real stored-code
// held-response negative reuses the compiled binary. No leaf campaign replay.
module tb_enabled_quarter;
 import ot_gpu_w6_secded_pkg::*;
`ifdef HC_POST
 localparam integer IW=10912,OW=8225,CASES=3;
 localparam FAMILY="HC_POST";
 localparam MAXWAIT=2+2+6+4*5+8+32; // held/prime, m6/a5, output and codec guard
`else
 localparam integer IW=2083,OW=2081,CASES=10;
 localparam FAMILY="SFU";
 localparam MAXWAIT=2+2+276+32; // deepest c12 side plus wrapper and three bank repairs
`endif
 reg clk=0,rst_n=0,req_v=0,rsp_r=0;
 always #416.666667 clk=~clk;
 reg [IW-1:0] req_d=0;
 wire req_r,rsp_v,fault;
 wire [OW-1:0] rsp_d;
`ifdef HC_POST
 ot_hbm_hc_quarter #(.ENABLE(1),.NG(64)) dut(
  .clk(clk),.rst_n(rst_n),.req_v(req_v),.req_r(req_r),.req_tag(req_d[10880+:32]),
  .req_rdata(req_d[0+:8192]),.req_y(req_d[8192+:2048]),
  .req_comb(req_d[10240+:512]),.req_post(req_d[10752+:128]),
  .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_tag(rsp_d[8193+:32]),
  .rsp_data(rsp_d[0+:8192]),.rsp_error(rsp_d[8192]),.fault(fault));
`else
 ot_hbm_sfu_quarter #(.ENABLE(1),.LANES(64)) dut(
  .clk(clk),.rst_n(rst_n),.req_v(req_v),.req_r(req_r),.req_tag(req_d[2051+:32]),
  .req_fn(req_d[2048+:3]),.req_x(req_d[0+:2048]),
  .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_tag(rsp_d[2049+:32]),
  .rsp_y(rsp_d[0+:2048]),.rsp_error(rsp_d[2048]),.fault(fault));
`endif
 // Independent minimum arithmetic mechanism, identical child/parameters to
 // all 64 wrapper instances. Hierarchical compilation creates one master.
 reg child_rst_n=0,child_v=0;
 reg [IW-1:0] child_d=0;
 wire child_vo,child_fault;
`ifdef HC_POST
 wire [127:0] child_y;
 ot_dsrom_su_hcpost_group #(.WIN(0),.WOUT(0),.ML(6),.AL(5)) child(
  .clk(clk),.rst_n(child_rst_n),.in_v(child_v),
  .r(child_d[0+:128]),.y(child_d[8192+:32]),
  .c(child_d[10240+:512]),.p(child_d[10752+:128]),
  .out_v(child_vo),.o(child_y),.fault(child_fault));
`else
 wire [31:0] child_y;
 ot_hbm_sfu_result_c12 child(.clk(clk),.rst_n(child_rst_n),
  .v(child_v),.fn(child_d[2048+:3]),.x(child_d[0+:32]),
  .vo(child_vo),.y(child_y),.fault(child_fault));
`endif
 reg [IW-1:0] requests[0:CASES-1];
 reg [OW-1:0] expected[0:CASES-1];
 integer roots=0,engine_edges=0,accepts=0,launches=0,retires=0;
 integer neg_hold=0,checked=0,ce_checks=0,ue_checks=0,reset_checks=0;
 string dir;
 always @(posedge clk)begin
  roots=roots+1;
  if(rst_n)begin
   if(req_v&&req_r)accepts=accepts+1;
   if(dut.g_on.launch)launches=launches+1;
   if(rsp_v&&rsp_r)retires=retires+1;
  end
 end
 always @(posedge dut.g_on.engine_clk)if(dut.g_on.engine_rst_n)engine_edges=engine_edges+1;
 task tick;begin @(posedge clk);#1;end endtask
 task step_negedge;begin @(negedge clk);#1;end endtask
 task por_flush;
  begin
   step_negedge();rst_n=0;req_v=0;rsp_r=0;
   repeat(3)tick();
   if(rsp_v!==0||req_r!==1||fault!==0) $fatal(1,"POR_FLAGS_FAIL family=%s",FAMILY);
   // rst_n is the existing bank POR: payload is cleared, not retained warm data.
   if(dut.g_on.u_hold.u_request.u_state.code[0]!==encode64(64'b0))
    $fatal(1,"POR_PAYLOAD_CONTRACT_FAIL family=%s",FAMILY);
   step_negedge();rst_n=1;tick();
   if(rsp_v!==0||fault!==0)$fatal(1,"RESET_GHOST_FAIL family=%s",FAMILY);
   reset_checks=reset_checks+1;
  end
 endtask
 task submit(input integer k);
  integer waits;
  begin
   waits=0;
   while(!req_r)begin tick();waits=waits+1;if(waits>8)$fatal(1,"REQUEST_NOT_READY family=%s",FAMILY);end
   step_negedge();req_d=requests[k];req_v=1;
   @(posedge clk);if(!req_r)$fatal(1,"REQUEST_REFUSED family=%s",FAMILY);#1;
   req_v=0;
   // Poison external ports after acceptance. Held engine payload must survive.
   req_d={IW{1'b1}};
  end
 endtask
 task wait_result(input integer k,input integer start_root);
  integer waits,w;
  begin
   waits=0;
   while(!rsp_v)begin
    tick();waits=waits+1;
    if(fault)$fatal(1,"UNEXPECTED_PROTECTION_FAULT family=%s k=%0d",FAMILY,k);
    if(req_r)$fatal(1,"EARLY_REQUEST_RETIRE family=%s",FAMILY);
    if(waits>MAXWAIT)$fatal(1,"COMPOSED_LATENCY_FAIL family=%s k=%0d bound=%0d",FAMILY,k,MAXWAIT);
   end
   if(rsp_d!==expected[k])begin
    for(w=0;w<(OW-33)/32;w=w+1)
     if(rsp_d[32*w+:32]!==expected[k][32*w+:32])
      $display("WORD_MISMATCH family=%s k=%0d lane=%0d got=%08h exp=%08h",FAMILY,k,w,rsp_d[32*w+:32],expected[k][32*w+:32]);
    $fatal(1,"GOLDEN_MISMATCH family=%s k=%0d",FAMILY,k);
   end
   $display("RESULT_READY family=%s k=%0d root_latency=%0d engine_edges_total=%0d",FAMILY,k,roots-start_root,engine_edges);
  end
 endtask
 task run_case(input integer k,input integer inject_ce);
  integer start_root,before_retire,before_launch,h;
  reg [OW-1:0] held;
  begin
   before_retire=retires;before_launch=launches;start_root=roots;
   submit(k);
   if(inject_ce)begin
    repeat(3)tick();step_negedge();
    dut.g_on.u_hold.u_request.u_state.code[0]=dut.g_on.u_hold.u_request.u_state.code[0]^72'h4;
    #1;
    if(!dut.g_on.u_hold.u_request.u_state.repairing)$fatal(1,"CE_NOT_DETECTED family=%s",FAMILY);
    ce_checks=ce_checks+1;
   end
   wait_result(k,start_root);held=rsp_d;
   if(inject_ce)begin
    // The result permission must withdraw while a correctable held-codeword
    // upset repairs; afterwards the exact word/tag must return unchanged.
    step_negedge();
    dut.g_on.u_hold.u_response.u_state.code[0]=dut.g_on.u_hold.u_response.u_state.code[0]^72'h4;
    #1;
    if(!dut.g_on.u_hold.u_response.u_state.repairing||rsp_v)
     $fatal(1,"HELD_CE_PERMISSION_FAIL family=%s",FAMILY);
    h=0;
    while(!rsp_v)begin tick();h=h+1;
     if(fault||req_r||retires!=before_retire||h>8)$fatal(1,"HELD_CE_REPAIR_FAIL family=%s",FAMILY);
    end
    if(rsp_d!==held)$fatal(1,"HELD_CE_DATA_FAIL family=%s",FAMILY);
    ce_checks=ce_checks+1;
   end
   // Upstream presents another real request throughout the blocked response.
   step_negedge();req_d=requests[(k+1)%CASES];req_v=1;
   for(h=0;h<17;h=h+1)begin
    if(neg_hold&&h==5)begin
     step_negedge();
     // Coherent nonzero codeword upset changes actual held payload while all
     // codec checks remain clean. This must trip the real hold/golden checker.
     dut.g_on.u_hold.u_response.u_state.code[0]=
      dut.g_on.u_hold.u_response.u_state.code[0]^encode64(64'b1);
     $display("NEGATIVE_HELD_CODEWORD_INJECTED family=%s",FAMILY);
    end
    tick();
    if(!rsp_v||rsp_d!==held)$fatal(1,"HELD_RESPONSE_CHANGED family=%s",FAMILY);
    if(req_r||retires!=before_retire||launches!=before_launch+1)
     $fatal(1,"BACKPRESSURE_OWNERSHIP_FAIL family=%s",FAMILY);
   end
   step_negedge();req_v=0;rsp_r=1;
   tick();if(retires!=before_retire+1)$fatal(1,"NOT_EXACTLY_ONCE family=%s",FAMILY);
   step_negedge();rsp_r=0;tick();
   if(rsp_v||fault)$fatal(1,"POST_RETIRE_GHOST family=%s",FAMILY);
   checked=checked+1;
   $display("CASE_PASS family=%s k=%0d held=17 launches=1 retires=1",FAMILY,k);
  end
 endtask
 task ue_refusal;
  integer j,old_retires;
  begin
   old_retires=retires;submit(2);step_negedge();
   dut.g_on.u_hold.u_request.u_state.code[0]=dut.g_on.u_hold.u_request.u_state.code[0]^72'hc;
   for(j=0;j<8;j=j+1)begin
    tick();if(!fault||req_r||rsp_v||retires!=old_retires)
     $fatal(1,"UE_PERMISSION_FAIL family=%s",FAMILY);
   end
   ue_checks=ue_checks+1;por_flush();
  end
 endtask
 task reset_cancel;
  integer j,old_retires;
  begin
   old_retires=retires;submit(2);repeat(3)tick();por_flush();
   for(j=0;j<8;j=j+1)begin tick();if(rsp_v||retires!=old_retires)$fatal(1,"RESET_STALE_RETURN family=%s",FAMILY);end
  end
 endtask
 task reset_held_cancel;
  integer old_retires;
  begin
   old_retires=retires;submit(0);wait_result(0,roots);
   por_flush();repeat(8)tick();
   if(rsp_v||retires!=old_retires)$fatal(1,"RESET_HELD_GHOST family=%s",FAMILY);
  end
 endtask
 task single_child_golden;
  integer c,w;
  begin
   for(c=0;c<CASES;c=c+1)begin
    step_negedge();child_rst_n=0;child_v=0;child_d=requests[c];
    repeat(3)tick();
    step_negedge();child_rst_n=1;
    // The real held wrapper provides PRIME before launch for side fn_d/fn_q.
    repeat(2)tick();step_negedge();child_v=1;tick();
    step_negedge();child_v=0;w=0;
    while(!child_vo)begin tick();w=w+1;
     if(w>MAXWAIT)$fatal(1,"CHILD_COMPLETION_FAIL family=%s k=%0d",FAMILY,c);
    end
`ifdef HC_POST
    if(child_y!==expected[c][0+:128]||child_fault!==expected[c][8192])
`else
    if(child_y!==expected[c][0+:32]||child_fault!==expected[c][2048])
`endif
     $fatal(1,"CHILD_GOLDEN_FAIL family=%s k=%0d got=%h expected_low=%h fault=%b",FAMILY,c,child_y,expected[c][0+:128],child_fault);
    $display("CHILD_RESULT family=%s k=%0d cycles=%0d",FAMILY,c,w);
   end
   step_negedge();child_rst_n=0;child_v=0;
   $display("SINGLE_CHILD_GOLDEN_PASS family=%s cases=%0d",FAMILY,CASES);
  end
 endtask
 integer k;
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR_REQUIRED");
  if($test$plusargs("NEG_HOLD"))neg_hold=1;
`ifdef HC_POST
  $readmemh({dir,"/hc_req.mem"},requests);$readmemh({dir,"/hc_exp.mem"},expected);
`else
  $readmemh({dir,"/sfu_req.mem"},requests);$readmemh({dir,"/sfu_exp.mem"},expected);
`endif
  if($test$plusargs("CHILD_ONLY"))begin single_child_golden();$finish;end
  por_flush();
  if(neg_hold)begin run_case(2,0);$fatal(1,"NEGATIVE_NOT_OBSERVED family=%s",FAMILY);end
  reset_cancel();reset_held_cancel();ue_refusal();
  for(k=0;k<CASES;k=k+1)run_case(k,k==2);
  $display("ENABLED_FULLSHAPE_PASS family=%s checked=%0d ce=%0d ue=%0d reset=%0d accepts=%0d launches=%0d retires=%0d",FAMILY,checked,ce_checks,ue_checks,reset_checks,accepts,launches,retires);
  $finish;
 end
endmodule
