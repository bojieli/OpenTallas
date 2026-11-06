`timescale 1ns/1ps
`default_nettype none
module tb;
 reg clk=0, rst_n=0; always #1 clk=~clk;
 reg [1:0] client_seq=0;
 reg [0:0] response_enable=0;
 reg [1:0] response_seq=0;
 reg [7:0] bank_enable=0;
 reg [7:0] bank_client=0;
 reg [1:0] hub_ring_enable=0;
 reg [1:0] hub_ring_client=0;
 reg [2223:0] cw_in=0;
 reg [2223:0] ccw_in=0;
 wire [2223:0] r_cw_out, d_cw_out;
 wire [2223:0] r_ccw_out, d_ccw_out;
 reg [1:0] ring_tx_enable=0;
 reg [5:0] ring_tx_source=0;
 reg [0:0] replay_enable=0;
 reg [0:0] replay_source=0;
 wire [275:0] r_b0_xq, d_b0_xq;
 wire [275:0] r_b0_xq2, d_b0_xq2;
 reg [0:0] b0_xq_done=0;
 reg [0:0] b0_xq2_done=0;
 reg [275:0] b0_eg=0;
 wire [284:0] r_b0_pq, d_b0_pq;
 reg [265:0] b0_pr=0;
 reg [17:0] b0_status=0;
 reg [0:0] b0_flt=0;
 wire [275:0] r_b1_xq, d_b1_xq;
 wire [275:0] r_b1_xq2, d_b1_xq2;
 reg [0:0] b1_xq_done=0;
 reg [0:0] b1_xq2_done=0;
 reg [275:0] b1_eg=0;
 wire [284:0] r_b1_pq, d_b1_pq;
 reg [265:0] b1_pr=0;
 reg [17:0] b1_status=0;
 reg [0:0] b1_flt=0;
 wire [275:0] r_b2_xq, d_b2_xq;
 wire [275:0] r_b2_xq2, d_b2_xq2;
 reg [0:0] b2_xq_done=0;
 reg [0:0] b2_xq2_done=0;
 reg [275:0] b2_eg=0;
 wire [284:0] r_b2_pq, d_b2_pq;
 reg [265:0] b2_pr=0;
 reg [17:0] b2_status=0;
 reg [0:0] b2_flt=0;
 wire [275:0] r_b3_xq, d_b3_xq;
 wire [275:0] r_b3_xq2, d_b3_xq2;
 reg [0:0] b3_xq_done=0;
 reg [0:0] b3_xq2_done=0;
 reg [275:0] b3_eg=0;
 wire [284:0] r_b3_pq, d_b3_pq;
 reg [265:0] b3_pr=0;
 reg [17:0] b3_status=0;
 reg [0:0] b3_flt=0;
 wire [275:0] r_b4_xq, d_b4_xq;
 wire [275:0] r_b4_xq2, d_b4_xq2;
 reg [0:0] b4_xq_done=0;
 reg [0:0] b4_xq2_done=0;
 reg [275:0] b4_eg=0;
 wire [284:0] r_b4_pq, d_b4_pq;
 reg [265:0] b4_pr=0;
 reg [17:0] b4_status=0;
 reg [0:0] b4_flt=0;
 wire [275:0] r_b5_xq, d_b5_xq;
 wire [275:0] r_b5_xq2, d_b5_xq2;
 reg [0:0] b5_xq_done=0;
 reg [0:0] b5_xq2_done=0;
 reg [275:0] b5_eg=0;
 wire [284:0] r_b5_pq, d_b5_pq;
 reg [265:0] b5_pr=0;
 reg [17:0] b5_status=0;
 reg [0:0] b5_flt=0;
 wire [275:0] r_b6_xq, d_b6_xq;
 wire [275:0] r_b6_xq2, d_b6_xq2;
 reg [0:0] b6_xq_done=0;
 reg [0:0] b6_xq2_done=0;
 reg [275:0] b6_eg=0;
 wire [284:0] r_b6_pq, d_b6_pq;
 reg [265:0] b6_pr=0;
 reg [17:0] b6_status=0;
 reg [0:0] b6_flt=0;
 wire [275:0] r_b7_xq, d_b7_xq;
 wire [275:0] r_b7_xq2, d_b7_xq2;
 reg [0:0] b7_xq_done=0;
 reg [0:0] b7_xq2_done=0;
 reg [275:0] b7_eg=0;
 wire [284:0] r_b7_pq, d_b7_pq;
 reg [265:0] b7_pr=0;
 reg [17:0] b7_status=0;
 reg [0:0] b7_flt=0;
 wire [2:0] r_hub_status, d_hub_status;
 wire [1:0] r_mirror_busy, d_mirror_busy;
 wire [18:0] r_vmstat, d_vmstat;
 wire [2:0] r_ring_fault, d_ring_fault;
 hfd_hgi_vms_glue_nw_t__fcore u_ref(.clk(clk),.rst_n(rst_n),.client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),.bank_enable(bank_enable),.bank_client(bank_client),.hub_ring_enable(hub_ring_enable),.hub_ring_client(hub_ring_client),.cw_in(cw_in),.ccw_in(ccw_in),.cw_out(r_cw_out),.ccw_out(r_ccw_out),.ring_tx_enable(ring_tx_enable),.ring_tx_source(ring_tx_source),.replay_enable(replay_enable),.replay_source(replay_source),.b0_xq(r_b0_xq),.b0_xq2(r_b0_xq2),.b0_xq_done(b0_xq_done),.b0_xq2_done(b0_xq2_done),.b0_eg(b0_eg),.b0_pq(r_b0_pq),.b0_pr(b0_pr),.b0_status(b0_status),.b0_flt(b0_flt),.b1_xq(r_b1_xq),.b1_xq2(r_b1_xq2),.b1_xq_done(b1_xq_done),.b1_xq2_done(b1_xq2_done),.b1_eg(b1_eg),.b1_pq(r_b1_pq),.b1_pr(b1_pr),.b1_status(b1_status),.b1_flt(b1_flt),.b2_xq(r_b2_xq),.b2_xq2(r_b2_xq2),.b2_xq_done(b2_xq_done),.b2_xq2_done(b2_xq2_done),.b2_eg(b2_eg),.b2_pq(r_b2_pq),.b2_pr(b2_pr),.b2_status(b2_status),.b2_flt(b2_flt),.b3_xq(r_b3_xq),.b3_xq2(r_b3_xq2),.b3_xq_done(b3_xq_done),.b3_xq2_done(b3_xq2_done),.b3_eg(b3_eg),.b3_pq(r_b3_pq),.b3_pr(b3_pr),.b3_status(b3_status),.b3_flt(b3_flt),.b4_xq(r_b4_xq),.b4_xq2(r_b4_xq2),.b4_xq_done(b4_xq_done),.b4_xq2_done(b4_xq2_done),.b4_eg(b4_eg),.b4_pq(r_b4_pq),.b4_pr(b4_pr),.b4_status(b4_status),.b4_flt(b4_flt),.b5_xq(r_b5_xq),.b5_xq2(r_b5_xq2),.b5_xq_done(b5_xq_done),.b5_xq2_done(b5_xq2_done),.b5_eg(b5_eg),.b5_pq(r_b5_pq),.b5_pr(b5_pr),.b5_status(b5_status),.b5_flt(b5_flt),.b6_xq(r_b6_xq),.b6_xq2(r_b6_xq2),.b6_xq_done(b6_xq_done),.b6_xq2_done(b6_xq2_done),.b6_eg(b6_eg),.b6_pq(r_b6_pq),.b6_pr(b6_pr),.b6_status(b6_status),.b6_flt(b6_flt),.b7_xq(r_b7_xq),.b7_xq2(r_b7_xq2),.b7_xq_done(b7_xq_done),.b7_xq2_done(b7_xq2_done),.b7_eg(b7_eg),.b7_pq(r_b7_pq),.b7_pr(b7_pr),.b7_status(b7_status),.b7_flt(b7_flt),.hub_status(r_hub_status),.mirror_busy(r_mirror_busy),.vmstat(r_vmstat),.ring_fault(r_ring_fault));
 hfd_hgi_vms_glue_nw_t__p11comp #(.XREG(2),.DMUT(`DMUT)) u_dut(.clk(clk),.rst_n(rst_n),.client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),.bank_enable(bank_enable),.bank_client(bank_client),.hub_ring_enable(hub_ring_enable),.hub_ring_client(hub_ring_client),.cw_in(cw_in),.ccw_in(ccw_in),.cw_out(d_cw_out),.ccw_out(d_ccw_out),.ring_tx_enable(ring_tx_enable),.ring_tx_source(ring_tx_source),.replay_enable(replay_enable),.replay_source(replay_source),.b0_xq(d_b0_xq),.b0_xq2(d_b0_xq2),.b0_xq_done(b0_xq_done),.b0_xq2_done(b0_xq2_done),.b0_eg(b0_eg),.b0_pq(d_b0_pq),.b0_pr(b0_pr),.b0_status(b0_status),.b0_flt(b0_flt),.b1_xq(d_b1_xq),.b1_xq2(d_b1_xq2),.b1_xq_done(b1_xq_done),.b1_xq2_done(b1_xq2_done),.b1_eg(b1_eg),.b1_pq(d_b1_pq),.b1_pr(b1_pr),.b1_status(b1_status),.b1_flt(b1_flt),.b2_xq(d_b2_xq),.b2_xq2(d_b2_xq2),.b2_xq_done(b2_xq_done),.b2_xq2_done(b2_xq2_done),.b2_eg(b2_eg),.b2_pq(d_b2_pq),.b2_pr(b2_pr),.b2_status(b2_status),.b2_flt(b2_flt),.b3_xq(d_b3_xq),.b3_xq2(d_b3_xq2),.b3_xq_done(b3_xq_done),.b3_xq2_done(b3_xq2_done),.b3_eg(b3_eg),.b3_pq(d_b3_pq),.b3_pr(b3_pr),.b3_status(b3_status),.b3_flt(b3_flt),.b4_xq(d_b4_xq),.b4_xq2(d_b4_xq2),.b4_xq_done(b4_xq_done),.b4_xq2_done(b4_xq2_done),.b4_eg(b4_eg),.b4_pq(d_b4_pq),.b4_pr(b4_pr),.b4_status(b4_status),.b4_flt(b4_flt),.b5_xq(d_b5_xq),.b5_xq2(d_b5_xq2),.b5_xq_done(b5_xq_done),.b5_xq2_done(b5_xq2_done),.b5_eg(b5_eg),.b5_pq(d_b5_pq),.b5_pr(b5_pr),.b5_status(b5_status),.b5_flt(b5_flt),.b6_xq(d_b6_xq),.b6_xq2(d_b6_xq2),.b6_xq_done(b6_xq_done),.b6_xq2_done(b6_xq2_done),.b6_eg(b6_eg),.b6_pq(d_b6_pq),.b6_pr(b6_pr),.b6_status(b6_status),.b6_flt(b6_flt),.b7_xq(d_b7_xq),.b7_xq2(d_b7_xq2),.b7_xq_done(b7_xq_done),.b7_xq2_done(b7_xq2_done),.b7_eg(b7_eg),.b7_pq(d_b7_pq),.b7_pr(b7_pr),.b7_status(b7_status),.b7_flt(b7_flt),.hub_status(d_hub_status),.mirror_busy(d_mirror_busy),.vmstat(d_vmstat),.ring_fault(d_ring_fault));
 integer cyc=0, err=0, ep=0, live=0, act=0; reg [5:0] en; reg [31:0] dens;
 function automatic [31:0] rb(input integer d); rb=($urandom%100)<d; endfunction
 task automatic drive; begin
  client_seq=en[3]?2'({$urandom}):'0;
  response_enable=en[3]?1'({$urandom}):'0;
  if(en[3]) response_enable=rb(dens);
  response_seq=en[3]?2'({$urandom}):'0;
  bank_enable=en[3]?8'({$urandom}):'0;
  bank_client=en[3]?8'({$urandom}):'0;
  hub_ring_enable=en[3]?2'({$urandom}):'0;
  hub_ring_client=en[3]?2'({$urandom}):'0;
  cw_in=en[0]?2224'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[0] && !rb(dens)) cw_in[2223]=1'b0;
  ccw_in=en[1]?2224'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[1] && !rb(dens)) ccw_in[2223]=1'b0;
  ring_tx_enable=en[0]?2'({$urandom}):'0;
  ring_tx_source=en[2]?6'({$urandom}):'0;
  replay_enable=en[4]?1'({$urandom}):'0;
  if(en[4]) replay_enable=rb(dens);
  replay_source=en[4]?1'({$urandom}):'0;
  if(en[4]) replay_source=rb(dens);
  b0_xq_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b0_xq_done=rb(dens);
  b0_xq2_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b0_xq2_done=rb(dens);
  b0_eg=en[5]?276'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b0_eg[275]=1'b0;
  b0_pr=en[5]?266'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b0_pr[265]=1'b0;
  b0_status=en[5]?18'({$urandom}):'0;
  b0_flt=en[5]?1'({$urandom}):'0;
  if(en[5]) b0_flt=rb(dens);
  b1_xq_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b1_xq_done=rb(dens);
  b1_xq2_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b1_xq2_done=rb(dens);
  b1_eg=en[5]?276'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b1_eg[275]=1'b0;
  b1_pr=en[5]?266'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b1_pr[265]=1'b0;
  b1_status=en[5]?18'({$urandom}):'0;
  b1_flt=en[5]?1'({$urandom}):'0;
  if(en[5]) b1_flt=rb(dens);
  b2_xq_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b2_xq_done=rb(dens);
  b2_xq2_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b2_xq2_done=rb(dens);
  b2_eg=en[5]?276'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b2_eg[275]=1'b0;
  b2_pr=en[5]?266'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b2_pr[265]=1'b0;
  b2_status=en[5]?18'({$urandom}):'0;
  b2_flt=en[5]?1'({$urandom}):'0;
  if(en[5]) b2_flt=rb(dens);
  b3_xq_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b3_xq_done=rb(dens);
  b3_xq2_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b3_xq2_done=rb(dens);
  b3_eg=en[5]?276'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b3_eg[275]=1'b0;
  b3_pr=en[5]?266'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b3_pr[265]=1'b0;
  b3_status=en[5]?18'({$urandom}):'0;
  b3_flt=en[5]?1'({$urandom}):'0;
  if(en[5]) b3_flt=rb(dens);
  b4_xq_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b4_xq_done=rb(dens);
  b4_xq2_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b4_xq2_done=rb(dens);
  b4_eg=en[5]?276'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b4_eg[275]=1'b0;
  b4_pr=en[5]?266'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b4_pr[265]=1'b0;
  b4_status=en[5]?18'({$urandom}):'0;
  b4_flt=en[5]?1'({$urandom}):'0;
  if(en[5]) b4_flt=rb(dens);
  b5_xq_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b5_xq_done=rb(dens);
  b5_xq2_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b5_xq2_done=rb(dens);
  b5_eg=en[5]?276'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b5_eg[275]=1'b0;
  b5_pr=en[5]?266'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b5_pr[265]=1'b0;
  b5_status=en[5]?18'({$urandom}):'0;
  b5_flt=en[5]?1'({$urandom}):'0;
  if(en[5]) b5_flt=rb(dens);
  b6_xq_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b6_xq_done=rb(dens);
  b6_xq2_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b6_xq2_done=rb(dens);
  b6_eg=en[5]?276'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b6_eg[275]=1'b0;
  b6_pr=en[5]?266'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b6_pr[265]=1'b0;
  b6_status=en[5]?18'({$urandom}):'0;
  b6_flt=en[5]?1'({$urandom}):'0;
  if(en[5]) b6_flt=rb(dens);
  b7_xq_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b7_xq_done=rb(dens);
  b7_xq2_done=en[5]?1'({$urandom}):'0;
  if(en[5]) b7_xq2_done=rb(dens);
  b7_eg=en[5]?276'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b7_eg[275]=1'b0;
  b7_pr=en[5]?266'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}):'0;
  if(en[5] && !rb(dens)) b7_pr[265]=1'b0;
  b7_status=en[5]?18'({$urandom}):'0;
  b7_flt=en[5]?1'({$urandom}):'0;
  if(en[5]) b7_flt=rb(dens);
 end endtask
 always @(negedge clk) begin
  if(rst_n && cyc>4) begin
   if(r_cw_out!==d_cw_out) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d cw_out ref %h dut %h",ep,cyc,r_cw_out,d_cw_out); end
   if(r_ccw_out!==d_ccw_out) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d ccw_out ref %h dut %h",ep,cyc,r_ccw_out,d_ccw_out); end
   if(r_b0_xq!==d_b0_xq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b0_xq ref %h dut %h",ep,cyc,r_b0_xq,d_b0_xq); end
   if(r_b0_xq2!==d_b0_xq2) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b0_xq2 ref %h dut %h",ep,cyc,r_b0_xq2,d_b0_xq2); end
   if(r_b0_pq!==d_b0_pq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b0_pq ref %h dut %h",ep,cyc,r_b0_pq,d_b0_pq); end
   if(r_b1_xq!==d_b1_xq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b1_xq ref %h dut %h",ep,cyc,r_b1_xq,d_b1_xq); end
   if(r_b1_xq2!==d_b1_xq2) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b1_xq2 ref %h dut %h",ep,cyc,r_b1_xq2,d_b1_xq2); end
   if(r_b1_pq!==d_b1_pq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b1_pq ref %h dut %h",ep,cyc,r_b1_pq,d_b1_pq); end
   if(r_b2_xq!==d_b2_xq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b2_xq ref %h dut %h",ep,cyc,r_b2_xq,d_b2_xq); end
   if(r_b2_xq2!==d_b2_xq2) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b2_xq2 ref %h dut %h",ep,cyc,r_b2_xq2,d_b2_xq2); end
   if(r_b2_pq!==d_b2_pq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b2_pq ref %h dut %h",ep,cyc,r_b2_pq,d_b2_pq); end
   if(r_b3_xq!==d_b3_xq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b3_xq ref %h dut %h",ep,cyc,r_b3_xq,d_b3_xq); end
   if(r_b3_xq2!==d_b3_xq2) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b3_xq2 ref %h dut %h",ep,cyc,r_b3_xq2,d_b3_xq2); end
   if(r_b3_pq!==d_b3_pq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b3_pq ref %h dut %h",ep,cyc,r_b3_pq,d_b3_pq); end
   if(r_b4_xq!==d_b4_xq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b4_xq ref %h dut %h",ep,cyc,r_b4_xq,d_b4_xq); end
   if(r_b4_xq2!==d_b4_xq2) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b4_xq2 ref %h dut %h",ep,cyc,r_b4_xq2,d_b4_xq2); end
   if(r_b4_pq!==d_b4_pq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b4_pq ref %h dut %h",ep,cyc,r_b4_pq,d_b4_pq); end
   if(r_b5_xq!==d_b5_xq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b5_xq ref %h dut %h",ep,cyc,r_b5_xq,d_b5_xq); end
   if(r_b5_xq2!==d_b5_xq2) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b5_xq2 ref %h dut %h",ep,cyc,r_b5_xq2,d_b5_xq2); end
   if(r_b5_pq!==d_b5_pq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b5_pq ref %h dut %h",ep,cyc,r_b5_pq,d_b5_pq); end
   if(r_b6_xq!==d_b6_xq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b6_xq ref %h dut %h",ep,cyc,r_b6_xq,d_b6_xq); end
   if(r_b6_xq2!==d_b6_xq2) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b6_xq2 ref %h dut %h",ep,cyc,r_b6_xq2,d_b6_xq2); end
   if(r_b6_pq!==d_b6_pq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b6_pq ref %h dut %h",ep,cyc,r_b6_pq,d_b6_pq); end
   if(r_b7_xq!==d_b7_xq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b7_xq ref %h dut %h",ep,cyc,r_b7_xq,d_b7_xq); end
   if(r_b7_xq2!==d_b7_xq2) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b7_xq2 ref %h dut %h",ep,cyc,r_b7_xq2,d_b7_xq2); end
   if(r_b7_pq!==d_b7_pq) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d b7_pq ref %h dut %h",ep,cyc,r_b7_pq,d_b7_pq); end
   if(r_hub_status!==d_hub_status) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d hub_status ref %h dut %h",ep,cyc,r_hub_status,d_hub_status); end
   if(r_mirror_busy!==d_mirror_busy) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d mirror_busy ref %h dut %h",ep,cyc,r_mirror_busy,d_mirror_busy); end
   if(r_vmstat!==d_vmstat) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d vmstat ref %h dut %h",ep,cyc,r_vmstat,d_vmstat); end
   if(r_ring_fault!==d_ring_fault) begin err=err+1; if(err<8) $display("DIFF ep %0d cyc %0d ring_fault ref %h dut %h",ep,cyc,r_ring_fault,d_ring_fault); end
   if(r_ring_fault!=0 || r_vmstat[18]) act=act+1;
   if(r_b0_pq[284]|r_b3_pq[284]|r_cw_out[2223]|r_ccw_out[2223]|r_b0_xq[275]|r_b5_xq2[275]) live=live+1;
  end
  if(rst_n) cyc=cyc+1;
  drive;
 end
 initial begin
  for(ep=0; ep<`EPS; ep=ep+1) begin
   en=(ep<2)?6'h3f:6'($urandom); if(ep%5==1) en=6'b000001; if(ep%5==2) en=6'b000110; if(ep%5==3) en=6'b011000;
   dens=(ep%3==0)?50:((ep%3==1)?8:90);
   rst_n=0; cyc=0; repeat(6) @(negedge clk); rst_n=1;
   repeat(`CYC) @(negedge clk);
  end
  $display("GLUE_LOCKSTEP DMUT %0d episodes %0d err %0d live %0d faultcycles %0d", `DMUT, `EPS, err, live, act);
  if(err!=0) $display("FAIL"); else $display("PASS");
  $finish;
 end
endmodule
`default_nettype wire
