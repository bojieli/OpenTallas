`timescale 1ps/1ps
// hbm-system 2026-10-08 (T3 gap 3): die-level KV / CKV / index-key WRITE PATH bench.
//   producer row beats -> ot_hbm_kvwb_hub (dskv_wb ALL_STACKS + K-port map + 4 credit-flowed sector links)
//   -> 4 x ot_hbm_svc_core WB=1 (the r25 stream service, SE parameters, read ports idle or loaded)
//   -> 4 x ot_hdc_v41x_idx_hbm (timed HBM3E stack: REFpb, write rules; one-sector masked writes, wr_done)
// Prints every write the PHYs accept (W lines), then, at the first fence_ok after the last row (or right after the
// last row with +early=1: a negative control), the DRAM word of every written address (M lines) and the fence time.
// tools/hbm_kvwb_die_bench.py builds the rows and checks the lines against an independent Python address map.
// Plusargs: +rows=FILE +die=N +out=FILE [+early=1] [+rd=1: concurrent KV reads on every stack's KV PC].
module tb_hbm_kvwb_die #(parameter integer MUT = 0, parameter integer WR0 = 0, parameter integer CR0 = 80,
                         parameter integer KR0 = 96, parameter integer XST = 2, parameter integer WQ_ST = 6);
  localparam integer TH = 833, TCK = 1024;
  reg hclk = 0, ck = 0, rst_n = 0;
  always #(TH/2) hclk = ~hclk;
  always #(TCK/2) ck = ~ck;
  reg [6:0] die;
  // ---------------------------------------------------------------- hub
  reg ri_v = 0, ri_hdr = 0; reg [255:0] ri_d = 0; wire ri_cr;
  wire [4*292-1:0] so_d; wire [4*16-1:0] si_g;
  wire fence_ok, map_fault; wire [15:0] issued, acked;
  ot_hbm_kvwb_hub #(.WIN_ROW0(WR0), .CKV_ROW0(CR0), .KEY_ROW0(KR0), .SLOT_ROWS(2), .MUT(MUT)) u_hub (
    .clk(hclk), .rst_n(rst_n), .die(die), .ri_v(ri_v), .ri_hdr(ri_hdr), .ri_d(ri_d), .ri_cr(ri_cr),
    .so_d(so_d), .si_g(si_g), .fence_ok(fence_ok), .issued(issued), .acked(acked), .map_fault(map_fault));
  // ---------------------------------------------------------------- 4 stacks
  integer fo;
  reg rd_en; integer rd_sent [0:3], rd_got [0:3];
  genvar t;
  generate for (t = 0; t < 4; t = t + 1) begin : gst
    wire phy_clk, phy_rst_n, fclk;
    wire [31:0] k_v, k_rdy, k_we, k_wr_done, kr_v, kr_rdy; wire [959:0] k_addr; wire [127:0] k_len, kr_beat;
    wire [543:0] k_tag, kr_tag; wire [8191:0] k_wdata, kr_data; wire [1023:0] k_wstrb;
    wire [8*1099-1:0] line; wire [1037:0] kv; wire [1023:0] ik; wire [7:0] q_rdy;
    reg [127:0] e_d = 0; reg e_fclk = 0;
    always #(TH/2) e_fclk = ~e_fclk;
    ot_hbm_svc_core #(.SM_PC0({5'd28, 5'd24, 5'd20, 5'd16, 5'd12, 5'd8, 5'd4, 5'd0}),
      .RSP_ST(128'h10111101210021002211322133212110), .REQ_ST(32'h11112332), .W_ST(32'hec985300),
      .FWD(8'b01010101), .KV_PC(16), .IK_PC(17), .KV_ST(0), .IK_ST(0), .E_ST(11), .XST(XST), .WB(1), .WQ_ST(WQ_ST)) u_svc (
      .ck(ck), .rst(rst_n), .q_d({8*42{1'b0}}), .q_v(8'd0), .q_fclk(8'd0), .q_rdy(q_rdy), .line(line), .fclk(fclk),
      .e_d(e_d), .e_fclk(e_fclk), .kv(kv), .ik(ik), .phy_clk(phy_clk), .phy_rst_n(phy_rst_n),
      .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we), .k_wdata(k_wdata),
      .k_wstrb(k_wstrb), .kr_v(kr_v), .kr_rdy(kr_rdy), .kr_tag(kr_tag), .kr_beat(kr_beat), .kr_data(kr_data),
      .w_v(), .w_rdy(1'b0), .w_addr(), .w_len(), .w_tag(), .w_room(8'd0), .wr_v(8'd0), .wr_rdy(), .wr_tag(80'd0),
      .wr_beat(40'd0), .wr_data(2048'd0),
      .wq_d(so_d[292*t +: 292]), .wq_fclk(hclk), .wq_g(si_g[16*t +: 16]), .k_wr_done(k_wr_done));
    ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(30), .DW(256), .MEM_WORDS(1 << 22), .TAGW(17), .LENW(4), .BEATW(4),
      .QD(64), .REFPB(3), .MEM_MODE(0), .CLK_PS(TCK)) u_m (
      .clk(phy_clk), .rst_n(phy_rst_n), .req_v(k_v), .req_rdy(k_rdy), .req_addr(k_addr), .req_len(k_len),
      .req_tag(k_tag), .req_we(k_we), .req_wdata(k_wdata), .req_wstrb(k_wstrb), .wr_done(k_wr_done),
      .rsp_v(kr_v), .rsp_rdy(kr_rdy), .rsp_tag(kr_tag), .rsp_beat(kr_beat), .rsp_data(kr_data));
    integer p;
    always @(posedge phy_clk) if (k_v[16] && !k_we[16] && t == 0 && hb > 0) $display("RD k_v16 rdy=%0d addr=%0d len=%0d tag=%h", k_rdy[16], k_addr[16*30 +: 30], k_len[64 +: 4], k_tag[16*17 +: 17]);
    always @(posedge ck) if (t == 0 && hb > 0 && u_svc.chv) $display("CHV kind=%0d busy16=%0d wreq16=%0d", u_svc.c_kind, u_svc.pc_busy[16], u_svc.wreq[16]);
    always @(posedge phy_clk) for (p = 0; p < 32; p = p + 1)
      if (k_v[p] && k_rdy[p] && k_we[p])
        $fdisplay(fo, "W %0d %0d %0d %h %h %0t", t, p, k_addr[p*30 +: 30], k_wstrb[p*32 +: 32], k_wdata[p*256 +: 256], $time);
    // background content of the read region (rows 120..123): a hash of the address
    integer ia;
    initial for (ia = 120 << 15; ia < 124 << 15; ia = ia + 1)
      u_m.mem[ia] = {8{32'(ia) * 32'h9e3779b1 ^ 32'(t) * 32'h85ebca6b}};
    // concurrent KV reads (+rd=1): kind 1 on the e link, 4 sectors at a 4-aligned address of PC 16 (reads the
    // write-free background region rows 120..123), one outstanding; checks the returned line is the DRAM content
    reg [29:0] ra; wire rpend = (rd_sent[t] != rd_got[t]);
    always @(posedge e_fclk) begin
      e_d[0] <= 1'b0;
      if (rd_en && go && !rpend && rd_sent[t] < 64 && ($urandom % 7 == 0)) begin : snd
        reg [29:0] s; s = {15'd120 + 15'($urandom % 4), 15'd0};
        // choose s[6:2] so pc_of(s) = 16 with col = s[11:7] random and s[1:0] = 0
        s[11:7] = $urandom; s[14:12] = $urandom;
        s[6:2] = 5'd16 ^ s[11:7] ^ s[16:12];
        ra <= s;
        e_d <= {79'd0, 10'(rd_sent[t]), 6'd4, s, 2'd1, 1'b1};
        rd_sent[t] = rd_sent[t] + 1;
      end
    end
    always @(posedge ck) if (kv[0]) begin
      if (kv[1037:14] !== {u_m.mem[ra + 3], u_m.mem[ra + 2], u_m.mem[ra + 1], u_m.mem[ra]})
        $fdisplay(fo, "RDERR %0d %h", t, ra);
      rd_got[t] = rd_got[t] + 1;
    end
  end endgenerate
  // ---------------------------------------------------------------- producer: rows file -> beats under credit
  integer credits = 32, nrows = 0, fr, rc, k, b, nb, pos, kind, slot, r2, sh, early;
  reg [4351:0] dat;
  string rows_f, out_f;
  // beats are preloaded and sent by a clocked process under credit (one beat a cycle, random gaps between rows)
  reg [256:0] bq [0:65535]; reg bgap [0:65535]; integer nbq = 0, ibq = 0, gap = 0; reg go = 0;
  always @(posedge hclk) begin
    ri_v <= 1'b0;
    if (go && ibq < nbq) begin
      if (gap > 0) gap <= gap - 1;
      else if (credits - (ri_v ? 1 : 0) + (ri_cr ? 1 : 0) > 0) begin
        ri_v <= 1'b1; ri_hdr <= bq[ibq][256]; ri_d <= bq[ibq][255:0];
        if (bgap[ibq]) gap <= $urandom % 4;
        ibq <= ibq + 1;
      end
    end
    credits <= credits - (ri_v ? 1 : 0) + (ri_cr ? 1 : 0);
  end
  integer t0, t_last, t_fence, nfail, hb;
  initial if ($value$plusargs("hb=%d", hb)) forever begin #(hb * 1000);
    $display("HEARTBEAT t=%0t rows=%0d credits=%0d ast=%0d iss=%0d ack=%0d fence=%0d", $time, nrows, credits,
             u_hub.ast, issued, acked, fence_ok);
    $display("  hub rwp=%0d rrp=%0d bi=%0d nb=%0d st=%0d row_r=%0d rv_q=%0d", u_hub.rwp, u_hub.rrp, u_hub.bi, u_hub.nb,
             u_hub.u_wb.on.st, u_hub.row_r, u_hub.rv_q); end
  initial begin
    if (!$value$plusargs("rows=%s", rows_f)) $fatal(1, "+rows");
    if (!$value$plusargs("out=%s", out_f)) $fatal(1, "+out");
    if (!$value$plusargs("die=%d", k)) k = 0;
    die = k[6:0];
    if (!$value$plusargs("early=%d", early)) early = 0;
    if (!$value$plusargs("rd=%d", k)) k = 0;
    rd_en = (k != 0);
    for (k = 0; k < 4; k = k + 1) begin rd_sent[k] = 0; rd_got[k] = 0; end
    fo = $fopen(out_f, "w");
    fr = $fopen(rows_f, "r");
    repeat (10) @(posedge hclk); rst_n = 1;
    repeat (40) @(posedge hclk);
    rc = 6;
    while (!$feof(fr) && rc == 6) begin
      rc = $fscanf(fr, "%d %d %d %d %d %h\n", kind, slot, r2, pos, sh, dat);
      if (rc == 6) begin
        nb = sh ? 17 : (kind == 1) ? 9 : (kind == 2) ? 3 : 17;
        bq[nbq] = {1'b1, 226'd0, sh[0], pos[19:0], r2[0], slot[5:0], kind[1:0]}; bgap[nbq] = 0; nbq = nbq + 1;
        for (b = 0; b < nb; b = b + 1) begin bq[nbq] = {1'b0, dat[256 * b +: 256]}; bgap[nbq] = (b == nb - 1); nbq = nbq + 1; end
        nrows = nrows + 1;
      end
    end
    t0 = $time;
    go = 1;
    while (ibq < nbq) @(posedge hclk);
    // wait until the hub has drained its beats and dskv_wb is idle, then for the fence
    repeat (200) @(posedge hclk);
    t_last = $time;
    if (!early) begin
      k = 0;
      while (!(fence_ok && issued == acked && issued != 0) && k < 400000) begin @(posedge hclk); k = k + 1; end
    end
    t_fence = $time;
    $fdisplay(fo, "F rows=%0d issued=%0d acked=%0d fence_ok=%0d map_fault=%0d t_rows_ps=%0d t_fence_ps=%0d early=%0d",
              nrows, issued, acked, fence_ok, map_fault, t_last - t0, t_fence - t0, early);
    $fflush(fo);
    // DRAM peek: the bench prints the words at every address the checker asks for (+peek file), at fence time
    begin : peek
      integer pf, st_, a_; string pk;
      if ($value$plusargs("peek=%s", pk)) begin
        pf = $fopen(pk, "r");
        while (!$feof(pf)) begin
          rc = $fscanf(pf, "%d %d\n", st_, a_);
          if (rc != 2) break;
          case (st_)
            0: $fdisplay(fo, "M %0d %0d %h", st_, a_, gst[0].u_m.mem[a_]);
            1: $fdisplay(fo, "M %0d %0d %h", st_, a_, gst[1].u_m.mem[a_]);
            2: $fdisplay(fo, "M %0d %0d %h", st_, a_, gst[2].u_m.mem[a_]);
            default: $fdisplay(fo, "M %0d %0d %h", st_, a_, gst[3].u_m.mem[a_]);
          endcase
        end
      end
    end
    if (rd_en) begin
      k = 0;
      while ((rd_got[0] + rd_got[1] + rd_got[2] + rd_got[3]) < (rd_sent[0] + rd_sent[1] + rd_sent[2] + rd_sent[3]) && k < 100000) begin
        @(posedge ck); k = k + 1; end
      $fdisplay(fo, "R sent=%0d got=%0d", rd_sent[0] + rd_sent[1] + rd_sent[2] + rd_sent[3], rd_got[0] + rd_got[1] + rd_got[2] + rd_got[3]);
    end
    $fdisplay(fo, "END");
    $fclose(fo);
    $finish;
  end
endmodule
