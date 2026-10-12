`timescale 1ns/1ps
// el1011-hbm-hcvm/vm: lockstep of the tiled VM (ot_hgi_vm_tunit) against the current ot_hgi_vm_unit at the die VM's
// configuration (ot_hgi_vm_die u_vmu: NC 9, WP 32, WDIRECT 1, RP 96, W2 96, LQ 32, AP 1) or any reduced one.
// The tunit's hub sees cq 2, wq / rq / w2q 3 and ap_cr / ap_done 1 cycle(s) late, so the unit is fed those inputs
// delayed; every tunit output is then the unit's shifted (XR = the tunit's extra relay stage): cr +8+2XR (valid always,
// payload when valid), status +9+2XR, wq_done +4+XR, wq_rdy +2, ap_q +1 (valid always, payload when valid), rq_cr +2+XR,
// rr +4+XR (valid always, data when valid), w2q_cr +2+XR, w2q_done +4+XR.
// Stimulus: random packet clients (outstanding count from the tunit's responses; up to 6 on client 5 in one window ->
// station overflow), random DMA lanes (VM sectors of the lane's bank, aperture sectors under wq_rdy, one misrouted
// lane late), read / W2 lanes under their credits (rq_cr / w2q_cr from the tunit; one misrouted read lane late), an HC
// aperture model returning ap_done / ap_cr 1-6 cycles after each ap_q sector, out-of-range packet addresses late.
// MUTS != 0 builds the tunit with that mutant: the lockstep must FAIL.
module tb_hgi_vm_tunit_full_lock;
 parameter integer NC = 9, RP = 96, W2 = 96, LQ = 32, AP = 1, XR = 1, MUTS = 0, NCYC = 6000;
 localparam integer WP = 32, RPL = RP > 0 ? RP : 1, W2L = W2 > 0 ? W2 : 1, WQW = 280 + AP;
 localparam integer KQ = 2, KW = 3, KA = 1, H = 16;
 localparam integer ER = 8 + 2*XR, ES = 9 + 2*XR, EW = 4 + XR, EY = 2, EA = 1, ERC = 2 + XR, ERR = 4 + XR, E2C = 2 + XR, E2D = 4 + XR;
 reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
 reg [NC*338-1:0] cq = 0; reg [WP*WQW-1:0] wq = 0; reg [RPL*16-1:0] rq = 0; reg [W2L*280-1:0] w2q = 0;
 reg [7:0] apcr = 0, apdn = 0;
 reg [NC*338-1:0] cqd [1:KQ]; reg [WP*WQW-1:0] wqd [1:KW]; reg [RPL*16-1:0] rqd [1:KW]; reg [W2L*280-1:0] w2qd [1:KW];
 reg [7:0] apcrd, apdnd;
 wire [NC*274-1:0] cr_a, cr_b; wire [18:0] st_a, st_b; wire [WP-1:0] wd_a, wd_b, wr_a, wr_b;
 wire [8*278-1:0] aq_a, aq_b; wire [RPL-1:0] rc_a, rc_b; wire [RPL*257-1:0] rr_a, rr_b;
 wire [W2L-1:0] w2c_a, w2c_b, w2d_a, w2d_b;
 ot_hgi_vm_tunit #(.NC(NC), .WP(WP), .WDIRECT(1), .RP(RP), .W2(W2), .LQ(LQ), .AP(AP), .XR(XR), .MUT(MUTS)) dut (.clk(clk), .rst_n(rst_n),
   .cq(cq), .cr(cr_a), .status(st_a), .wq(wq), .wq_done(wd_a), .wq_rdy(wr_a), .ap_q(aq_a), .ap_cr(apcr), .ap_done(apdn),
   .rq(rq), .rq_cr(rc_a), .rr(rr_a), .w2q(w2q), .w2q_cr(w2c_a), .w2q_done(w2d_a));
 ot_hgi_vm_unit #(.NC(NC), .WP(WP), .WDIRECT(1), .RP(RP), .W2(W2), .LQ(LQ), .AP(AP)) ref_ (.clk(clk), .rst_n(rst_n),
   .cq(cqd[KQ]), .cr(cr_b), .status(st_b), .wq(wqd[KW]), .wq_done(wd_b), .wq_rdy(wr_b), .ap_q(aq_b), .ap_cr(apcrd), .ap_done(apdnd),
   .rq(rqd[KW]), .rq_cr(rc_b), .rr(rr_b), .w2q(w2qd[KW]), .w2q_cr(w2c_b), .w2q_done(w2d_b));
 reg [NC*274-1:0] hcr [0:H-1]; reg [18:0] hst [0:H-1]; reg [WP-1:0] hwd [0:H-1], hwr [0:H-1]; reg [8*278-1:0] haq [0:H-1];
 reg [RPL-1:0] hrc [0:H-1]; reg [RPL*257-1:0] hrr [0:H-1]; reg [W2L-1:0] h2c [0:H-1], h2d [0:H-1];
 integer out [0:NC-1]; integer rqc [0:RPL-1]; integer w2c [0:W2L-1]; integer hcd [0:7];
 integer cyc = 0, nrsp = 0, nreq = 0, seed = 11, errs = 0, ovf = 0, nwr = 0, nrd = 0, nwq = 0, nap = 0, napq = 0;
 integer nrq = 0, nrr = 0, nw2 = 0, nw2d = 0;
 reg [31:0] rs = 32'h2545F491;                               // xorshift32 (simulator-independent stimulus)
 function automatic [31:0] rnd(input integer dummy);
  begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 17); rs = rs ^ (rs << 5); rnd = rs; end
 endfunction
 task automatic miss(input [8*12-1:0] what, input integer i);
  begin errs = errs + 1; if (errs < 8) $display("MISMATCH %0s cyc %0d idx %0d", what, cyc, i); end
 endtask
 initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 11; rs = 32'h2545F491 ^ seed; $display("SEED=%0d NC=%0d RP=%0d W2=%0d AP=%0d MUTS=%0d", seed, NC, RP, W2, AP, MUTS); end
 initial begin
  for (integer c = 0; c < NC; c = c + 1) out[c] = 0;
  for (integer l = 0; l < RPL; l = l + 1) rqc[l] = LQ;
  for (integer l = 0; l < W2L; l = l + 1) w2c[l] = LQ;
  for (integer k = 0; k < 8; k = k + 1) hcd[k] = 0;
  for (integer k = 1; k <= KQ; k = k + 1) cqd[k] = 0;
  for (integer k = 1; k <= KW; k = k + 1) begin wqd[k] = 0; rqd[k] = 0; w2qd[k] = 0; end
  apcrd = 0; apdnd = 0;
 end
 always @(negedge clk) if (rst_n) begin
  cyc = cyc + 1;
  for (integer k = H - 1; k > 0; k = k - 1) begin
   hcr[k] = hcr[k-1]; hst[k] = hst[k-1]; hwd[k] = hwd[k-1]; hwr[k] = hwr[k-1]; haq[k] = haq[k-1];
   hrc[k] = hrc[k-1]; hrr[k] = hrr[k-1]; h2c[k] = h2c[k-1]; h2d[k] = h2d[k-1];
  end
  hcr[0] = cr_b; hst[0] = st_b; hwd[0] = wd_b; hwr[0] = wr_b; haq[0] = aq_b; hrc[0] = rc_b; hrr[0] = rr_b; h2c[0] = w2c_b; h2d[0] = w2d_b;
  if (cyc > H) begin
   for (integer c = 0; c < NC; c = c + 1) begin : cmp
    reg [273:0] a, b; a = cr_a[c*274 +: 274]; b = hcr[ER][c*274 +: 274];
    if (a[273] !== b[273] || (b[273] && a[272:0] !== b[272:0])) miss("cr", c);
   end
   if (st_a !== hst[ES]) miss("status", 0);
   if (wd_a !== hwd[EW]) miss("wq_done", 0);
   if (wr_a !== hwr[EY]) miss("wq_rdy", 0);
   for (integer k = 0; k < 8; k = k + 1) begin : cap
    reg [277:0] a, b; a = aq_a[k*278 +: 278]; b = haq[EA][k*278 +: 278];
    if (a[277] !== b[277] || (b[277] && a !== b)) miss("ap_q", k);
   end
   if (rc_a !== hrc[ERC]) miss("rq_cr", 0);
   for (integer l = 0; l < RPL; l = l + 1) begin : crr_
    reg [256:0] a, b; a = rr_a[l*257 +: 257]; b = hrr[ERR][l*257 +: 257];
    if (a[256] !== b[256] || (b[256] && a !== b)) miss("rr", l);
   end
   if (w2c_a !== h2c[E2C]) miss("w2q_cr", 0);
   if (w2d_a !== h2d[E2D]) miss("w2q_done", 0);
  end
  // tunit outputs drive the clients' bookkeeping
  for (integer c = 0; c < NC; c = c + 1) if (cr_a[c*274 + 273]) begin out[c] = out[c] - 1; nrsp = nrsp + 1; end
  for (integer l = 0; l < RPL; l = l + 1) begin if (RP > 0 && rc_a[l]) rqc[l] = rqc[l] + 1; if (RP > 0 && rr_a[l*257 + 256]) nrr = nrr + 1; end
  for (integer l = 0; l < W2L; l = l + 1) begin if (W2 > 0 && w2c_a[l]) w2c[l] = w2c[l] + 1; if (W2 > 0 && w2d_a[l]) nw2d = nw2d + 1; end
  apcrd = apcr; apdnd = apdn;                                         // the unit sees them 1 cycle later
  // HC aperture model: each ap_q sector -> ap_done + ap_cr 1-6 cycles later
  apcr = 0; apdn = 0;
  for (integer k = 0; k < 8; k = k + 1) begin
   if (hcd[k] > 0) begin hcd[k] = hcd[k] - 1; if (hcd[k] == 0) begin apcr[k] = 1'b1; apdn[k] = 1'b1; end end
   if (AP != 0 && aq_a[k*278 + 277]) begin hcd[k] = 1 + ($unsigned(rnd(0)) % 6); napq = napq + 1; end
  end
  for (integer k = KQ; k > 1; k = k - 1) cqd[k] = cqd[k-1]; cqd[1] = cq;
  for (integer k = KW; k > 1; k = k - 1) begin wqd[k] = wqd[k-1]; rqd[k] = rqd[k-1]; w2qd[k] = w2qd[k-1]; end
  wqd[1] = wq; rqd[1] = rq; w2qd[1] = w2q;
  cq = 0; wq = 0; rq = 0; w2q = 0;
  if (cyc > 12 && cyc < NCYC) begin
   for (integer c = 0; c < NC; c = c + 1) begin
    integer lim; lim = (cyc > 3000 && cyc < 3100 && c == 5) ? 6 : 4;
    if (out[c] < lim && (rnd(0) & 1)) begin : rqb
     reg [336:0] q; reg [14:0] sec;
     sec = $unsigned(rnd(0)) % 2048;
     q = {rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), rnd(0), rnd(0),
          rnd(0), rnd(0), rnd(0)};
     q[335:304] = {12'd0, sec, 5'd0};
     q[336] = rnd(0) & 1;                                                       // half reads
     if (cyc > NCYC - 400 && c == 2 && (rnd(0) & 7) == 0) q[335:324] = 12'h001;   // out of range (late)
     q[47:16] = (rnd(0) & 1) ? 32'hFFFFFFFF : {rnd(0)} & 32'hF0F0FF0F;
     if (q[336]) nwr = nwr + 1; else nrd = nrd + 1;
     cq[c*338 +: 338] = {1'b1, q}; out[c] = out[c] + 1; nreq = nreq + 1;
     if (out[c] > 4) ovf = ovf + 1;
    end
   end
   for (integer p = 0; p < WP; p = p + 1) if ((rnd(0) & 3) == 0 && wr_a[p]) begin : dl
    reg [WQW-1:0] w; reg isap;
    isap = (AP != 0) && ((rnd(0) & 15) == 0);
    w = '0;
    w[0 +: 264] = {{8{rnd(0)}}, 8'(rnd(0))};
    w[264 +: 15] = isap ? 15'($unsigned(rnd(0)) % 8192) : 15'(p + 32 * ($unsigned(rnd(0)) % 64));
    if (AP != 0) w[279] = isap;
    w[WQW-1] = 1'b1;
    if (!isap && cyc > NCYC - 300 && p == 7 && cyc % 97 == 0) w[264 +: 5] = 5'd9;          // misrouted lane (late)
    wq[p*WQW +: WQW] = w; nwq = nwq + 1; if (isap) nap = nap + 1;
   end
   for (integer l = 0; l < RP; l = l + 1) if (rqc[l] > 0 && (rnd(0) & 1)) begin
    reg [14:0] s; s = 15'((l % 32) + 32 * ($unsigned(rnd(0)) % 1024));
    if (cyc == NCYC - 200 && l == 40) s[4:0] = 5'd3;                                     // misrouted read lane (late)
    rq[l*16 +: 16] = {1'b1, s}; rqc[l] = rqc[l] - 1; nrq = nrq + 1;
   end
   for (integer l = 0; l < W2; l = l + 1) if (w2c[l] > 0 && (rnd(0) & 3) == 0) begin
    reg [14:0] s; s = 15'((l % 32) + 32 * ($unsigned(rnd(0)) % 1024));
    w2q[l*280 +: 280] = {1'b1, s, {8{rnd(0)}}, 8'(rnd(0))}; w2c[l] = w2c[l] - 1; nw2 = nw2 + 1;
   end
  end
 end
 initial begin
  repeat (3) @(negedge clk); rst_n = 1;
  repeat (NCYC + 80) @(negedge clk);
  if (errs == 0 && nrsp > 1000 && st_a[18] && st_a[17] && (RP == 0 || nrr > 1000) && (W2 == 0 || nw2d > 1000) && (AP == 0 || napq > 100))
   $display("PASS VM tunit full lockstep: %0d requests (%0d rd %0d wr) %0d responses, %0d wide (%0d aperture, %0d ap_q), %0d lane reads %0d rr, %0d W2 writes %0d done, %0d overflow pushes, status %h",
            nreq, nrd, nwr, nrsp, nwq, nap, napq, nrq, nrr, nw2, nw2d, ovf, st_a);
  else $display("FATAL lockstep errs %0d nrsp %0d nrr %0d nw2d %0d napq %0d status %h", errs, nrsp, nrr, nw2d, napq, st_a);
  $finish;
 end
endmodule
