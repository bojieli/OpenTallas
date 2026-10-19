`timescale 1ns/1ps
// MU-S81/HOST bench for dsdv_mu_hslot (the S81 host-plane static slot table) on a fixed-latency stand-in of the unit's
// start -> next-token path (the unit's t_kd done lands RL edges after its f_ks pin flop captured the start, the same
// for every start: compiled calendar).  The stand-in computes user u's next token f(u, pos, tok); the bench routes
// every return to the user named by the RETURN TAG (t_kd[31:22]) and starts that user's next position in its next
// slot with the returned token, so a wrong tag corrupts the per-user token chains.
//   NS > 1: leaf NSLOT = NS, NU users in slots 0..NU-1 of an NP-slot round (slot S cycles), t_kd composed as
//           dsdv_seq_host_mu does ({kd[53:32], ku[30:0], 0}).  NS = 1: no leaf (dsdv_seq_host_mu NSLOT 1), user 0 only.
//   Every run prints user 0's start / return trace ("U0 ..."): the runner diffs it between NS = 1 and NS > 1.
//   COLLIDE 1: RL > one round, so user 0's next start finds its slot occupied: t_mf[0] must rise.
//   OFFCAL 1: user 1's first start one edge off its slot boundary: t_mf[1] must rise.
// PASS line: "MUHSLOT PASS" (normal) or "MUHSLOT ... PASS (fault raised)".
module tb_dsdv_mu_hslot;
`ifndef NS
    localparam integer NS = 8;
`else
    localparam integer NS = `NS;
`endif
`ifndef NP
    localparam integer NP = 8;
`else
    localparam integer NP = `NP;
`endif
`ifndef NU
    localparam integer NU = (NS > 1) ? NP : 1;
`else
    localparam integer NU = `NU;
`endif
`ifndef MUT
    localparam integer MUT = 0;
`else
    localparam integer MUT = `MUT;
`endif
`ifndef COLLIDE
    localparam integer COLLIDE = 0;
`else
    localparam integer COLLIDE = `COLLIDE;
`endif
`ifndef OFFCAL
    localparam integer OFFCAL = 0;
`else
    localparam integer OFFCAL = `OFFCAL;
