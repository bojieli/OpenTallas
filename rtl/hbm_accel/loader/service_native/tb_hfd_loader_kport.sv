`timescale 1ps/1ps
// ot_hfd_loader_kport bench (hgi-takeover; hbm-phys [svc] 2026-10-10: bursts + multi-outstanding): two loader lanes ->
// four stacks, each an actual ot_hbm_svc_core_native (NATIVE, WB, WB_SOURCE_ACK, KVS; native bursts, NATIVE_NO = NO) +
// refresh-aware controller model, through the lq / lr die packing.
//   phase 0  both lanes write interleaved sectors over all four stacks and all PCs, and lane 0 a contiguous region of
//            256 sectors on stack 1 (REGION)
//   phase 1  one-sector reads of phase 0's sparse sectors, one outstanding a lane: every write packet lands on the svc
//            of the stack that owns it, every read returns its data on the issuing lane
//   phase 2  BURST reads, both lanes, random length 1..8 at random region offsets, up to NO outstanding a lane: every
//            response in request order, address order within a burst, data exact, rsp_last exactly on the L-th
//   phase 3  FETCH RATE: lane 1 reads the region as 32 sequential 8-sector bursts with up to NO outstanding (the CP
//            ring fetch shape); B/cycle from the first request to the last response
// Checks everywhere: a PHY request's sectors stay in the PC that owns them (row boundary), no fault.
//   MUT: 1 responses to lane 0, 2 stack bit 1 ignored, 3 bursts cross the row boundary (must FAIL)
//   NO (outstanding a stack), XLAT (extra PHY request + response latency, ps), RATE_MIN (phase 3 gate, B/cycle x 1000)
module tb_hfd_loader_kport;
 parameter integer MUT = 0;
 parameter integer NO = 8;
 parameter integer XLAT = 0;
 parameter integer RATE_MIN = 1734;               // 2 x 0.867 B/cycle (the DS CP fetch need, x2 margin)
 parameter integer CH = 12;                       // die-chain register stages each way (lq loader -> svc, lr svc -> loader)
 parameter integer NQ = 4;                        // svc request queue credits
 parameter integer RB = 16;                       // kport response FIFO a stack (sectors)
 reg clk=0; always #416 clk=~clk; reg rst_n=0;
 localparam [35:0] SB = 36'd65536;            // per-stack capacity used here (fits the controller model's memory)
 localparam integer REGION = 512;            // first sector of the contiguous region on stack 1 (256 sectors)
 reg [1:0] req_v=0, req_we=0, rsp_rdy=0; reg [73:0] req_addr=0; reg [511:0] req_wdata=0; reg [31:0] req_tag=0;
 reg [7:0] req_len=0;
 wire [1:0] req_rdy, rsp_v, rsp_we, rsp_last; wire [31:0] rsp_tag; wire [511:0] rsp_data; wire fault;
 wire [4*350-1:0] lq; wire [4*293-1:0] lr;
 ot_hfd_loader_kport #(.ENABLE(1),.ND(2),.STACK_BYTES(SB),.NO(NO),.NQ(NQ),.RB(RB),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.req_v(req_v),
  .req_rdy(req_rdy),.req_we(req_we),.req_addr(req_addr),.req_wdata(req_wdata),.req_wstrb({32'hffffffff,32'hffffffff}),
  .req_tag(req_tag),.req_len(req_len),.rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_we(rsp_we),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
  .rsp_last(rsp_last),.lq(lq),.lr(lr),.fault(fault));
 genvar s, gp;
 integer placed_bad=0, row_bad=0;
 for (s=0;s<4;s=s+1) begin : g_st
  // the die's forwarded chains: CH register stages each way (the credited native protocol must tolerate them)
  reg [349:0] qp [0:CH]; reg [292:0] rp [0:CH]; wire [292:0] r_svc;
  always @* begin qp[0] = lq[s*350 +: 350]; rp[0] = r_svc; end
  for (gp=0; gp<CH; gp=gp+1) begin : g_ch
   always @(posedge clk or negedge rst_n) if (!rst_n) begin qp[gp+1] <= '0; rp[gp+1] <= '0; end
                                          else begin qp[gp+1] <= qp[gp]; rp[gp+1] <= rp[gp]; end
  end
  wire [349:0] q = qp[CH];
  assign lr[s*293 +: 293] = rp[CH];
  wire[31:0]k_v,k_rdy,k_we,kr_v,kr_rdy,k_wr_done; wire[959:0]k_addr; wire[127:0]k_len,kr_beat; wire[543:0]k_tag,kr_tag;
  wire[8191:0]k_wdata,kr_data; wire[1023:0]k_wstrb; wire[31:0]wq_source_g,wq_source_busy; wire wq_source_fault,wq_pending,native_fault,phy_rst_n;
  wire n_rdy,n_rsp_v; wire[4:0]n_rsp_pc; wire[15:0]n_rsp_tag; wire[3:0]n_rsp_beat; wire[255:0]n_rsp_data;
  assign r_svc = {wq_source_fault, wq_source_g[31:24], native_fault, n_rsp_data, n_rsp_beat, n_rsp_tag, n_rsp_pc, n_rsp_v, n_rdy};
  ot_hbm_svc_core_native #(.NATIVE(1),.WB(1),.WB_SOURCE_ACK(1),.KVS(1),.XST(0),.WQ_ST(1),.NATIVE_NO(NO),.NATIVE_NQ(NQ),.NATIVE_CHAIN(1)) service(
   .ck(clk),.rst(rst_n),.q_d(336'b0),.q_v(8'b0),.q_fclk(8'b0),.e_d(128'b0),.e_fclk(1'b0),
   .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
   .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),
   .w_rdy(1'b1),.w_room(8'hff),.wr_v(8'b0),.wr_tag(80'b0),.wr_beat(40'b0),.wr_data(2048'b0),
   .wq_d(q[291:0]),.wq_fclk(clk),.wq_source(2'd2),.wq_source_g(wq_source_g),.wq_source_fault(wq_source_fault),
   .wq_source_busy(wq_source_busy),.wq_pending(wq_pending),.k_wr_done(k_wr_done),.phy_rst_n(phy_rst_n),
   .outer_write_pending(q[345]),
   .native_v(q[292]),.native_rdy(n_rdy),.native_pc(q[297:293]),.native_addr(q[327:298]),.native_tag(q[343:328]),.native_len(q[349:346]),
   .native_rsp_v(n_rsp_v),.native_rsp_rdy(q[344]),.native_rsp_pc(n_rsp_pc),.native_rsp_tag(n_rsp_tag),
   .native_rsp_beat(n_rsp_beat),.native_rsp_data(n_rsp_data),.native_fault(native_fault));
  ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.DW(256),.MEM_WORDS(1024),.TAGW(17),.LENW(4),.BEATW(4),.QD(64),.REFPB(3),.MEM_MODE(0),
   .REQ_PS(10000 + XLAT / 2),.RSP_PS(10000 + XLAT - XLAT / 2)) phy(
   .clk(clk),.rst_n(phy_rst_n),.req_v(k_v),.req_rdy(k_rdy),.req_addr(k_addr),.req_len(k_len),.req_tag(k_tag),.req_we(k_we),
   .req_wdata(k_wdata),.req_wstrb(k_wstrb),.wr_done(k_wr_done),.rsp_v(kr_v),.rsp_rdy(kr_rdy),.rsp_tag(kr_tag),.rsp_beat(kr_beat),.rsp_data(kr_data));
  // placement: a write packet's data carries its stack in word 1 (the bench's pattern), it must land on stack s
  always @(posedge clk) if (rst_n && q[0] && q[291:260] != 32'(s)) begin
   $display("FATAL: stack %0d received a write for stack %0d", s, q[291:260]); placed_bad = placed_bad + 1;
  end
  // row boundary: every sector of a PHY request belongs to the PC it is sent to
  for (gp=0; gp<32; gp=gp+1) begin : g_pc
   always @(posedge clk) if (rst_n && k_v[gp] && k_rdy[gp]) begin : rb
    integer b; reg [29:0] a;
    for (b = 0; b < k_len[gp*4 +: 4]; b = b + 1) begin
     a = k_addr[gp*30 +: 30] + 30'(b);
     if ((a[6:2] ^ a[11:7] ^ a[16:12]) != 5'(gp)) begin
      if (row_bad < 5) $display("FATAL: stack %0d PC %0d got sector %0d of PC %0d", s, gp, a, a[6:2] ^ a[11:7] ^ a[16:12]);
      row_bad = row_bad + 1;
     end
    end
   end
  end
 end
 function [255:0] pat(input integer stk, input integer lane, input integer j);
  pat = {32'(stk), 32'h5a000000 + 32'(lane*4096 + j), 192'(j * 32'h01010101 + lane)};
 endfunction
 function [255:0] rpat(input integer sec);      // region sector data (stack 1)
  rpat = {32'd1, 32'hc0de0000 + 32'(sec), 192'(sec * 32'h9e3779b1)};
 endfunction
 // lane d, transaction j: stack (j + d) % 4, sector 32*j + 4*d (+ stack base) : spreads PCs and stacks
 function [36:0] adr(input integer lane, input integer j);
  adr = {2'((j + lane) % 4), 35'(((j * 8 + lane) * 32) % 65536)};
 endfunction
 integer ph, j, d, done_n=0, cycles=0, k;
 integer jj [0:1]; reg [1:0] pend, acc;
 // phase 2 / 3 bookkeeping: per lane FIFO of outstanding bursts {first sector, len, tag}
 integer eq_s [0:1][0:63]; integer eq_l [0:1][0:63]; integer eq_t [0:1][0:63]; integer eq_h [0:1], eq_n [0:1], eb [0:1];
 integer nb [0:1], burst_n, rsp_n, t_first, t_last, t_rsp1, nreq [0:1], lastp = 0;
 task automatic check_burst_rsp(input integer dd);
  integer sec;
  begin
   if (eq_n[dd] == 0) $fatal(1, "FATAL: lane %0d response with nothing outstanding", dd);
   sec = eq_s[dd][eq_h[dd]] + eb[dd];
   if (rsp_tag[dd*16 +: 16] !== 16'(eq_t[dd][eq_h[dd]]) || rsp_we[dd] !== 1'b0 || rsp_data[dd*256 +: 256] !== rpat(sec) ||
       rsp_last[dd] !== (eb[dd] == eq_l[dd][eq_h[dd]] - 1))
    $fatal(1, "FATAL: lane %0d burst response mismatch: burst sector %0d len %0d beat %0d tag %h last %0d data %s", dd,
           eq_s[dd][eq_h[dd]], eq_l[dd][eq_h[dd]], eb[dd], rsp_tag[dd*16 +: 16], rsp_last[dd],
           rsp_data[dd*256 +: 256] === rpat(sec) ? "ok" : "BAD");
   if (rsp_n == 0) t_rsp1 = cycles;
   rsp_n = rsp_n + 1; t_last = cycles;
   if (eb[dd] == eq_l[dd][eq_h[dd]] - 1) begin eb[dd] = 0; eq_h[dd] = (eq_h[dd] + 1) % 64; eq_n[dd] = eq_n[dd] - 1; end
   else eb[dd] = eb[dd] + 1;
  end
 endtask
 initial begin
  repeat(4) @(posedge clk); rst_n=1; repeat(16) @(posedge clk);
  for (ph=0; ph<2; ph=ph+1) begin                       // 0: write all (+ the region, lane 0), 1: read all back
   jj[0]=0; jj[1]=0; pend=0;
   while (jj[0] < (ph == 0 ? 64 + 256 : 64) || jj[1] < 64 || pend != 0 || req_v != 0) begin
    @(posedge clk); cycles=cycles+1; if (cycles > 4000000) $fatal(1, "FATAL: liveness");
    for (d=0; d<2; d=d+1) begin                  // handshakes at this edge (pre-edge values)
     if (rsp_v[d] && rsp_rdy[d]) begin
      if (jj[d] - 1 < 64) begin
       if (rsp_tag[d*16 +: 16] !== 16'(jj[d]-1 + d*1024) || rsp_we[d] !== (ph==0) || rsp_last[d] !== 1'b1 ||
           rsp_data[d*256 +: 256] !== (ph==0 ? 256'd0 : pat((jj[d]-1 + d) % 4, d, jj[d]-1)))
         $fatal(1, "FATAL: lane %0d response mismatch j=%0d tag=%h", d, jj[d]-1, rsp_tag[d*16 +: 16]);
      end
      pend[d]=0; done_n = done_n + 1;
     end
     acc[d] = req_v[d] && req_rdy[d];
    end
    @(negedge clk);
    for (d=0; d<2; d=d+1) begin
     if (acc[d]) begin req_v[d]=0; pend[d]=1; end
     rsp_rdy[d] = pend[d] && ($random & 1);
     if (!req_v[d] && !pend[d] && jj[d] < (ph == 0 && d == 0 ? 64 + 256 : 64)) begin
      req_v[d]=1; req_we[d]=(ph==0); req_len[d*4 +: 4]=4'd1;
      if (jj[d] < 64) begin
       req_addr[d*37 +: 37]=adr(d, jj[d]); req_tag[d*16 +: 16]=16'(jj[d] + d*1024);
       req_wdata[d*256 +: 256]=pat((jj[d] + d) % 4, d, jj[d]);
      end else begin
       req_addr[d*37 +: 37]={2'd1, 35'((REGION + jj[d] - 64) * 32)}; req_tag[d*16 +: 16]=16'hffff;
       req_wdata[d*256 +: 256]=rpat(REGION + jj[d] - 64);
      end
      jj[d]=jj[d]+1;
     end
    end
   end
  end
  if (done_n != 256 + 256) $fatal(1, "FATAL: %0d of 512 transactions completed", done_n);
  // ---------------- phase 2: random bursts, both lanes, up to NO outstanding a lane; phase 3: the fetch stream
  for (ph=2; ph<4; ph=ph+1) begin
   for (d=0; d<2; d=d+1) begin eq_h[d]=0; eq_n[d]=0; eb[d]=0; nreq[d]=0; end
   burst_n = (ph == 2) ? 200 : 32; rsp_n = 0; t_first = -1; req_v = 0; req_we = 0; lastp = cycles;
   while (nreq[0] < (ph == 2 ? burst_n : 0) || nreq[1] < burst_n || eq_n[0] != 0 || eq_n[1] != 0 || req_v != 0) begin
    @(posedge clk); cycles=cycles+1;
    if (rsp_v != 0 || req_v != 0 && (req_v & req_rdy) != 0) lastp = cycles;
    if (cycles - lastp > 20000) begin
     $display("STALL phase %0d: lane outstanding %0d / %0d, lane cnt %0d / %0d, req_v %b", ph, eq_n[0], eq_n[1],
              dut.g_lane[0].l_cnt_dbg, dut.g_lane[1].l_cnt_dbg, req_v);
     $display("  stack1 rqn %0d fn %0d hact %0d rem %0d rsticky %0d n_rdy %0d n_rsp_v %0d | boundary fn %0d nr %h nrv %h busy %h",
              dut.g_st[1].rqn, dut.g_st[1].fn, dut.g_st[1].hact, dut.g_st[1].rem, dut.g_st[1].rsticky, dut.g_st[1].n_rdy,
              dut.g_st[1].n_rsp_v, g_st[1].service.u_native.fn, g_st[1].service.u_native.nr, g_st[1].service.u_native.nrv,
              g_st[1].service.u_native.native_busy);
     $display("  head pc %0d len %0d fh %0d; kport head lane %0d tag %h len %0d bt %0d",
              g_st[1].service.u_native.pc_q, g_st[1].service.u_native.len_q, g_st[1].service.u_native.fh,
              dut.g_st[1].fh_[24:23], dut.g_st[1].fh_[22:7], dut.g_st[1].fh_[6:3], dut.g_st[1].bt);
     for (k = 0; k < 32; k = k + 1) if (g_st[1].service.u_native.native_busy[k]) $display("  busy PC %0d k_v %0d k_rdy %0d kr_v %0d kr_rdy %0d",
       k, g_st[1].k_v[k], g_st[1].k_rdy[k], g_st[1].kr_v[k], g_st[1].kr_rdy[k]);
     $display("  lease19 state %0d reply_full %0d received %0d len %0d kr_tag %h tag_q %h kr_beat %0d sticky %0d",
       g_st[1].service.u_native.pc[19].u_lease.on.state, g_st[1].service.u_native.pc[19].u_lease.on.reply_full,
       g_st[1].service.u_native.pc[19].u_lease.on.received_q, g_st[1].service.u_native.pc[19].u_lease.on.len_q,
       g_st[1].kr_tag[19*17 +: 17], g_st[1].service.u_native.pc[19].u_lease.on.tag_q, g_st[1].kr_beat[19*4 +: 4],
       g_st[1].service.u_native.pc[19].u_lease.on.sticky);
     $fatal(1, "FATAL: liveness (burst phase %0d)", ph);
    end
    for (d=0; d<2; d=d+1) begin
     if (rsp_v[d] && rsp_rdy[d]) check_burst_rsp(d);
     acc[d] = req_v[d] && req_rdy[d];
    end
    @(negedge clk);
    for (d=0; d<2; d=d+1) begin
     if (acc[d]) begin
      req_v[d]=0;
      eq_s[d][(eq_h[d]+eq_n[d])%64] = req_addr[d*37 +: 35] / 32 % 65536; eq_l[d][(eq_h[d]+eq_n[d])%64] = req_len[d*4 +: 4];
      eq_t[d][(eq_h[d]+eq_n[d])%64] = req_tag[d*16 +: 16]; eq_n[d] = eq_n[d] + 1; nreq[d] = nreq[d] + 1;
      if (t_first < 0) t_first = cycles;
     end
     rsp_rdy[d] = (ph == 3) ? 1'b1 : ($random & 3) != 0;
     if (!req_v[d] && eq_n[d] < 2 * NO && nreq[d] < (ph == 2 || d == 1 ? burst_n : 0)) begin
      integer L, off;
      if (ph == 2) begin L = 1 + ($urandom % 8); off = $urandom % (256 - L + 1); end
      else begin L = 8; off = nreq[d] * 8; end
      req_v[d]=1; req_we[d]=0; req_len[d*4 +: 4]=4'(L); req_addr[d*37 +: 37]={2'd1, 35'((REGION + off) * 32)};
      req_tag[d*16 +: 16]=16'(ph * 4096 + d * 1024 + nreq[d]);
     end
    end
   end
   if (ph == 2) $display("BURSTS lanes=2 bursts=400 sectors=%0d (lengths 1..8, up to %0d outstanding a lane): exact", rsp_n, NO);
   else begin
    $display("FETCH_RATE sectors=%0d cycles=%0d rate=%0.3f B/cycle RTT=%0d cycles (NO %0d NQ %0d RB %0d CH %0d, extra PHY latency %0d ps; gate >= %0.3f)",
             rsp_n, t_last - t_first + 1, 32.0 * rsp_n / (t_last - t_first + 1), t_rsp1 - t_first, NO, NQ, RB, CH, XLAT,
             RATE_MIN / 1000.0);
    if (32000 * rsp_n / (t_last - t_first + 1) < RATE_MIN) $fatal(1, "FATAL: fetch rate below the gate");
   end
  end
  if (fault || placed_bad || row_bad) $fatal(1, "FATAL: fault=%0d placement errors=%0d row-boundary errors=%0d", fault, placed_bad, row_bad);
  $display("PASS HFD-LOADER-KPORT lanes=2 stacks=4 transactions=512 (384 writes / 128 reads) + 400 bursts + fetch stream cycles=%0d", cycles);
  $finish;
 end
endmodule
