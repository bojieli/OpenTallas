`timescale 1ns/1ps
// attn-split 2026-10-08: lockstep of the split attention tile (hfd_attn_half_lo + hfd_attn_half_hi, xp / xr joined
// through a die-link model) against the one-piece bank-built tile hfd_attn_tile_b with the same stage parameters.  Quads
// and banks are full RTL in both.  Every output pin (cf, rf, o: all bits, valid or not) must be equal every cycle.
// ROLE 0..3 as tb_hfd_attn_tile_b (corner k/q, column ci, row ri, chain i only); ROLE 4: every input port driven at
// once (k / q / ci / ri packets ORed at ROOT, a chain word on i every cycle: merge collisions).
// MUT (bench sensitivity, each must FAIL): 1 one xp bit flipped in the link, 2 xr one cycle late in the link,
// 3 xr quad words swapped, 4 hi built with NLL + 1 (result latency mismatch between the halves), 5 xp one cycle late.
// Prints ATTNHALF role=<r> mut=<m> cycles=<n> mismatches=<m> ov=<valid o words>; $fatal on mismatch or no valid word.
module tb_hfd_attn_half_b (input wire clk);
    parameter integer NK = 4, NC = 2, NR = 3, PMID = 2, NFC = 2, NFR = 3, NL = 8, NI = 6, NLL = 3;
    localparam integer H = 16, TD = 32, NBANK = 5, BW = 3, PWORDS = 2;
    parameter integer NCYC = 4000;
    parameter integer ROLE = 4;
    parameter integer MUT = 0;
    parameter integer LDK = 0;     // hbm-forks: 1 = the entry-point strap (ROLE 4 packets; reference sees chain ld masked)
    reg rst_n = 1'b0;
    reg [1617:0] pk0, pk1, pk2;
    reg [528:0] iw;
    integer cyc = 0, mism = 0, nov = 0, i, j;
    function automatic [15:0] rbf16(input integer dummy);
        reg [15:0] x;
        begin
            x = $random;
            case ($urandom % 8)
                0: x[14:7] = 8'd0;
                1: x[14:7] = 8'hff;
                2: x[14:7] = 8'd120 + ($urandom % 16);
                default: ;
            endcase
            rbf16 = x;
        end
    endfunction
    function automatic [17:0] relem(input integer dummy);
        reg [17:0] e;
        begin
            e = {$random};
            e[17] = (($urandom % 16) == 0);
            if (($urandom % 4) == 0) e[15:8] = 8'h7f;
            if (($urandom % 4) == 0) e[7:0] = 8'd127 + ($urandom % 8) - 4;
            relem = e;
        end
    endfunction
    // one packet {ld_v, ld_mode, ld_bank, ld_grp, ld_w, ld_w2v, iv, ibank, ib}
    function automatic [1617:0] rpkt(input integer sparse);
        reg [1617:0] p;
        integer n;
        begin
            p = 1618'd0;
            if (($urandom % sparse) == 0) begin
                p[1617] = (($urandom % 3) == 0);
                p[1616] = $urandom % 2;
                p[1615:1613] = $urandom % NBANK;
                p[1612:1605] = (($urandom % 8) == 0) ? $urandom : ($urandom % H);
                for (n = 0; n < PWORDS * TD; n = n + 1) p[581 + n*16 +: 16] = rbf16(0);
                p[580] = $urandom % 2;
                p[579] = (($urandom % 4) != 0);
                p[578:576] = $urandom % NBANK;
                for (n = 0; n < TD; n = n + 1) p[n*18 +: 18] = relem(0);
            end
            rpkt = p;
        end
    endfunction
    wire [1617:0] pk_k = (ROLE == 0 || ROLE == 4) ? pk0 : 1618'd0;
    wire [1617:0] pk_c = (ROLE == 1 || ROLE == 4) ? pk1 : 1618'd0;
    wire [1617:0] pk_r = (ROLE == 2 || ROLE == 4) ? pk2 : 1618'd0;
    // LDK = 1: the reference one-piece tile sees the forward chains with their ld field cleared (what the strap means)
    // LDK = 1: the split tile's entry gets the k packet as a PS row on ks (the formatter must rebuild it bit for bit)
    wire [1037:0] ldp = pk_k[1617:580];          // {ld_v, ld_mode, ld_bank3, ld_grp8, ld_w1024, ld_w2v}
    wire [1101:0] ks_in = LDK ? {3'b101, 31'd0, ldp[1036], ldp[1035:1033], ldp[1032:1025], ldp[0], 1'b0, 5'd3, 4'hF, 10'd0,
                                 ldp[1024:1], 10'd7, ldp[1037]} : 1102'd0;
    wire [1617:0] pk_cr = LDK ? {1038'd0, pk_c[579:0]} : pk_c;
    wire [1617:0] pk_rr = LDK ? {1038'd0, pk_r[579:0]} : pk_r;
    wire [528:0]  i_in = (ROLE == 3 || ROLE == 4) ? iw : 529'd0;
    wire [1040:0] k_in = {3'b101, pk_k[1617:580]};
    wire [581:0]  q_in = {2'b10, pk_k[579:0]};
    // reference: the one-piece tile
    wire [1617:0] cf_r, rf_r; wire [528:0] o_r;
    hfd_attn_tile_b #(.NK(NK), .NC(NC), .NR(NR), .PMID(PMID), .NFC(NFC), .NFR(NFR), .NL(NL), .NI(NI)) u_ref (
        .ck(clk), .rst(rst_n), .k(k_in), .q(q_in), .ci(pk_cr), .ri(pk_rr), .i(i_in), .cf(cf_r), .rf(rf_r), .o(o_r));
    // the split pair + the die-link model (abutting pins: a wire; mutants corrupt it)
    wire [1618:0] xp_l, xp_h; wire [271:0] xr_l, xr_h;
    reg  [1618:0] xp_d; reg [271:0] xr_d;
    always @(posedge clk) begin xp_d <= xp_l; xr_d <= xr_l; end
    assign xp_h = (MUT == 1) ? (xp_l ^ (1619'd1 << 1000)) : (MUT == 5) ? xp_d : xp_l;
    assign xr_h = (MUT == 2) ? xr_d : (MUT == 3) ? {xr_l[135:0], xr_l[271:136]} : xr_l;
    wire [1617:0] cf_s, rf_s; wire [528:0] o_s;
    hfd_attn_half_lo #(.NK(NK), .NC(NC), .NR(NR), .PMID(PMID), .NFR(NFR), .NLL(NLL)) u_lo (
        .ck(clk), .rst(rst_n), .k(LDK ? 1041'd0 : k_in), .ks(ks_in), .ldk(LDK[0]), .q(q_in), .ci(pk_c), .ri(pk_r), .rf(rf_s), .xp(xp_l), .xr(xr_l));
    hfd_attn_half_hi #(.PMID(PMID), .NFC(NFC), .NL(NL), .NLL(NLL + ((MUT == 4) ? 1 : 0)), .NI(NI)) u_hi (
        .ck(clk), .xp(xp_h), .xr(xr_h), .i(i_in), .cf(cf_s), .o(o_s));
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        pk0 <= rpkt((ROLE == 4) ? 3 : 1);
        pk1 <= rpkt((ROLE == 4) ? 3 : 1);
        pk2 <= rpkt((ROLE == 4) ? 3 : 1);
        for (j = 0; j < 17; j = j + 1) iw[j*32 +: 32] <= $random;
        iw[528] <= (($urandom % 3) == 0);
        if (cyc > 2) begin
            if (o_r[528]) nov <= nov + 1;
            if (o_s !== o_r || cf_s !== cf_r || rf_s !== rf_r) begin
                mism <= mism + 1;
                if (mism < 5) $display("MISMATCH cyc=%0d o %0d cf %0d rf %0d", cyc, o_s !== o_r, cf_s !== cf_r, rf_s !== rf_r);
            end
        end
        if (cyc == NCYC) begin
            $display("ATTNHALF role=%0d mut=%0d cycles=%0d mismatches=%0d ov=%0d", ROLE, MUT, cyc, mism, nov);
            if (mism != 0 || nov == 0) $fatal(1, "ATTNHALF FAIL role=%0d mut=%0d mismatches=%0d ov=%0d", ROLE, MUT, mism, nov);
            $finish;
        end
    end
endmodule
