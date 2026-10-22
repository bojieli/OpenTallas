`timescale 1ns/1ps
// tb_xhead3: lockstep of the structural successor qfd_dv_s5_xhead3 against the current leaf qfd_dv_s5_xhead
// (rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv + ot_qfd_xhead).  Both see the same a_d / cid / rst_n; the leaf answers lq / lq_v /
// lq_bad and fault_i reach the successor one edge later (its read requests leave one edge later).  Every output is
// compared every edge: new(t + 1) == old(t).  Stimulus: legal x-slice operations (descriptor, data beats aimed at the
// tile windows, go with the matching instruction, back-to-back / overlapped epochs, pooled k 24 / 32 at split 7),
// interleaved with illegal / random words (faults), random leaf answers, quiesced mid-run resets.
// +seed=N +cycles=N +cid=N.  Prints S5_XH3_EQ PASS <compares> ... or S5_XH3_EQ FAIL <first mismatch>.
module tb_xhead3;
    localparam integer AW = 24, NW = 18, XCW = 12, NH = 8, NR = 16, IBW = 379, FW = 1187, HW = 1567, DESC = 73;
    reg ck = 1'b0;
    reg rst_n = 1'b0;
    reg [5:0] cid = 6'd0;
    reg fault_i = 1'b0, fault_i_d = 1'b0;
    reg [HW-1:0] a_d = {HW{1'b0}};
    reg [511:0] lq = 512'd0, lq_d = 512'd0;
    reg [7:0] lq_v = 8'hff, lq_v_d = 8'hff, lq_bad = 8'd0, lq_bad_d = 8'd0;
    wire [515:0] o_n, o_s, n_n, n_s;
    wire [1:0] o_lwv, o_lwep, o_lcv, o_lcep, n_lwv, n_lwep, n_lcv, n_lcep;
    wire [11:0] o_lwoff, n_lwoff;
    wire [127:0] o_lwm, n_lwm;
    wire [2047:0] o_lwd, n_lwd;
    wire [143:0] o_lwctl, n_lwctl;
    wire [7:0] o_lrv, o_lrt, o_lrep, n_lrv, n_lrt, n_lrep;
    wire [223:0] o_lrp, n_lrp;
    wire o_lrst, n_lrst, o_flt, n_flt;
    qfd_dv_s5_xhead u_old (.ck(ck), .rst_n(rst_n), .cid(cid), .fault_i(fault_i), .a_d(a_d), .n_d(o_n), .s_d(o_s),
        .lw_v(o_lwv), .lw_ep(o_lwep), .lc_v(o_lcv), .lc_ep(o_lcep), .lw_off(o_lwoff), .lw_m(o_lwm), .lw_d(o_lwd),
        .lw_ctl(o_lwctl), .lr_v(o_lrv), .lr_t(o_lrt), .lr_ep(o_lrep), .lr_p(o_lrp), .lq(lq), .lq_v(lq_v),
        .lq_bad(lq_bad), .l_rst_n(o_lrst), .fault(o_flt));
    qfd_dv_s5_xhead3 u_new (.ck(ck), .rst_n(rst_n), .cid(cid), .fault_i(fault_i_d), .a_d(a_d), .n_d(n_n), .s_d(n_s),
        .lw_v(n_lwv), .lw_ep(n_lwep), .lc_v(n_lcv), .lc_ep(n_lcep), .lw_off(n_lwoff), .lw_m(n_lwm), .lw_d(n_lwd),
        .lw_ctl(n_lwctl), .lr_v(n_lrv), .lr_t(n_lrt), .lr_ep(n_lrep), .lr_p(n_lrp), .lq(lq_d), .lq_v(lq_v_d),
        .lq_bad(lq_bad_d), .l_rst_n(n_lrst), .fault(n_flt));
    localparam integer OW = 516 * 2 + 8 + 12 + 128 + 2048 + 144 + 24 + 224 + 2;
    wire [OW-1:0] o_all = {o_n, o_s, o_lwv, o_lwep, o_lcv, o_lcep, o_lwoff, o_lwm, o_lwd, o_lwctl, o_lrv, o_lrt, o_lrep,
                           o_lrp, o_lrst, o_flt};
    wire [OW-1:0] n_all = {n_n, n_s, n_lwv, n_lwep, n_lcv, n_lcep, n_lwoff, n_lwm, n_lwd, n_lwctl, n_lrv, n_lrt, n_lrep,
                           n_lrp, n_lrst, n_flt};
    reg [OW-1:0] o_prev;

    // ---- the column's tile ids (copy of the strap function) ----
    function automatic integer tid(input integer c, input integer r);
        integer dr, bc, br, lbc, lbr, blk, z, p, i;
        begin
            dr = (r < NH) ? NH + r : NH - 1 - (r - NH);
            bc = 4; br = 4; lbc = 2; lbr = 2;
            blk = (c / bc) * (2 * NH / br) + dr / br;
            z = 0; p = 0;
            for (i = 0; i < 2; i = i + 1) begin
                if (i < lbc) begin z = z | (((c % bc) >> i) & 1) << p; p = p + 1; end
                if (i < lbr) begin z = z | (((dr % br) >> i) & 1) << p; p = p + 1; end
            end
            tid = bc * br * blk + z;
        end
    endfunction

    integer seed, cycles, cyc, compares, mism, pass_start;
    integer n_lw, n_en, n_lr, n_go, n_vd, n_pool, c_flt, n_ops, n_rst, n_bits_nz;
    // generator state
    integer ph_state, gap, beats, k_cur, sp_cur, tiles_cur, ep_cur, go_due, next_go_min, q, noise, quiet;
    integer w_rows [0:NR-1];
    reg [AW-1:0] xb_cur;
    reg rnd_cur;
    reg [5:0] ksel;
    integer ex_ep, pend_go;           // the epoch whose data is loaded and waiting for its go
    integer i, r, bad;
    function automatic integer urand(input integer n);
        urand = (n <= 1) ? 0 : ($urandom % n);
    endfunction
    function automatic integer pick_k(input integer pooled);
        integer x;
        begin
            x = urand(3);
            if (pooled != 0) pick_k = (urand(2) == 0) ? 24 : 32;
            else pick_k = (x == 0) ? 2 : (x == 1) ? 6 : 8;
        end
    endfunction
    reg [HW-1:0] w;
    task automatic make_desc(input integer ep);
        integer pooled, rr2, pr, emin, fm;
        begin
            pooled = (urand(4) == 0);
            k_cur = pick_k(pooled);
            sp_cur = pooled ? 7 : 7 + urand(5);
            xb_cur = pooled ? (AW'(urand(1 << 12)) << 6) : AW'(urand(1 << 16));
            if (urand(16) == 0) xb_cur = AW'($urandom);          // anywhere (beat wrap)
            rnd_cur = urand(2);
            tiles_cur = 1 + urand(3);
            fm = 4 * k_cur - 1;
            for (rr2 = 0; rr2 < NR; rr2 = rr2 + 1) begin
                q = tid(cid, rr2) & ((1 << (sp_cur - 2)) - 1);
                pr = 4 * k_cur * q;
                emin = xb_cur + pr;
                w_rows[rr2] = ((emin >> 6) + ((fm >= 64 && rr2 >= NH) ? 1 : 0)) & ((1 << 18) - 1);
            end
            w = {HW{1'b0}};
            w[1 + IBW + 0] = 1'b1;                                  // d_v
            w[1 + IBW + 1] = ep[0];
            w[1 + IBW + 2 +: AW] = xb_cur;
            w[1 + IBW + 26 +: XCW] = XCW'(k_cur);                   // x_cs = k
            w[1 + IBW + 38 +: XCW] = 12'd1;                         // x_ks = 1
            w[1 + IBW + 50 +: 4] = 4'(sp_cur);
            w[1 + IBW + 54 +: NW] = NW'(k_cur);
            w[1 + IBW + 72] = rnd_cur;
            if (urand(64) == 0) w[1 + IBW + 26 +: XCW] = XCW'(urand(40));   // occasional illegal descriptor
            if (urand(64) == 0) w[1 + IBW + 50 +: 4] = 4'(urand(16));
        end
    endtask
    task automatic make_beat(input integer ep);
        integer fb;
        begin
            w = {HW{1'b0}};
            for (i = 0; i < HW / 32 + 1; i = i + 1) w[32 * i +: 32] = $urandom;
            w[0] = 1'b0;
            w[1 + IBW + 0] = 1'b0;                                  // no descriptor
            w[1 + IBW + DESC] = 1'b1;                               // fv
            w[1 + IBW + DESC + 1] = ep[0];
            fb = w_rows[urand(NR)] + urand(3) - 1;
            if (urand(8) == 0) fb = $urandom;
            w[1 + IBW + DESC + 2 +: 18] = 18'(fb);
            if (urand(32) == 0) w[1 + IBW + DESC + 1] = ~ep[0];
        end
    endtask
    task automatic make_go(input integer ep);
        begin
            w = {HW{1'b0}};
            for (i = 0; i < IBW / 32 + 1; i = i + 1) w[1 + 32 * i +: 32] = $urandom;
            w[0] = 1'b1;
            w[1 + IBW - 2*NW +: NW] = NW'(tiles_cur);               // tiles
            w[1 + IBW - 3*NW +: NW] = NW'(k_cur);                   // k
            w[1 + 13*AW + 12] = 1'b0;                               // wsrc
            w[1 + 8*AW + 12 +: AW] = xb_cur;
            w[1 + 7*AW + 12 +: AW] = 24'd1;                         // x_ks
            w[1 + 6*AW + 12 +: AW] = 24'd0;                         // x_js
            w[1 + 5*AW + 12 +: AW] = AW'(k_cur);                    // x_cs
            w[1 + 5*AW + 5 +: 4] = 4'(sp_cur);
            w[1 + 4*AW + 4] = rnd_cur;
            w[1 + IBW +: FW] = {FW{1'b0}};
            for (i = 0; i < FW / 32; i = i + 1) w[1 + IBW + 99 + 32 * i +: 32] = (urand(2) == 0) ? $urandom : 0;
            w[1 + IBW + 0] = 1'b0; w[1 + IBW + DESC] = 1'b0;
            if (urand(48) == 0) w[1 + 8*AW + 12 +: AW] = AW'($urandom);   // occasional mismatching go
        end
    endtask

    always #5 ck = ~ck;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("cycles=%d", cycles)) cycles = 200000;
        if (!$value$plusargs("cid=%d", cid)) cid = 6'd0;
        void'($urandom(seed));
        compares = 0; mism = 0; n_lw = 0; n_en = 0; n_lr = 0; n_go = 0; n_vd = 0; n_pool = 0; c_flt = 0; n_ops = 0;
        n_rst = 0; n_bits_nz = 0;
        ph_state = 0; gap = 4; beats = 0; ep_cur = 0; go_due = 0; next_go_min = 0; noise = 0; quiet = 0; pend_go = 0;
        pass_start = 40;
        o_prev = {OW{1'b0}};
        rst_n = 1'b0;
        repeat (4) @(negedge ck);
        rst_n = 1'b1;
        for (cyc = 0; cyc < cycles; cyc = cyc + 1) begin
            @(negedge ck);
            // ---- compare: new(now) against old(previous edge) ----
            if (cyc >= pass_start) begin
                compares = compares + 1;
                if (n_all !== o_prev) begin
                    mism = mism + 1;
                    if (mism <= 4) begin
                        $display("S5_XH3_EQ MISMATCH cyc %0d", cyc);
                        for (i = 0; i < OW; i = i + 1)
                            if (n_all[i] !== o_prev[i]) begin bad = i; end
                        $display("  highest differing output bit %0d (o_all index; n_d at top)", bad);
                        if (n_n !== o_prev[OW-1 -: 516]) $display("  n_d differs");
                        if (n_s !== o_prev[OW-517 -: 516]) $display("  s_d differs");
                        if (n_lwd !== o_prev[OW-1032-8-12-128-1 -: 2048]) $display("  lw_d differs");
                        if (n_lwctl !== o_prev[OW-1032-8-12-128-2048-1 -: 144]) $display("  lw_ctl differs");
                        if (n_lrp !== o_prev[2 +: 224]) $display("  lr_p differs");
                        if (n_flt !== o_prev[0]) $display("  fault differs");
                    end
                end
            end
            o_prev = o_all;
            // coverage
            if (|o_lwv) n_lw = n_lw + 1;
            for (i = 0; i < 16; i = i + 1) if (o_lwctl[9*i + 8]) n_en = n_en + 1;
            if (|o_lrv) n_lr = n_lr + 1;
            if (o_n[0]) n_go = n_go + 1;
            if (o_n[515]) n_vd = n_vd + 1;
            if (o_flt) c_flt = c_flt + 1;
            if (|o_n[380 +: 128]) n_bits_nz = n_bits_nz + 1;
            // ---- next inputs ----
            lq_d = lq; lq_v_d = lq_v; lq_bad_d = lq_bad; fault_i_d = fault_i;
            for (i = 0; i < 16; i = i + 1) lq[32 * i +: 32] = $urandom;
            lq_v = (urand(4000) == 0) ? 8'(~(1 << urand(8))) : 8'hff;
            lq_bad = (urand(20000) == 0) ? 8'(1 << urand(8)) : 8'd0;
            fault_i = (urand(30000) == 0) ? 1'b1 : (urand(50) == 0 ? 1'b0 : fault_i);
            w = {HW{1'b0}};
            if (quiet > 0) begin
                // quiesced reset window
                quiet = quiet - 1;
                if (quiet == 30) rst_n = 1'b0;
                if (quiet == 26) begin rst_n = 1'b1; n_rst = n_rst + 1; end
                if (quiet == 0) begin ph_state = 0; gap = 2; pend_go = 0; next_go_min = cyc; ep_cur = 0; end
                if (quiet == 31) pass_start = cyc + 40;          // stop comparing from the reset edge on
            end else if (noise > 0) begin
                noise = noise - 1;
                if (urand(3) == 0) for (i = 0; i < HW / 32 + 1; i = i + 1) w[32 * i +: 32] = $urandom;
                if (urand(2) == 0) w[0] = 1'b0;
                if (noise == 0) begin quiet = 140; end
            end else begin
                // legal stream: desc(e) .. beats(e) .. go(e) at >= next_go_min; next desc(e') right after the go
                case (ph_state)
                    0: begin                                     // gap, then descriptor
                        if (gap > 0) gap = gap - 1;
                        else begin make_desc(ep_cur); beats = 2 + urand(12); gap = 2 + urand(3); ph_state = 1; end
                    end
                    1: begin                                     // data beats (>= 3 edges behind the descriptor)
                        if (gap > 0) begin gap = gap - 1; if (urand(3) == 0) make_beat(ep_cur ^ 1); end
                        else if (beats > 0) begin make_beat(ep_cur); beats = beats - 1; end
                        else begin ph_state = 2; gap = urand(4); end
                    end
                    2: begin                                     // go when the previous op ends (back-to-back allowed)
                        if (gap > 0) gap = gap - 1;
                        else if (cyc >= next_go_min) begin
                            make_go(ep_cur);
                            n_ops = n_ops + 1;
                            next_go_min = cyc + 8 * k_cur * tiles_cur - 1 + ((urand(3) == 0) ? 0 : urand(4));
                            // the next descriptor claims the other epoch: it must reach the head after this go's
                            // g_q (5 edges), the previous op's last edge on that epoch
                            ep_cur = ep_cur ^ 1; ph_state = 0; gap = 6 + urand(3);
                            if (urand(150) == 0) noise = 50 + urand(200);
                            else if (urand(60) == 0) quiet = 140;
                        end
                    end
                endcase
            end
            a_d = w;
        end
        $display("S5_XH3_COVER ops %0d lw_v %0d en %0d lr_v %0d go %0d xvalid %0d xnz %0d fault %0d resets %0d",
                 n_ops, n_lw, n_en, n_lr, n_go, n_vd, n_bits_nz, c_flt, n_rst);
        if (mism == 0 && compares > 0 && n_en > 0 && n_vd > 0)
            $display("S5_XH3_EQ PASS %0d compares seed %0d cid %0d", compares, seed, cid);
        else begin
            $display("S5_XH3_EQ FAIL %0d mismatches of %0d compares seed %0d cid %0d", mism, compares, seed, cid);
            $fatal(1, "S5_XH3_EQ FAIL");
        end
        $finish;
    end
endmodule
