`timescale 1ns/1ps
// QDIE5-TLD 10-22: CALR table-load CONSUMER bench (Q.STA.TTC.HP13 owed port table_req, class A).
// The RELEASE tt_ctlm master qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1 (5d45a822) is the producer: its {cmd, table_req}
// output trace (realcalendar_native fixture, CALRDIR 2 = the CALR10 image with the QW-TLPROD stage-relative loads, user 0
// plays stages 0..37) is replayed onto a chain of NS release slices (qfd_dv_slice2_wt / _et face variants = qfd_dv_slice2
// PRIVATE_CALR 1, the die order W5..W0 | E0..E5, slice k = TSLICE k = mask set table_s<k>_m0..3) through die lanes of
// the GEN's latency (ctlm -> W5 DLANE cycles, slice -> slice DHOP cycles, cmd and treq on the SAME lane latency = the
// OT_SPLIT_DV_TREQ record bundle).  Per slice, every edge:
//   CMD    lockstep: the slice's cmd input equals the producer's cmd DCMD(k) edges earlier (SETID id field masked);
//   ALIGN  every table_req reaches the slice's loader face exactly DCMD(k) edges after the producer emitted it (it rides
//          beside cmd: QW-TLPROD CONSUMER_GAP is measured at the ctlm outputs, so it holds at every slice);
//   ORDER  the n-th load is stage n (1..36, layer order), user 0;
//   TABLE  the joined VM table-write bundle (u_core tw_*) equals the slice's golden table image row for (stage, user,
//          slot) on every one of the 88 slots, at the closed qfd_dv_slice_tload contract age (first write 5 edges after
//          the request edge): the golden = programme_store.py logical images of the committed compact table manifest
//          (sha c63242ab..., QW-TLOAD2 fixture, b8e6c6f86) = the right per-layer slice constants;
//   FAULT  no slice tload fault (collision / loader fault).
// VAR (one build each): 0 consumer as built (must PASS); 1 no consumer (old qfd_dv_slice2_w / _e: no loads -> layers
// 2..36 keep stale constants); 2 treq hop of one edge (QW-F16PROG4 / s8_lp form, cmd hop is 2); 3 treq die lane one edge
// longer than cmd (ctlm -> W5); 4 loader stage bit 0 dropped (qfd_dv_slice_tload MUT 2); 5 the stage-17 table_req
// dropped at the producer.  Every VAR != 0 must print TLD_CHAIN FAIL.
module tb_qdie5_tld_chain #(parameter integer NS = 12, parameter integer VAR = 0, parameter integer DLANE = 20,
                            parameter integer DHOP = 3, parameter integer NTR = 65536);
    reg ck = 0; always #5 ck = ~ck;
    reg rst_n = 0;
    integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;
    // ------------------------------------------------------------------ producer replay
    integer tr_n = 0, tr_i = 0, ofs = 0, fd, r, tc;
    integer tr_c [0:NTR-1]; reg [115:0] tr_cmd [0:NTR-1]; reg [8:0] tr_tq [0:NTR-1];
    reg [115:0] lo_c, co_c; reg [8:0] lo_t, co_t;
    reg [115:0] p_cmd = 0; reg [8:0] p_tq = 0;
    string trf, fxd;
    initial begin
        if (!$value$plusargs("TRACE=%s", trf)) $fatal(1, "TRACE required");
        fd = $fopen(trf, "r"); if (fd == 0) $fatal(1, "TRACE open");
        while (!$feof(fd) && tr_n < NTR) begin
            r = $fscanf(fd, "%d %h %h %h %h\n", tc, lo_c, lo_t, co_c, co_t);
            if (r == 5) begin tr_c[tr_n] = tc; tr_cmd[tr_n] = co_c; tr_tq[tr_n] = co_t; tr_n = tr_n + 1; end
        end
        $fclose(fd);
        ofs = tr_c[0] - 40;
        $display("TRACE entries=%0d first=%0d last=%0d", tr_n, tr_c[0], tr_c[tr_n - 1]);
    end
    always @(negedge ck) begin                       // value presented before posedge `cyc`+1 ... sampled at that edge
        p_cmd <= 0; p_tq <= 0;
        if (tr_i < tr_n && tr_c[tr_i] == cyc + 1 + ofs) begin
            p_cmd <= tr_cmd[tr_i];
            p_tq <= (VAR == 5 && tr_tq[tr_i][8] && tr_tq[tr_i][7:2] == 6'd17) ? 9'd0 : tr_tq[tr_i];
            tr_i <= tr_i + 1;
        end
    end
    // producer history (ring) and emission log
    reg [115:0] ph [0:1023];
    integer pn = 0, first_p = -1; integer pe [0:63]; integer ps [0:63];
    always @(posedge ck) begin
        ph[cyc % 1024] = p_cmd;
        if (p_cmd != 0 && first_p < 0) first_p = cyc;
        if (p_tq[8]) begin if (pn < 64) begin pe[pn] = cyc; ps[pn] = p_tq[7:2]; end pn = pn + 1; end
    end
    function automatic [115:0] cmask(input [115:0] c);
        cmask = (c[0] && c[3:1] == 3'd7) ? {c[115:8], 4'd0, c[3:0]} : c;
    endfunction
    // ------------------------------------------------------------------ die lanes + slices
    wire [115:0] c_in [0:NS-1]; wire [115:0] c_out [0:NS-1];
    wire [8:0]   t_in [0:NS-1]; wire [8:0]   t_out [0:NS-1];
    tld_dly #(116, DLANE) u_lc (.ck(ck), .i(p_cmd), .o(c_in[0]));
    tld_dly #(9, DLANE + ((VAR == 3) ? 1 : 0)) u_lt (.ck(ck), .i(p_tq), .o(t_in[0]));
    string fx; initial if (!$value$plusargs("FX=%s", fx)) $fatal(1, "FX required");
    integer pass_k [0:NS-1];
    genvar k;
    generate for (k = 0; k < NS; k = k + 1) begin : g_s
        if (k > 0) begin : g_lane
            tld_dly #(116, DHOP) u_c (.ck(ck), .i(c_out[k - 1]), .o(c_in[k]));
            tld_dly #(9, DHOP) u_t (.ck(ck), .i(t_out[k - 1]), .o(t_in[k]));
        end
        wire mwe, mfault; wire [1:0] mkind; wire [23:0] maddr; wire [1023:0] mdata; wire swe;
        if (VAR == 1) begin : g_old
            if (k < 6) begin : g_w
                qfd_dv_slice2_w #(.MU_NU(4), .ARF(1), .RP(1)) u_s (.ck(ck), .rst_n(rst_n), .cmd_wi(c_in[k]), .cmd_eo(c_out[k]),
                    .hr_wi(453'd0), .st_wi(1088'd0), .st_ei(1088'd0), .sc_wi(48'd0), .sc_ei(48'd0), .arv_ei(1'b0), .art_ei(32'd0),
                    .arm_ei(1'b0), .arl_ei(1'b0), .ard_ei(512'd0), .dd_ei(548'd0), .rv_wi(1'b0), .re_wi(1'b0), .rr_wi(3'd0),
                    .rl_wi(1'b0), .rd_wi(512'd0), .dr_wi(520'd0), .ag_ei(10'd0), .l9_wi(514'd0), .rs_n0(514'd0), .rs_n1(514'd0),
                    .rs_s0(514'd0), .rs_s1(514'd0));
                assign mwe = u_s.u_core.tw_we; assign mkind = u_s.u_core.tw_kind; assign maddr = u_s.u_core.tw_addr;
                assign mdata = u_s.u_core.tw_data; assign mfault = 1'b0; assign swe = 1'b0;
            end else begin : g_e
                qfd_dv_slice2_e #(.MU_NU(4), .ARF(1), .RP(1)) u_s (.ck(ck), .rst_n(rst_n), .cmd_ei(c_in[k]), .cmd_wo(c_out[k]),
                    .hr_ei(453'd0), .st_ei(1088'd0), .st_wi(1088'd0), .sc_ei(48'd0), .sc_wi(48'd0), .arv_wi(1'b0), .art_wi(32'd0),
                    .arm_wi(1'b0), .arl_wi(1'b0), .ard_wi(512'd0), .dd_wi(548'd0), .rv_ei(1'b0), .re_ei(1'b0), .rr_ei(3'd0),
                    .rl_ei(1'b0), .rd_ei(512'd0), .dr_ei(520'd0), .ag_wi(10'd0), .l9_wi(514'd0), .rs_n0(514'd0), .rs_n1(514'd0),
                    .rs_s0(514'd0), .rs_s1(514'd0));
                assign mwe = u_s.u_core.tw_we; assign mkind = u_s.u_core.tw_kind; assign maddr = u_s.u_core.tw_addr;
                assign mdata = u_s.u_core.tw_data; assign mfault = 1'b0; assign swe = 1'b0;
            end
            assign t_out[k] = 9'd0;
        end else begin : g_new
            localparam integer TQ = (VAR == 2) ? 1 : (VAR == 4) ? 2 : 0;
            if (k < 6) begin : g_w
                qfd_dv_slice2_wt #(.MU_NU(4), .ARF(1), .RP(1), .TSLICE(k), .TQ_MUT(TQ)) u_s (.ck(ck), .rst_n(rst_n),
                    .cmd_wi(c_in[k]), .cmd_eo(c_out[k]), .treq_wi(t_in[k]), .treq_eo(t_out[k]),
                    .hr_wi(453'd0), .st_wi(1088'd0), .st_ei(1088'd0), .sc_wi(48'd0), .sc_ei(48'd0), .arv_ei(1'b0), .art_ei(32'd0),
                    .arm_ei(1'b0), .arl_ei(1'b0), .ard_ei(512'd0), .dd_ei(548'd0), .rv_wi(1'b0), .re_wi(1'b0), .rr_wi(3'd0),
                    .rl_wi(1'b0), .rd_wi(512'd0), .dr_wi(520'd0), .ag_ei(10'd0), .l9_wi(514'd0), .rs_n0(514'd0), .rs_n1(514'd0),
                    .rs_s0(514'd0), .rs_s1(514'd0));
                assign mwe = u_s.u_core.tw_we; assign mkind = u_s.u_core.tw_kind; assign maddr = u_s.u_core.tw_addr;
                assign mdata = u_s.u_core.tw_data; assign mfault = u_s.u_core.tld_fault; assign swe = u_s.u_core.stm_tw_we;
            end else begin : g_e
                qfd_dv_slice2_et #(.MU_NU(4), .ARF(1), .RP(1), .TSLICE(k), .TQ_MUT(TQ)) u_s (.ck(ck), .rst_n(rst_n),
                    .cmd_ei(c_in[k]), .cmd_wo(c_out[k]), .treq_ei(t_in[k]), .treq_wo(t_out[k]),
                    .hr_ei(453'd0), .st_ei(1088'd0), .st_wi(1088'd0), .sc_ei(48'd0), .sc_wi(48'd0), .arv_wi(1'b0), .art_wi(32'd0),
                    .arm_wi(1'b0), .arl_wi(1'b0), .ard_wi(512'd0), .dd_wi(548'd0), .rv_ei(1'b0), .re_ei(1'b0), .rr_ei(3'd0),
                    .rl_ei(1'b0), .rd_ei(512'd0), .dr_ei(520'd0), .ag_wi(10'd0), .l9_wi(514'd0), .rs_n0(514'd0), .rs_n1(514'd0),
                    .rs_s0(514'd0), .rs_s1(514'd0));
                assign mwe = u_s.u_core.tw_we; assign mkind = u_s.u_core.tw_kind; assign maddr = u_s.u_core.tw_addr;
                assign mdata = u_s.u_core.tw_data; assign mfault = u_s.u_core.tld_fault; assign swe = u_s.u_core.stm_tw_we;
            end
        end
        // ---------------------------------------------------------------- per-slice checker
        reg [1050:0] gold [0:12671];
        initial $readmemh($sformatf("%s/s%0d/expected.hex", fx, k), gold);
        integer dcmd = -1, first_c = -1, nld = 0, req = -1, st = 0, u = 0, slot, nedge = 0, ncmd = 0;
        integer bad_cmd = 0, bad_align = 0, bad_order = 0, bad_tab = 0, bad_flt = 0, bad_coll = 0, st_ok2 = 0;
        reg [1050:0] want, got;
        integer c0;
        always @(posedge ck) begin
            c0 = cyc;                                    // this edge's index (c0's own NBA update lands after #1)
            if (rst_n) begin
                // CMD lockstep (first arrival fixes the measured lane + hop latency of THIS slice)
                if (c_in[k] != 0 && first_c < 0) begin first_c = c0; dcmd = c0 - first_p; end
                if (dcmd >= 0 && dcmd < 1000 && c0 - dcmd >= 0) begin
                    ncmd = ncmd + 1;
                    if (cmask(c_in[k]) !== cmask(ph[(c0 - dcmd) % 1024])) begin
                        bad_cmd = bad_cmd + 1;
                        if (bad_cmd <= 3) $display("TLD_CMD_MISMATCH slice=%0d c0=%0d", k, c0);
                    end
                end
                // ALIGN + ORDER
                if (t_in[k][8]) begin
                    if (nld >= pn || nld >= 64) begin bad_align = bad_align + 1; $display("TLD_UNEXPECTED_REQ slice=%0d c0=%0d", k, c0); end
                    else if (c0 - pe[nld] != dcmd) begin
                        bad_align = bad_align + 1;
                        if (bad_align <= 3) $display("TLD_ALIGN slice=%0d load=%0d treq_lane=%0d cmd_lane=%0d", k, nld, c0 - pe[nld], dcmd);
                    end
                    if (t_in[k][7:2] != 6'(nld + 1) || t_in[k][1:0] != 2'd0) begin
                        bad_order = bad_order + 1;
                        if (bad_order <= 3) $display("TLD_ORDER slice=%0d load=%0d stage=%0d user=%0d want_stage=%0d", k, nld, t_in[k][7:2], t_in[k][1:0], nld + 1);
                    end
                    req = c0; st = t_in[k][7:2]; u = t_in[k][1:0]; nld = nld + 1;
                end
            end
            #1;
            if (rst_n) begin
                if (mfault) begin bad_flt = bad_flt + 1; if (bad_flt <= 1) $display("TLD_FAULT slice=%0d c0=%0d", k, c0); end
                if (swe) bad_coll = bad_coll + 1;
                if (req >= 0 && c0 >= req + 4 && c0 < req + 4 + 88 && st >= 1 && st <= 36) begin
                    slot = c0 - (req + 4);
                    want = gold[(((st - 1) * 4) + u) * 88 + slot];
                    got = {maddr, mkind, mwe, mdata};
                    if (mwe !== want[1024] || (want[1024] && got !== want)) begin
                        bad_tab = bad_tab + 1;
                        if (bad_tab <= 3) $display("TLD_TABLE_MISMATCH slice=%0d stage=%0d user=%0d slot=%0d c0=%0d we=%0d want_we=%0d", k, st, u, slot, c0, mwe, want[1024]);
                    end
                    nedge = nedge + 1;
                    if (slot == 87 && st >= 2) st_ok2 = st_ok2 + 1;
                end
            end
        end
    end endgenerate
    // ------------------------------------------------------------------ run + verdict
    integer kk, fails, tot_ld;
    initial begin
        repeat (6) @(negedge ck); rst_n = 1;
        wait (tr_n > 0);
        wait (tr_i >= tr_n); repeat (600) @(negedge ck);
        fails = 0; tot_ld = 0;
        $display("PRODUCER table_req pulses=%0d (cpub39_1 trace)", pn);
        for (kk = 0; kk < pn && kk < 64; kk = kk + 1) if (ps[kk] != kk + 1) begin $display("PRODUCER_ORDER load=%0d stage=%0d", kk, ps[kk]); end
        if (pn != 36 && VAR != 5) begin $display("PRODUCER_COUNT %0d != 36", pn); fails = fails + 1; end
        if (VAR == 5 && pn != 35) begin $display("PRODUCER_COUNT(drop17) %0d", pn); end
        for (kk = 0; kk < NS; kk = kk + 1) fails = fails + sfail[kk];
        if (fails == 0) $display("TLD_CHAIN PASS VAR=%0d NS=%0d DLANE=%0d DHOP=%0d", VAR, NS, DLANE, DHOP);
        else $display("TLD_CHAIN FAIL VAR=%0d NS=%0d fails=%0d", VAR, NS, fails);
        $finish;
    end
    integer sfail [0:NS-1];
    initial for (kk = 0; kk < NS; kk = kk + 1) sfail[kk] = 0;
    // summary printer
    generate for (k = 0; k < NS; k = k + 1) begin : g_sum
        always @(negedge ck) if (tr_n > 0 && tr_i >= tr_n && cyc == tr_c[tr_n - 1] - ofs + 590) begin
            $display("SLICE %0d TSLICE=%0d cmd_lane=%0d cmd_checks=%0d bad_cmd=%0d loads=%0d bad_align=%0d bad_order=%0d table_edges=%0d bad_table=%0d stages2_36_loaded=%0d faults=%0d stream_tw=%0d",
                k, k, g_s[k].dcmd, g_s[k].ncmd, g_s[k].bad_cmd, g_s[k].nld, g_s[k].bad_align, g_s[k].bad_order, g_s[k].nedge, g_s[k].bad_tab,
                g_s[k].st_ok2, g_s[k].bad_flt, g_s[k].bad_coll);
            if (g_s[k].bad_cmd || g_s[k].bad_align || g_s[k].bad_order || g_s[k].bad_tab || g_s[k].bad_flt || g_s[k].bad_coll
                || g_s[k].nld != 36 || g_s[k].st_ok2 != 35 || g_s[k].nedge != 36 * 88)
            begin $display("SLICE_FAIL %0d", k); sfail[k] = 1; end
        end
    end endgenerate
endmodule

module tld_dly #(parameter integer W = 1, parameter integer D = 0) (input wire ck, input wire [W-1:0] i, output wire [W-1:0] o);
    generate if (D == 0) begin : g0
        assign o = i;
    end else begin : gd
        reg [W-1:0] s [0:D-1];
        integer j;
        initial for (j = 0; j < D; j = j + 1) s[j] = {W{1'b0}};
        always @(posedge ck) begin s[0] <= i; for (j = 1; j < D; j = j + 1) s[j] <= s[j - 1]; end
        assign o = s[D - 1];
    end endgenerate
endmodule
