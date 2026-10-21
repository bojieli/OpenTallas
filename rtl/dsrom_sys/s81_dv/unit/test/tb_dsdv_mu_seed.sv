`timescale 1ns/1ps
// MU-S81/HOST bench for dsdv_mu_seed (per-MTP-user seed-state addressing of the S81 draft die) on a model seed store
// (SB + NUSER x 320 words of 1,024 b, write on t_a we, read data taken on the t_a edge).  NU users, NUP slots a round
// (slot SL edges): in user u's slot of round r the calendar reads u's state (r > 0; must equal what u wrote in round
// r - 1) and then writes u's new state g(u, r, beat) -- one 320-beat window each, one beat an edge.
//   Every run prints user 0's address / edge trace hash ("U0 TRACE"): the runner diffs it between NU = 1 and NU > 1.
//   COLLIDE 1: one beat of user 1's round-0 write window is replaced by user 0's beat 0: t_mf[0] must rise.
// PASS line "MUSEED PASS" or "MUSEED COLLIDE ... PASS (fault raised)".
module tb_dsdv_mu_seed;
`ifndef NU
    localparam integer NU = 4;
`else
    localparam integer NU = `NU;
`endif
`ifndef NUP
    localparam integer NUP = 4;
`else
    localparam integer NUP = `NUP;
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
    localparam integer SW = 320, SL = 700, R = 3, T0 = 40, SB = 1000, AW = 24, NWD = SB + NU * SW;
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    integer cyc = 0, errs = 0, nrd = 0, nwr = 0, u, r, b, k;
    function automatic [1023:0] g(input integer uu, input integer rr, input integer bb);
        integer q; reg [31:0] w;
        begin for (q = 0; q < 32; q = q + 1) begin w = 32'(uu * 1000003 + rr * 7919 + bb * 131 + q * 2654435 + 17); g[32*q +: 32] = w ^ {w[15:0], w[31:16]}; end end
    endfunction
    reg [20:0] f_c = 0; reg [1024:0] f_d = 0; wire [AW+1:0] t_a; wire [1023:0] t_d; wire [2:0] mf;
    dsdv_mu_seed #(.NUSER(NU), .SB(SB), .AW(AW), .MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .f_c(f_c), .f_d(f_d),
        .t_a(t_a), .t_d(t_d), .t_mf(mf));
    reg [1023:0] mem [0:NWD-1];
    // expected-beat pipe (drive edge -> t_a after 2 edges)
    reg pv [0:7]; integer pu [0:7], pr [0:7], pb [0:7]; reg pw [0:7];
    initial for (k = 0; k < 8; k = k + 1) pv[k] = 0;
    integer t, ws;
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (cyc == 10) rst_n <= 1'b1;
        f_c <= 21'd0; f_d <= 1025'd0; pv[cyc % 8] = 0;
        for (u = 0; u < NU; u = u + 1) for (r = 0; r < R; r = r + 1) begin
            ws = T0 + (r * NUP + u) * SL;
            // read window (r > 0) at ws, write window at ws + SW + 10
            if (r > 0 && cyc >= ws && cyc < ws + SW) begin
                b = cyc - ws; f_c <= {1'b1, 1'b0, 10'(u), 9'(b)};
                pv[cyc % 8] = 1; pu[cyc % 8] = u; pr[cyc % 8] = r - 1; pb[cyc % 8] = b; pw[cyc % 8] = 0;
            end
            if (cyc >= ws + SW + 10 && cyc < ws + 2 * SW + 10) begin
                b = cyc - ws - SW - 10;
                if (COLLIDE && u == 1 && r == 0 && b == 100) begin
                    f_c <= {1'b1, 1'b1, 10'd0, 9'd0}; f_d <= {g(0, 99, 0), 1'b1}; pv[cyc % 8] = 0;
                end else begin
                    f_c <= {1'b1, 1'b1, 10'(u), 9'(b)}; f_d <= {g(u, r, b), 1'b1};
                    pv[cyc % 8] = 1; pu[cyc % 8] = u; pr[cyc % 8] = r; pb[cyc % 8] = b; pw[cyc % 8] = 1;
                end
            end
        end
        if (t_a[AW+1] && t_a[AW]) mem[t_a[AW-1:0]] <= t_d;
    end
    // check at the negedge after the t_a edge: the beat driven at edge cyc - 3
    reg [63:0] h0 = 64'd0; integer n0 = 0, e;
    always @(negedge ck) if (rst_n) begin
        e = (cyc + 8 - 3) % 8;
        if (t_a[AW+1] != (pv[e] === 1'b1 && cyc >= 3)) begin
            errs = errs + 1; if (errs < 6) $display("ERR %0d t_a valid %0d expected %0d", cyc, t_a[AW+1], pv[e]);
        end else if (t_a[AW+1]) begin
            if (t_a[AW-1:0] != AW'(SB + pu[e] * SW + pb[e]) || t_a[AW] != pw[e]) begin
                errs = errs + 1; if (errs < 6) $display("ERR %0d user %0d beat %0d addr %0d we %0d", cyc, pu[e], pb[e], t_a[AW-1:0], t_a[AW]);
            end
            if (!t_a[AW]) begin
                nrd = nrd + 1;
                if (mem[t_a[AW-1:0]] !== g(pu[e], pr[e], pb[e])) begin
                    errs = errs + 1; if (errs < 6) $display("ERR %0d user %0d round %0d beat %0d: read state != own write", cyc, pu[e], pr[e], pb[e]);
                end
            end else nwr = nwr + 1;
            if (pu[e] == 0) begin h0 = (h0 * 64'd1099511628211) ^ {cyc[31:0], 7'd0, t_a[AW:0]}; n0 = n0 + 1; end
        end
    end
    initial begin
        #(T0 + (R * NUP + NU) * SL + 100);
        if (COLLIDE) begin
            if (mf[0]) $display("MUSEED COLLIDE NU %0d PASS (fault raised) t_mf %b", NU, mf);
            else $display("MUSEED COLLIDE NU %0d FAIL (no fault) t_mf %b", NU, mf);
        end else begin
        if (mf != 3'd0) begin errs = errs + 1; $display("ERR t_mf %b", mf); end
        if (nrd != NU * (R - 1) * SW || nwr != NU * R * SW) begin errs = errs + 1; $display("ERR beats rd %0d wr %0d", nrd, nwr); end
        $display("U0 TRACE n %0d hash %h", n0, h0);
        $display("MUSEED NU %0d NUP %0d: %0d read beats, %0d write beats, errs %0d", NU, NUP, nrd, nwr, errs);
        if (errs == 0) $display("MUSEED PASS"); else $display("MUSEED FAIL");
        end
        $finish;
    end
endmodule
