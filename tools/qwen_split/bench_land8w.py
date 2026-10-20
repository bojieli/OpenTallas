#!/usr/bin/env python3
"""QW-LANDW 10-19: writes the Verilator testbench of the WIDE D8 hop-0 landings for one master (bench_land8.py
generalised: full-width words, and --sram for the SRAM record slice rtl/qwen_split/qfd_land8s.sv).

usage: bench_land8w.py <master module> <W> <out tb.sv> [--sram]

Flop masters (ot_qfd_land8, W 107 / 116): the bench_land8.py calendar, K = (L + G - R0 - 1) mod 16, age (L - 1) T + phi.
SRAM masters (ot_qfd_land8s): SR = 1, o after receiver edge t = w(t - L) with K = (L + G - R0 - 2) mod 16, macro write ->
read age (L - 3) T + phi in the D8 window, o = 0 until R0 + 4 + K (K = 0 -> 16); the checks skip one more edge after each
reset drop (the registered read).  Words are full width (one 32-bit hash per 32-bit chunk), so every bank is checked.

72 lanes = 8 receiver phases (0 .. 8.75 ns of a 10 ns period, T/8 steps) x LADD 0..2 (write -> read age from 1.25 T to
~4.2 T, the D8 window [1.25 T, 4.125 T] plus margin) x 3 release orders (source first / receiver first / near).  Every
lane gets its own strap K = (L + G - R0 - 1) mod 16, targeted so that K = 0..15 are all covered (K >= 8 needs the fourth
strap pin), and one of four reset scenarios:
  SC0 single release;  SC1 PAIRED restart (both resets drop, re-release with G2 - R2 = G - R0);
  SC2 SOURCE-only restart (receiver keeps running, G2 = G mod 16);  SC3 RECEIVER-only restart (R2 = R0 mod 16).
Checked on EVERY receiver edge except the two edges at each reset drop: o = 0 before warm (K read edges after the
receiver release, K = 0 meaning 16), o = 0 for a word not written in the current source epoch, else o = w(t - L); fault
stays 0.  Data leg 1.2 ns, bank contents start arbitrary (--x-initial unique, several seeds).
"""
import sys

T = 10.0


