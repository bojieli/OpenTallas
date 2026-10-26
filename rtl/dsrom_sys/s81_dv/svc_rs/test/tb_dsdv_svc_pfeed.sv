`timescale 1ns/1ps
// S81U-SVC4 2026-10-17: probe of the D = 32 attention engine share (ot_hdc_v41x_attn_s exactly as dsdv_svc_att
// instantiates it) for the STATIC P.V feed.  It runs dsdv_svc_att's compiled program (job at 0, q heads 1..16, row
// beats 1..nbeat, score credit back the next cycle, owner-slice P.V drain 5 words a beat) and offers the p words at a
// FIXED cycle P0 after the job, one step (2 words) every cycle, with no look at p_ready.  It reports, per T, the
// smallest P0 from which the engine accepts every step (pfeed_min) and the cycle the last P.V beat leaves, so the
// compiler's PO rule (the GO frame's p offset) and the slice's sticky refusal fault are pinned to the engine.
// +t=T, +p0=P0 (the probe sweeps nothing itself; tools/s81_dv/svc_rs/pfeed_probe.sh sweeps).
module tb_dsdv_svc_pfeed;
    localparam integer H = 16, D = 32, TD = 32, NL = 4, NT = NL * (D / TD), R = TD / H;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer T = 46, P0 = 40, cyc = 0;
    reg ej_v = 0, eq_v = 0, ekv_v = 0, ep_v = 0, sc_cr = 0, pv_cr = 0;
    wire ej_ready, eq_ready, kv_ready, ep_ready;
    wire sc_v; wire [15:0] sc_row; wire [NL-1:0] sc_m; wire [NL*H*32-1:0] sc_y; wire [NL*H-1:0] sc_f;
    wire pv_v; wire [7:0] pv_c; wire [NT*H*32-1:0] pv_y; wire [NT*H-1:0] pv_f;
    reg [D*16-1:0] eq_w = 0; reg [NL*(D/32)*265-1:0] ekv_w = 0; reg [NL-1:0] ekv_m = 0; reg [2*TD*16-1:0] ep_w = 0;
    ot_hdc_v41x_attn_s #(.H(H), .D(D), .TD(TD), .NL(NL), .TROWS(640), .SRAM_MACRO(0), .PWORDS(2),
                         .ILV(1), .REPL(2), .NSTAGE(2), .FPL(3), .FML(3), .NBANKP(0), .TILE_S(0),
                         .NARROW(0), .MFAN(0), .TRX(0), .F12(0), .FPLX(0), .SC_CRED(8), .PV_CRED(4)) u_eng (
        .clk(clk), .rst_n(rst_n), .job_v(ej_v), .job_t(16'(T)), .job_ready(ej_ready),
        .q_v(eq_v), .q_w(eq_w), .q_ready(eq_ready),
        .kv_v(ekv_v), .kv_m(ekv_m), .kv_w(ekv_w), .kv_ready(kv_ready),
        .sc_v(sc_v), .sc_row(sc_row), .sc_m(sc_m), .sc_y(sc_y), .sc_f(sc_f), .sc_cr(sc_cr),
        .p_v(ep_v), .p_w(ep_w), .p_ready(ep_ready),
        .pv_v(pv_v), .pv_c(pv_c), .pv_y(pv_y), .pv_f(pv_f), .pv_cr(pv_cr),
        .qk_iss(), .pv_iss());
    integer nbeat, p_left, refused = 0, first_ref = -1, rc = 0, pv_n = 0, last_pv = -1, pvq = 0, p_i = 0, last_sc = -1;
    integer bad_rdy = 0;
    initial begin
        if ($value$plusargs("t=%d", T)) ;
        if ($value$plusargs("p0=%d", P0)) ;
        nbeat = (T + 3) / 4; p_left = (T + R - 1) / R;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1;
        // compiled program, job at rc = 0 (cycle 10)
        ej_v <= 0; eq_v <= 0; ekv_v <= 0; ep_v <= 0; sc_cr <= sc_v; pv_cr <= 0;
        if (cyc >= 10) rc = cyc - 10; else rc = -1;
        if (rc == 0) ej_v <= 1;
        if (rc >= 1 && rc <= 16) begin eq_v <= 1; eq_w <= {D*16{1'b0}} | 512'(rc); end
        if (rc >= 1 && rc <= nbeat) begin
            ekv_v <= 1; ekv_m <= (4 * rc <= T) ? 4'hf : 4'((1 << (T - 4 * (rc - 1))) - 1);
        end
        if (ej_v && !ej_ready || eq_v && !eq_ready || ekv_v && !kv_ready) bad_rdy = bad_rdy + 1;
        // static p feed: one step a cycle from P0
        if (rc >= P0 && p_left > 0) begin
            ep_v <= 1; ep_w <= {2*TD*16{1'b0}} | 1024'(rc);
            p_left = p_left - ((p_left >= 2) ? 2 : p_left);
        end
        if (ep_v && !ep_ready) begin refused = refused + 1; if (first_ref < 0) first_ref = rc - 1; end
        if (sc_v) last_sc = rc;
        // owner P.V drain: 5 words a beat, credit back with the last word
        if (pv_v) begin pvq = pvq + 1; pv_n = pv_n + 1; end
        if (pvq > 0) begin
            if (p_i == 4) begin p_i = 0; pvq = pvq - 1; pv_cr <= 1; last_pv = rc; end else p_i = p_i + 1;
        end
        if (rc == 4000) begin
            $display("PFEED T=%0d p0=%0d refused=%0d first_refused_rc=%0d last_score_rc=%0d pv_beats=%0d last_pv_word_rc=%0d prog_not_ready=%0d",
                     T, P0, refused, first_ref, last_sc, pv_n, last_pv, bad_rdy);
            $finish;
        end
    end
endmodule
