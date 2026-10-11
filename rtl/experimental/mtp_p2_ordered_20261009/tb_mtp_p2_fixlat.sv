`timescale 1ns/1ps
// Stationed bench of the P2 draft-die links (mtp-fixlat-1011): collective end dsfd_coll_p2_ep + VM end dsfd_vm_p2_ep
// -> registered relay stations at the draft-A generator counts -> dsfd_p2_rtt (dsfd_p2_lnk + the unchanged rb4 core
// ot_mtp_p2_prefix_path ROOTPIPE 1).  Same transaction as tb_mtp_p2_prefix_path (start, 80 lane-1 E3 words,
// 160 lane-0 words E127 then E65, 80 numeric output rows checked against gold.hex), but the lanes are independent
// streams with random gaps, NTX back-to-back transactions (identity + t), lanes ungated by the start (the core holds
// in_r low until its start) and the collective consumer stalls (incl. a 200-cycle window): every receiver is stalled
// with flits in flight.
//   default             PASS expected
//   +OT_FIXLAT_MUT_LAT1 every link receiver sized for a latency-1 link (0 hops) -> receive FIFO overflow (FAIL)
//   +OT_P2_NAIVE        the core's own valid / ready pins straight onto the stations (no link ends; senders and
//                       consumer judge the handshake on the ready they see) -> lost / duplicated words (FAIL)
module p2fl_relay #(parameter integer W=1, N=0)(input wire clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
 generate if(N==0) begin: z assign q=d; end else begin: p
  reg [W-1:0] s[0:N-1]; integer i;
  always @(posedge clk) if(!rst_n) for(i=0;i<N;i=i+1) s[i]<='0; else begin s[0]<=d; for(i=1;i<N;i=i+1) s[i]<=s[i-1]; end
  assign q=s[N-1];
 end endgenerate
endmodule
module tb_mtp_p2_fixlat #(parameter integer FV=12, RV=14, FC=8, RC=9, SEED=1, NTX=2, START_DELAY=300, NOSTALL=0);
 reg clk=0; always #0.416667 clk=~clk;
 reg rst_n=0;
 reg [31:0] inputs[0:3839], gold[0:1279];
 localparam [73:0] IDN0=74'h12345678; localparam [26:0] IDS={9'd127,9'd65,9'd3};
 integer cycles=0, received=0, s0=0, s1=0, i;
 function automatic [511:0] flit(input integer e, w);
  integer s; begin for(s=0;s<16;s=s+1) flit[32*s+:32]=inputs[e*1280+w*16+s]; end
 endfunction
 // lane words {identity74, expert9, shared1, last1, word7, data512}
 // transaction t = word index / per-transaction count; identity IDN0 + t
 function automatic [603:0] l1w(input integer n); integer w; reg [73:0] id; begin w=n%80; id=IDN0+n/80;
  l1w={id,9'd3,1'b0,w==79,7'(w),flit(0,w)}; end endfunction
 function automatic [603:0] l0w(input integer n); integer k; reg [73:0] id; begin k=n%160; id=IDN0+n/160;
  l0w = k<80 ? {id,9'd127,1'b0,k==79,7'(k),flit(2,k)} : {id,9'd65,1'b0,k==159,7'(k-80),flit(1,k-80)}; end
 endfunction
 function automatic [31:0] mix(input [31:0] a, b); mix=(a^(b*32'h9e3779b9))*32'h85ebca6b ^ (a>>13); endfunction
 reg [31:0] rnd;
 always @(negedge clk) rnd = mix(cycles+SEED, 32'h51ed2701);
 // core-side driver regs (collective core: start + lane 1 + output consumer; VM core: lane 0)
 reg cs_v=0, c1_v=0, c0_v=0, co_r=0; integer starts=0;
 wire cs_r, c1_r, c0_r, co_v; wire [593:0] co_d;
 wire done, fault, corr;
`ifndef OT_P2_NAIVE
 wire l0v_s, l0g_s, l1v_s, l1g_s, sv_s, sg_s, ov_s, og_s; wire [603:0] l0d_s, l1d_s; wire [100:0] sd_s; wire [593:0] od_s;
 wire l0v_p, l0g_p, l1v_p, l1g_p, sv_p, sg_p, ov_p, og_p; wire [603:0] l0d_p, l1d_p; wire [100:0] sd_p; wire [593:0] od_p;
 dsfd_vm_p2_ep vme(.ck(clk), .rst(rst_n), .c_l0v(c0_v), .c_l0r(c0_r), .c_l0d(l0w(s0)), .t_l0v(l0v_s), .t_l0d(l0d_s), .f_l0g(l0g_s));
 // lane 1 sender: a grant-protocol transmitter (as dsfd_coll_p2_lane_ba OGRANT on the die bus)
 ot_dsrom_mtp_ltx_rc #(.W(604)) l1tx(.clk(clk), .rst_n(rst_n), .c_valid(c1_v), .c_ready(c1_r), .c_data(l1w(s1)),
  .l_valid(l1v_s), .l_ready(l1g_s), .l_data(l1d_s));
 dsfd_coll_p2_ep #(.FWD_C(FC),.RET_C(RC)) cle(.ck(clk), .rst(rst_n), .c_sv(cs_v), .c_sr(cs_r), .c_sd({IDN0+starts,IDS}), .t_sv(sv_s), .t_sd(sd_s), .f_sg(sg_s),
  .f_ov(ov_s), .f_od(od_s), .t_og(og_s), .c_ov(co_v), .c_or(co_r), .c_od(co_d));
 p2fl_relay #(.W(605),.N(FV)) r0 (clk, rst_n, {l0v_s,l0d_s}, {l0v_p,l0d_p});
 p2fl_relay #(.W(1),.N(RV))   r0g(clk, rst_n, l0g_p, l0g_s);
 p2fl_relay #(.W(605),.N(FC)) r1 (clk, rst_n, {l1v_s,l1d_s}, {l1v_p,l1d_p});
 p2fl_relay #(.W(1),.N(RC))   r1g(clk, rst_n, l1g_p, l1g_s);
 p2fl_relay #(.W(102),.N(FC)) rs (clk, rst_n, {sv_s,sd_s}, {sv_p,sd_p});
 p2fl_relay #(.W(1),.N(RC))   rsg(clk, rst_n, sg_p, sg_s);
 p2fl_relay #(.W(595),.N(RC)) ro (clk, rst_n, {ov_p,od_p}, {ov_s,od_s});
 p2fl_relay #(.W(1),.N(FC))   rog(clk, rst_n, og_s, og_p);
 dsfd_p2_rtt #(.FWD_V(FV),.RET_V(RV),.FWD_C(FC),.RET_C(RC)) dut(.ck(clk), .rst(rst_n),
  .f_l0v(l0v_p), .f_l0d(l0d_p), .t_l0g(l0g_p), .f_l1v(l1v_p), .f_l1d(l1d_p), .t_l1g(l1g_p), .f_sv(sv_p), .f_sd(sd_p), .t_sg(sg_p),
  .t_ov(ov_p), .t_od(od_p), .f_og(og_p), .f_abort(1'b0), .t_done(done), .t_fault(fault), .t_corrected(corr));
`else
 // as-is: plain valid / ready across the same stations; a sender's handshake = its valid && the ready it sees
 wire [1:0] ir_p; wire sr_p, ov_p; wire [593:0] od_p; wire [603:0] l0d_p, l1d_p; wire l0v_p, l1v_p, sv_p; wire [100:0] sd_p; wire or_p;
 wire [1:0] ir_s; wire sr_s; wire ov_s; wire [593:0] od_s;
 p2fl_relay #(.W(605),.N(FV)) r0 (clk, rst_n, {c0_v,l0w(s0)}, {l0v_p,l0d_p});
 p2fl_relay #(.W(1),.N(RV))   r0g(clk, rst_n, ir_p[0], ir_s[0]);
 p2fl_relay #(.W(605),.N(FC)) r1 (clk, rst_n, {c1_v,l1w(s1)}, {l1v_p,l1d_p});
 p2fl_relay #(.W(1),.N(RC))   r1g(clk, rst_n, ir_p[1], ir_s[1]);
 p2fl_relay #(.W(102),.N(FC)) rs (clk, rst_n, {cs_v,IDN0+starts,IDS}, {sv_p,sd_p});
 p2fl_relay #(.W(1),.N(RC))   rsg(clk, rst_n, sr_p, sr_s);
 p2fl_relay #(.W(595),.N(RC)) ro (clk, rst_n, {ov_p,od_p}, {ov_s,od_s});
 p2fl_relay #(.W(1),.N(FC))   rog(clk, rst_n, co_r, or_p);
 assign c0_r=ir_s[0]; assign c1_r=ir_s[1]; assign cs_r=sr_s; assign co_v=ov_s; assign co_d=od_s;
 wire [511:0] od; wire [73:0] oid; wire [6:0] ow; wire ol; assign od_p={od,oid,ow,ol};
 ot_mtp_p2_prefix_path #(.ENABLE(1),.REGB(1),.ROOTPIPE(1)) dut(.clk(clk),.rst_n(rst_n),
  .start_v(sv_p),.start_r(sr_p),.start_identity(sd_p[100:27]),.start_ids(sd_p[26:0]),
  .in_v({l1v_p,l0v_p}),.in_r(ir_p),.in_identity({l1d_p[603:530],l0d_p[603:530]}),.in_expert({l1d_p[529:521],l0d_p[529:521]}),
  .in_shared({l1d_p[520],l0d_p[520]}),.in_last({l1d_p[519],l0d_p[519]}),.in_word({l1d_p[518:512],l0d_p[518:512]}),
  .in_data({l1d_p[511:0],l0d_p[511:0]}),.out_v(ov_p),.out_r(or_p),.out_data(od),.out_identity(oid),.out_word(ow),.out_last(ol),
  .abort(1'b0),.done(done),.fault(fault),.corrected(corr));
`endif
 // drivers (negedge; handshakes sampled at posedge)
 always @(negedge clk) if(rst_n) begin
  // lanes are not gated by the start: the core holds in_r low until its start (and between transactions), so the
  // link receivers sit stalled with flits in flight; the first start is held back START_DELAY cycles
  cs_v = starts<NTX && cycles>=START_DELAY;
  // NOSTALL: saturated sources / always-ready consumer (latency measurement: lnk at 0 stations vs OT_P2_NAIVE at 0
  // stations = the core driven directly).
  c1_v = s1<80*NTX  && (NOSTALL || rnd[2:0]!=0);
  c0_v = s0<160*NTX && (NOSTALL || rnd[5:3]!=0);
  co_r = NOSTALL || (!(cycles>=900 && cycles<1100) && rnd[9:7]!=0 && !(cycles%300>=250));
 end
 always @(posedge clk) if(rst_n) begin
  cycles<=cycles+1;
  if(cs_v&&cs_r) starts<=starts+1;
  if(c1_v&&c1_r) s1<=s1+1;
  if(c0_v&&c0_r) s0<=s0+1;
  if(fault) $fatal(1,"P2FL unexpected fault cycle %0d",cycles);
  if(co_v&&co_r) begin
   if(received>=80*NTX) $fatal(1,"P2FL extra/duplicate output row %0d",received);
   if(co_d[81:8]!==IDN0+received/80 || co_d[7:1]!==7'(received%80) || co_d[0]!==(received%80==79))
    $fatal(1,"P2FL metadata row %0d (word %0d last %0d)",received,co_d[7:1],co_d[0]);
   for(i=0;i<16;i=i+1) if(co_d[82+32*i+:32]!==gold[(received%80)*16+i]) $fatal(1,"P2FL numeric row %0d lane %0d",received,i);
   received<=received+1;
  end
  if(cycles>20000*NTX) $fatal(1,"P2FL timeout received=%0d s0=%0d s1=%0d",received,s0,s1);
 end
 integer done_seen=0;
 always @(posedge clk) if(done) done_seen<=done_seen+1;
 initial begin
  $readmemh("inputs.hex",inputs); $readmemh("gold.hex",gold);
  repeat(6) @(negedge clk); rst_n=1;
  wait(received==80*NTX && done_seen==NTX);
  repeat(3*(FV+RV+FC+RC)+20) @(posedge clk);
  if(co_v || done_seen!=NTX) $fatal(1,"P2FL extra output / done after completion");
  $display("P2FL PASS FV=%0d RV=%0d FC=%0d RC=%0d transactions=%0d rows=%0d lane0=%0d lane1=%0d cycles=%0d", FV,RV,FC,RC,NTX,received,s0,s1,cycles);
  $finish;
 end
endmodule
