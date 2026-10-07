// CLAUDE HBM-ABSTRACTS (svcidx): stream-service view bench body (included by the generated tb_svc_<st>.sv, which
// declares the DUT on these uniform nets, in core SM order k = SM ports by x).  One seed; exits nonzero ($fatal) on
// any mismatch, on a missing / duplicate / unexpected response and on timeout.
//   SM k request (addr, tag) -> line on SM k {v, tag, data} with data = beats 0..3 + beat 4[63:0] of f(addr, beat)
//   e kind 0 (W, lane tag[2:0])  -> line on SM tag[2:0] with the W data f(addr ^ W_SALT, beat)
//   e kind 1 (KV)                -> kv {v, tag13, data1024 = f(addr, 0..3)}
//   e kind 2 (index keys)        -> ik data1024 = f(addr, 0..3)
  localparam integer TCK = 1024, TFW = 833;
  localparam [31:0] W_SALT = 32'h5a5a_0000;
  reg ck = 0, rst = 0, fck = 0;
  always #(TCK/2) ck = ~ck;
  always #(TFW/2) fck = ~fck;
  // uniform DUT-side nets
  reg  [7:0] qv; reg [41:0] qd [0:7]; wire [7:0] qrdy;
  wire [1098:0] ln [0:7];
  reg ev; reg [127:1] ed;
  wire [1037:0] kvo; wire [1023:0] iko;
  wire [22237:0] phy;
  // ---------------------------------------------------------------- PHY stub (request-level K / W ports)
  wire pclk, prst_n;
  wire [31:0] k_v; reg [31:0] k_rdy; wire [959:0] k_addr; wire [127:0] k_len; wire [543:0] k_tag; wire [31:0] k_we;
  wire [8191:0] k_wdata; wire [1023:0] k_wstrb; reg [31:0] k_wr_done = 0;
  reg [31:0] kr_v; wire [31:0] kr_rdy; reg [543:0] kr_tag; reg [127:0] kr_beat; reg [8191:0] kr_data;
  wire w_v; reg w_rdy; wire [23:0] w_addr; wire [5:0] w_len; wire [9:0] w_tag; reg [7:0] w_room;
  reg [7:0] wr_v; wire [7:0] wr_rdy; reg [79:0] wr_tag; reg [39:0] wr_beat; reg [2047:0] wr_data;
  reg k_oor = 0, w_oor = 0; reg [63:0] refreshes = 0; reg [31:0] w_reads = 0;
  tb_svc_physide u_ps (.phy(phy), .clk(pclk), .rst_n(prst_n), .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len),
    .k_tag(k_tag), .k_we(k_we), .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done), .kr_v(kr_v),
    .kr_rdy(kr_rdy), .kr_tag(kr_tag), .kr_beat(kr_beat), .kr_data(kr_data), .w_v(w_v), .w_rdy(w_rdy), .w_addr(w_addr),
    .w_len(w_len), .w_tag(w_tag), .w_room(w_room), .wr_v(wr_v), .wr_rdy(wr_rdy), .wr_tag(wr_tag), .wr_beat(wr_beat),
    .wr_data(wr_data), .k_oor(k_oor), .w_oor(w_oor), .refreshes(refreshes), .w_reads(w_reads));
  function automatic [255:0] f(input [31:0] a, input [4:0] b);
    integer j; reg [31:0] x;
    begin x = a * 32'h9e3779b1 ^ {27'd0, b} * 32'h85ebca6b;
      for (j = 0; j < 8; j = j + 1) begin x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); f[j*32 +: 32] = x ^ a; end
    end
  endfunction
  integer seed = 20261006;
  // per-PC queue of reads: (addr, len, tag, issue time)
  reg [29:0] qa [0:31][0:15]; reg [3:0] ql [0:31][0:15]; reg [16:0] qt [0:31][0:15]; integer qh [0:31], qn [0:31];
  integer bcount [0:31]; integer lat [0:31];
  integer pc, j, k, err = 0;
  initial for (pc = 0; pc < 32; pc = pc + 1) begin qh[pc] = 0; qn[pc] = 0; bcount[pc] = 0; lat[pc] = 0; end
  always @(posedge pclk) begin
    for (pc = 0; pc < 32; pc = pc + 1) begin
      if (k_v[pc] && k_rdy[pc]) begin
        if (k_we[pc]) begin err = err + 1; $display("ERR write on PC %0d", pc); end
        qa[pc][(qh[pc]+qn[pc]) % 16] = k_addr[pc*30 +: 30]; ql[pc][(qh[pc]+qn[pc]) % 16] = k_len[pc*4 +: 4];
        qt[pc][(qh[pc]+qn[pc]) % 16] = k_tag[pc*17 +: 17]; qn[pc] = qn[pc] + 1;
      end
      k_rdy[pc] <= ($urandom % 4) != 0 && qn[pc] < 14;
      // response engine: one beat at a time per PC, in order, random gaps; kr_v held until kr_rdy
      if (kr_v[pc] && kr_rdy[pc]) begin
        kr_v[pc] <= 1'b0; bcount[pc] = bcount[pc] + 1;
        if (bcount[pc] == ql[pc][qh[pc]]) begin bcount[pc] = 0; qh[pc] = (qh[pc] + 1) % 16; qn[pc] = qn[pc] - 1;
          lat[pc] = 2 + ($urandom % 8); end
      end else if (!kr_v[pc] && qn[pc] > 0) begin
        if (lat[pc] > 0) lat[pc] = lat[pc] - 1;
        else if ($urandom % 3 != 0) begin
          kr_v[pc] <= 1'b1; kr_tag[pc*17 +: 17] <= qt[pc][qh[pc]]; kr_beat[pc*4 +: 4] <= bcount[pc][3:0];
          kr_data[pc*256 +: 256] <= f({2'b00, qa[pc][qh[pc]]}, bcount[pc][4:0]);
        end
      end
    end
  end
  // W port: one request at a time per lane, 5 beats on lane tag[2:0]
  reg [23:0] wa [0:7]; reg [9:0] wt [0:7]; integer wb [0:7]; reg [7:0] wbusy;
  always @(posedge pclk) begin
    w_rdy <= ($urandom % 3) != 0;
    if (w_v && w_rdy) begin
      if (wbusy[w_tag[2:0]]) begin err = err + 1; $display("ERR W request on busy lane %0d", w_tag[2:0]); end
      if (w_len != 6'd5) begin err = err + 1; $display("ERR W len %0d", w_len); end
      wa[w_tag[2:0]] <= w_addr; wt[w_tag[2:0]] <= w_tag; wbusy[w_tag[2:0]] <= 1'b1; wb[w_tag[2:0]] <= 0;
    end
    for (k = 0; k < 8; k = k + 1) begin
      if (wr_v[k] && wr_rdy[k]) begin
        wr_v[k] <= 1'b0; wb[k] <= wb[k] + 1;
        if (wb[k] == 4) wbusy[k] <= 1'b0;
      end else if (!wr_v[k] && wbusy[k] && ($urandom % 2)) begin
        wr_v[k] <= 1'b1; wr_tag[k*10 +: 10] <= wt[k]; wr_beat[k*5 +: 5] <= wb[k][4:0];
        wr_data[k*256 +: 256] <= f({8'd0, wa[k]} ^ W_SALT, wb[k][4:0]);
      end
    end
  end
  initial begin k_rdy = 0; kr_v = 0; w_rdy = 0; w_room = 8'hff; wr_v = 0; wbusy = 0; end
  // ---------------------------------------------------------------- expected responses
  // SM line expectations: tag -> (addr, kind) per SM, unique tags
  reg [31:0] exp_a [0:7][0:1023]; reg exp_w [0:7][0:1023]; reg exp_on [0:7][0:1023];
  integer outst [0:7], done_lines = 0, want_lines = 0, kv_want = 0, kv_got = 0, ik_want = 0, ik_got = 0;
  reg [31:0] kv_a [0:63]; reg [9:0] kv_t [0:63]; reg [31:0] ik_a [0:63];
  function automatic [1087:0] lineof(input [31:0] a);
    reg [255:0] b4;
    begin b4 = f(a, 4); lineof = {b4[63:0], f(a, 3), f(a, 2), f(a, 1), f(a, 0)}; end
  endfunction
  always @(posedge ck) begin
    for (k = 0; k < 8; k = k + 1) if (ln[k][0]) begin : chk
      reg [9:0] t; t = ln[k][10:1];
      if (!exp_on[k][t]) begin err = err + 1; $display("ERR SM %0d unexpected line tag %0d", k, t); end
      else begin
        if (ln[k][1098:11] !== (exp_w[k][t] ? lineof(exp_a[k][t] ^ W_SALT) : lineof(exp_a[k][t]))) begin
          err = err + 1; $display("ERR SM %0d tag %0d data mismatch (W=%0d)", k, t, exp_w[k][t]); end
        exp_on[k][t] = 1'b0; outst[k] = outst[k] - 1; done_lines = done_lines + 1;
      end
    end
    if (kvo[0]) begin
      if (kv_got >= kv_want) begin err = err + 1; $display("ERR unexpected kv"); end
      else if (kvo[1037:14] !== {f(kv_a[kv_got], 3), f(kv_a[kv_got], 2), f(kv_a[kv_got], 1), f(kv_a[kv_got], 0)} ||
               kvo[10:1] !== kv_t[kv_got]) begin err = err + 1; $display("ERR kv %0d mismatch", kv_got); end
      kv_got = kv_got + 1;
    end
  end
  // index keys: ik carries no valid; it is checked when it changes (each command has a distinct address)
  reg [1023:0] ik_prev = {1024{1'bx}};
  always @(posedge ck) if (iko !== ik_prev && rst) begin
    ik_prev <= iko;
    if (ik_got >= ik_want) begin err = err + 1; $display("ERR unexpected ik change"); end
    else if (iko !== {f(ik_a[ik_got], 3), f(ik_a[ik_got], 2), f(ik_a[ik_got], 1), f(ik_a[ik_got], 0)}) begin
      err = err + 1; $display("ERR ik %0d mismatch", ik_got); end
    ik_got = ik_got + 1;
  end
  // ---------------------------------------------------------------- stimulus
  localparam integer NREQ = 24;        // per SM
  reg [9:0] ntag [0:7];
  integer sent [0:7];
  task automatic expect_line(input integer s, input [9:0] t, input [31:0] a, input w);
    begin exp_a[s][t] = a; exp_w[s][t] = w; exp_on[s][t] = 1'b1; outst[s] = outst[s] + 1; want_lines = want_lines + 1; end
  endtask
  // row-0 SMs: valid/ready on ck
  genvar gk;
  generate for (gk = 0; gk < 8; gk = gk + 1) begin : gs
    if (!FWDV[gk]) begin : loc
      always @(posedge ck) if (rst) begin
        if (qv[gk] && qrdy[gk]) begin qv[gk] <= 1'b0; end
        else if (!qv[gk] && sent[gk] < NREQ && outst[gk] < 6 && ($urandom % 2)) begin : snd
          reg [31:0] a; a = {$urandom} & 32'h3fff_fff0 | gk;
          qd[gk] <= {ntag[gk], a}; qv[gk] <= 1'b1; expect_line(gk, ntag[gk], a, 1'b0);
          ntag[gk] <= ntag[gk] + 1; sent[gk] <= sent[gk] + 1;
        end
      end
    end else begin : fwd   // row-1 SMs: forwarded, no ready: at most 3 outstanding (the SM's ring), one per fck
      always @(posedge fck) begin
        qv[gk] <= 1'b0;
        if (rst && sent[gk] < NREQ && outst[gk] < 3 && ($urandom % 3 == 0)) begin : snd
          reg [31:0] a; a = {$urandom} & 32'h3fff_fff0 | gk;
          qd[gk] <= {ntag[gk], a}; qv[gk] <= 1'b1; expect_line(gk, ntag[gk], a, 1'b0);
          ntag[gk] <= ntag[gk] + 1; sent[gk] <= sent[gk] + 1;
        end
      end
    end
  end endgenerate
  // e commands on the forwarded e link: W fetches, KV rows, index keys
  integer ne = 0;
  always @(posedge fck) begin
    ev <= 1'b0;
    if (rst && ne < 48 && ($urandom % 9 == 0)) begin : snd
      reg [1:0] kind; reg [31:0] a; reg [9:0] t; integer s;
      kind = ne % 3; a = {$urandom} & 32'h00ff_fff0; s = $urandom % 8;
      if (kind == 0 && outst[s] < 6) begin
        t = {ntag[s][9:3] | 7'h40, s[2:0]};      // W tags: bit 9 set (disjoint from SM tags < 512 here)
        ed <= {79'd0, t, 6'd5, a[29:0], 2'd0}; ev <= 1'b1; expect_line(s, t, {8'd0, a[23:0]}, 1'b1);
        ntag[s] <= ntag[s] + 8; ne = ne + 1;
      end else if (kind == 1 && kv_want - kv_got < 1) begin
        t = ne; ed <= {79'd0, t, 6'd4, a[29:0], 2'd1}; ev <= 1'b1;
        kv_a[kv_want] = a; kv_t[kv_want] = t; kv_want = kv_want + 1; ne = ne + 1;
      end else if (kind == 2 && ik_want - ik_got < 1) begin
        t = ne; ed <= {79'd0, t, 6'd4, a[29:0], 2'd2}; ev <= 1'b1;
        ik_a[ik_want] = a; ik_want = ik_want + 1; ne = ne + 1;
      end
    end
  end
  initial begin
    for (k = 0; k < 8; k = k + 1) begin outst[k] = 0; sent[k] = 0; ntag[k] = 0; qv[k] = 0; end
    ev = 0;
    for (k = 0; k < 8; k = k + 1) for (j = 0; j < 1024; j = j + 1) exp_on[k][j] = 1'b0;
    repeat (8) @(posedge ck); rst = 1;
    fork : wait_done
      begin
        wait (ne >= 48 && done_lines == want_lines && kv_got == kv_want && ik_got == ik_want &&
              sent[0] + sent[1] + sent[2] + sent[3] + sent[4] + sent[5] + sent[6] + sent[7] == 8 * NREQ);
        repeat (50) @(posedge ck);
        disable wait_done;
      end
      begin repeat (200000) @(posedge ck); $display("ERR timeout lines %0d/%0d kv %0d/%0d ik %0d/%0d e %0d", done_lines,
          want_lines, kv_got, kv_want, ik_got, ik_want, ne); err = err + 1; disable wait_done; end
    join
    $display("SVC_BENCH lines=%0d kv=%0d ik=%0d e=%0d errors=%0d", done_lines, kv_got, ik_got, ne, err);
    if (err != 0 || done_lines == 0) $fatal(1, "SVC_BENCH FAIL");
    $display("SVC_BENCH PASS");
    $finish;
  end
