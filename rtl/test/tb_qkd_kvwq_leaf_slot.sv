// Slot cell qkd_kvwq_leaf_s_w129_m (rtl/qwen_sys/kv_die_20261009/qkd_kvwq_leaf_slot.sv) driven ONLY through its die
// buses.  Bit offsets of every field come from kvwq_leaf_slot_map.vh, which bench.sh generates from
// tools/qwen_kv_die/kv_die.py BINDINGS (the die's bind convention), not from the wrapper: a wrapper that packs a bus
// in another order fails.  The reference is a transaction-level scoreboard written here (no DUT code):
//   feed   : n == c one cycle after its pin flop (two edges), all 293 bits, every cycle
//   take   : a valid feed word whose lane field equals the strap is held (a later one replaces it)
//   push   : a held, unsent word is written once when room was seen: w_v pulse + {sec, data, tag} exact
//   done   : a return wd_v with the held+sent tag frees the leaf and raises dp_v; any other return raises dp_bad
//   chain  : dn_v / dn_bad pass to dp_v / dp_bad (ORed)
// Coverage floors: pushes, dones, bads, replaced words must all be > 0.  -D OT_QKD_KVWQ_LEAF_MUT must FAIL.
`timescale 1ns/1ps
`include "kvwq_leaf_slot_map.vh"
module tb_qkd_kvwq_leaf_slot;
    parameter integer N = 60000;
    reg ck = 0, rst_n = 0;
    reg  [2:0]   lane = 0;
    reg  [292:0] c = 0;
    wire [292:0] n;
    reg  [1:0]   dn = 0;
    wire [1:0]   dp;
    wire [289:0] w;
    reg  [10:0]  wr = 0;
    qkd_kvwq_leaf_s_w129_m u (.ck(ck), .rst_n(rst_n), .lane(lane), .c(c), .n(n), .dn(dn), .dp(dp), .w(w), .wr(wr));
    always #1 ck = ~ck;

    // stimulus fields (TB side)
    reg s_cv, s_room, s_wdv, s_dnv, s_dnbad;
    reg [255:0] s_cd; reg [23:0] s_csec; reg [2:0] s_clane; reg [8:0] s_ctag, s_wdtag;
    // scoreboard state
    reg [292:0] c1 = 0;                         // feed history
    reg p_cv = 0, p_room = 0, p_wdv = 0; reg [255:0] p_cd; reg [23:0] p_csec; reg [2:0] p_clane; reg [8:0] p_ctag, p_wdtag;
    reg held = 0, sent = 0; reg [255:0] h_d; reg [23:0] h_sec; reg [8:0] h_tag;
    reg [255:0] e_wd = 0; reg [23:0] e_wsec = 0; reg [8:0] e_wtag = 0;
    reg e_wvalid_seen = 0;
    integer i, bad = 0, seed = 11, n_push = 0, n_done = 0, n_bad = 0, n_repl = 0, n_feed = 0, k;
    reg take = 0, push = 0, done = 0, isbad = 0;
    reg [31:0] rnd;

    task randw; output [255:0] o; integer j; begin for (j = 0; j < 8; j = j + 1) o[32*j +: 32] = $random(seed); end endtask

    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 11;
        lane = $random(seed);
        repeat (4) @(posedge ck);
        @(negedge ck); rst_n = 1;
        for (i = 0; i < N; i = i + 1) begin
            // ---- drive (negedge) ----
            rnd = $random(seed);
            s_cv = (rnd[3:0] < 5);
            randw(s_cd); s_csec = $random(seed); s_ctag = $random(seed);
            s_clane = rnd[5] ? lane : rnd[10:8];
            s_room = (rnd[14:12] != 0);
            // returns: mostly the held tag after a send, sometimes a foreign tag
            s_wdv = held && sent ? (rnd[19:16] < 3) : (rnd[19:16] == 0);
            s_wdtag = (rnd[21:20] != 0) ? h_tag : $random(seed);
            s_dnv = (rnd[26:24] == 0); s_dnbad = (rnd[30:27] == 0);
            c = 0; c[`C_V] = s_cv; c[`C_D +: 256] = s_cd; c[`C_SEC +: 24] = s_csec; c[`C_LANE +: 3] = s_clane; c[`C_TAG +: 9] = s_ctag;
            wr = 0; wr[`WR_ROOM] = s_room; wr[`WR_WDV] = s_wdv; wr[`WR_WDTAG +: 9] = s_wdtag;
            dn = 0; dn[`DN_V] = s_dnv; dn[`DN_BAD] = s_dnbad;
            @(posedge ck); #0.2;
            // ---- check the outputs of this edge against the expectations computed for it ----
            if (i > 3) begin
                if (n !== c1) begin bad = bad + 1; if (bad < 5) $display("feed mismatch at %0d", i); end
                if (w[`W_V] !== push) begin bad = bad + 1; if (bad < 5) $display("w_v mismatch at %0d", i); end
                if (e_wvalid_seen && (w[`W_DATA +: 256] !== e_wd || w[`W_SEC +: 24] !== e_wsec || w[`W_TAG +: 9] !== e_wtag))
                    begin bad = bad + 1; if (bad < 5) $display("w payload mismatch at %0d", i); end
                // the done chain inputs are not pin-registered in the leaf (dp is the register): dn of this cycle
                if (dp[`DP_V] !== (s_dnv | done) || dp[`DP_BAD] !== (s_dnbad | isbad))
                    begin bad = bad + 1; if (bad < 5) $display("dp mismatch at %0d", i); end
            end
            // ---- scoreboard transition of THIS edge (inputs act one cycle after their pin flop) ----
            take = p_cv && (p_clane == lane);
            if (take) begin
                if (held) n_repl = n_repl + 1;
                held = 1; sent = 0; h_d = p_cd; h_sec = p_csec; h_tag = p_ctag;
            end else begin
                if (push) sent = 1;
                if (done) held = 0;
            end
            p_cv = s_cv; p_cd = s_cd; p_csec = s_csec; p_clane = s_clane; p_ctag = s_ctag;
            p_room = s_room; p_wdv = s_wdv; p_wdtag = s_wdtag;
            c1 = c; if (s_cv) n_feed = n_feed + 1;
            // ---- what the NEXT edge must show ----
            push  = held && !sent && p_room;
            done  = p_wdv && held && sent && (p_wdtag == h_tag);
            isbad = p_wdv && !done;
            if (push) begin e_wd = h_d; e_wsec = h_sec; e_wtag = h_tag; e_wvalid_seen = 1; n_push = n_push + 1; end
            if (done) n_done = n_done + 1;
            if (isbad) n_bad = n_bad + 1;
            @(negedge ck);
        end
        if (n_push < 100 || n_done < 100 || n_bad < 100 || n_repl < 20) begin
            $display("FAIL kvwq_leaf_slot coverage pushes=%0d dones=%0d bads=%0d replaced=%0d", n_push, n_done, n_bad, n_repl); $finish;
        end
        if (bad == 0) $display("PASS kvwq_leaf_slot cycles=%0d feed=%0d pushes=%0d dones=%0d bads=%0d replaced=%0d", N, n_feed, n_push, n_done, n_bad, n_repl);
        else $display("FAIL kvwq_leaf_slot mismatches=%0d of %0d cycles", bad, N);
        $finish;
    end
endmodule
