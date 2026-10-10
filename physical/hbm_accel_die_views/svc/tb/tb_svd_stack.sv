`timescale 1ps/1ps
// hbm-forks 2026-10-10: stack-level bench of the svc DMA stream (ot_hbm_svc_dma_lib.sv hub + the DMA paths of
// ot_svs_grp / ot_svs_pcs): one hub, 8 group units on the command / inward chains (wire stages between them), 32 PC
// units with a request-level PHY model each (in order a PC, random latency), a front model (random requests: tag,
// nsec 1..256, any sector address; per-lane credits CR returned after a random delay).  Scoreboard: every lane carries
// exactly the sectors idx % 8 == l of every request, in request order and idx order, data = the PHY's sector data, no
// beat without a credit, no X on dd; reports the sector rate in the saturated window.
//   +define+NREQ=<n> requests, LAT_MIN / LAT_SPAN PHY latency, HOPS wire stages between chain nodes, CRD front delay
module tb_svd_stack;
`ifndef NREQ
  `define NREQ 400
`endif
`ifndef LAT_MIN
  `define LAT_MIN 20
`endif
`ifndef LAT_SPAN
  `define LAT_SPAN 40
`endif
`ifndef HOPS
  `define HOPS 3
`endif
`ifndef CRD
  `define CRD 1
`endif
`ifndef CR0
  `define CR0 8
