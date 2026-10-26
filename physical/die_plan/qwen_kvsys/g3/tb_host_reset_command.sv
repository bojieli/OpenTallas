`timescale 1ps/1ps
module tb_host_reset_command;
 reg clk=0;initial forever begin #416;clk=1;#417;clk=0;end
 reg host_wavefront_n=0,receiver_wavefront_n=0,soft_rst=0;
 reg [2:0] die_id=0;reg [1:0] link_up=0;reg [7:0] boot_done=0,boot_ok=8'hff;
 wire host_n,link_n,hbm_n,boot_go,die_n,ready,fault;wire[3:0]state,err;wire[31:0]cycles;
 qkd_host_rst_role_pins #(.NL(2),.ND(8),.T_LINK(24),.T_HBM(24)) host(
 .clk(clk),.por_n(host_wavefront_n),.soft_rst(soft_rst),.die_id(die_id),.link_up(link_up),.boot_done(boot_done),.boot_ok(boot_ok),
 .host_rst_n(host_n),.link_rst_n(link_n),.hbm_rst_n(hbm_n),.boot_go(boot_go),.die_rst_n(die_n),.sys_ready(ready),.boot_fault(fault),.boot_state(state),.boot_err(err),.boot_cycles(cycles));
 wire[1:0]source_cmd;wire[1:0]delivered;assign source_cmd={die_n,hbm_n};
 // Exact bind_cells primitive, three representative registered transport hops.
 ot_dp_dly #(.W(2),.D(3)) path(.clk(clk),.d(source_cmd),.q(delivered));
 wire[1:0]rx,legacy;reg [1:0]contract_rx=0,last_legacy=0,last_qualified=0;
 wire[1:0]qualified=delivered & {2{receiver_wavefront_n}};
 wire[1:0]cmd_to_rx;
`ifdef MUT_ROUTE
 assign cmd_to_rx=source_cmd;
`elsif MUT_COMMAND
 assign cmd_to_rx=2'b11;
`elsif MUT_POLARITY
 assign cmd_to_rx=~delivered;
`else
 assign cmd_to_rx=delivered;
`endif
 wire wf_to_rx;
`ifdef MUT_WAVEFRONT
 assign wf_to_rx=1'b1;
`else
 assign wf_to_rx=receiver_wavefront_n;
`endif
 genvar g;generate for(g=0;g<2;g=g+1)begin:pair
  qkd_host_reset_command_rx dut(.clk(clk),.wavefront_rst_n(wf_to_rx),.command_rst_n(cmd_to_rx[g]),.local_rst_n(rx[g]));
  // Actual current receiver: asynchronous assertion and two-edge release.
  ot_dp_rsync #(.W(1),.S(2)) old(.clk(clk),.a(qualified[g]),.q(legacy[g]));
 end endgenerate
 reg a=0,b=0;wire[1:0]actual_leaf,reference_leaf;
 generate for(g=0;g<2;g=g+1)begin:leaf
  // Actual hub_C recipient of ri_ahub_rst_n, not a stand-in reset counter.
  qkd_astk_fault_join new_leaf(.ck(clk),.rst_n(rx[g]),.a(a),.b(b),.q(actual_leaf[g]));
  qkd_astk_fault_join old_leaf(.ck(clk),.rst_n(contract_rx[g]),.a(a),.b(b),.q(reference_leaf[g]));
 end endgenerate
 integer n=0,k=0,checks=0,errors=0,seen_hbm=0,seen_die=0,seen_fault=0,seen_warm=0;
 always @(posedge clk)begin
  n=n+1;
  #1;
  // The only deliberate difference from the real old receiver is one
  // assertion sample: the new receiver cannot react asynchronously between
  // edges. Release remains the actual old two-consecutive-high-edge rule.
  for(k=0;k<2;k=k+1)
   contract_rx[k]=(!qualified[k] && last_qualified[k]) ? last_legacy[k] : legacy[k];
  last_legacy=legacy;last_qualified=qualified;
  #2;
  if(n>8)begin
   checks=checks+1;
   if(rx !== contract_rx || actual_leaf !== reference_leaf)begin
    errors=errors+1;
    if(errors<8)$display("MISMATCH cycle=%0d src=%b delivered=%b wf=%b rx=%b contract=%b leaf=%b/%b",n,source_cmd,delivered,receiver_wavefront_n,rx,contract_rx,actual_leaf,reference_leaf);
   end
  end
  if(rx[0])seen_hbm=1;if(rx[1])seen_die=1;if(fault)seen_fault=1;
 end
 task automatic step(input integer count);integer i;begin for(i=0;i<count;i=i+1)@(negedge clk);end endtask
 task automatic wait_ready;integer timeout;begin timeout=0;while(!ready && !fault && timeout<260)begin step(1);timeout=timeout+1;if(boot_go)boot_done=8'hff;end if(!ready)$fatal(1,"actual HOST did not reach READY state=%d err=%d",state,err);end endtask
 initial begin
  step(8);host_wavefront_n=1;link_up=2'b11;
  // HBM command may be high while this receiver's wavefront is still low.
  while(!hbm_n)step(1);step(6);receiver_wavefront_n=1;
  wait_ready();a=1;step(10);
  // Warm software reset: preserve actual HOST boot/recovery state machine.
  boot_done=0;soft_rst=1;step(1);soft_rst=0;step(6);seen_warm=1;wait_ready();step(8);
  // Real HBM boot-check failure, then warm replay into a good boot.
  boot_done=0;boot_ok=0;soft_rst=1;step(1);soft_rst=0;step(6);
  while(!boot_go)step(1);boot_done=8'hff;step(8);
  if(!fault || err!=3)$fatal(1,"HBM check fault not exercised");
  boot_done=0;boot_ok=8'hff;soft_rst=1;step(1);soft_rst=0;step(6);wait_ready();step(8);
  // Actual role fault forces both command families low without a second START.
  die_id=1;step(12);if(!fault || err!=4)$fatal(1,"role fault not exercised");
  // A new cold reset uses the same delivered POR/wavefront domain.
  host_wavefront_n=0;receiver_wavefront_n=0;step(5);die_id=0;boot_done=0;a=0;b=1;
  host_wavefront_n=1;receiver_wavefront_n=1;wait_ready();step(8);
  if(!seen_hbm || !seen_die || !seen_fault || !seen_warm || checks<700)$fatal(1,"coverage incomplete checks=%d",checks);
  if(errors)$fatal(1,"HOST_RESET_COMMAND FAIL %0d errors",errors);
  $display("HOST_RESET_COMMAND PASS %0d cycles %0d checks: cold/boot/HBMfault/rolefault/warm, assert transport+1 release transport+2",n,checks);$finish;
 end
 initial begin step(1800);$fatal(1,"timeout state=%d",state);end
endmodule
