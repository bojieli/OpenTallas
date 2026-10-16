`timescale 1ps/1ps
module tb;
 reg sc=1,tc=1,rn=0,run_s=1,run_t=1;
 always #556 if(run_s)sc=~sc;
 always #417 if(run_t)tc=~tc;
 reg[80:0]sf=0;reg[15:0]cf=0;
 wire ss,cs,old_vm,new_vm;
 dsfd_vm_capture_fault_serial u_s(.ck(sc),.rst_n(rn),.i_lo(sf[39:0]),.i_hi(sf[79:40]),.i_status(sf[80]),.fault(ss));
 dsfd_vm_native_valid_diag u_t(tc,rn,32'd0,18'd0,90'd0,cf,cs);
 wire ns,nc;
`ifdef CAP_FAULT_MUT_DROP_SERIAL
 assign ns=0;
`else
 assign ns=ss;
`endif
`ifdef CAP_FAULT_MUT_DROP_CORE
 assign nc=0;
`else
 assign nc=cs;
`endif
 wire[39:0]mf={35'd0,nc,4'd0};
 dsfd_vm_seq_tile original(.ck(tc),.rst(rn),.c_cmd(85'd0),.c_done(),.c_st(),
 .o_cv(128'd0),.o_ca(1152'd0),.o_cm(512'd0),.o_rv(32'd0),.o_rr(448'd0),
 .t_inp_su(),.t_inp_hc(),.nf_v(),.nf_d(),.larm_v(),.larm_g(),.larm_base(),
 .pqx_chk(8'd0),.read_fault(8'd0),.edge_f({2'd0,(|sf)|(|cf)}),.x_hdr(9'd0),.x_al(3'd0),
 .w_flt(1'b0),.m_flt(40'd0),.l_flt(3'd0),.r_flt(1'b0),.vm_fault(old_vm));
 dsfd_vm_seq_tile changed(.ck(tc),.rst(rn),.c_cmd(85'd0),.c_done(),.c_st(),
 .o_cv(128'd0),.o_ca(1152'd0),.o_cm(512'd0),.o_rv(32'd0),.o_rr(448'd0),
 .t_inp_su(),.t_inp_hc(),.nf_v(),.nf_d(),.larm_v(),.larm_g(),.larm_base(),
 .pqx_chk(8'd0),.read_fault(8'd0),.edge_f({2'd0,ns}),.x_hdr(9'd0),.x_al(3'd0),
 .w_flt(1'b0),.m_flt(mf),.l_flt(3'd0),.r_flt(1'b0),.vm_fault(new_vm));
 integer bad=0,cases=0,checks=0,phase,bitn;reg checking=0;time old_at,new_at,ss_at,cs_at,event_at;
 always @(posedge tc)begin
  #1;
  if(checking)begin
   checks=checks+1;
   if(old_vm!==($time>=old_at) || new_vm!==($time>=new_at))begin
    bad=bad+1;if(bad<8)$display("CAP_SPLIT mismatch time=%0t old=%b/%b new=%b/%b",$time,old_vm,$time>=old_at,new_vm,$time>=new_at);
   end
  end
 end
 task clear_all;
 begin
  checking=0;rn=0;sf=0;cf=0;run_s=1;run_t=1;
  repeat(10)@(negedge sc);rn=1;
  repeat(10)@(negedge sc);
  if(old_vm!==0||new_vm!==0)begin bad=bad+1;$display("CAP_SPLIT reset mismatch");end
 end endtask
 task check_case(input integer domain,input integer b,input integer ph);
 time first_t,first_s;
 begin
  clear_all();#(37+ph*417);event_at=$time;
  first_t=(event_at/834+1)*834;first_s=(event_at/1112+1)*1112;
  old_at=first_t+2*834;
  if(domain==0)begin
   sf=81'd1<<b;ss_at=first_s+1112;
   new_at=(ss_at/834+1)*834+2*834;
  end else begin cf=16'd1<<b;cs_at=first_t+834;new_at=first_t+3*834;end
`ifdef CAP_FAULT_MUT_EARLY
  new_at=new_at-834;
`endif
  checking=1;repeat(14)@(negedge sc);checking=0;
  if(!new_vm||!old_vm)begin bad=bad+1;$display("CAP_SPLIT missing stickyfault domain=%0d bit=%0d",domain,b);end
  $display("CAP_SPLIT LAT phase=%0d domain=%0d bit=%0d event=%0t old=%0t new=%0t delta=%0t",ph,domain,b,event_at,old_at,new_at,new_at-old_at);
  cases=cases+1;
 end endtask
 initial begin
  // All81 serial leaf/status bits and all16 stream x34 faults at all8 phases.
  // Assertion is deliberately asynchronous to either sampling edge; inputs are
  // sticky levels, as the actual capl/status/x34 fault source RTL guarantees.
  for(phase=0;phase<8;phase=phase+1)begin
   for(bitn=0;bitn<81;bitn=bitn+1)check_case(0,bitn,phase);
   for(bitn=0;bitn<16;bitn=bitn+1)check_case(1,bitn,phase);
  end
  // Stop the serial summary clock while a sticky actual-source level arrives.
  // The stream receiver stays running; fault must survive and appear on resume.
  clear_all();@(negedge sc);run_s=0;#123;sf[80]=1;
  repeat(8)@(negedge tc);if(new_vm!==0)begin bad=bad+1;$display("CAP_SPLIT serial stop early");end
  run_s=1;repeat(8)@(negedge sc);if(new_vm!==1)begin bad=bad+1;$display("CAP_SPLIT serial stop lost");end
  // Warm reset while halted: per-root reset stays asserted through resumed
  // sampling, matching the active-low epoch reset contract. No stale replay.
  @(negedge sc);run_s=0;rn=0;sf=0;cf=0;repeat(6)@(negedge tc);
  run_s=1;repeat(8)@(negedge sc);rn=1;repeat(8)@(negedge sc);
  if(new_vm!==0||old_vm!==0)begin bad=bad+1;$display("CAP_SPLIT warm reset stale");end
  clear_all();@(negedge tc);run_t=0;#127;cf[15]=1;
  repeat(8)@(negedge sc);if(new_vm!==0)begin bad=bad+1;$display("CAP_SPLIT core stop early");end
  run_t=1;repeat(8)@(negedge tc);if(new_vm!==1)begin bad=bad+1;$display("CAP_SPLIT core stop lost");end
  clear_all();
  $display("CAPTURE_FAULT_SPLIT %s cases=%0d checks=%0d phases=8 serial_bits=81 core_bits=16 clockstop=2 warmreset=1",bad?"FAIL":"PASS",cases,checks);
  if(bad)$fatal(1);$finish;
 end
endmodule
