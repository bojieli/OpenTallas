`timescale 1ns/1ps
// S81/SVCG (2026-10-25): unit bench of the 2-beat fold gather lane (dsdv_svc_f2b_tx -> L boundary flops -> dsdv_svc_f2b_rx)
// against the DEC12 FOLD 2-BEAT CONTRACT (claude/s81-dec12-1024r@d206dfb226 lanes/S81.md 00:19):
//   port {beat, payload[1066:0]}; word {go_d[2131:0], go_v}; beat 0 payload = word[1066:0]; beat 1 (next cycle)
//   payload[1065:0] = word[2132:1067], payload[1066] = 0.  TX output = the face pin register (stands in for the last
//   OUT station), RX input = a pin register (stands in for the first IN station): a word presented to the TX in cycle t
//   leaves as beat 0 in t + 1 and reaches the RX output in t + L + 3 (one cycle more than a full-width face: t + L + 2).
// Phase A (exact): NW random words (random data incl. all-0 / all-1 halves), spacing 2 (back-to-back at the allowed rate)
//   or 2 + random gaps; idle cycles carry random v = 0 data.  Checks: every port beat == the contract bits; every RX word
//   == its TX word bit for bit at exactly t + L + 3; no RX word without a TX word; no fault.
// Phase B (rate): a word in the cycle after a word -> TX sticky fault (stays set); the dropped word never reaches RX.
// Phase C (RX order): a second RX fed directly: a lone beat 1 -> sticky fault; beat 0 (v) then beat 0 -> sticky fault;
//   beat 1 with the pad bit set -> sticky fault (three fresh RX instances).
// -DF2B_MUT=1: TX beat order swapped -> phase A must FAIL.
module tb_dsdv_svc_f2b;
    localparam integer W = 2133, P = 1067, L = 2, NW = 3000;
`ifndef F2B_MUT
`define F2B_MUT 0
`endif
    reg ck = 0, rn = 0;
    always #0.5 ck = ~ck;
    integer seed = 1, cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    reg v = 0; reg [W-2:0] d = 0;
    wire [P:0] o, li; wire rv; wire [W-2:0] rd; wire tf, rf;
    dsdv_svc_f2b_tx #(.W(W), .MUT(`F2B_MUT)) u_tx (.ck(ck), .rn(rn), .v(v), .d(d), .o(o), .fault(tf));
    // the lane: L boundary flops (the plan lane's src + dst ot_dp_st)
    reg [P:0] lane [0:L-1];
    always @(posedge ck) begin lane[0] <= o; for (int k = 1; k < L; k++) lane[k] <= lane[k-1]; end
    assign li = lane[L-1];
    dsdv_svc_f2b_rx #(.W(W)) u_rx (.ck(ck), .rn(rn), .i(li), .v(rv), .d(rd), .fault(rf));
    // phase C receivers
    reg [P:0] ci [0:2]; wire [2:0] cf; wire [2:0] cv; wire [W-2:0] cd [0:2];
    genvar g;
    generate for (g = 0; g < 3; g = g + 1) begin : g_c
        dsdv_svc_f2b_rx #(.W(W)) u (.ck(ck), .rn(rn), .i(ci[g]), .v(cv[g]), .d(cd[g]), .fault(cf[g]));
    end endgenerate

    // scoreboard: words by TX cycle
    reg [W-1:0] sent [0:NW+16]; integer sent_cyc [0:NW+16]; integer ns = 0, nr = 0, err = 0, perr = 0;
    reg pend = 0; reg [W-1:0] pword;
    function automatic [W-2:0] rnd_d(input integer k);
        reg [W-2:0] x;
        for (int i = 0; i < W - 1; i += 32) x[i +: 32] = $urandom;
        case (k % 17) 3: x[P-2:0] = '0; 5: x[W-2:P-1] = '1; 7: x = '0; 11: x = '1; default: ; endcase
        return x;
    endfunction
    // port-format check (TX side): o in cycle k+1 = beat 1 of the word of cycle k-1 when owed, else beat 0 of the word
    // of cycle k (idle cycles: beat 0 with v = 0 and the low half as presented); every bit compared
    reg [P:0] eo; reg eo_ok = 0;
    always @(posedge ck) if (rn) begin
        if (eo_ok && o !== eo) begin perr++; if (perr <= 5) $display("PORT mismatch cyc %0d", cyc); end
        eo <= pend ? {1'b1, 1'b0, pword[W-1:P]} : {1'b0, d[P-2:0], v};
        eo_ok <= 1'b1;
        pend <= v && !pend; pword <= {d, v};
        if (v && !pend && ns <= NW) begin sent[ns] = {d, v}; sent_cyc[ns] = cyc; ns = ns + 1; end
        if (rv) begin
            if (nr >= ns || {rd, 1'b1} !== sent[nr] || cyc != sent_cyc[nr] + L + 3) begin
                err++; if (err <= 5) $display("RX MISMATCH word %0d cyc %0d (sent cyc %0d)", nr, cyc, nr < ns ? sent_cyc[nr] : -1);
            end
            nr = nr + 1;
        end
    end
    integer nab = 0, ns_a, tf_a, rf_a, tf_b, tf_b2, nr_b, cf_c;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        void'($urandom(seed));
        for (int k = 0; k < 3; k++) ci[k] = '0;
        repeat (4) @(posedge ck); #0.1 rn = 1;
        // ---- phase A
        for (int k = 0; k < NW; k++) begin
            @(negedge ck); v = 1; d = rnd_d(k);
            @(negedge ck); v = 0; d = rnd_d(k + 5);              // beat 1 cycle: v = 0 (allowed), random idle data
            if (($urandom % 4) == 0) repeat (1 + $urandom % 3) begin @(negedge ck); v = 0; d = rnd_d(k + 9); end
            if (k % 500 == 0 && k > 0) nab++;
        end
        @(negedge ck); v = 0;
        repeat (L + 4) @(negedge ck);
        tf_a = tf; rf_a = rf; ns_a = ns;
        // ---- phase B: two words in consecutive cycles
        nr_b = nr;
        @(negedge ck); v = 1; d = rnd_d(1);
        @(negedge ck); v = 1; d = rnd_d(2);                        // rate violation: beat 1 owed
        @(negedge ck); v = 0;
        repeat (L + 4) @(negedge ck);
        tf_b = tf;
        repeat (20) @(negedge ck);
        tf_b2 = tf;                                                // sticky
        // ---- phase C
        @(negedge ck); ci[0] = {1'b1, {P{1'b0}}};                  // lone beat 1
        ci[1] = {1'b0, {(P-1){1'b0}}, 1'b1};                      // beat 0 with v ...
        ci[2] = {1'b0, {(P-1){1'b0}}, 1'b1};                      // beat 0 with v ...
        @(negedge ck); ci[0] = '0; ci[1] = {1'b0, {(P-1){1'b0}}, 1'b1};   // ... then beat 0 again (beat 1 missing)
        ci[2] = {1'b1, 1'b1, {(P-1){1'b0}}};                      // ... then beat 1 with the pad bit set
        @(negedge ck); ci[0] = '0; ci[1] = '0; ci[2] = '0;
        repeat (20) @(negedge ck);
        cf_c = cf;
        $display("F2B_UNIT A: sent %0d recv %0d (rx err %0d, port err %0d) tx fault %0d rx fault %0d | B: tx fault %0d -> %0d (sticky), rx words +%0d | C: rx faults %b | MUT %0d",
                 ns_a, nr_b, err, perr, tf_a, rf_a, tf_b, tf_b2, nr - nr_b, cf_c, `F2B_MUT);
        if (ns_a == NW && nr_b == NW && err == 0 && perr == 0 && tf_a == 0 && rf_a == 0 && tf_b == 1 && tf_b2 == 1 &&
            nr - nr_b == 1 && cf_c == 3'b111) $display("F2B_UNIT PASS");
        else $display("F2B_UNIT FAIL");
        $finish;
    end
endmodule