`endif
    localparam integer S = 64, ROUNDS = 6, T0 = 40;
    localparam integer RL = COLLIDE ? NP * S + S / 2 : NP * S - S / 2 - 3;
    localparam integer NST = NU * ROUNDS;
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    integer cyc = 0, errs = 0, nret = 0, nst = 0, i, u;
    function automatic [20:0] fnext(input [9:0] uu, input [20:0] p, input [20:0] t);
        fnext = t * 21'd31 + {11'd0, uu} * 21'd7 + p * 21'd3 + 21'd1;
    endfunction
    // ---- stimulus / stand-in state
    reg [52:0] f_ks = 0; reg [25:0] f_mc = 0; reg [53:0] kd = 0;
    reg [20:0] tok_u [0:NU-1]; reg [20:0] pos_u [0:NU-1]; reg [20:0] gtok [0:NU-1];
    integer rnd_u [0:NU-1];                                   // rounds started per user
    integer sT [0:NST-1]; reg [9:0] sU [0:NST-1]; reg [20:0] sP [0:NST-1], sK [0:NST-1];
    wire [31:0] ku; wire [3:0] mf; wire [53:0] t_kd;
    generate if (NS > 1) begin : g_mu
        dsdv_mu_hslot #(.NSLOT(NS), .MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .f_ks(f_ks), .f_kd(kd), .f_mc(f_mc),
            .t_ku(ku), .t_mf(mf));
        assign t_kd = {kd[53:32], ku[30:0], 1'b0};
    end else begin : g_su
        assign ku = 32'd0; assign mf = 4'd0; assign t_kd = kd;
    end endgenerate
    initial begin
        for (u = 0; u < NU; u = u + 1) begin
            tok_u[u] = 21'(1000 + 37 * u); pos_u[u] = 21'(500 + 11 * u); gtok[u] = tok_u[u]; rnd_u[u] = 0;
            for (i = 0; i < ROUNDS; i = i + 1) gtok[u] = fnext(10'(u), 21'(500 + 11 * u + i), gtok[u]);
        end
    end
    // ---- drive (edge cyc): config at 20 / 22, starts at T0 + (r * NP + u) * S (+1 for OFFCAL user 1 round 0)
    integer ts, r;
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (cyc == 10) rst_n <= 1'b1;
        f_mc <= 26'd0; f_ks <= 53'd0;
        if (cyc == 20) f_mc <= {1'b1, 1'b0, 24'(S)};
        if (cyc == 22) f_mc <= {1'b1, 1'b1, 24'(RL)};
        for (u = 0; u < NU; u = u + 1) begin
            r = rnd_u[u];
            ts = T0 + (r * NP + u) * S + ((OFFCAL && u == 1 && r == 0) ? 1 : 0);
            if (r < ROUNDS && cyc == ts) begin
                f_ks <= {1'b1, 10'(u), tok_u[u], pos_u[u]};
                sT[nst] = cyc; sU[nst] = 10'(u); sP[nst] = pos_u[u]; sK[nst] = tok_u[u]; nst = nst + 1;
                rnd_u[u] = r + 1;
                if (u == 0) $display("U0 S %0d tok %0d pos %0d", cyc, tok_u[u], pos_u[u]);
            end
        end
        // stand-in unit: t_kd done at edge (start drive edge) + 1 + RL
        kd <= 54'd0;
        for (i = 0; i < nst; i = i + 1)
            if (cyc == sT[i] + 1 + RL) kd <= {1'b1, fnext(sU[i], sP[i], sK[i]), 32'd0};
    end
    // ---- observe (negedge of the cycle after edge k = cyc - 1): a return for the start driven at cyc - 2 - RL
    integer j, hit; reg [9:0] tu; reg [20:0] tp;
    always @(negedge ck) if (rst_n && t_kd[53]) begin
        hit = -1;
        for (j = 0; j < nst; j = j + 1) if (sT[j] == cyc - 2 - RL) hit = j;
        tu = (NS > 1) ? t_kd[31:22] : 10'd0; tp = (NS > 1) ? t_kd[21:1] : (hit >= 0 ? sP[hit] : 21'd0);
        if (hit < 0) begin errs = errs + 1; $display("ERR return at %0d with no start RL before", cyc); end
        else if (tu != sU[hit] || tp != sP[hit]) begin
            errs = errs + 1;
            if (errs < 6) $display("ERR return at %0d tag {user %0d pos %0d} != start {user %0d pos %0d}", cyc, tu, tp, sU[hit], sP[hit]);
        end
        if (tu < NU) begin                                  // route by the TAG (as the host does)
            tok_u[tu] = t_kd[52:32]; pos_u[tu] = tp + 21'd1;
        end else errs = errs + 1;
        if (tu == 0) $display("U0 R %0d tok %0d", cyc, t_kd[52:32]);
        nret = nret + 1;
    end
    integer ndone;
    initial begin
        #(T0 + (ROUNDS * NP + NU) * S + RL + 200);
        if (COLLIDE || OFFCAL) begin
            if ((COLLIDE && mf[0]) || (OFFCAL && mf[1])) $display("MUHSLOT %s NS %0d PASS (fault raised) t_mf %b", COLLIDE ? "COLLIDE" : "OFFCAL", NS, mf);
            else $display("MUHSLOT %s NS %0d FAIL (no fault) t_mf %b", COLLIDE ? "COLLIDE" : "OFFCAL", NS, mf);
        end else begin
        ndone = 0;
        for (u = 0; u < NU; u = u + 1) begin
            if (tok_u[u] != gtok[u]) begin errs = errs + 1; $display("ERR user %0d final tok %0d != golden %0d", u, tok_u[u], gtok[u]); end
            else ndone = ndone + 1;
        end
        if (nret != NST) begin errs = errs + 1; $display("ERR %0d returns, expected %0d", nret, NST); end
        if (mf != 4'd0) begin errs = errs + 1; $display("ERR t_mf %b", mf); end
        $display("MUHSLOT NS %0d NP %0d NU %0d RL %0d: %0d starts, %0d returns, %0d/%0d users exact, max outstanding %0d, errs %0d",
                 NS, NP, NU, RL, nst, nret, ndone, NU, (RL + S - 1) / S, errs);
        if (errs == 0) $display("MUHSLOT PASS"); else $display("MUHSLOT FAIL");
        end
        $finish;
    end
endmodule
