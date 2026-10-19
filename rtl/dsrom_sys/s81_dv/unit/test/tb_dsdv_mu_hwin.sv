`timescale 1ns/1ps
// MU-S81-2/DIE bench (port of MU-S81/DIE tb_dsdv_mu_win, 908a67c18) for the NEW leaf dsdv_mu_hwin BESIDE the CLOSED
// dsdv_mu_hslot (NEV-free, source untouched): both tap the same start pin f_ks and the same S / RL boot words f_mc;
// the window rows come on hwin's own word stream f_mw (die: host CSR 0x16), so hslot never sees a window word.
// NU users on an NP-slot shift calendar (slot S), 3 events {TX ep0 D 20, TX ep1 D 33, replay ep0 D 47}, per-slot
// {land, ab} attributes.  The unit's return is the stand-in loopback t_kd done = t_ku valid.  Checks:
//   * every event of every start fires exactly once, at start + D + K (K the same constant for every event / start),
//     on its endpoint, with the start's {pos, user} and the slot's {land, ab}; a replay only where land = 1;
//   * RX tags (mu_rt) of outstanding {user, pos} raise no fault; t_ku trace ("KU ...") is printed for the NEV 0 diff;
//   * hslot t_mf stays 0 and hwin t_wf stays 0 (no window word reaches hslot; both tables agree);
//   * BADRT 1: one RX tag of a user that is not outstanding -> hwin t_wf[0] must rise.
// WMUT (RTL mutants of dsdv_mu_hwin): 3 = ab bit dropped, 4 = replay enable ignored -> both must FAIL.
// PASS line "MUWIN PASS".
module tb_dsdv_mu_hwin;
`ifndef NEV
    localparam integer NEV = 3;
`else
    localparam integer NEV = `NEV;
`endif
`ifndef BADRT
    localparam integer BADRT = 0;
`else
    localparam integer BADRT = `BADRT;
`endif
`ifndef WMUT
    localparam integer WMUT = 0;
`else
    localparam integer WMUT = `WMUT;
