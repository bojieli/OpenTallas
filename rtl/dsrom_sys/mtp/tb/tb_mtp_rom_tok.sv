`timescale 1ns/1ps
// tb_mtp_rom_tok: dsfd_wfc_tok against a reference model (stream mtp-rom, 2026-10-08).  Random DRAFT blocks
// (user, epoch, base, n, tokens) and random WFC prompt-port reads (user, pos, blk) every cycle; the reference
// applies a DRAFT write two cycles after it is presented (the documented visibility) and answers
// known = prompt (pos < plen) or (epoch match and base <= pos < base + n); the token is checked when known.
module tb_mtp_rom_tok;
    parameter integer SEED = 1, NCYC = 40000;
    localparam integer FLIT = 512, NW = 21, USER_W = 10, MAXU = 8, PU = 8, PMAX = 16, G = 5, PLEN = 6;
    localparam integer HDR_TYPE = 16, HDR_USER = 32, HDR_POS = 40, HDR_ADDR = 135, DR_N = 248, DR_D = 256;
    reg clk = 0; always #1.5 clk = ~clk;
    reg rst_n = 0;
    function automatic [31:0] mix(input [31:0] h, input [31:0] x);
        reg [31:0] t; begin t = (h ^ (x * 32'h9E3779B1)) + 32'h7F4A7C15; t = t ^ (t >> 15); t = t * 32'h2C1B3C6D;
        mix = t ^ (t >> 12); end
    endfunction
    reg [2+USER_W+2*NW:0] cfgw = 0;
    reg [FLIT:0] dw = 0;
    reg [USER_W+NW+4:0] pr = 0;
    wire [9+2*NW:0] cfg; wire [NW:0] q; wire ft;
    dsfd_wfc_tok u (.ck(clk), .rst(rst_n), .f_c(cfgw), .t_cfg(cfg), .f_dw(dw), .f_pr(pr), .t_pr(q), .t_ft(ft));
    // reference
    integer pm [0:PU*PMAX-1];
    integer ep [0:MAXU-1], bs [0:MAXU-1], nn [0:MAXU-1], tk [0:MAXU*G-1];
    reg [FLIT:0] d1, d2;                          // the write pipeline of the reference (2 cycles)
    integer cyc = 0, reads = 0, hits = 0, dhits = 0, i, uu, pp, bb, rnd, eknown, etok;
    reg pend; integer pk, pt;
    task apply(input [FLIT:0] w);
        integer u_, k_; begin
            if (w[FLIT]) begin
                u_ = w[HDR_USER +: 8];
                ep[u_] = w[HDR_ADDR +: 4]; bs[u_] = w[HDR_POS +: NW]; nn[u_] = w[DR_N +: 3];
                for (k_ = 0; k_ < G; k_ = k_ + 1) tk[u_ * G + k_] = w[DR_D + k_ * NW +: NW];
            end
        end
    endtask
    task cput(input [1:0] sel, input integer uu_, input integer pp_, input integer vv);
        begin @(negedge clk); cfgw = {1'b1, sel, USER_W'(uu_), NW'(pp_), NW'(vv)}; @(negedge clk); cfgw = 0; end
    endtask
    initial begin
        for (i = 0; i < MAXU; i = i + 1) begin ep[i] = 0; nn[i] = 0; bs[i] = 0; end
        cput(0, 0, 0, 4); cput(1, 0, 0, PLEN); cput(2, 0, 0, 100);
        for (uu = 0; uu < PU; uu = uu + 1) for (pp = 0; pp < PLEN; pp = pp + 1) begin
            pm[uu * PMAX + pp] = mix(uu, pp) % 129280; cput(3, uu, pp, pm[uu * PMAX + pp]);
        end
        repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
        d1 = 0; d2 = 0; pend = 0;
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            @(negedge clk);
            // check the read launched on the previous edge
            if (pend) begin
                if (q[NW] !== pk[0] || (pk[0] && q[NW-1:0] !== pt)) begin
                    $display("MTP_TOK FAIL: read %0d got qk %b q %0d, expected %0d %0d", reads, q[NW], q[NW-1:0], pk, pt);
                    $finish;
                end
                reads = reads + 1; if (pk) hits = hits + 1;
            end
            apply(d1); d1 = dw;              // a write presented at K-2 is visible to the read presented at K
            rnd = mix(SEED, cyc);
            dw = 0;
            if (rnd[3:0] == 0) begin
                uu = rnd[6:4]; dw[FLIT] = 1'b1; dw[HDR_TYPE +: 4] = 4'd4; dw[HDR_USER +: 8] = uu;
                dw[HDR_POS +: NW] = PLEN + rnd[12:7]; dw[HDR_ADDR +: 4] = rnd[16:13] & 4'h3; dw[DR_N +: 3] = rnd[19:17] % 6;
                for (i = 0; i < G; i = i + 1) dw[DR_D + i * NW +: NW] = mix(rnd, i) % 129280;
            end
            // a read: user, pos near the user's block, blk = the stored epoch most of the time
            rnd = mix(SEED + 7, cyc);
            uu = rnd[2:0]; bb = rnd[5:3] < 6 ? ep[uu] : rnd[9:6] & 4'h3;
            pp = rnd[10] ? rnd[14:11] : bs[uu] + rnd[13:11] - 1;
            if (pp < 0) pp = 0;
            pr = {1'b1, USER_W'(uu), NW'(pp), 4'(bb)};
            // the answer the reference expects at the next edge (after this edge's write lands)
            begin : expect_
                integer kk; eknown = 0; etok = 0;
                if (pp >= 0 && pp < PLEN && pp < PMAX) begin eknown = 1; etok = pm[uu * PMAX + pp]; end
                else if (ep[uu] == bb) for (kk = 0; kk < G; kk = kk + 1)
                    if (kk < nn[uu] && bs[uu] + kk == pp) begin eknown = 1; etok = tk[uu * G + kk]; dhits = dhits + 1; end
            end
            pend = 1; pk = eknown; pt = etok;
        end
        if (ft) begin $display("MTP_TOK FAIL: fault"); $finish; end
        if (dhits < 100) begin $display("MTP_TOK FAIL: weak coverage (%0d draft hits)", dhits); $finish; end
        $display("MTP_TOK PASS reads=%0d known=%0d draft_hits=%0d", reads, hits, dhits);
        $finish;
    end
endmodule
