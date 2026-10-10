`timescale 1ps/1ps
// hbm-phys [svc] 2026-10-10: bench of the svc DMA stream v2 (ot_svd_stack: request unit, 32 PC units, 8 group units)
// against tb_svd_phy (32 in-order PC models: latency LAT_MIN + rand(LAT_SPAN) from a read's acceptance, the PC's
// bandwidth RATE_PPM sectors a cycle (0.7716 = 3.80 TB/s a die / 4 stacks / 32 PCs at 1.2 GHz), a beat held while the
// PC's kr_rdy is low) and a front model (requests {tag, nsec, addr}, 16 tags, a tag reused only after all its sectors;
// per-lane credits CR0 returned CRD cycles after the beat = the front's land/pop/credit cycles + 2 x die hops).
// Scoreboard: every sector of every request arrives exactly once, on the lane of the PC that stores it, with the
// PHY's data, never without a credit, no X on a valid lane.  BW: 256-sector requests back to back; steady rate over
// the 10..90 % beats against the PHY's offered 32 x RATE.
//   +define+NREQ, NTAG (tags the front gives this stack, <= 16), BW, LAT_MIN, LAT_SPAN, CR0, CRD, RATE_PPM, RH, PH, TMO
`ifndef NREQ
  `define NREQ 400
`endif
`ifndef LAT_MIN
  `define LAT_MIN 20
`endif
`ifndef LAT_SPAN
  `define LAT_SPAN 40
`endif
`ifndef CR0
  `define CR0 32
`endif
`ifndef CRD
  `define CRD 25
`endif
`ifndef RATE_PPM
  `define RATE_PPM 771600
`endif
`ifndef RH
  `define RH 1
`endif
`ifndef PH
  `define PH 3
`endif
`ifndef MF
  `define MF 32
`endif
`ifndef QD
  `define QD 16
`endif
`ifndef NTAG
  `define NTAG 16
`endif
`ifndef TMO
  `define TMO 400000