`endif
    localparam integer NS = 8, NU = 8, S = 64, ROUNDS = 4, T0 = 200;
    localparam integer RL = NS * S - S / 2 - 3;
    localparam integer NE = 3;
    integer DK [0:NE-1], KD [0:NE-1], EP [0:NE-1];        // D / kind / endpoint per event
    initial begin DK[0] = 20; DK[1] = 33; DK[2] = 47; KD[0] = 0; KD[1] = 0; KD[2] = 1; EP[0] = 0; EP[1] = 1; EP[2] = 0; end
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    integer cyc = 0, errs = 0, i, e, nfire = 0, nexp = 0;
    reg [52:0] f_ks = 0; reg [25:0] f_mc = 0, f_mw = 0; reg [2*32-1:0] mu_rt = 0;
    wire [31:0] ku; wire [3:0] hmf; wire [1:0] wf; wire [4*34-1:0] mu_c; wire [4*11-1:0] mu_rc;
    wire [3:0] mf = {hmf[3] | wf[1], hmf[2] | wf[0], hmf[1:0]};      // the die master's t_mf fold
    dsdv_mu_hslot #(.NSLOT(NS), .MUT(0)) u_hs (.ck(ck), .rst_n(rst_n), .f_ks(f_ks),
        .f_kd({ku[31], 53'd0}), .f_mc(f_mc), .t_ku(ku), .t_mf(hmf));
    dsdv_mu_hwin #(.NSLOT(NS), .NEV(NEV), .NEP(4), .NRT(2), .MUT(WMUT)) dut (.ck(ck), .rst_n(rst_n), .f_ks(f_ks),
        .f_mc(f_mc), .f_mw(f_mw), .mu_c(mu_c), .mu_rc(mu_rc), .mu_rt(mu_rt), .t_wf(wf));
    // slot attributes: land = slot[0], ab = slot[1]
    function automatic [1:0] att(input integer sl); att = {sl[0] ? 1'b1 : 1'b0, sl[1] ? 1'b1 : 1'b0}; endfunction
    integer stc [0:NU*ROUNDS-1]; integer stu [0:NU*ROUNDS-1]; integer stp [0:NU*ROUNDS-1]; integer nst = 0;
    integer kconst = -1;
    task automatic cfg(input [25:0] w); begin f_mc = w; @(posedge ck); #0.1; f_mc = 0; @(posedge ck); #0.1; end endtask
    task automatic wcfg(input [25:0] w); begin f_mw = w; @(posedge ck); #0.1; f_mw = 0; @(posedge ck); #0.1; end endtask
    always @(posedge ck) cyc <= cyc + 1;
    // ---- monitor: match every output against the starts
    integer s, d, hit; reg [1:0] aa;
    always @(posedge ck) if (rst_n) begin
        for (e = 0; e < NE; e = e + 1) begin
            if (KD[e] == 0 ? mu_c[34*EP[e]] : mu_rc[11*EP[e]]) begin
                hit = 0;
                for (s = 0; s < nst; s = s + 1) begin
                    d = cyc - stc[s] - DK[e];
                    if (kconst < 0 && s == 0 && e == 0) kconst = d;
                    if (d == kconst) begin
                        hit = 1; nfire = nfire + 1; aa = att(stu[s]);
                        if (KD[e] == 0) begin
                            if (mu_c[34*EP[e] +: 34] !== {stp[s][20:0], stu[s][9:0], aa, 1'b1}) begin
                                errs = errs + 1; $display("ERR c%0d ev%0d start%0d mu_c %h", cyc, e, s, mu_c[34*EP[e] +: 34]);
                            end
                        end else begin
                            if (!aa[1] || mu_rc[11*EP[e] +: 11] !== {stu[s][9:0], 1'b1}) begin
                                errs = errs + 1; $display("ERR c%0d ev%0d start%0d mu_rc %h", cyc, e, s, mu_rc[11*EP[e] +: 11]);
                            end
                        end
                    end
                end
                if (!hit) begin errs = errs + 1; $display("ERR c%0d ev%0d fires with no start at offset K", cyc, e); end
            end
        end
        if (ku[31]) $display("KU c%0d user %0d pos %0d", cyc, ku[30:21], ku[20:0]);
    end
    integer r, u, q, j;
    initial begin
        repeat (4) @(posedge ck); #0.1; rst_n = 1; repeat (4) @(posedge ck); #0.1;
        cfg({1'b1, 1'b0, 24'(S)}); cfg({1'b1, 1'b1, 24'(RL)});
        for (q = 0; q < NE; q = q + 1) begin
            wcfg({1'b1, 1'b0, 1'b0, 2'd0, 10'd0, 2'(EP[q]), 1'(KD[q]), 3'd0, 5'(q)});
            wcfg({1'b1, 1'b0, 1'b0, 2'd1, 21'(DK[q])});
            for (j = 0; j < NS; j = j + 1) wcfg({1'b1, 1'b0, 1'b0, 2'd2, 9'd0, att(j), 10'(j)});
        end
        while (cyc < T0) begin @(posedge ck); #0.1; end
        for (r = 0; r < ROUNDS; r = r + 1)
            for (u = 0; u < NU; u = u + 1) begin
                while (cyc < T0 + (r * NS + u) * S) begin @(posedge ck); #0.1; end
                f_ks = {1'b1, 10'(u), 21'd0, 21'(r)};
                stc[nst] = cyc; stu[nst] = u; stp[nst] = r; nst = nst + 1;
                // RX tag of an outstanding start (the previous user), on both returning end slices
                if (nst > 1) mu_rt = {{1'b1, 10'(stu[nst-2]), 21'(stp[nst-2])}, {1'b1, 10'(stu[nst-2]), 21'(stp[nst-2])}};
                if (BADRT && r == 2 && u == 3) mu_rt[31:0] = {1'b1, 10'd77, 21'd5};
                @(posedge ck); #0.1; f_ks = 0; mu_rt = 0;
            end
        repeat (RL + 100) @(posedge ck);
        for (j = 0; j < nst; j = j + 1) begin nexp = nexp + 2 + att(stu[j]) / 2; end
        $display("MUWIN starts %0d fires %0d expected %0d K %0d t_mf %b hslot %b hwin %b", nst, nfire, nexp, kconst, mf, hmf, wf);
        if (BADRT) begin
            if (wf[0] && mf[2] && hmf == 4'd0) $display("MUWIN BADRT PASS (fault raised)"); else $display("MUWIN BADRT FAIL (no fault)");
        end else if (errs == 0 && nfire == nexp && mf == 4'd0) $display("MUWIN PASS");
        else $display("MUWIN FAIL errs %0d", errs);
        $finish;
    end
endmodule