def lanes(sr=0):
    out = []
    idx = 0
    for ph in range(8):
        doff = ph * T / 8.0
        for ladd in range(3):
            for order in range(3):
                l0 = -int(-(2.25 + 2 * sr - doff / T) // 1)   # ceil: smallest L with (L - 1 - 2 SR) T + doff >= 1.25 T
                L = l0 + ladd
                K = (idx * 5 + ph) % 16
                if order == 0:      # source first
                    r0 = 40
                    base_g = 12
                elif order == 1:    # receiver first (source late: zero bubbles after warm)
                    r0 = 12
                    base_g = 45
                else:               # near
                    r0 = 20
                    base_g = 18
                g = base_g + ((K - L + r0 + 1 + sr - base_g) % 16)
                assert (L + g - r0 - 1 - sr) % 16 == K
                sc = idx % 4
                out.append(dict(i=idx, doff=doff, L=L, K=K, G=g, R0=r0, SC=sc, SR=sr))
                idx += 1
    return out


def main():
    master, w, path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    sr = 1 if '--sram' in sys.argv[4:] else 0
    L = lanes(sr)
    src = [r"""`timescale 1ns/1ps
module lane8 #(parameter integer W = 1, parameter real DOFF = 0.0, parameter integer L = 2, K = 0, G = 20, R0 = 20,
               SC = 0, SR = 0) (input wire cks, input wire [31:0] es, output integer err, output integer chk, output wire flt);
    localparam integer KW = (K == 0) ? 16 : K;
    // restarts: source drop after edge XS, re-release G2; receiver drop after edge Y, re-release R2
    localparam integer XS = (SC == 1 || SC == 2) ? G + 150 : 1 << 30;
    localparam integer G2 = (SC == 1) ? G + 163 : (SC == 2) ? G + 160 : G;
    localparam integer Y  = (SC == 1) ? R0 + 150 : (SC == 3) ? R0 + 140 : 1 << 30;
    localparam integer R2 = (SC == 1) ? R0 + 163 : (SC == 3) ? R0 + 160 : R0;
    // receiver root DOFF behind the source root (an inverted, shorter delay when DOFF >= T/2: no swallowed pulses)
    wire ckd;
    generate if (DOFF < 5.0) begin : g_lo
        assign #(DOFF) ckd = cks;
    end else begin : g_hi
        wire nck = ~cks;
        assign #(DOFF - 5.0) ckd = nck;
    end endgenerate
    reg [31:0] ed = 0;
    always @(posedge ckd) ed <= ed + 1;
    reg [W-1:0] src = 0;
    // power-on: both resets are released for the first 3 edges (arbitrary state runs), then ASSERT: the asynchronous
    // clear chains see real falling edges (a simulator applies negedge-only clears to a cascade only on events)
    reg en = 1, rs = 1;
    function automatic [W-1:0] w_of(input integer e);
        integer j; reg [31:0] h;
        begin
            for (j = 0; j < W; j = j + 1) begin
                h = (e * 40503 + (e >>> 3) + 7) ^ ((j / 32) * 32'h9e3779b9) ^ ((j / 32) * 977);
                w_of[j] = h[j % 32];
            end
        end
    endfunction
    always @(posedge cks) begin
        src <= w_of(es);
        en  <= (es < 3 || (es >= G && !(es >= XS && es < G2))) ? 1'b1 : 1'b0;
    end
    always @(posedge ckd) rs <= (ed < 3 || (ed >= R0 && !(ed >= Y && ed < R2))) ? 1'b1 : 1'b0;
    wire [W-1:0] a;
    assign #(1.2) a = src;
    wire [W-1:0] o; wire hi, lo;
    wire [3:0] kk = K[3:0];
    MASTER u_l (.ck_s(cks), .en(en), .a(a), .ck(ckd), .rs(rs), .k0(kk[0]), .k1(kk[1]), .k2(kk[2]), .k3(kk[3]),
                .tie_hi(hi), .tie_lo(lo), .b(o), .fault(flt));
    initial begin
        err = 0; chk = 0;
        $display("LAND8_LANE %m DOFF=%0.3f L=%0d K=%0d G=%0d R0=%0d SC=%0d SR=%0d age=%0.3fT", DOFF, L, K, G, R0, SC, SR,
                 ((L - 1 - 2 * SR) * 10.0 + DOFF) / 10.0);
    end
    integer t, e, gc, rc_, skip;
    reg [W-1:0] ex;
    always @(negedge ckd) begin
        t = ed - 1;                                   // o now holds the capture of receiver edge t
        if ($test$plusargs("trace") && t < 45) $display("LAND8_TRACE %m t=%0d es=%0d en=%b rs=%b rc=%0d wc=%0d warm=%b o=%h", t, es,
            en, rs, u_l.u_land.rc, u_l.u_land.wc, u_l.u_land.warm, o);
        if (t >= 6) begin
            skip = ((t >= XS && t <= XS + 1 + SR) || (t >= Y && t <= Y + 1 + SR)) ? 1 : 0;
            // paired restart: between the first drop and the later re-release only ONE side has restarted, so the
            // strap does not describe that interval (the die never uses a lane there); checked again after both
            if (SC == 1 && t >= ((XS < Y) ? XS : Y) && t < ((G2 + L + 3 > R2 + 3 + SR + KW) ? G2 + L + 3 : R2 + 3 + SR + KW)) skip = 1;
            rc_ = (t > Y) ? R2 : R0;
            gc  = (t > XS) ? G2 : G;
            e = t - L;
            if (t < rc_ + 3 + SR + KW) ex = {W{1'b0}};
            else if (e >= gc + 2) ex = w_of(e);
            else ex = {W{1'b0}};
            if (!skip) begin
                chk = chk + 1;
                if (o !== ex) begin
                    err = err + 1;
                    if (err < 4 || $test$plusargs("all")) $display("LAND8_MISMATCH %m t=%0d o=%h exp=%h", t, o, ex);
                end
                if (flt !== 1'b0) begin
                    err = err + 1;
                    if (err < 4) $display("LAND8_FAULT %m t=%0d fault=%b", t, flt);
                end
            end
        end
    end
endmodule

module tb;
    reg cks = 0;
    reg [31:0] es = 0;
    always #5 cks = ~cks;
    always @(posedge cks) es <= es + 1;
""".replace("MASTER", master)]
    src.append(f"    localparam integer NL = {len(L)};")
    src.append("    integer e [0:NL-1], c [0:NL-1]; wire f [0:NL-1];")
    for r in L:
        src.append(f"    lane8 #(.W({w}), .DOFF({r['doff']:.3f}), .L({r['L']}), .K({r['K']}), .G({r['G']}), .R0({r['R0']}), "
                   f".SC({r['SC']}), .SR({r['SR']})) l{r['i']} (cks, es, e[{r['i']}], c[{r['i']}], f[{r['i']}]);")
    ks = sorted({r['K'] for r in L})
    src.append(f"    // K coverage: {ks}")
    src.append(r"""    initial begin
        #4200;
        begin : sum
            integer i, te, tc;
            te = 0; tc = 0;
            for (i = 0; i < NL; i = i + 1) begin te = te + e[i]; tc = tc + c[i]; end
            $display("LAND8_BENCH %s %0d errors in %0d checks (%0d lanes, K 0..15)", (te || tc < 20000) ? "FAIL" : "PASS",
                     te, tc, NL);
        end
        $finish;
    end
endmodule""")
    open(path, "w").write("\n".join(src) + "\n")


if __name__ == "__main__":
    main()