`endif

module tb_svd_phy #(parameter integer LAT_MIN = 20, parameter integer LAT_SPAN = 40, parameter integer RATE_PPM = 771600) (
  input wire ck, input wire rn,
  input wire [31:0] k_v, output reg [31:0] k_rdy, input wire [32*30-1:0] k_addr, input wire [32*4-1:0] k_len,
  input wire [32*17-1:0] k_tag,
  output reg [31:0] kr_v, input wire [31:0] kr_rdy, output reg [32*17-1:0] kr_tag, output reg [32*4-1:0] kr_beat,
  output reg [32*256-1:0] kr_data,
  output integer nstall, output integer nerr);
  function automatic [255:0] f(input [31:0] a);
    integer j; reg [31:0] x;
    begin x = a * 32'h9e3779b1 ^ 32'h1234567;
      for (j = 0; j < 8; j = j + 1) begin x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); f[j*32 +: 32] = x ^ a; end
    end
  endfunction
  reg [29:0] qa [0:31][0:63]; reg [16:0] qt [0:31][0:63]; integer qr [0:31][0:63];
  integer qh [0:31], qn [0:31], bc [0:31], tok [0:31], cyc;
  integer pc;
  initial begin cyc = 0; nstall = 0; nerr = 0; for (pc = 0; pc < 32; pc = pc + 1) begin qh[pc] = 0; qn[pc] = 0; bc[pc] = 0; tok[pc] = 0; end
    k_rdy = 0; kr_v = 0; kr_tag = 0; kr_beat = 0; kr_data = 0; end
  always @(posedge ck) if (rn) begin
    cyc = cyc + 1;
    for (pc = 0; pc < 32; pc = pc + 1) begin
      if (k_v[pc] && k_rdy[pc]) begin
        if (k_len[pc*4 +: 4] != 4'd4) begin nerr = nerr + 1; $display("ERR PC %0d len %0d", pc, k_len[pc*4 +: 4]); end
        if ((k_addr[pc*30+2 +: 5] ^ k_addr[pc*30+7 +: 5] ^ k_addr[pc*30+12 +: 5]) != 5'(pc)) begin nerr = nerr + 1;
          $display("ERR PC %0d got a row of another PC", pc); end
        qa[pc][(qh[pc] + qn[pc]) % 64] = k_addr[pc*30 +: 30]; qt[pc][(qh[pc] + qn[pc]) % 64] = k_tag[pc*17 +: 17];
        qr[pc][(qh[pc] + qn[pc]) % 64] = cyc + LAT_MIN + (LAT_SPAN > 0 ? ($urandom % LAT_SPAN) : 0);
        qn[pc] = qn[pc] + 1;
      end
      k_rdy[pc] <= qn[pc] < 56;
      // bandwidth: RATE_PPM / 1e6 sectors a cycle, at most 2 beats banked
      tok[pc] = tok[pc] + RATE_PPM; if (tok[pc] > 2000000) tok[pc] = 2000000;
      if (kr_v[pc] && !kr_rdy[pc]) nstall = nstall + 1;                 // beat held: the svc is not ready
      else begin
        kr_v[pc] <= 1'b0;
        if (qn[pc] > 0 && cyc >= qr[pc][qh[pc]] && tok[pc] >= 1000000) begin
          tok[pc] = tok[pc] - 1000000;
          kr_v[pc] <= 1'b1; kr_tag[pc*17 +: 17] <= qt[pc][qh[pc]]; kr_beat[pc*4 +: 4] <= bc[pc][3:0];
          kr_data[pc*256 +: 256] <= f({2'b00, qa[pc][qh[pc]]} + bc[pc]);
          bc[pc] = bc[pc] + 1;
          if (bc[pc] == 4) begin bc[pc] = 0; qh[pc] = (qh[pc] + 1) % 64; qn[pc] = qn[pc] - 1; end
        end
      end
    end
  end
endmodule

module tb_svd2_stack;
  localparam integer TCK = 1000;
  reg ck = 0, rn = 0;
  always #(TCK/2) ck = ~ck;
  function automatic [255:0] f(input [31:0] a);
    integer j; reg [31:0] x;
    begin x = a * 32'h9e3779b1 ^ 32'h1234567;
      for (j = 0; j < 8; j = j + 1) begin x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); f[j*32 +: 32] = x ^ a; end
    end
  endfunction
  reg [50:0] dq = 0; wire dq_rdy; wire [32*270-1:0] dd; reg [31:0] dd_cr = 0;
  wire [31:0] k_v, k_rdy, kr_v, kr_rdy; wire [32*30-1:0] k_addr; wire [32*4-1:0] k_len, kr_beat; wire [32*17-1:0] k_tag, kr_tag;
  wire [32*256-1:0] kr_data; wire [7:0] ovf; integer nstall, perr;
  ot_svd_stack #(.CR0(`CR0), .RH(`RH), .PH(`PH), .MF(`MF), .QD(`QD)) u_s (.ck(ck), .rn(rn), .dq(dq), .dq_rdy(dq_rdy), .dd(dd), .dd_cr(dd_cr),
    .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .kr_v(kr_v), .kr_rdy(kr_rdy), .kr_tag(kr_tag),
    .kr_beat(kr_beat), .kr_data(kr_data), .ovf(ovf));
  tb_svd_phy #(.LAT_MIN(`LAT_MIN), .LAT_SPAN(`LAT_SPAN), .RATE_PPM(`RATE_PPM)) u_phy (.ck(ck), .rn(rn), .k_v(k_v), .k_rdy(k_rdy),
    .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .kr_v(kr_v), .kr_rdy(kr_rdy), .kr_tag(kr_tag), .kr_beat(kr_beat),
    .kr_data(kr_data), .nstall(nstall), .nerr(perr));
  // ------------------------------------------------------------------ front model
  reg [15:0] tbusy = 0; integer tleft [0:15]; reg [29:0] ts [0:15]; reg [8:0] tn [0:15]; reg [255:0] tgot [0:15];
  integer nreq = 0, nacc = 0, k, l, err = 0, beats = 0, want = 0, cyc = 0, t0 = 0, t1 = 0, ta = 0, tb = 0;
  integer crd [0:31];
  initial for (l = 0; l < 32; l = l + 1) crd[l] = `CR0;
  always @(posedge ck) if (rn) begin : gen
    integer t, ft; reg [29:0] s; reg [8:0] n;
    cyc = cyc + 1;
    if (dq[50] && dq_rdy) begin dq[50] <= 1'b0; nacc = nacc + 1; end
    if ((!dq[50] || dq_rdy) && nreq < `NREQ) begin
      ft = -1; for (t = `NTAG - 1; t >= 0; t = t - 1) if (!tbusy[t]) ft = t;
`ifdef BW
      if (ft >= 0) begin
        n = 9'd256;
`else
      if (ft >= 0 && ($urandom % 8) != 0) begin
        n = (($urandom % 4) == 0) ? 9'(1 + ($urandom % 16)) : (($urandom % 3) == 0) ? 9'd256 : 9'(1 + ($urandom % 256));
`endif
        s = ($urandom % 2) ? 30'($urandom) : 30'(($urandom % 4096) * 4);
        if ({1'b0, s} + 31'(n) > 31'h3fffffff) s = 30'd0;
        dq <= {1'b1, 4'(ft), n, 2'b00, s, 5'd0};
        tbusy[ft] = 1'b1; tleft[ft] = n; ts[ft] = s; tn[ft] = n; tgot[ft] = 256'd0; nreq = nreq + 1; want = want + n;
        if (nreq == 8) t0 = cyc;
      end
    end
  end
  // lanes: scoreboard + credits (returned CRD cycles after the beat)
  reg [31:0] crq [0:255]; integer cri = 0;
  always @(posedge ck) if (rn) begin : sb
    reg [269:0] b; reg [31:0] cr_now; reg [3:0] tg; reg [7:0] ix; reg [29:0] sa; reg [27:0] rw;
    cr_now = 32'd0;
    for (l = 0; l < 32; l = l + 1) begin
      b = dd[l*270 +: 270];
      if (b[269] === 1'bx) begin err = err + 1; if (err < 10) $display("ERR X valid on lane %0d", l); end
      if (b[269] === 1'b1) begin
        if (^b === 1'bx) begin err = err + 1; if (err < 10) $display("ERR X on lane %0d", l); end
        if (crd[l] == 0) begin err = err + 1; $display("ERR lane %0d beat without a credit", l); end
        crd[l] = crd[l] - 1; cr_now[l] = 1'b1;
        tg = b[267:264]; ix = b[263:256];
        if (!tbusy[tg] || {1'b0, ix} >= tn[tg] || tgot[tg][ix]) begin
          err = err + 1; if (err < 20) $display("ERR lane %0d: tag %0d idx %0d not expected (busy %0d nsec %0d dup %0d)", l, tg, ix,
                                               tbusy[tg], tn[tg], tgot[tg][ix]);
        end else begin
          sa = ts[tg] + 30'(ix); rw = sa[29:2];
          if ((rw[4:0] ^ rw[9:5] ^ rw[14:10]) != 5'(l)) begin err = err + 1; if (err < 20) $display("ERR lane %0d carries a sector of PC %0d", l, rw[4:0] ^ rw[9:5] ^ rw[14:10]); end
          if (b[255:0] !== f({2'b00, sa}) || b[268]) begin err = err + 1; if (err < 20) $display("ERR lane %0d tag %0d idx %0d data", l, tg, ix); end
          tgot[tg][ix] = 1'b1; tleft[tg] = tleft[tg] - 1;
          if (tleft[tg] == 0) tbusy[tg] = 1'b0;
        end
        beats = beats + 1; t1 = cyc;
        if (beats == `NREQ * 256 / 10) ta = cyc;
        if (beats == `NREQ * 256 * 9 / 10) tb = cyc;
      end
    end
    crq[(cri + `CRD) % 256] = cr_now;
    dd_cr <= crq[cri % 256]; for (l = 0; l < 32; l = l + 1) if (crq[cri % 256][l]) crd[l] = crd[l] + 1;
    crq[cri % 256] = 32'd0; cri = cri + 1;
    if (ovf != 0) begin err = err + 1; $display("ERR group overflow %b", ovf); end
  end
  initial begin
    for (k = 0; k < 256; k = k + 1) crq[k] = 32'd0;
    repeat (4) @(posedge ck); rn = 1;
    begin : wait_done
      forever begin
        @(posedge ck);
        if (nreq == `NREQ && beats == want) disable wait_done;
        if (cyc > `TMO) begin $display("ERR timeout: beats %0d / %0d, requests %0d accepted %0d", beats, want, nreq, nacc);
          err = err + 1; disable wait_done; end
      end
    end
    repeat (50) @(posedge ck);
    err = err + perr;
    $display("SVD2_STACK requests=%0d sectors=%0d cycles=%0d rate=%0.3f sectors/cycle phy_stall_beats=%0d errors=%0d", nreq, beats,
             t1 - t0, (1.0 * beats) / (t1 - t0 + 1), nstall, err);
`ifdef BW
    $display("SVD2_STACK steady rate=%0.3f sectors/cycle = %0.1f B/cycle a stack = %0.1f %% of the PHY's %0.2f (gate: >= 22.3 sectors/cycle)",
             (0.8 * `NREQ * 256) / (tb - ta), 32.0 * (0.8 * `NREQ * 256) / (tb - ta),
             100.0 * (0.8 * `NREQ * 256) / (tb - ta) / (32.0 * `RATE_PPM / 1.0e6), 32.0 * `RATE_PPM / 1.0e6);
`endif
    if (err != 0) $fatal(1, "SVD2_STACK FAIL");
    $display("SVD2_STACK PASS");
    $finish;
  end
endmodule