`endif
`ifndef TMO
  `define TMO 400000
`endif
  localparam integer TCK = 1000;
  reg ck = 0, rn = 0;
  always #(TCK/2) ck = ~ck;
  function automatic [255:0] f(input [31:0] a);
    integer j; reg [31:0] x;
    begin x = a * 32'h9e3779b1 ^ 32'h1234567;
      for (j = 0; j < 8; j = j + 1) begin x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); f[j*32 +: 32] = x ^ a; end
    end
  endfunction
  // ------------------------------------------------------------------ hub
  reg [50:0] dq = 0; wire dq_rdy; wire [8*270-1:0] dd; reg [7:0] dd_cr = 0;
  wire [93:0] cmd; wire av, bv; wire [1038:0] ad, bd;
  ot_svd_hub #(.DH(8), .DP(128), .NQ(8), .CR0(`CR0)) u_h (.ck(ck), .rn(rn), .dq(dq), .dq_rdy(dq_rdy), .dd(dd), .dd_cr(dd_cr),
    .cmd(cmd), .av(av), .ad(ad), .bv(bv), .bd(bd));
  // ------------------------------------------------------------------ groups (index 0 nearest the hub)
  wire [7:0] gci_v, gco_v; wire [93:0] gci_d [0:7]; wire [93:0] gco_d [0:7];
  wire [7:0] gai_v, gao_v, gbi_v, gbo_v; wire [1038:0] gai_d [0:7]; wire [1038:0] gao_d [0:7];
  wire [1038:0] gbi_d [0:7]; wire [1038:0] gbo_d [0:7];
  wire [31:0] pdq_v, pdcr_v, gdq_v, gdcr_v; wire [37:0] pdq_d [0:31]; wire [37:0] gdq_d [0:31];
  wire [3:0] pdcr_d [0:31]; wire [3:0] gdcr_d [0:31];
  wire [31:0] bvv, sv_i; wire [276:0] bq [0:31]; wire [276:0] sq_i [0:31];
  genvar g, p;
  generate for (g = 0; g < 8; g = g + 1) begin : gg
    if (g == 0) begin : c0
      ot_svc_vpipe #(.W(94), .N(`HOPS)) u_c (.ck(ck), .rst_n(rn), .v(|{cmd[93], cmd[46]}), .d(cmd), .qv(gci_v[0]), .q(gci_d[0]));
      ot_svc_vpipe #(.W(1039), .N(`HOPS)) u_a (.ck(ck), .rst_n(rn), .v(gao_v[0]), .d(gao_d[0]), .qv(av), .q(ad));
      ot_svc_vpipe #(.W(1039), .N(`HOPS)) u_b (.ck(ck), .rst_n(rn), .v(gbo_v[0]), .d(gbo_d[0]), .qv(bv), .q(bd));
    end else begin : cn
      ot_svc_vpipe #(.W(94), .N(`HOPS)) u_c (.ck(ck), .rst_n(rn), .v(gco_v[g-1]), .d(gco_d[g-1]), .qv(gci_v[g]), .q(gci_d[g]));
      ot_svc_vpipe #(.W(1039), .N(`HOPS)) u_a (.ck(ck), .rst_n(rn), .v(gao_v[g]), .d(gao_d[g]), .qv(gai_v[g-1]), .q(gai_d[g-1]));
      ot_svc_vpipe #(.W(1039), .N(`HOPS)) u_b (.ck(ck), .rst_n(rn), .v(gbo_v[g]), .d(gbo_d[g]), .qv(gbi_v[g-1]), .q(gbi_d[g-1]));
    end
    if (g == 7) begin : ce
      assign gai_v[7] = 1'b0; assign gai_d[7] = 1039'd0; assign gbi_v[7] = 1'b0; assign gbi_d[7] = 1039'd0;
    end
    wire [1101:0] ks; wire [3:0] cr; wire ovf;
    ot_svs_grp #(.K(g), .DMA(1), .DG(4)) u_g (.ck(ck), .rst(rn), .rn(rn), .sv_i(sv_i[4*g +: 4]),
      .sq_i({sq_i[4*g+3], sq_i[4*g+2], sq_i[4*g+1], sq_i[4*g]}), .kq(2'b00), .sg_v(1'b0), .sg_d(13'd0), .cr(cr), .ks(ks),
      .ovf(ovf), .ci_v(gci_v[g]), .ci_d(gci_d[g]), .co_v(gco_v[g]), .co_d(gco_d[g]),
      .dq_v(gdq_v[4*g +: 4]), .dq_d({gdq_d[4*g+3], gdq_d[4*g+2], gdq_d[4*g+1], gdq_d[4*g]}),
      .dcr_v(gdcr_v[4*g +: 4]), .dcr_d({gdcr_d[4*g+3], gdcr_d[4*g+2], gdcr_d[4*g+1], gdcr_d[4*g]}),
      .ai_v(gai_v[g]), .ai_d(gai_d[g]), .ao_v(gao_v[g]), .ao_d(gao_d[g]),
      .bi_v(gbi_v[g]), .bi_d(gbi_d[g]), .bo_v(gbo_v[g]), .bo_d(gbo_d[g]));
    always @(posedge ck) if (rn && ovf) begin $display("ERR group %0d overflow", g); $fatal(1, "SVD_STACK FAIL"); end
  end endgenerate
  // ------------------------------------------------------------------ PCs + PHY models
  reg [31:0] k_rdy = 0; reg [31:0] kr_v = 0; reg [16:0] kr_tag [0:31]; reg [3:0] kr_beat [0:31]; reg [255:0] kr_data [0:31];
  wire [31:0] k_v; wire [29:0] k_addr [0:31]; wire [3:0] k_len [0:31]; wire [16:0] k_tag [0:31];
  generate for (p = 0; p < 32; p = p + 1) begin : pp
    ot_svc_vpipe #(.W(38), .N(2)) u_q (.ck(ck), .rst_n(rn), .v(gdq_v[p]), .d(gdq_d[p]), .qv(pdq_v[p]), .q(pdq_d[p]));
    ot_svc_vpipe #(.W(4), .N(2)) u_r (.ck(ck), .rst_n(rn), .v(gdcr_v[p]), .d(gdcr_d[p]), .qv(pdcr_v[p]), .q(pdcr_d[p]));
    wire b_v; wire [16:0] b_t; wire [3:0] b_b; wire [255:0] b_d; wire do_v, dno_ok, dno_ph; wire [61:0] do_d;
    ot_svs_pcs #(.PCID(p), .DMA(1), .DH(8), .DG(4)) u_p (.ck(ck), .rn(rn), .rdy_q2(1'b1), .iss_v(1'b0), .iss_d(51'd0),
      .k_v(k_v[p]), .k_rdy(k_rdy[p]), .k_addr(k_addr[p]), .k_len(k_len[p]), .k_tag(k_tag[p]),
      .kr_v(kr_v[p]), .kr_tag(kr_tag[p]), .kr_beat(kr_beat[p]), .kr_data(kr_data[p]),
      .b_v(b_v), .b_t(b_t), .b_b(b_b), .b_d(b_d), .di_v(1'b0), .di_d(62'd0), .do_v(do_v), .do_d(do_d),
      .dni_ok(1'b1), .dni_ph(1'b0), .dno_ok(dno_ok), .dno_ph(dno_ph), .cr_v(1'b0),
      .dq_v(pdq_v[p]), .dq_d(pdq_d[p]), .dcr_v(pdcr_v[p]), .dcr_d(pdcr_d[p]));
    ot_svc_vpipe #(.W(277), .N(2)) u_s (.ck(ck), .rst_n(rn), .v(b_v), .d({b_t, b_b, b_d}), .qv(sv_i[p]), .q(sq_i[p]));
  end endgenerate
  // PHY: per PC a queue of reads; in order; latency LAT_MIN + rand(LAT_SPAN) to the first beat, then a beat a cycle
  reg [29:0] qa [0:31][0:31]; reg [16:0] qt [0:31][0:31]; integer qh [0:31], qn [0:31], bc [0:31], lt [0:31];
  integer pc, err = 0;
  initial for (pc = 0; pc < 32; pc = pc + 1) begin qh[pc] = 0; qn[pc] = 0; bc[pc] = 0; lt[pc] = 0; end
  always @(posedge ck) if (rn) begin
    for (pc = 0; pc < 32; pc = pc + 1) begin
      if (k_v[pc] && k_rdy[pc]) begin
        if (k_len[pc] != 4'd4) begin err = err + 1; $display("ERR PC %0d len %0d", pc, k_len[pc]); end
        if ((k_addr[pc][6:2] ^ k_addr[pc][11:7] ^ k_addr[pc][16:12]) != 5'(pc)) begin err = err + 1;
          $display("ERR PC %0d got a row of PC %0d", pc, k_addr[pc][6:2] ^ k_addr[pc][11:7] ^ k_addr[pc][16:12]); end
        qa[pc][(qh[pc] + qn[pc]) % 32] = k_addr[pc]; qt[pc][(qh[pc] + qn[pc]) % 32] = k_tag[pc];
        if (qn[pc] == 0) lt[pc] = `LAT_MIN + ($urandom % `LAT_SPAN);
        qn[pc] = qn[pc] + 1;
      end
      k_rdy[pc] <= qn[pc] < 24;
      kr_v[pc] <= 1'b0;
      if (qn[pc] > 0) begin
        if (lt[pc] > 0) lt[pc] = lt[pc] - 1;
        else begin
          kr_v[pc] <= 1'b1; kr_tag[pc] <= qt[pc][qh[pc]]; kr_beat[pc] <= bc[pc][3:0];
          kr_data[pc] <= f({2'b00, qa[pc][qh[pc]]} + bc[pc]);
          bc[pc] = bc[pc] + 1;
          if (bc[pc] == 4) begin bc[pc] = 0; qh[pc] = (qh[pc] + 1) % 32; qn[pc] = qn[pc] - 1;
            lt[pc] = (qn[pc] > 0) ? ($urandom % 3) : 0; end
        end
      end
    end
  end
  // ------------------------------------------------------------------ front model
  reg [15:0] tbusy = 0; integer tleft [0:15];
  reg [29:0] rs [0:4095]; reg [8:0] rnsec [0:4095]; reg [3:0] rtag [0:4095];   // requests in order
  integer nreq = 0, nacc = 0, k, l;
  integer lr [0:7], li [0:7];                                  // per lane: request index, next idx
  integer crd [0:7];                                           // credits held by the svc (front's view)
  integer beats = 0, want = 0, t0 = 0, t1 = 0, cyc = 0;
  reg rdy_seen;
  initial for (l = 0; l < 8; l = l + 1) begin lr[l] = 0; li[l] = l; crd[l] = `CR0; end
  // request generator: valid held until the front sees dq_rdy (the spec's protocol)
  always @(posedge ck) if (rn) begin : gen
    integer t, ft; reg [29:0] s; reg [8:0] n;
    cyc = cyc + 1;
    if (dq[50] && dq_rdy) begin dq[50] <= 1'b0; nacc = nacc + 1; end
    if ((!dq[50] || dq_rdy) && nreq < `NREQ) begin
      ft = -1; for (t = 15; t >= 0; t = t - 1) if (!tbusy[t]) ft = t;
      if (ft >= 0 && ($urandom % 8) != 0) begin
        n = (($urandom % 4) == 0) ? 9'(1 + ($urandom % 16)) : (($urandom % 3) == 0) ? 9'd256 : 9'(1 + ($urandom % 256));
        s = ($urandom % 2) ? 30'($urandom) : 30'(($urandom % 4096) * 4);
        if ({1'b0, s} + 31'(n) > 31'h3fffffff) s = 30'd0;
        dq <= {1'b1, 4'(ft), n, 2'b00, s, 5'd0};
        tbusy[ft] = 1'b1; tleft[ft] = n; rs[nreq] = s; rnsec[nreq] = n; rtag[nreq] = 4'(ft); nreq = nreq + 1; want = want + n;
        if (nreq == 8) t0 = cyc;
      end
    end
  end
  // lanes: scoreboard + credits
  reg [7:0] crq [0:63]; integer cri = 0;
  always @(posedge ck) if (rn) begin : sb
    reg [269:0] b; integer m; reg [7:0] cr_now;
    cr_now = 8'd0;
    for (l = 0; l < 8; l = l + 1) begin
      b = dd[l*270 +: 270];
      if (^b === 1'bx) begin err = err + 1; if (err < 10) $display("ERR X on lane %0d", l); end
      if (b[269]) begin
        while (lr[l] < nreq && li[l] >= rnsec[lr[l]]) begin lr[l] = lr[l] + 1; li[l] = l; end
        if (crd[l] == 0) begin err = err + 1; $display("ERR lane %0d beat without a credit", l); end
        crd[l] = crd[l] - 1;
        if (lr[l] >= nreq) begin err = err + 1; $display("ERR lane %0d unexpected beat", l); end
        else if (b[267:264] !== rtag[lr[l]] || b[263:256] !== 8'(li[l]) || b[255:0] !== f({2'b00, rs[lr[l]]} + li[l]) || b[268]) begin
          err = err + 1;
          if (err < 20) $display("ERR lane %0d req %0d: got tag %0d idx %0d, want tag %0d idx %0d (data %0s)", l, lr[l], b[267:264],
                                 b[263:256], rtag[lr[l]], li[l], b[255:0] === f({2'b00, rs[lr[l]]} + li[l]) ? "ok" : "BAD");
        end
        tleft[b[267:264]] = tleft[b[267:264]] - 1;
        if (tleft[b[267:264]] == 0) tbusy[b[267:264]] = 1'b0;
        li[l] = li[l] + 8; beats = beats + 1; t1 = cyc;
        cr_now[l] = 1'b1;
      end
    end
    // credit back after CRD cycles
    crq[(cri + `CRD) % 64] = cr_now;
    dd_cr <= crq[cri % 64]; for (l = 0; l < 8; l = l + 1) if (crq[cri % 64][l]) crd[l] = crd[l] + 1;
    crq[cri % 64] = 8'd0; cri = cri + 1;
  end
  initial begin
    for (k = 0; k < 64; k = k + 1) crq[k] = 8'd0;
    repeat (4) @(posedge ck); rn = 1;
    begin : wait_done
      forever begin
        @(posedge ck);
        if (nreq == `NREQ && beats == want) disable wait_done;
        if (cyc > `TMO) begin $display("ERR timeout: beats %0d / %0d, requests %0d accepted %0d", beats, want, nreq, nacc);
          $display("  hub act %0d ik %0d rf_n %0d rqv %b gn %0d gmin %0d", u_h.act, u_h.ik, u_h.rf_n, u_h.rqv, u_h.gn, u_h.gmin);
          for (l = 0; l < 8; l = l + 1) $display("  lane %0d lq %0d li %0d lcr %0d act %0d adv %0d req %0d", l, u_h.lq[l], u_h.li[l], u_h.lcr[l], u_h.lact[l], u_h.ladv[l], u_h.lreq[l]);
          err = err + 1; disable wait_done; end
      end
    end
    repeat (50) @(posedge ck);
    $display("SVD_STACK requests=%0d sectors=%0d cycles=%0d rate=%0.3f sectors/cycle (of 8) errors=%0d", nreq, beats,
             t1 - t0, (1.0 * beats) / (t1 - t0 + 1), err);
    if (err != 0) $fatal(1, "SVD_STACK FAIL");
    $display("SVD_STACK PASS");
    $finish;
  end
endmodule
