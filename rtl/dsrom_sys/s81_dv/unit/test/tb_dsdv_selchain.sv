`timescale 1ns/1ps
// S81/H23 (2026-10-24, COORD H3): exact chain bench of the on-die SEL_IDS producer.
//   bk_sel encoder dsdv_bk_selids (tap = u_sel.vo_s)  -> +1 (dsdv_bk_sel_vmtx vo_n merge register) + LXT edges (plan lane
//   xtier__bk_sel__seqhost, 65)  -> dsdv_seq_host SELR 1 (L0 sink + dsdv_sh_selr relay; the real unit, L0..L4)
//   -> s_hw_w + LW edges (unit__seqhost__svc_5, 7) / s_hw_e + LE edges (unit__seqhost__svc_11, 11)
//   -> dsdv_svc_selq (the svc entry leg of rsv_05 / rsv_11) -> the injected q words.
// Stimulus: NJOB jobs; per job a CTL job beat (uid 0x5C op 3, K, OT, mask 1) on vo, then the selector's egress IDX words
// (kind 5, part 0 + part 1, random gaps) = K ascending random 20-b positions, 16 a word, lv a prefix (last word partial),
// plus decoy words of another tag (must be ignored).  Also non-relay northbound beats on the rung between relay beats
// (they must cross the seqhost unchanged to its vo_n after 7 edges; relay beats must NOT reach vo_n).
// GOLDEN (TB model of svc_att's SEL_IDS frame, independent of the RTL): per index word with n = popcount(lv) > 0, a
// header q word {type 7, END 0, mask, tag 0, len 1, [19:10] n, [9:0] s_first} and the payload q word (rank s_first + e
// at [32 e +: 32] = its position zero-extended, 0 past n), consecutive, in word order; s_first = ranks before the word.
// PASS = both entries' q word streams equal the golden exactly, every header immediately followed by its payload, the
// rung transparency check, no fault anywhere in the clean jobs, and the negative check (a job-gate q word in the cycle
// of a relay word at entry W) raises the selq fault.  Reports the latency (edges) from the last word's part 1 at the
// vo tap to its payload q word at each entry (+1 = the entry's r1 register, which the dn tree starts from).
// +seed= +njob=.  Mutants: SEL_MUT 1 (encoder s_first frozen), SQ_MUT 1 (entry payload halves swapped).
`ifndef SEL_MUT
`define SEL_MUT 0
`endif
`ifndef SQ_MUT
`define SQ_MUT 0
`endif
module tb_dsdv_selchain;
    localparam integer V = 276, LXT = 65, LW = 7, LE = 11;
    reg ck = 0; always #0.5 ck = ~ck;
    reg rst_n = 0;
    reg [V-1:0] vo = 0;
    wire [V-1:0] eo; wire ef;
    dsdv_bk_selids #(.V(V), .EK(5), .UID(8'h5C), .MUT(`SEL_MUT)) u_enc (.ck(ck), .rst(rst_n), .vo(vo), .o(eo), .fault(ef));
    // vmtx merge register (+1) + rung lane LXT, with TB's own northbound non-relay beats merged on idle slots
    reg [V-1:0] xl [0:LXT]; reg [V-1:0] nb = 0; reg nb_on = 1;
    integer cyc = 0;
    always @(posedge ck) begin
        xl[0] <= eo;
        for (int k = 1; k <= LXT; k++) xl[k] <= xl[k - 1];
    end
    wire [V-1:0] vi_s = xl[LXT] | nb;
    wire [V-1:0] sh_vo_n, sh_vo_s; wire [76:0] t_host; wire [53:0] t_kd; wire [32:0] s_j; wire [291:0] s_hw_w, s_hw_e;
    wire cw_v; wire [9:0] cw_a; wire [255:0] cw_d;
    dsdv_seq_host #(.V(V), .SELR(1)) u_sh (.ck(ck), .rst_n(rst_n), .tap_k(8'h00), .sink_k(8'h00), .vi_s(vi_s), .vo_s(sh_vo_s),
        .vi_n({V{1'b0}}), .vo_n(sh_vo_n), .f_host(515'd0), .t_host(t_host), .f_lf(4'b0101), .f_ks(53'd0), .t_kd(t_kd),
        .s_j(s_j), .s_jd_w(2'b00), .s_jd_e(2'b00), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(9'd0), .s_hc_e(9'd0),
        .st_rg_w(2'b01), .st_rg_e(2'b01), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    reg [291:0] lw [0:LW-1]; reg [291:0] le [0:LE-1];
    always @(posedge ck) begin
        lw[0] <= s_hw_w; for (int k = 1; k < LW; k++) lw[k] <= lw[k - 1];
        le[0] <= s_hw_e; for (int k = 1; k < LE; k++) le[k] <= le[k - 1];
    end
    // entry pin flops (hp) then the selq legs
    reg [291:0] hpw = 0, hpe = 0; reg cqw = 0;
    always @(posedge ck) begin hpw <= lw[LW-1]; hpe <= le[LE-1]; end
    wire qvw, qve, hsw, hse, fw, fe; wire [511:0] qdw, qde;
    dsdv_svc_selq #(.MUT(`SQ_MUT)) u_qw (.ck(ck), .rn(rst_n), .hw(hpw), .cq_v(cqw), .hw_sel(hsw), .q_v(qvw), .q_d(qdw), .fault(fw));
    dsdv_svc_selq #(.MUT(`SQ_MUT)) u_qe (.ck(ck), .rn(rst_n), .hw(hpe), .cq_v(1'b0), .hw_sel(hse), .q_v(qve), .q_d(qde), .fault(fe));

    // ------------------------------------------------------------------ stimulus + golden
    integer NJOB = 4, SEED = 1;
    reg [V-1:0] st [0:65535]; integer ns = 0;
    reg [511:0] gq [$]; integer last_p1 [$], first_p0 [$], gq_job [$];
    reg [V-1:0] nbs [int]; integer n_nb = 0;
    function automatic [V-1:0] ctl(input [9:0] k, input [7:0] ot, input [3:0] m);
        reg [V-1:0] b; reg [185:0] cp; cp = '0; cp[7:0] = 8'h5C; cp[10:8] = 3'd3; cp[40:31] = k; cp[68:61] = ot; cp[72:69] = m;
        b = '0; b[0] = 1'b1; b[21 +: 186] = cp; ctl = b;
    endfunction
    task automatic put(input [V-1:0] b); st[ns] = b; ns++; endtask
    task automatic gap(input integer n); for (int i = 0; i < n; i++) put('0); endtask
    task automatic word(input [511:0] w); reg [V-1:0] b0, b1;
        b0 = '0; b0[0] = 1; b0[3:1] = 3'd5; b0[275:20] = w[255:0];
        b1 = '0; b1[0] = 1; b1[3:1] = 3'd5; b1[6] = 1; b1[275:20] = w[511:256];
        put(b0); if ($urandom % 3 == 0) gap(1 + $urandom % 2); put(b1);
    endtask
    task automatic job(input integer k, input [7:0] ot, input bit golden);
        integer pos [$]; integer rk = 0;
        begin reg [V-1:0] tj; tj = ctl(10'(k), ot, 4'd1); tj[21 + 8 +: 3] = 3'd2; put(tj); gap(1); end   // a tx job (op 2): ignored
        put(ctl(10'(k), ot, 4'd1)); gap(2 + $urandom % 4);
        begin int s [int]; while (s.num() < k) s[$urandom % (1 << 20)] = 1; foreach (s[p]) pos.push_back(p); end
        for (int wi = 0; wi * 16 < k; wi++) begin
            reg [511:0] w; integer n; n = (k - 16 * wi >= 16) ? 16 : k - 16 * wi;
            w = '0; w[511:508] = 4'd3; w[507:500] = ot;
            for (int e = 0; e < 16; e++) begin
                w[320 + e] = (e < n);
                w[20 * e +: 20] = (e < n) ? 20'(pos[16 * wi + e]) : 20'($urandom);   // stale lanes past lv: ignored
            end
            if ($urandom % 5 == 0) begin reg [511:0] d; d = w; d[507:500] = ot ^ 8'h3C; word(d); gap($urandom % 3); end   // decoy tag
            if (wi == 0) first_p0.push_back(ns);
            word(w);
            if (golden) begin
                reg [511:0] h, p; h = '0; h[511:508] = 4'd7; h[503] = 1'b1; h[491:480] = 12'd1; h[19:10] = 10'(n); h[9:0] = 10'(rk);
                p = '0; for (int e = 0; e < n; e++) p[32 * e +: 32] = 32'(pos[16 * wi + e]);
                gq.push_back(h); gq.push_back(p);
            end
            rk += n;
            if (wi * 16 + 16 >= k) last_p1.push_back(ns - 1);
            gap($urandom % 3);
        end
        gap(8);
    endtask

    // ------------------------------------------------------------------ monitors
    reg [511:0] sw [$]; reg [511:0] se_ [$]; integer cw_ [$], ce_ [$];
    integer pair_err = 0, nb_err = 0, relay_leak = 0, nb_lat = -1;
    reg pw = 0, pe = 0;
    reg [V-1:0] nbq [int];
    always @(posedge ck) begin
        #0.1;
        if (rst_n && qvw && !cqw) begin sw.push_back(qdw); cw_.push_back(cyc); end
        if (rst_n && qve) begin se_.push_back(qde); ce_.push_back(cyc); end
        // pairing: a header (type 7) must be followed on the next edge by a non-header word
        if (rst_n) begin
            if (pw && !(qvw && qdw[511:508] != 4'd7)) pair_err++;
            if (pe && !(qve && qde[511:508] != 4'd7)) pair_err++;
            pw = qvw && qdw[511:508] == 4'd7 && !cqw; pe = qve && qde[511:508] == 4'd7;
        end
        // seqhost rung north: relay beats never leave; TB beats leave unchanged 7 edges after vi_s (6 + RL)
        if (sh_vo_n != 0) begin
            if (sh_vo_n[0] && sh_vo_n[3:1] == 3'd0 && sh_vo_n[20:13] == 8'hA5) relay_leak++;
            else begin
                integer hit; hit = -1;
                foreach (nbq[c]) if (hit < 0 && nbq[c] == sh_vo_n) hit = c;
                if (hit < 0) nb_err++;
                else begin
                    if (nb_lat < 0) nb_lat = cyc - hit; else if (cyc - hit != nb_lat) nb_err++;
                    nbq.delete(hit);
                end
            end
        end
        cyc++;
    end
    always @(negedge ck) begin
        nb <= '0;
        if (rst_n && nb_on && cyc > 20 && cyc % 37 == 5 && xl[LXT] == '0) begin   // xl[LXT] = vi_s's relay part at the next edge
            reg [V-1:0] b; b = {V{1'b0}}; for (int k = 0; k < 9; k++) b[32 * k +: 32] = $urandom; b[0] = 1'b1;
            b[20:13] = 8'h00; b[3:1] = 3'(1 + $urandom % 7); if (b[3:1] == 3'd1 || b[3:1] == 3'd2) b[3:1] = 3'd5;
            nb <= b; nbq[cyc] = b; n_nb++;
        end
    end

    integer err = 0;
    initial begin
        integer first_job_cyc, pi, neg_ok, lat_w = -1, lat_e = -1, t0;
        void'($value$plusargs("seed=%d", SEED)); void'($value$plusargs("njob=%d", NJOB)); void'($urandom(SEED));
        gap(4);
        for (int j = 0; j < NJOB; j++) job((j == 0) ? 512 : (j == 1) ? 7 : 16 + $urandom % 497, 8'(8'h40 + j), 1);
        repeat (20) @(posedge ck); #0.2 rst_n = 1; repeat (30) @(posedge ck);
        t0 = cyc;
        for (pi = 0; pi < ns; pi++) begin #0.2 vo = st[pi]; @(posedge ck); end
        #0.2 vo = '0;
        repeat (LXT + 60) @(posedge ck);
        // compare
        if (sw.size() != gq.size() || se_.size() != gq.size()) err++;
        for (int k = 0; k < gq.size(); k++) begin
            if (k < sw.size() && sw[k] !== gq[k]) begin err++; if (err < 4) $display("SELC_MISMATCH W %0d got %h exp %h", k, sw[k][511:480], gq[k][511:480]); end
            if (k < se_.size() && se_[k] !== gq[k]) begin err++; if (err < 4) $display("SELC_MISMATCH E %0d", k); end
        end
        // job 0 = K 512 (32 index words): first IDX part 0 at the vo tap -> last SEL_IDS payload q word at entry W / E
        if (sw.size() >= 64 && se_.size() >= 64)
            $display("SELC_JOB0 K 512 words 32 vo_span %0d first_part0_to_last_payload W %0d E %0d", last_p1[0] - first_p0[0] + 1,
                     cw_[63] - (t0 + first_p0[0]) + 1, ce_[63] - (t0 + first_p0[0]) + 1);
        if (gq.size() >= 2 && sw.size() == gq.size()) lat_w = cw_[gq.size() - 1] - (t0 + last_p1[last_p1.size() - 1]) + 1;
        if (gq.size() >= 2 && se_.size() == gq.size()) lat_e = ce_[gq.size() - 1] - (t0 + last_p1[last_p1.size() - 1]) + 1;
        begin
            integer clean_f; clean_f = ef | fw | fe | t_host[75];
            if (clean_f) $display("SELC_FAULT enc %0d selq_w %0d selq_e %0d t_host_fault %0d", ef, fw, fe, t_host[75]);
            // negative: a job-gate q word in the cycle of the first relay word at entry W of one more job
            begin
                integer c0; c0 = sw.size();
                nb_on = 0; ns = 0; job(32, 8'h77, 0);
                for (pi = 0; pi < ns; pi++) begin
                    #0.2 vo = st[pi];
                    @(posedge ck);
                end
                #0.2 vo = '0;
                fork
                    begin : arm
                        while (!(hpw[0] && hpw[291:290] == 2'b11)) begin @(negedge ck); end
                        cqw = 1; @(posedge ck); #0.2 cqw = 0;
                    end
                    begin repeat (LXT + 60) @(posedge ck); end
                join
                neg_ok = fw;
            end
            err += clean_f + pair_err + nb_err + relay_leak + (neg_ok ? 0 : 1) + (nbq.num() != 0 ? 1 : 0);
            $display("SELC jobs %0d qwords_gold %0d w %0d e %0d pair_err %0d rung_beats %0d rung_lat %0d rung_err %0d rung_lost %0d relay_leak %0d lat_part1_to_payload_W %0d E %0d neg_fault %0d sel_mut %0d sq_mut %0d verdict=%s",
                     NJOB, gq.size(), sw.size(), se_.size(), pair_err, n_nb, nb_lat, nb_err, nbq.num(), relay_leak, lat_w, lat_e, neg_ok,
                     `SEL_MUT, `SQ_MUT, err == 0 ? "PASS" : "FAIL");
        end
        $finish;
    end
endmodule
