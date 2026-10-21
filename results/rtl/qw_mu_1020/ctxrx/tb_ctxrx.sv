`timescale 1ns/1ps
// QW-MU 10-20: standalone bench of qfd_mu_ctx_rx_die (the die-GEN form, whole rx_payload port) for its hard view.
// Random D2D RX traffic: context slots (1 in 6 edges) carrying canonical kind-12 records of users 0..3 (user 0 = the
// latency user's own context: loads nothing), random non-slot words, random unread payload bits.  Reference model in
// the bench: on the edge after a good filler slot ctx_x[128] = 1, ctx_x[127:0] = the mu_opcal.ctx_words record
// (4D43 | mask 1<<(u-1) | {tok18, pos18} at 36(u-1), other fields 0) and ctx_user = u; ctx_x[128] = 0 on every other edge
// (record bits are don't-care then); mu_fault stays 0.
// +bad=N: the N-th context slot carries a bad record (kind 11): PASS = mu_fault rises on the next edge and stays.
// -GMUT=1 (record loaded into the wrong user): TB_CTXRX FAIL (the mutant witness).
module tb_ctxrx;
    parameter integer MUT = 0;
    reg ck = 0, rst_n = 0;
    reg slot = 0, rxv = 0;
    reg [547:0] pay = 0;
    wire [128:0] cx; wire [1:0] cu; wire mf;
    qfd_mu_ctx_rx_die #(.NU(4), .MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .prog_context_slot(slot), .prog_rx_v(rxv),
        .rx_payload(pay), .ctx_x(cx), .ctx_user(cu), .mu_fault(mf));
    always #0.5 ck = ~ck;
    integer bad = -1, nslot = 0, nld = 0, err = 0, det = -1, cyc;
    reg         e_ld; reg [127:0] e_rec; reg [1:0] e_u; reg e_bad;
    reg [1:0] u; reg [17:0] tok; reg [12:0] pos; reg [15:0] ep; reg [58:0] tag; reg [127:0] r;
    initial begin
        if (!$value$plusargs("bad=%d", bad)) bad = -1;
        e_ld = 0; e_bad = 0;
        repeat (4) @(posedge ck);
        #0.1 rst_n = 1;
        for (cyc = 0; cyc < 6000; cyc = cyc + 1) begin
            @(negedge ck);
            pay = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                   $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
            slot = ($urandom % 6) == 0; rxv = slot; e_ld = 0; e_bad = 0;
            if (slot) begin
                u = $urandom % 4; tok = $urandom % 151936; pos = $urandom; ep = {u, 14'($urandom)};
                ep[15:14] = 2'($urandom); ep[1:0] = u;   // TAG epoch[1:0] = user (TAG[44:43])
                tag = {ep, 6'd0, tok, pos, 6'd0};
                pay[58:0] = tag; pay[516:512] = 5'd0;
                pay[547:517] = {5'd0, (nslot == bad) ? 4'd11 : 4'd12, 6'd63, ep};
                e_bad = (nslot == bad);
                r = 128'd0;
                if (u != 0) begin
                    r[127:112] = 16'h4D43; r[108 + u - 1] = 1'b1;
                    r[36 * (u - 1) + 18 +: 18] = tok; r[36 * (u - 1) +: 18] = {5'd0, pos};
                end
                e_ld = !e_bad && u != 0; e_rec = r; e_u = u;
                nslot = nslot + 1;
            end
            @(posedge ck); #0.1;
            if (cx[128] !== e_ld) begin err = err + 1; if (err < 5) $display("ERR cyc %0d load %b exp %b", cyc, cx[128], e_ld); end
            else if (e_ld) begin
                nld = nld + 1;
                if (cx[127:0] !== e_rec || cu !== e_u) begin
                    err = err + 1; if (err < 5) $display("ERR cyc %0d user %0d rec %h exp %h ctx_user %0d", cyc, e_u, cx[127:0], e_rec, cu);
                end
            end
            if (mf && det < 0) det = e_bad ? (nslot - 1) : -2;
            if (!mf && det >= 0) begin err = err + 1; $display("ERR mu_fault dropped"); end
        end
        if (bad >= 0) begin
            if (det == bad && err == 0) $display("TB_CTXRX PASS (bad record at slot %0d detected on its edge) slots %0d loads %0d", bad, nslot, nld);
            else $display("TB_CTXRX FAIL (bad record at %0d not detected: det %0d err %0d)", bad, det, err);
        end else if (err == 0 && det == -1 && nld > 100) $display("TB_CTXRX PASS slots %0d loads %0d (record, user, mu_fault 0)", nslot, nld);
        else $display("TB_CTXRX FAIL errors %0d det %0d loads %0d", err, det, nld);
        $finish;
    end
endmodule
