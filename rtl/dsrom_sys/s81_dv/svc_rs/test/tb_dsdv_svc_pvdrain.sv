`timescale 1ns/1ps
// SVC-PV 2026-10-18: P.V drain probe of the D = 32 engine share (tb_dsdv_svc_pfeed + dsdv_svc_att's EXACT owner drain):
// p feed one step a cycle from P0 (no look at p_ready), the owner drain from the fixed cycle DS (8 beats x 5 words back
// to back, the 4-deep pvq, pv_cr with the beat's last word, as dsdv_svc_att).  Reports fc15 (push into a full pvq),
// fc19 (beat absent at its slot), the cycle of every P.V beat and the max occupancy, so the compiler's PO / PVO rule
// (DS - P0 window per owner) is pinned to the engine.  +t=T +p0=P0 +ds=DS +nocr (never return pv_cr: no-credit check)
module tb_dsdv_svc_pvdrain #(parameter integer PVC = 4);   // PVC = dsdv_svc_att PV_CRED (engine credits = pvq depth)
    localparam integer H = 16, D = 32, TD = 32, NL = 4, NT = NL * (D / TD), R = TD / H;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer T = 46, P0 = 40, DS = 200, NOCR = 0, RCEND = 4000, cyc = 0;
    reg ej_v = 0, eq_v = 0, ekv_v = 0, ep_v = 0, sc_cr = 0, pv_cr = 0;
    wire ej_ready, eq_ready, kv_ready, ep_ready;
    wire sc_v; wire [15:0] sc_row; wire [NL-1:0] sc_m; wire [NL*H*32-1:0] sc_y; wire [NL*H-1:0] sc_f;
    wire pv_v; wire [7:0] pv_c; wire [NT*H*32-1:0] pv_y; wire [NT*H-1:0] pv_f;
    reg [D*16-1:0] eq_w = 0; reg [NL*(D/32)*265-1:0] ekv_w = 0; reg [NL-1:0] ekv_m = 0; reg [2*TD*16-1:0] ep_w = 0;
    ot_hdc_v41x_attn_s #(.H(H), .D(D), .TD(TD), .NL(NL), .TROWS(640), .SRAM_MACRO(0), .PWORDS(2),
                         .ILV(1), .REPL(2), .NSTAGE(2), .FPL(3), .FML(3), .NBANKP(0), .TILE_S(0),
                         .NARROW(0), .MFAN(0), .TRX(0), .F12(0), .FPLX(0), .SC_CRED(8), .PV_CRED(PVC)) u_eng (
        .clk(clk), .rst_n(rst_n), .job_v(ej_v), .job_t(16'(T)), .job_ready(ej_ready),
        .q_v(eq_v), .q_w(eq_w), .q_ready(eq_ready),
        .kv_v(ekv_v), .kv_m(ekv_m), .kv_w(ekv_w), .kv_ready(kv_ready),
        .sc_v(sc_v), .sc_row(sc_row), .sc_m(sc_m), .sc_y(sc_y), .sc_f(sc_f), .sc_cr(sc_cr),
        .p_v(ep_v), .p_w(ep_w), .p_ready(ep_ready),
        .pv_v(pv_v), .pv_c(pv_c), .pv_y(pv_y), .pv_f(pv_f), .pv_cr(pv_cr),
        .qk_iss(), .pv_iss());
    integer nbeat, p_left, refused = 0, first_ref = -1, rc = 0, pv_n = 0, last_pv = -1, pvq = 0, p_i = 0, last_sc = -1;
    integer bad_rdy = 0, pvw = 0, pvr = 0, pvw_n = 0, pvr_n = 0, f15 = 0, f19 = 0, occ_max = 0, dbeat = 0, first_pv = -1;
    reg dr_on = 0;
    initial begin
        if ($value$plusargs("t=%d", T)) ;
        if ($value$plusargs("p0=%d", P0)) ;
        if ($value$plusargs("ds=%d", DS)) ;
        if ($test$plusargs("nocr")) NOCR = 1;
        if ($value$plusargs("rcend=%d", RCEND)) ;
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
        // owner P.V drain exactly as dsdv_svc_att: from DS, 8 beats x 5 words back to back; pv_cr with word 4
        if (pv_v) begin
            if (pvw - pvr >= PVC) f15 = f15 + 1;
            pv_n = pv_n + 1; $display("PVBEAT n=%0d rc=%0d occ_before=%0d cred=%0d", pv_n, rc, pvw - pvr, u_eng.pv_cred);
            pvw_n = pvw + 1;
        end else pvw_n = pvw;
        pvr_n = pvr;
        if (rc == DS) begin dr_on = 1; p_i = 0; dbeat = 0; end
        else if (dr_on) begin
            if (p_i == 0 && pvw == pvr) f19 = f19 + 1;
            if (p_i == 4) begin
                pvr_n = pvr + 1; if (!NOCR) pv_cr <= 1; last_pv = rc; dbeat = dbeat + 1; p_i = 0;
                if (dbeat == 8) dr_on = 0;
            end else p_i = p_i + 1;
        end
        pvw = pvw_n; pvr = pvr_n;
        if (pvw - pvr > occ_max) occ_max = pvw - pvr;
        if (rc == RCEND) begin
            $display("PVDRAIN PVC=%0d T=%0d p0=%0d ds=%0d nocr=%0d refused=%0d first_refused_rc=%0d last_score_rc=%0d pv_beats=%0d f15=%0d f19=%0d occ_max=%0d last_pv_word_rc=%0d prog_not_ready=%0d",
                     PVC, T, P0, DS, NOCR, refused, first_ref, last_sc, pv_n, f15, f19, occ_max, last_pv, bad_rdy);
            $finish;
        end
    end
endmodule
