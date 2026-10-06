`timescale 1ns/1ps
// Claude HBM SU/attn: tb_hfd_attn_tile (CLAUDE HBM-ABSTRACTS, claude/hbm-abstracts-20261006) for the bank-built
// margin tile hfd_attn_tile_b, every delay from its stage parameters.  Originally: lockstep of the die view hfd_attn_tile (quads as full RTL ot_attn_tile_m6h1q) against the
// H16 quad parent ot_attn_tile_m6h1p (lockstep-proven against tile_l: results/rtl/hbm_attn_tile_r_20261006 lockr13_p).
// ROLE 0: corner tile (packet split over k / q); 1: column tile (packet on ci); 2: row tile (packet on ri);
// 3: result chain pass-through (no packet, random words on i).  Every cycle: o against the reference (roles 0-2:
// the parent's output delayed 3; role 3: i delayed 4; the word compared whenever valid, valid every cycle) and cf / rf against the packet delayed 6.
// Prints ATTNDIE role=<r> cycles=<n> mismatches=<m> ov=<compared valid words>; $fatal on any mismatch or no valid word.
// NEG=1: flips one oy bit of the view's o in the compare (negative control, must fail).
module tb_hfd_attn_tile_b (input wire clk);
    parameter integer NK = 3, NC = 1, NR = 2, PMID = 1, NFC = 1, NFR = 2, NL = 4, NI = 4;
    localparam integer H = 16, TD = 32, NBANK = 5, BW = 3, PWORDS = 2;
    parameter integer NCYC = 6000;
    parameter integer NEG = 0;
    parameter integer ROLE = 0;
    reg rst_n = 1'b0;
    reg ld_v, ld_mode, ld_w2v, iv;
    reg [BW-1:0] ld_bank, ibank;
    reg [7:0] ld_grp;
    reg [PWORDS*TD*16-1:0] ld_w;
    reg [TD*18-1:0] ib;
    reg [528:0] iw;
    wire [1037:0] kp = {ld_v, ld_mode, ld_bank, ld_grp, ld_w, ld_w2v};
    wire [579:0]  qp = {iv, ibank, ib};
    wire [1617:0] pkt = {kp, qp};
    wire pkt_on = (ROLE != 3);
    localparam integer DIN = 1 + ((ROLE == 1) ? NC : (ROLE == 2) ? NR : NK);
    // reference: the quad parent fed 3 cycles late
    wire [1618:0] pk_d;
    // the tile's rst rides with q (the local packet pipe, 1 + NK) whatever the role; the packet with its role's pipe
    wire [1617:0] pk_dd; wire rst_dd;
    ot_hdc_v41x_dly #(.W(1618), .D(DIN)) u_id (.clk(clk), .d(pkt_on ? pkt : 1618'd0), .q(pk_dd));
    ot_hdc_v41x_dly #(.W(1), .D(1 + NK)) u_ir (.clk(clk), .d(rst_n), .q(rst_dd));
    assign pk_d = {rst_dd, pk_dd};
    wire r_rst_n, r_ld_v, r_ld_mode, r_ld_w2v, r_iv;
    wire [BW-1:0] r_ld_bank, r_ibank;
    wire [7:0] r_ld_grp;
    wire [PWORDS*TD*16-1:0] r_ld_w;
    wire [TD*18-1:0] r_ib;
    assign {r_rst_n, r_ld_v, r_ld_mode, r_ld_bank, r_ld_grp, r_ld_w, r_ld_w2v, r_iv, r_ibank, r_ib} = pk_d;
    wire ov_r; wire [511:0] oy_r; wire [15:0] of_r;
    ot_attn_tile_m6h1p #(.PMID(PMID)) u_ref (.clk(clk), .rst_n(r_rst_n), .ld_v(r_ld_v), .ld_mode(r_ld_mode), .ld_bank(r_ld_bank),
        .ld_grp(r_ld_grp), .ld_w(r_ld_w), .ld_w2v(r_ld_w2v), .iv(r_iv), .ibank(r_ibank), .ib(r_ib), .ov(ov_r), .oy(oy_r),
        .oflt(of_r));
    wire [528:0] exp_loc, exp_chn;
    ot_hdc_v41x_dly #(.W(529), .D(NL + 1)) u_xd (.clk(clk), .d({ov_r, oy_r, of_r}), .q(exp_loc));
    ot_hdc_v41x_dly #(.W(529), .D(2 + NI)) u_cd (.clk(clk), .d(iw), .q(exp_chn));
    wire [1617:0] exp_fc, exp_fr;
    ot_hdc_v41x_dly #(.W(1618), .D(DIN + 2 + NFC)) u_fd (.clk(clk), .d(pkt_on ? pkt : 1618'd0), .q(exp_fc));
    ot_hdc_v41x_dly #(.W(1618), .D(DIN + 2 + NFR)) u_fr (.clk(clk), .d(pkt_on ? pkt : 1618'd0), .q(exp_fr));
    // the view
    wire [1617:0] cf, rf; wire [528:0] o;
    hfd_attn_tile_b #(.NK(NK), .NC(NC), .NR(NR), .PMID(PMID), .NFC(NFC), .NFR(NFR), .NL(NL), .NI(NI)) u_v (
        .ck(clk), .rst(rst_n),
        .k((ROLE == 0) ? {3'b101, kp} : 1041'd0), .q((ROLE == 0) ? {2'b10, qp} : 582'd0),
        .ci((ROLE == 1) ? pkt : 1618'd0), .ri((ROLE == 2) ? pkt : 1618'd0), .i((ROLE == 3) ? iw : 529'd0),
        .cf(cf), .rf(rf), .o(o));
    wire [528:0] o_c = (NEG != 0) ? (o ^ 529'h10000) : o;
    wire [528:0] exp_o = (ROLE == 3) ? exp_chn : exp_loc;
    integer cyc = 0, mism = 0, nov = 0, i;
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
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        ld_v <= (($urandom % 3) == 0);
        ld_mode <= $urandom % 2;
        ld_w2v <= $urandom % 2;
        ld_bank <= $urandom % NBANK;
        ld_grp <= (($urandom % 8) == 0) ? $urandom : ($urandom % H);
        for (i = 0; i < PWORDS * TD; i = i + 1) ld_w[i*16 +: 16] <= rbf16(0);
        iv <= (($urandom % 4) != 0);
        ibank <= $urandom % NBANK;
        for (i = 0; i < TD; i = i + 1) ib[i*18 +: 18] <= relem(0);
        for (i = 0; i < 17; i = i + 1) iw[i*32 +: 32] <= $random;
        iw[528] <= (($urandom % 3) == 0);
        if (cyc > 40) begin
            if (exp_o[528]) nov <= nov + 1;
            // a result word is defined only while its valid (bit 528) is set: compare valid always, data when valid
            if (o_c[528] !== exp_o[528] || (exp_o[528] && o_c !== exp_o)) begin
                mism <= mism + 1;
                if (mism < 5) $display("MISMATCH o cyc=%0d view %h ref %h", cyc, o_c[528:512], exp_o[528:512]);
            end
            if (cf !== exp_fc || rf !== exp_fr) begin
                mism <= mism + 1;
                if (mism < 5) $display("MISMATCH fwd cyc=%0d", cyc);
            end
        end
        if (cyc == NCYC) begin
            $display("ATTNDIE role=%0d cycles=%0d mismatches=%0d ov=%0d", ROLE, cyc, mism, nov);
            if (mism != 0 || nov == 0) $fatal(1, "ATTNDIE FAIL role=%0d mismatches=%0d ov=%0d", ROLE, mism, nov);
            $finish;
        end
    end
endmodule
