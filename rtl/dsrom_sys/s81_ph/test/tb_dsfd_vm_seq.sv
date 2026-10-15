`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// tb_dsfd_vm_seq (claude s81-grpA r6, 2026-10-14): exact bench of the S81 VM sequencer engine dsfd_vm_seq on the
// REAL VM master dsfd_sp_vm_m (VM v2: FE, 16 dsfd_vm_bgq tiles with the SRAM macro models, BE).  Clocks as
// tb_dsfd_sp_vm (serial ck = VCO / 4, stream cks = VCO / 3); the engine and the sequencer model run on cks.
//
// Sequencer model (engine 12 'vm', the die command plane): NJ jobs in program order, each SU or HC, each with ONE vm op
//   (CLIENT arm of its operand region: base16 / nrows, or GIVE).  Ops are issued under the 8-credit rule with unique
//   {jslot, op} tags, at most WIN jobs ahead of the oldest uncredited one.  A job's PRODUCER starts only when the vm
//   op's done arrives (the die program: the producer takes the arm as a predecessor) and writes the region's rows in a
//   random order through the dsfd_sp_ctrl VM port (vwe), interleaved at random with the other active producers (so
//   regions complete OUT of program order).  CONSUMERS: every t_inp_su / t_inp_hc pulse must be the next job of that
//   client in program order, all its rows must have been written, and the consumer then READS the region (vre) and
//   checks every row bit-exact.  Every 4th credited SU arm also re-reads its region through the PASS-THROUGH ops
//   XMAP + XGO (streamer X0 -> bus lane 0, t_bl), rows checked in order, the XGO done after its rows were issued.
// PASS iff: every job credited once in order, every read / stream row exact, every sequencer done once with a pending
//   tag, no fault (engine c_st, VM flt: incl. the VM's EARLY_READ assertion), within NCYC stream cycles.
// Negative controls (+define): OT_VMSEQ_MUT_EARLYCR / _ORDER / _NOFENCE (see dsfd_vm_seq.sv) must FAIL.
// ---------------------------------------------------------------------------------------------------------------
module tb_dsfd_vm_seq;
    parameter integer NJ = 120, WIN = 6, NRMAX = 40, NCYC = 60000, PGAP = 3, GIVEP = 8;
    reg clk = 0, cks = 0;
    always #2 clk = ~clk;
    always #1.5 cks = ~cks;
    reg rst_n = 0, rss_n = 0;
    integer cyc = 0, nbad = 0;
    integer SEED = 1, rs = 1;
    initial begin if (!$value$plusargs("SEED=%d", SEED)) SEED = 1; rs = SEED; end
    function automatic integer rnd(input integer m);
        begin rs = rs * 1103515245 + 12345; rnd = ((rs >>> 8) & 32'h7fffff) % m; end
    endfunction
    function automatic [511:0] rowdata(input integer j, input integer r);
        integer w; reg [31:0] h;
        begin
            for (w = 0; w < 16; w = w + 1) begin
                h = j * 32'h9E3779B1 ^ r * 32'h85EBCA77 ^ w * 32'hC2B2AE3D ^ SEED;
                h = h ^ (h >> 15); h = h * 32'h2C1B3C6D; h = h ^ (h >> 12);
                rowdata[32*w +: 32] = h;
            end
        end
    endfunction
    // ------------------------------------------------------------ DUT: engine + real VM
    wire t_swg, t_srg, t_err, vrv, dv, c_wv, c_l0v; wire [52:0] t_ks; wire [1025:0] t_srq; wire [511:0] vrq;
    wire [7:0] dt; wire [16*513-1:0] t_bl; wire [2:0] t_cts; wire [9:0] c_wd; wire [603:0] c_l0d; wire flt; wire [31:0] fvec;
    wire [2:0] max_occ; wire [3:0] t_rdy;
    reg vwe = 0, vre = 0; reg [13:0] vwa = 0, vra = 0; reg [511:0] vwd = 0;
    wire cv; wire [83:0] cd;
    reg [84:0] c_cmd = 0; wire [8:0] c_done; wire [1:0] c_st; wire inp_su, inp_hc;
    dsfd_sp_vm_m #(.MACRO(1)) u_vm (
        .ck(clk), .rst(rst_n), .cks(cks), .rss(rss_n),
        .f_swv(1'b0), .f_swd(527'd0), .t_swg(t_swg), .f_srv(1'b0), .f_srd(31'd0), .t_srg(t_srg),
        .t_ks(t_ks), .t_srq(t_srq), .t_err(t_err), .f_cap(13376'd0),
        .vwe(vwe), .vwa(vwa), .vwd(vwd), .vre(vre), .vra(vra), .vrv(vrv), .vrq(vrq), .cv(cv), .cd(cd), .dv(dv), .dt(dt),
        .f_svc(1027'd0), .f_coll(2100'd0), .t_cts(t_cts), .f_sel(515'd0), .f_col(515'd0), .f_hc(1026'd0), .t_bl(t_bl),
        .c_wv(c_wv), .c_wd(c_wd), .c_wr(1'b1), .t_rdy(t_rdy), .c_l0v(c_l0v), .c_l0d(c_l0d), .c_l0r(1'b1),
        .flt(flt), .fvec(fvec), .max_occ(max_occ));
    dsfd_vm_seq u_seq (.ck(cks), .rst(rss_n), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st),
        .v_cv(cv), .v_cd(cd), .v_dv(dv), .v_dt(dt), .v_flt(flt), .t_inp_su(inp_su), .t_inp_hc(inp_hc));
    // ------------------------------------------------------------ program
    integer j_cli [0:NJ-1], j_give [0:NJ-1], j_b16 [0:NJ-1], j_nr [0:NJ-1];
    integer j_wr [0:NJ-1];              // rows written by the producer
    integer j_cr [0:NJ-1];              // credited
    integer j_dn [0:NJ-1];              // vm op done seen
    integer j_pr [0:NJ-1];              // producer started
    integer nxt_cli [0:1];              // next job index of each client expected to be credited
    integer alloc = 0, k, r;
    initial begin
        #1;
        for (k = 0; k < NJ; k = k + 1) begin
            j_cli[k] = rnd(2); j_give[k] = (rnd(GIVEP) == 0); j_nr[k] = 1 + rnd(NRMAX);
            if (rnd(10) == 0) j_nr[k] = 16 * (1 + rnd(4));          // whole blocks too
            j_b16[k] = alloc; if (!j_give[k]) alloc = alloc + (j_nr[k] + 15) / 16;
            j_wr[k] = 0; j_cr[k] = 0; j_dn[k] = 0; j_pr[k] = 0;
        end
        if (alloc * 16 > 16384) begin $display("FAIL: bench region allocation %0d rows", alloc * 16); $finish; end
        nxt_cli[0] = 0; nxt_cli[1] = 0;
        while (nxt_cli[0] < NJ && j_cli[nxt_cli[0]] != 0) nxt_cli[0] = nxt_cli[0] + 1;
        while (nxt_cli[1] < NJ && j_cli[nxt_cli[1]] != 1) nxt_cli[1] = nxt_cli[1] + 1;
    end
    function automatic integer next_of(input integer c, input integer from);
        integer x; begin x = from + 1; while (x < NJ && j_cli[x] != c) x = x + 1; next_of = x; end
    endfunction
    // ------------------------------------------------------------ sequencer model (credits, tags, issue window)
    integer n_out = 0, j_iss = 0, oldest = 0, n_cred = 0, n_done = 0;
    reg [255:0] pend = 0;
    integer x_q [$];                    // pass-through streams to issue: job index
    integer x_state = 0, x_job = -1, x_tag = 0, x_rows = 0, x_ndone = 0, x_seen = 0;
    reg [7:0] tag;
    always @(posedge cks) begin
        c_cmd <= 85'd0;
        if (rss_n && cyc > 80 && n_out < 8) begin
            // pass-through XMAP / XGO (one stream at a time) have priority
            if (x_state == 0 && x_q.size() != 0) begin
                x_job = x_q.pop_front(); x_tag = 200 + (x_ndone % 50); x_state = 1;
            end
            if (x_state == 1 && !pend[x_tag]) begin           // XMAP {xp 0, go 0, lane 0, nrows - 1}
                tag = x_tag;
                c_cmd <= {1'b1, tag[7], 10'd5, 21'd0, 21'd0, 3'd7, 3'd0, 1'b0, 4'd0, 13'(j_nr[x_job] - 1), tag[6:0]};
                pend[tag] = 1'b1; n_out = n_out + 1; x_state = 2;
            end else if (x_state == 3 && !pend[x_tag]) begin  // XGO {xp 0, go 1, base}
                tag = x_tag;
                c_cmd <= {1'b1, tag[7], 10'd5, 21'd0, 21'd0, 3'd7, 3'd0, 1'b1, 3'd0, 14'(16 * j_b16[x_job]), tag[6:0]};
                pend[tag] = 1'b1; n_out = n_out + 1; x_state = 4; x_rows = 0;
            end else if (j_iss < NJ && j_iss < oldest + WIN) begin
                tag = j_iss;
                if (j_give[j_iss])
                    c_cmd <= {1'b1, tag[7], 10'(j_iss), 21'(j_iss * 3), 21'(j_iss * 7), 3'd0, 1'(j_cli[j_iss]), 10'h3FF, 10'h3FF, tag[6:0]};
                else
                    c_cmd <= {1'b1, tag[7], 10'(j_iss), 21'(j_iss * 3), 21'(j_iss * 7), 3'd0, 1'(j_cli[j_iss]),
                              10'(j_b16[j_iss]), 10'(j_nr[j_iss] - 1), tag[6:0]};
                if (pend[tag]) begin $display("FAIL cyc %0d: bench tag reuse %0d", cyc, tag); nbad = nbad + 1; end
                pend[tag] = 1'b1; n_out = n_out + 1; j_iss = j_iss + 1;
            end
        end
        if (c_done[8]) begin
            tag = c_done[7:0];
            if (!pend[tag]) begin $display("FAIL cyc %0d: done for tag %0d not pending", cyc, tag); nbad = nbad + 1; end
            pend[tag] = 1'b0; n_out = n_out - 1; n_done = n_done + 1;
            if (tag < NJ) begin
                j_dn[tag] = cyc;
                if (!j_give[tag]) j_pr[tag] = cyc + rnd(4) * rnd(PGAP + 1);     // producer start (often at once)
            end else if (x_state == 2) x_state = 3;
            else if (x_state == 4) begin
                if (x_rows > j_nr[x_job]) begin $display("FAIL: stream rows"); nbad = nbad + 1; end
                x_state = 5;                                              // wait for the remaining rows
            end
        end
        if (x_state == 5 && x_seen == j_nr[x_job]) begin x_state = 0; x_seen = 0; x_ndone = x_ndone + 1; end
    end
    // ------------------------------------------------------------ producers + consumers on the ctrl VM port
    integer wr_order [0:NJ-1][$];
    integer rd_q [$], rd_j [$];
    reg [511:0] exp_q [$];
    integer n_rd = 0, n_wr = 0, pick, c2, rr2;
    integer act [$];
    always @(posedge cks) begin
        vwe <= 1'b0; vre <= 1'b0;
        // producers become active
        for (k = 0; k < NJ; k = k + 1)
            if (j_pr[k] != 0 && j_pr[k] <= cyc && j_pr[k] > 0) begin
                // shuffle the region's rows once
                for (r = 0; r < j_nr[k]; r = r + 1) wr_order[k].push_back(r);
                for (r = j_nr[k] - 1; r > 0; r = r - 1) begin
                    pick = rnd(r + 1); rr2 = wr_order[k][r]; wr_order[k][r] = wr_order[k][pick]; wr_order[k][pick] = rr2;
                end
                act.push_back(k); j_pr[k] = -1;
            end
        // credits (client order)
        if (inp_su || inp_hc) begin
            for (c2 = 0; c2 < 2; c2 = c2 + 1) if ((c2 == 0) ? inp_su : inp_hc) begin
                k = nxt_cli[c2];
                if (k >= NJ) begin $display("FAIL cyc %0d: extra credit client %0d", cyc, c2); nbad = nbad + 1; end
                else begin
                    if (j_dn[k] == 0) begin $display("FAIL cyc %0d: credit for job %0d before its vm op done", cyc, k); nbad = nbad + 1; end
                    if (!j_give[k] && j_wr[k] != j_nr[k]) begin
                        $display("FAIL cyc %0d: credit for job %0d (client %0d) with %0d of %0d rows written", cyc, k, c2, j_wr[k], j_nr[k]);
                        nbad = nbad + 1;
                    end
                    j_cr[k] = cyc; n_cred = n_cred + 1;
                    if (!j_give[k]) begin
                        for (r = 0; r < j_nr[k]; r = r + 1) begin rd_q.push_back(16 * j_b16[k] + r); rd_j.push_back(k * 65536 + r); end
                        if (c2 == 0 && (n_cred % 4) == 0 && j_nr[k] > 1) x_q.push_back(k);
                    end
                    nxt_cli[c2] = next_of(c2, k);
                    while (oldest < NJ && j_cr[oldest] != 0) oldest = oldest + 1;
                end
            end
        end
        // one ctrl-port op a cycle: a consumer read or a producer write
        if (rss_n && cyc > 80) begin
            if (rd_q.size() != 0 && (act.size() == 0 || rnd(2) == 0)) begin
                vre <= 1'b1; vra <= rd_q[0];
                exp_q.push_back(rowdata(rd_j[0] / 65536, rd_j[0] % 65536));
                void'(rd_q.pop_front()); void'(rd_j.pop_front());
            end else if (act.size() != 0 && rnd(4) != 0) begin
                pick = rnd(act.size()); k = act[pick];
                r = wr_order[k].pop_front();
                vwe <= 1'b1; vwa <= 16 * j_b16[k] + r; vwd <= rowdata(k, r);
                j_wr[k] = j_wr[k] + 1; n_wr = n_wr + 1;
                if (wr_order[k].size() == 0) act.delete(pick);
            end
        end
    end
    always @(posedge cks) if (rss_n && vrv) begin
        if (exp_q.size() == 0) begin $display("FAIL: read data without a read"); nbad = nbad + 1; end
        else begin
            if (exp_q[0] !== vrq) begin nbad = nbad + 1; if (nbad < 12) $display("MISMATCH ctrl read %0d", n_rd); end
            void'(exp_q.pop_front()); n_rd = n_rd + 1;
        end
    end
    // ------------------------------------------------------------ X0 stream on bus lane 0
    integer n_xr = 0;
    always @(posedge clk) if (rst_n && t_bl[0]) begin
        if (x_job < 0 || x_seen >= j_nr[x_job]) begin $display("FAIL: stream row without a stream"); nbad = nbad + 1; end
        else begin
            if (t_bl[1 +: 512] !== rowdata(x_job, x_seen)) begin
                nbad = nbad + 1; if (nbad < 12) $display("MISMATCH stream job %0d row %0d", x_job, x_seen);
            end
            x_seen = x_seen + 1; x_rows = x_rows + 1; n_xr = n_xr + 1;
        end
    end
    // ------------------------------------------------------------ run
    integer fst = 0;
    always @(posedge cks) begin
        cyc = cyc + 1;
        if (c_st[0] && !fst) begin fst = 1; $display("FAULT cyc %0d: engine c_st fault (VM flt %0b fvec %h)", cyc, flt, fvec); end
    end
    integer arm_n = 0, give_n = 0;
    initial begin
        #200; rst_n = 1; rss_n = 1;
        wait (cyc == NCYC || (n_cred == NJ && rd_q.size() == 0 && exp_q.size() == 0 && x_q.size() == 0 && x_state == 0 && n_out == 0));
        repeat (40) @(posedge cks);
        for (k = 0; k < NJ; k = k + 1) begin
            if (j_give[k]) give_n = give_n + 1; else arm_n = arm_n + 1;
            if (j_cr[k] == 0) begin nbad = nbad + 1; if (nbad < 20) $display("FAIL: job %0d (client %0d) never credited (vm done %0d, written %0d / %0d)", k, j_cli[k], j_dn[k], j_wr[k], j_nr[k]); end
        end
        if (c_st[0] || flt) begin $display("FAIL: fault engine %0b VM %0b fvec %h", c_st[0], flt, fvec); nbad = nbad + 1; end
        if (n_out != 0 || x_state != 0 || x_q.size() != 0 || rd_q.size() != 0 || exp_q.size() != 0) begin
            $display("FAIL: incomplete program at end (out %0d xstate %0d queued streams %0d reads %0d responses %0d)",
                     n_out, x_state, x_q.size(), rd_q.size(), exp_q.size()); nbad = nbad + 1;
        end
        if (!c_st[1]) begin $display("FAIL: engine not online"); nbad = nbad + 1; end
        $display("RESULT jobs %0d (arm %0d give %0d) credited %0d dones %0d writes %0d reads %0d stream rows %0d (%0d streams) cycles %0d bad %0d",
                 NJ, arm_n, give_n, n_cred, n_done, n_wr, n_rd, n_xr, x_ndone, cyc, nbad);
        if (nbad == 0 && n_cred == NJ) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
