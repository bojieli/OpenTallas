`timescale 1ns/1ps
// RTLGAP2-HEADTB (10-21) CUT-B of the per-tile hierarchical head-die token TB (G-HEAD-DIE-TB), derived from
// TOK-FUNC2-S81-LX tb_s81hd_die.sv (9b63a7e8f) for the CURRENT head die (S81-HEAD H10b strict-bind dv_die: 253 x
// ot_s81hd_tile on 26 spine segments, 13 spo + 13 spr, ot_s81hd_ctl_glue + dsfd_mtp_seq, ot_s81hd_lep_regional,
// 13 ot_s81hd_lane, 17 ot_pdie_serdes_col, every landing / relay of the bind) -- all bound RTL EXCEPT the inside of each
// tile's ot_s81hd_bundle, which is ot_s81hd_bundle_replay.sv (input face bit-checked against the golden bus-B stream,
// output face = CUT-A's recorded full-RTL bundle result of that tile).  CUT-A (tb_s81hd_tilecut) ran every tile's bundle
// in RTL on the released DeepSeek-V4.1 head.weight rank-0 ROM images with the golden final-norm x (logits bit-exact).
//
// Only the off-die legs are modelled: every die link (lk_*) is cabled to a link partner that is the SAME RTL the peer die
// carries -- ot_pdie_serdes (behavioural PMA, real KP4 / link layer) + ot_s81hd_lane (host / mesh / draft) or
// ot_s81hd_lep (stage NEXT circuit, = the end-slice endpoint s_0N speaks bit for bit) -- and the test bench drives the
// partners' core faces with the programme:
//   host lane 1   CSR writes (HSF0 type 6): plen, glen, rank 0, {ngrp 1, grp 0}, row base 0, RESULT dest, run
//   lep pair A    the XB message = 80 ring beats {bf 1024, gidx g, kind 2, hops 1, v}, one per 2 cycles (lane rate 0.764)
//   mesh lanes    after this die's own BEST frame leaves on all 6 mesh lanes, the 3 peer ranks' BEST records (golden
//                 argmax of ranks 1..3: the other three head dies, off this die) on both lanes of each pair
// Checks: the merged token (ring K_TOK beat at the stage partner + host lane 0 RESULT frame) = golden row / bits,
// the own BEST record = golden local argmax of the rows this die holds, no landing fault, no partner lane fault,
// no chain fault at the N / S spine returns (a bundle face mismatch raises the chain flt).
// Plusargs: +XB= (xb_beats.hex) +LROW +LBITS (local) +P1ROW.. +P3BITS (peers) +TROW +TBITS (token) + shim +HC_REC +DIR.
// Verdict: "PASS head_die ..." / "FAIL head_die ...".  Cycle report line "CYC ...".
module tb_s81hd_diecut;
    localparam integer FW = 553;
    reg ck = 1'b0; always #0.5 ck = ~ck;
    reg rst_n = 1'b0;
    integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;
    integer errs = 0;
    task fail(input [8*96-1:0] msg); begin if (errs < 20) $display("FAIL head_die %0s (cycle %0d)", msg, cyc); errs = errs + 1; end endtask
    task tick; @(negedge ck); endtask

    // ------------------------------------------------------------------ die pads
`define PADS(X) wire [543:0] d_``X``_tx, p_``X``_tx; wire d_``X``_tck, p_``X``_tck;
    `PADS(HOST0) `PADS(HOST1) `PADS(WN0) `PADS(WN1) `PADS(WN2) `PADS(WN3) `PADS(DW0) `PADS(DW1)
    `PADS(M0) `PADS(M1) `PADS(M2) `PADS(M3) `PADS(M4) `PADS(M5) `PADS(DE0) `PADS(DE1) `PADS(DE2)
    wire [182:0] land_fault;
`define DLK(X) .lk_``X``_pma_tx(d_``X``_tx), .lk_``X``_pma_tck(d_``X``_tck), .lk_``X``_pma_rx(p_``X``_tx), .lk_``X``_pma_rck(p_``X``_tck)
    dv_die dut (
        .ck_clN00E(ck), .ck_clN00W(ck), .ck_clN01E(ck), .ck_clN01W(ck), .ck_clN02E(ck), .ck_clN02W(ck), .ck_clN03E(ck),
        .ck_clN03W(ck), .ck_clN04E(ck), .ck_clN04W(ck), .ck_clN05E(ck), .ck_clN05W(ck), .ck_clN06E(ck), .ck_clN06W(ck),
        .ck_clS00E(ck), .ck_clS00W(ck), .ck_clS01E(ck), .ck_clS01W(ck), .ck_clS02E(ck), .ck_clS02W(ck), .ck_clS03E(ck),
        .ck_clS03W(ck), .ck_clS04E(ck), .ck_clS04W(ck), .ck_clS05E(ck), .ck_clS05W(ck),
        .ck_cl_lk_WN0(ck), .ck_cl_lk_WN1(ck), .ck_cl_lk_WN2(ck), .ck_cl_ln_draft0(ck), .ck_cl_ln_draft1(ck), .ck_cl_ln_draft2(ck), .ck_cl_ln_draft3(ck), .ck_cl_ln_draft4(ck),
        .ck_cl_ln_host0(ck), .ck_cl_ln_host1(ck), .ck_cl_ln_mesh0(ck), .ck_cl_ln_mesh1(ck), .ck_cl_ln_mesh2(ck),
        .ck_cl_ln_mesh3(ck), .ck_cl_ln_mesh4(ck), .ck_cl_ln_mesh5(ck), .ck_clctl(ck), .ck_cllep(ck), .ck_edge0(ck),
        .ck_hbm(ck), .ck_head_lep_A(ck), .ck_head_lep_B(ck), .ck_head_lep_C(ck), .rst_n(rst_n),
        `DLK(HOST0), `DLK(WN2), `DLK(WN3), `DLK(WN0), `DLK(WN1), `DLK(HOST1), `DLK(DW0), `DLK(DW1), `DLK(M0), `DLK(M1),
        `DLK(M2), `DLK(M3), `DLK(M4), `DLK(DE0), `DLK(M5), `DLK(DE1), `DLK(DE2), .land_fault(land_fault));

    // ------------------------------------------------------------------ link partners (the peer die's RTL)
`define PSER(X) wire [511:0] t_``X``_tx, t_``X``_rx; wire [1:0] t_``X``_st; \
    ot_pdie_serdes u_ps_``X (.clk(ck), .rst(rst_n), .tx(t_``X``_tx), .rx(t_``X``_rx), .st(t_``X``_st), \
        .pma_tx(p_``X``_tx), .pma_tck(p_``X``_tck), .pma_rx(d_``X``_tx), .pma_rck(d_``X``_tck));
    `PSER(HOST0) `PSER(HOST1) `PSER(WN0) `PSER(WN1) `PSER(WN2) `PSER(WN3) `PSER(DW0) `PSER(DW1)
    `PSER(M0) `PSER(M1) `PSER(M2) `PSER(M3) `PSER(M4) `PSER(M5) `PSER(DE0) `PSER(DE1) `PSER(DE2)
    // lane partners: index 0 host0, 1 host1, 2..6 draft (DW0, DW1, DE0, DE1, DE2), 7..12 mesh M0..M5
    reg  [12:0] l_tv = 0; reg [13*FW-1:0] l_td = 0;
    wire [12:0] l_rv; wire [13*FW-1:0] l_rd; wire [13*4-1:0] l_flt;
`define PLANE(I, X) ot_s81hd_lane u_pl_``X (.ck(ck), .rst_n(rst_n), .chb(1'b1), .rx({t_``X``_st, t_``X``_rx}), .tx(t_``X``_tx), \
        .tx_v(l_tv[I]), .tx_d(l_td[I*FW +: FW]), .rx_v(l_rv[I]), .rx_d(l_rd[I*FW +: FW]), .flt(l_flt[4*I +: 4]));
    `PLANE(0, HOST0) `PLANE(1, HOST1) `PLANE(2, DW0) `PLANE(3, DW1) `PLANE(4, DE0) `PLANE(5, DE1) `PLANE(6, DE2)
    `PLANE(7, M0) `PLANE(8, M1) `PLANE(9, M2) `PLANE(10, M3) `PLANE(11, M4) `PLANE(12, M5)
    // stage NEXT-circuit partner: pair A = WN0/1, pair B = WN2/3
    reg  [1103:0] s_ro = 0; wire [1103:0] s_ri; wire [31:0] s_rt; wire [10:0] s_lw; wire s_flt;
    ot_s81hd_lep u_pstage (.ck(ck), .rst_n(rst_n), .ch_b(1'b1),
        .tx0(t_WN0_tx), .tx1(t_WN1_tx), .rx0({t_WN0_st, t_WN0_rx}), .rx1({t_WN1_st, t_WN1_rx}),
        .tx2(t_WN2_tx), .tx3(t_WN3_tx), .rx2({t_WN2_st, t_WN2_rx}), .rx3({t_WN3_st, t_WN3_rx}),
        .ro(s_ro), .ri(s_ri), .mu_c(34'd0), .mu_rt(s_rt), .mu_rc(11'd0), .lw(s_lw), .sl_f(1'b0), .fault(s_flt));

    // ------------------------------------------------------------------ programme data / goldens
    reg [1023:0] xb [0:79];
    reg [8*1024-1:0] xbf;
    integer lrow, p1row, p2row, p3row, trow;
    reg [31:0] lbits, p1bits, p2bits, p3bits, tbits;
    initial begin
        if (!$value$plusargs("XB=%s", xbf)) $fatal(1, "+XB");
        $readmemh(xbf, xb);
        if (!$value$plusargs("LROW=%d", lrow)) $fatal(1, "+LROW");
        if (!$value$plusargs("LBITS=%h", lbits)) $fatal(1, "+LBITS");
        if (!$value$plusargs("P1ROW=%d", p1row)) $fatal(1, "+P1ROW");
        if (!$value$plusargs("P1BITS=%h", p1bits)) $fatal(1, "+P1BITS");
        if (!$value$plusargs("P2ROW=%d", p2row)) $fatal(1, "+P2ROW");
        if (!$value$plusargs("P2BITS=%h", p2bits)) $fatal(1, "+P2BITS");
        if (!$value$plusargs("P3ROW=%d", p3row)) $fatal(1, "+P3ROW");
        if (!$value$plusargs("P3BITS=%h", p3bits)) $fatal(1, "+P3BITS");
        if (!$value$plusargs("TROW=%d", trow)) $fatal(1, "+TROW");
        if (!$value$plusargs("TBITS=%h", tbits)) $fatal(1, "+TBITS");
    end

    // ------------------------------------------------------------------ monitors
    integer t_x0 = -1, t_xl = -1, t_go = -1, t_n = -1, t_s = -1, t_best = -1, t_tok = -1, t_res = -1;
    integer ntok = 0, nres = 0, nbest = 0, k;
    reg [80:0] ownrec = 0;
    reg [80:0] lrec [0:5];
    integer t_lane [0:5];
    integer nlanes = 0;
    integer q;
    initial for (q = 0; q < 6; q = q + 1) begin lrec[q] = 0; t_lane[q] = -1; end
    always @(negedge ck) if (rst_n) begin
        if (t_go < 0 && dut.u_ctl.sn_o[512]) t_go = cyc;
        if (t_n < 0 && dut.u_ctl.sn_i[514]) t_n = cyc;
        if (t_s < 0 && dut.u_ctl.ss_i[514]) t_s = cyc;
        if (dut.u_ctl.sn_i[514] && dut.u_ctl.sn_i[564]) fail("N spine return flt");
        if (dut.u_ctl.ss_i[514] && dut.u_ctl.ss_i[564]) fail("S spine return flt");
        if (land_fault != 0) fail("die landing fault");
        if (s_flt) fail("stage partner lep fault");
        for (k = 0; k < 13; k = k + 1) if (l_flt[4*k +: 4] != 4'd0) fail("partner lane fault");
        // own BEST on the mesh partners (all 6 lanes carry the record).  With the die lane-flight model the 6 mesh
        // lanes land on different edges (per-landing K from the land plan), so every lane's record is kept and checked
        // on its own; the verdict waits for all 6 (S81d-TOK 10-22: the old lane-7-only capture raced the first lane).
        for (k = 7; k < 13; k = k + 1) if (l_rv[k]) begin
            if (l_rd[k*FW +: 4] != 4'd1) fail("mesh frame is not BEST");
            if (t_lane[k-7] < 0) begin lrec[k-7] = l_rd[k*FW + 16 +: 81]; t_lane[k-7] = cyc; nlanes = nlanes + 1; end
            if (k == 7) begin ownrec = l_rd[k*FW + 16 +: 81]; end
            if (t_best < 0) t_best = cyc;
            nbest = nbest + 1;
        end
        if (s_ri[0] && s_ri[3:1] == 3'd5) begin
            $display("TOK ring row %0d bits %08h pos %0d at %0d", s_ri[21+61 +: 21], s_ri[21+82 +: 32], s_ri[21+40 +: 21], cyc);
            if (s_ri[21+61 +: 21] != trow[20:0] || s_ri[21+82 +: 32] != tbits || s_ri[21+40 +: 21] != 21'd0) fail("token value (ring)");
            if (t_tok < 0) t_tok = cyc;
            ntok = ntok + 1;
        end
        if (l_rv[0]) begin
            $display("RESULT host0 type %0d row %0d at %0d", l_rd[3:0], l_rd[16+61 +: 21], cyc);
            if (l_rd[3:0] != 4'd9 || l_rd[16+61 +: 21] != trow[20:0]) fail("host RESULT frame");
            if (t_res < 0) t_res = cyc;
            nres = nres + 1;
        end
    end

    task csrw(input [7:0] a, input [63:0] d);
        begin l_tv[1] = 1; l_td[FW +: FW] = {1'b1, 464'd0, d, a, 8'd0, 2'd0, 2'd0, 4'd6}; tick; l_tv[1] = 0; repeat (5) tick; end
    endtask
    task peer(input integer lane, input [1:0] rank, input [16:0] row, input [31:0] bits);
        begin l_tv[lane] = 1; l_td[lane*FW +: FW] = {1'b1, 455'd0, 21'd0, 10'd0, bits, row, 1'b1, 8'd0, 2'd0, rank, 4'd1};
              tick; l_tv[lane] = 0; end
    endtask

    integer b, w;
    initial begin
        repeat (20) tick; rst_n = 1'b1;
        // link bring-up: every partner SerDes live, then the die-side link layers settle
        w = 0;
        while (!(t_HOST0_st[1] && t_HOST1_st[1] && t_WN0_st[1] && t_WN1_st[1] && t_M0_st[1] && t_M5_st[1]) && w < 20000) begin tick; w = w + 1; end
        if (w >= 20000) fail("partner SerDes never live");
        repeat (3000) tick;
        $display("LINKS live at %0d", cyc);
        csrw(8'd0, 64'd4); csrw(8'd1, 64'd8); csrw(8'd2, 64'd0); csrw(8'd3, 64'h4); csrw(8'd4, 64'd0);
        csrw(8'd5, 64'h0201); csrw(8'd8, 64'd1);
        repeat (300) tick;
        // the XB message (h of the token), one beat per 2 cycles
        t_x0 = cyc;
        for (b = 0; b < 80; b = b + 1) begin
            s_ro = 0; s_ro[0] = 1'b1; s_ro[3:1] = 3'd2; s_ro[8:4] = 5'd1; s_ro[20:13] = b[7:0]; s_ro[1044:21] = xb[b];
            tick; s_ro = 0; tick;
        end
        t_xl = cyc;
        // wait for this die's BEST, then the 3 peers (both lanes of each pair, rank p + 1 on pair p)
        w = 0; while (nlanes < 6 && w < 200000) begin tick; w = w + 1; end
        if (nbest == 0) fail("no BEST frame from the die");
        if (nlanes < 6) fail("BEST frame missing on a mesh lane");
        for (b = 0; b < 6; b = b + 1) begin
            $display("BEST lane %0d at %0d row %0d bits %08h", b + 7, t_lane[b], lrec[b][17:1], lrec[b][49:18]);
            if (lrec[b][0] != 1'b1 || lrec[b][17:1] != lrow[16:0] || lrec[b][49:18] != lbits)
                begin $display("  own BEST lane %0d row %0d bits %08h exp row %0d bits %08h", b + 7, lrec[b][17:1], lrec[b][49:18], lrow, lbits); fail("own BEST (local argmax)"); end
        end
        repeat (8) tick;
        peer(7, 2'd1, p1row[16:0], p1bits); peer(8, 2'd1, p1row[16:0], p1bits); tick;
        peer(9, 2'd2, p2row[16:0], p2bits); peer(10, 2'd2, p2row[16:0], p2bits); tick;
        peer(11, 2'd3, p3row[16:0], p3bits); peer(12, 2'd3, p3row[16:0], p3bits);
        w = 0; while ((ntok == 0 || nres == 0) && w < 20000) begin tick; w = w + 1; end
        repeat (500) tick;
        if (ntok != 1) fail("ring token count != 1");
        if (nres != 1) fail("host RESULT count != 1");
        $display("CYC xb_first %0d xb_last %0d go %0d n_ret %0d s_ret %0d best_at_peer %0d token_at_stage %0d result_at_host %0d",
                 t_x0, t_xl, t_go, t_n, t_s, t_best, t_tok, t_res);
        $display("CYC rel xb_first->go %0d go->n_ret %0d go->s_ret %0d xb_first->best_at_peer %0d best->token_at_stage %0d xb_first->token_at_stage %0d",
                 t_go - t_x0, t_n - t_go, t_s - t_go, t_best - t_x0, t_tok - t_best, t_tok - t_x0);
        if (errs == 0) $display("PASS head_die token %0d bits %08h own %0d", trow, tbits, ownrec[17:1]);
        else $display("FAIL head_die errors %0d", errs);
        $finish;
    end
    initial begin #2000000; $display("FAIL head_die timeout (cycle %0d) go %0d n %0d s %0d best %0d", cyc, t_go, t_n, t_s, t_best); $finish; end
endmodule
