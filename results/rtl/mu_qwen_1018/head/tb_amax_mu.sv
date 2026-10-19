`timescale 1ns/1ps
// MU-QWEN-HEAD (R4) behavioural bench for qfd_dv_amax_mu.  Verilator 5.050 --binary --timing.
//   Phase A (default-mode identity): qfd_dv_amax_mu #(.NU(1)) against amax_today_ref (the qfd_dv_slice2 block,
//     verbatim) under random STN / result / AMAX traffic: every output equal on every edge.
//   Phase B (4 users, chunked LM head): every user's head is NCH row chunks (STN ops armed with amax, S result words
//     of 16 logits each) issued interleaved at op level with the other users' chunks and non-head ops (back-to-back
//     included); AMAX clear / emit per user.  Each emitted {idx, val} must equal the single-shot argmax over the
//     head's ROWS logits (okey order, ties -> lowest index).  Logit modes: random 32-bit, small pool (ties
//     everywhere, +-0, negatives), chunk-boundary tie (the max only at rows 64k-1 and 64k), all equal.  Half of the
//     heads issue their chunks in row order, half in a random chunk order (the index-carrying merge is order-free).
//   PASS needs: 0 mismatches, every head emitted, mu_fault = 0, no emit-empty.
//   +neg : negative control -- one AMAX clear of a user whose head is open (a schedule violation): must FAIL (fault).
module tb_amax_mu;
    parameter integer MUT = 0;
    localparam integer NU = 4, NCH = 8, S = 4, CHR = S * 16, ROWS = NCH * CHR;
    integer HEADS = 120, ACYC = 60000, NEG = 0, seed = 1;
    reg ck = 1'b0;
    always #1 ck = ~ck;
    reg rst = 1'b0;
    reg c_stn = 0, stn_amax_bit = 0, r_v = 0, c_am = 0, am_clr = 0, am_emit_cmd = 0;
    reg [1:0] stn_user = 0, am_user = 0;
    reg [23:0] r_addr = 0;
    reg [511:0] r_d = 0;
    // ---------------- DUTs
    wire a1_v, a1_e, r1_v, r1_e, a4_v, a4_e, f1, f4;
    wire [23:0] a1_i, r1_i, a4_i;
    wire [31:0] a1_d, r1_d, a4_d;
    qfd_dv_amax_mu #(.NU(1)) u_one (.ck(ck), .rst(rst), .c_stn(c_stn), .stn_amax_bit(stn_amax_bit), .stn_user(stn_user), .stn_pend(1'b0),
        .r_v(r_v), .r_addr(r_addr), .r_d(r_d), .c_am(c_am), .am_clr(am_clr), .am_emit_cmd(am_emit_cmd), .am_user(am_user),
        .am_v(a1_v), .am_idx(a1_i), .am_val(a1_d), .emit_empty(a1_e), .mu_fault(f1));
    wire [115:0] cmd_q = {65'd0, stn_amax_bit, 44'd0, am_emit_cmd, am_clr, 4'd0};
    amax_today_ref u_ref (.ck(ck), .rst(rst), .c_stn(c_stn), .cmd_q(cmd_q), .go(c_stn | c_am),
        .kind(c_am ? 3'd6 : 3'd2), .r_v(r_v), .r_addr(r_addr), .r_d(r_d),
        .am_v(r1_v), .am_idx(r1_i), .am_val(r1_d), .emit_empty(r1_e));
    qfd_dv_amax_mu #(.NU(NU), .MUT(MUT)) u_mu (.ck(ck), .rst(rst), .c_stn(c_stn), .stn_amax_bit(stn_amax_bit), .stn_user(stn_user), .stn_pend(1'b0),
        .r_v(r_v), .r_addr(r_addr), .r_d(r_d), .c_am(c_am), .am_clr(am_clr), .am_emit_cmd(am_emit_cmd), .am_user(am_user),
        .am_v(a4_v), .am_idx(a4_i), .am_val(a4_d), .emit_empty(a4_e), .mu_fault(f4));

    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    // ---------------- per-user head state
    reg [31:0] lg [0:NU-1][0:ROWS-1];
    integer ord [0:NU-1][0:NCH-1];
    integer phase [0:NU-1], nxt [0:NU-1], done_h [0:NU-1], last_r [0:NU-1], emit_c [0:NU-1], hmode [0:NU-1];
    reg [23:0] base [0:NU-1];
    integer cyc = 0, errs = 0, eqerr = 0, emits = 0, empty_seen = 0, btie = 0, xtie = 0, permh = 0, b2b = 0, neg_done = 0;
    integer i, j, k, u, t, m;
    always @(posedge ck) cyc <= cyc + 1;
    always @(negedge ck) if (rst && a4_e) empty_seen = empty_seen + 1;

    task automatic idle;
        begin c_stn = 0; stn_amax_bit = 0; r_v = 0; c_am = 0; am_clr = 0; am_emit_cmd = 0; @(negedge ck); end
    endtask
    task automatic new_head(input integer uu);
        integer a, b, mm, kk; reg [31:0] mx;
        begin
            mm = $urandom % 4; hmode[uu] = mm;
            for (a = 0; a < ROWS; a = a + 1)
                case (mm)
                    0: lg[uu][a] = $urandom;
                    1: case ($urandom % 6) 0: lg[uu][a] = 32'h3f80_0000; 1: lg[uu][a] = 32'hbf80_0000; 2: lg[uu][a] = 32'h0000_0000;
                                           3: lg[uu][a] = 32'h8000_0000; 4: lg[uu][a] = 32'h4000_0000; default: lg[uu][a] = 32'h3f00_0000; endcase
                    2: lg[uu][a] = {1'b0, 8'h7e, 23'($urandom)} ;            // all < 1.0
                    default: lg[uu][a] = 32'h4120_0000;
                endcase
            if (mm == 2) begin                                                   // the max only at a chunk boundary
                kk = 1 + $urandom % (NCH - 1); mx = 32'h3f80_0000 + ($urandom % 4);
                lg[uu][kk * CHR - 1] = mx; lg[uu][kk * CHR] = mx;
            end
            for (a = 0; a < NCH; a = a + 1) ord[uu][a] = a;
            if ($urandom % 2) begin
                permh = permh + 1;
                for (a = NCH - 1; a > 0; a = a - 1) begin b = $urandom % (a + 1); kk = ord[uu][a]; ord[uu][a] = ord[uu][b]; ord[uu][b] = kk; end
            end
            base[uu] = 24'(uu * 24'h01_0000 + ($urandom % 64) * 16);
        end
    endtask
    task automatic head_ref(input integer uu, output reg [23:0] ri, output reg [31:0] rv);
        integer a, c, nmax; reg [31:0] bk;
        begin
            bk = okey(lg[uu][0]); ri = 0; rv = lg[uu][0];
            for (a = 1; a < ROWS; a = a + 1) if (okey(lg[uu][a]) > bk) begin bk = okey(lg[uu][a]); ri = 24'(a); rv = lg[uu][a]; end
            // statistics: is the max present in more than one chunk (a cross-chunk tie the merge must resolve)?
            c = -1; nmax = 0;
            for (a = 0; a < ROWS; a = a + 1) if (okey(lg[uu][a]) == bk && (a / CHR) != c) begin c = a / CHR; nmax = nmax + 1; end
            if (nmax > 1) xtie = xtie + 1;
            if (hmode[uu] == 2) btie = btie + 1;
            ri = ri + base[uu];
        end
    endtask
    task automatic noise_op;
        integer w;
        begin
            c_stn = 1; stn_amax_bit = 0; stn_user = 2'($urandom); c_am = 0; r_v = 0; @(negedge ck);
            c_stn = 0;
            for (w = 0; w < 1 + $urandom % 3; w = w + 1) begin
                r_v = 1; r_addr = 24'($urandom); r_d = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                                                       $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                @(negedge ck);
            end
            r_v = 0;
        end
    endtask
    task automatic chunk_op(input integer uu);
        integer w, q, row0;
        begin
            row0 = ord[uu][nxt[uu]] * CHR;
            c_stn = 1; stn_amax_bit = 1; stn_user = 2'(uu); c_am = 0; r_v = 0; @(negedge ck);
            c_stn = 0;
            for (w = 0; w < S; w = w + 1) begin
                if ($urandom % 4 == 0) begin r_v = 0; @(negedge ck); end
                r_v = 1; r_addr = base[uu] + 24'(row0 + 16 * w);
                for (q = 0; q < 16; q = q + 1) r_d[32 * q +: 32] = lg[uu][row0 + 16 * w + q];
                @(negedge ck);
            end
            r_v = 0; last_r[uu] = cyc;
            nxt[uu] = nxt[uu] + 1;
            if (nxt[uu] == NCH) phase[uu] = 2;
            if ($urandom % 2) begin b2b = b2b + 1; noise_op; end               // another op right behind the chunk
        end
    endtask

    reg [23:0] ri; reg [31:0] rv; integer left;
    initial begin
        if ($value$plusargs("seed=%d", seed)) ;
        if ($value$plusargs("heads=%d", HEADS)) ;
        if ($test$plusargs("neg")) NEG = 1;
        void'($urandom(seed));
        repeat (3) @(negedge ck); rst = 1; @(negedge ck);
        // ---------------- Phase A: NU = 1 identity against today's block
        for (t = 0; t < ACYC; t = t + 1) begin
            m = $urandom % 16;
            c_stn = (m == 0); stn_amax_bit = $urandom % 2; stn_user = 2'($urandom);
            c_am = (m == 1); am_clr = $urandom % 2; am_emit_cmd = $urandom % 2; am_user = 2'($urandom);
            r_v = ($urandom % 3) != 0; r_addr = 24'($urandom);
            for (k = 0; k < 16; k = k + 1) r_d[32 * k +: 32] = ($urandom % 3 == 0) ? 32'h3f80_0000 : (($urandom % 2) ? {1'b1, 31'($urandom % 8)} : $urandom);
            @(negedge ck);
            if ({a1_v, a1_i, a1_d, a1_e} !== {r1_v, r1_i, r1_d, r1_e} || f1 !== 1'b0) begin
                eqerr = eqerr + 1;
                if (eqerr <= 5) $display("EQ MISMATCH cyc %0d: mu1 {%b %h %h %b} ref {%b %h %h %b}", cyc, a1_v, a1_i, a1_d, a1_e, r1_v, r1_i, r1_d, r1_e);
            end
        end
        idle; idle;
        // fresh reset for phase B (phase A left random state everywhere)
        rst = 0; idle; rst = 1; idle; empty_seen = 0;
        $display("phase A: %0d edges compared, %0d mismatches", ACYC, eqerr);
        // ---------------- Phase B: 4 users, chunked heads, op-level interleave
        for (u = 0; u < NU; u = u + 1) begin phase[u] = 0; nxt[u] = 0; done_h[u] = 0; last_r[u] = -100; emit_c[u] = -100; end
        left = NU * HEADS;
        while (left > 0) begin
            u = $urandom % NU;
            if (done_h[u] == HEADS) begin idle; continue; end
            if ($urandom % 5 == 0) begin noise_op; continue; end
            if ($urandom % 6 == 0) begin idle; continue; end
            case (phase[u])
                0: if (cyc > emit_c[u] + 1) begin
                       new_head(u); nxt[u] = 0; phase[u] = 1;
                       c_am = 1; am_clr = 1; am_emit_cmd = 0; am_user = 2'(u); @(negedge ck); c_am = 0; am_clr = 0;
                   end else idle;
                1: begin
                       chunk_op(u);
                       if (NEG && !neg_done && nxt[u] == 3) begin           // schedule violation: clear an open head
                           neg_done = 1; c_am = 1; am_clr = 1; am_user = 2'(u); @(negedge ck); c_am = 0; am_clr = 0;
                       end
                   end
                default: if (cyc >= last_r[u] + 6) begin
                       c_am = 1; am_emit_cmd = 1; am_clr = 0; am_user = 2'(u); @(negedge ck); c_am = 0; am_emit_cmd = 0;
                       head_ref(u, ri, rv);
                       emits = emits + 1;
                       if (!(a4_v === 1'b1 && a4_i === ri && a4_d === rv)) begin
                           errs = errs + 1;
                           if (errs <= 8) $display("MISMATCH user %0d head %0d mode %0d: got v %b idx %h val %h, single-shot idx %h val %h",
                                                   u, done_h[u], hmode[u], a4_v, a4_i, a4_d, ri, rv);
                       end
                       emit_c[u] = cyc; done_h[u] = done_h[u] + 1; phase[u] = 0; left = left - 1;
                   end else idle;
            endcase
        end
        idle; idle;
        $display("phase B: users %0d heads/user %0d chunks/head %0d rows/head %0d emits %0d mismatches %0d", NU, HEADS, NCH, ROWS, emits, errs);
        $display("phase B: cross-chunk-tie heads %0d, chunk-boundary-tie heads %0d, permuted-order heads %0d, back-to-back other-op %0d, mu_fault %b, emit_empty %0d",
                 xtie, btie, permh, b2b, f4, empty_seen);
        if (eqerr == 0 && errs == 0 && emits == NU * HEADS && f4 === 1'b0 && empty_seen == 0 && xtie > 0 && btie > 0)
            $display("TB_AMAX_MU PASS MUT=%0d NEG=%0d seed=%0d", MUT, NEG, seed);
        else
            $display("TB_AMAX_MU FAIL MUT=%0d NEG=%0d seed=%0d (eq %0d, mismatches %0d, mu_fault %b, emit_empty %0d)", MUT, NEG, seed, eqerr, errs, f4, empty_seen);
        $finish;
    end
endmodule
