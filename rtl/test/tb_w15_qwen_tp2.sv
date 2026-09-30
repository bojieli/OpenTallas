`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W15: the Qwen3-8B TP-2 pair's UCIe exchanges end to end.  Two dies, each on
// its own clock, each with the one-shot engine ot_rom_oneshot_die N=2 exactly
// as rtl/test/hostbinding/ot_qwen_tp_host_binding.sv binds it (LANES, DEPTH
// parameters), joined by two ot_link_tx -> ot_link_chan_model -> ot_link_rx
// UCIe-A link directions with the floorplan's hub-to-edge wire stages.
//
// A token's exchange sequence: EXCH exchanges, the first EXCH-1 all-reduces of
// H FP32 partials each (2 per layer: after o and after down), the last the
// argmax gather (one word).  Every die issues exchange 0 at global time T0 and
// each next exchange GAP cycles after its own last result word.  Every result
// word is checked against the golden sum p0 + p1 (tools/hdc_golden.add).
// ---------------------------------------------------------------------------
module tb_w15_qwen_tp2 #(
    parameter integer LANES = 16,
    parameter integer DEPTH = 16,
    parameter integer ADD_LAT = 5,
    parameter integer FIFO_SRAM = 0, SRAM_MACRO = 0,
    parameter integer H = 4096,
    parameter integer EXCH = 73,
    parameter real    T_CORE = 0.9102,
    parameter real    U_T = 1.0,
    parameter integer U_WIRE = 17, U_FC = 1, U_NL = 2,
    parameter integer T0 = 64, GAP = 2
);
    localparam integer N = 2, FW = 32 * LANES, PW = FW + 2 + 32, TSW = 16;
    localparam integer WPE = (H * 32 + FW - 1) / FW;       // words per all-reduce exchange
    localparam integer BW = TSW + 1 + 1 + PW, FRW = U_FC * U_NL * (BW + 1) + 32;
    integer seed, seed0, DET, U_DREL;
    real U_DLY, U_JS, U_WAN;
    string vecdir;
    reg [FW-1:0] part [0:N*WPE-1];
    reg [FW-1:0] expw [0:WPE-1];
    reg [FW-1:0] gat  [0:N-1];
    reg ready = 0, go_clk = 0;
    real ph [0:3];
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        seed0 = seed;
        if (!$value$plusargs("VEC=%s", vecdir)) $fatal(1, "missing VEC");
        if (!$value$plusargs("DET=%d", DET)) DET = 1;
        if (!$value$plusargs("U_DREL=%d", U_DREL)) U_DREL = 64;
        if (!$value$plusargs("U_DLY=%f", U_DLY)) U_DLY = 2.0;
        if (!$value$plusargs("U_JS=%f", U_JS)) U_JS = 0.5;
        if (!$value$plusargs("U_WAN=%f", U_WAN)) U_WAN = 0.05;
        for (integer i = 0; i < 4; i = i + 1) ph[i] = (($unsigned($random(seed)) % 1000) / 1000.0);
        $readmemh({vecdir, "/part.hex"}, part);
        $readmemh({vecdir, "/exp.hex"}, expw);
        $readmemh({vecdir, "/gather.hex"}, gat);
        ready = 1;
        $display("W15QCFG seed=%0d lanes=%0d depth=%0d det=%0d words_per_exchange=%0d U(T=%0.4f dly=%0.3f js=%0.3f wire=%0d nl=%0d drel=%0d)",
                 seed0, LANES, DEPTH, DET, WPE, U_T, U_DLY, U_JS, U_WIRE, U_NL, U_DREL);
        go_clk = 1;
    end
    reg [N-1:0] clk = 0, lu = 0, rst_n = 0, rst_u = 0;
    reg [TSW-1:0] now [0:N-1];
    genvar s;
    generate for (s = 0; s < N; s = s + 1) begin : g_clk
        initial begin wait(go_clk); #(T_CORE * ph[2*s]); forever #(T_CORE/2) clk[s] = ~clk[s]; end
        initial begin wait(go_clk); #(U_T * ph[2*s+1]);  forever #(U_T/2) lu[s] = ~lu[s]; end
        always @(posedge clk[s]) rst_n[s] <= ($realtime > 40.0) && ready;
        always @(posedge lu[s]) rst_u[s] <= ($realtime > 40.0);
        initial now[s] = 0;
        always @(posedge clk[s]) if (rst_n[s]) now[s] <= now[s] + 1'b1;
    end endgenerate

    wire [N-1:0] txv, iv, ir, ov, ol, oe, flt;
    wire [N*PW-1:0] txr;
    wire [N*N-1:0] txrdy, crin, crout, rxv;
    wire [N*N*PW-1:0] rxr;
    wire [N*FW-1:0] od;
    wire [N-1:0] orank;
    wire [N*3-1:0] fc;
    reg  [N-1:0] fin = 0;
    wire [N-1:0] lf;
    generate for (s = 0; s < N; s = s + 1) begin : g_die
        // producer: exchange e streams WPE partial words (or one argmax word), one per accepted cycle
        integer e = -1, k = 0, st = 0, waitc = 0, got = 0;
        integer issue_c [0:EXCH-1], first_o [0:EXCH-1], last_o [0:EXCH-1], last_in [0:EXCH-1];
        wire gatherx = (e == EXCH - 1);
        wire [31:0] nw = gatherx ? 1 : WPE;
        assign iv[s] = (st == 1) && (k < nw);
        wire [FW-1:0] ind = gatherx ? gat[s] : part[s*WPE + k];
        ot_rom_oneshot_die #(.N(N), .RANK(s), .LANES(LANES), .TAGW(32), .DEPTH(DEPTH), .ADD_LAT(ADD_LAT), .FIFO_SRAM(FIFO_SRAM), .SRAM_MACRO(SRAM_MACRO)) u_e (
            .clk(clk[s]), .rst_n(rst_n[s]), .in_valid(iv[s]), .in_ready(ir[s]), .in_data(ind),
            .in_last(k == nw - 1), .in_mode(gatherx), .in_tag(e[31:0]),
            .tx_valid(txv[s]), .tx_rec(txr[s*PW +: PW]), .tx_ready(txrdy[s*N +: N]), .cr_in(crin[s*N +: N]),
            .rx_valid(rxv[s*N +: N]), .rx_rec(rxr[s*N*PW +: N*PW]), .cr_out(crout[s*N +: N]),
            .out_valid(ov[s]), .out_data(od[s*FW +: FW]), .out_last(ol[s]), .out_rank(orank[s]),
            .out_err(oe[s]), .fault(flt[s]), .fault_code(fc[s*3 +: 3]));
        always @(posedge clk[s]) if (rst_n[s]) begin
            case (st)
                0: if (now[s] == T0 - 1) begin e <= 0; k <= 0; got <= 0; st <= 1; issue_c[0] = now[s] + 1; end
                1: begin
                    if (iv[s] && ir[s]) begin
                        k <= k + 1;
                        if (k == nw - 1) begin last_in[e] = now[s]; st <= 2; end
                    end
                end
                2: ;
                3: if (waitc <= 1) begin
                        e <= e + 1; k <= 0; got <= 0; st <= 1; issue_c[e + 1] = now[s] + 1;
                   end else waitc <= waitc - 1;
                default: ;
            endcase
            if (ov[s]) begin : chk
                integer want_words;
                want_words = gatherx ? N : WPE;
                if (got == 0) first_o[e] = now[s];
                if (gatherx) begin
                    if (od[s*FW +: FW] !== gat[got]) $fatal(1, "gather mismatch die=%0d word=%0d", s, got);
                end else if (od[s*FW +: FW] !== expw[got]) $fatal(1, "reduce mismatch die=%0d ex=%0d word=%0d", s, e, got);
                got <= got + 1;
                if (got == want_words - 1) begin
                    last_o[e] = now[s];
                    if (e == EXCH - 1) begin fin[s] <= 1'b1; st <= 4; end
                    else begin waitc <= GAP; st <= 3; end
                end
            end
        end
    end endgenerate

    // two UCIe link directions
    generate for (s = 0; s < N; s = s + 1) begin : g_link
        localparam integer T = 1 - s;
        wire rdy, fv, rfv, rclk, ovv, f0, f1, f2, f3;
        wire [FRW-1:0] fd, rfd;
        wire [PW-1:0] orec;
        wire [TSW-1:0] amin, amax;
        assign txrdy[s*N + s] = 1'b1;
        assign txrdy[s*N + T] = rdy;
        assign crin[s*N + s] = 1'b0;
        assign rxv[T*N + T] = 1'b0;
        assign rxr[(T*N + T)*PW +: PW] = {PW{1'b0}};
        ot_link_tx #(.NVC(1), .PW(PW), .CW(1), .TSW(TSW), .WIRE(U_WIRE), .AW(6), .NL(U_NL), .FRAME_CYCLES(U_FC)) u_tx (
            .clk(clk[s]), .rst_n(rst_n[s]), .now(now[s]), .vc_valid(txv[s]), .vc_ready(rdy), .vc_rec(txr[s*PW +: PW]),
            .cr_pulse(crout[s*N + T]), .lclk(lu[s]), .lrst_n(rst_u[s]), .f_valid(fv), .f_data(fd), .fault(f0),
            .stat_bundles(), .stat_gated_stall());
        ot_link_chan_model #(.FRW(FRW), .T_NS(U_T), .JDYN_FRAC(0.8)) u_ch (
            .DLY_NS(U_DLY), .JSTATIC_NS(U_JS), .WANDER_NS(U_WAN), .clk_tx(lu[s]), .f_valid(fv), .f_data(fd), .seed(seed0 * 31 + s), .flip_at(-1),
            .rclk(rclk), .rf_valid(rfv), .rf_data(rfd));
        reg rr = 0;
        always @(posedge rclk) rr <= ($realtime > 40.0);
        ot_link_rx #(.NVC(1), .PW(PW), .CW(1), .TSW(TSW), .WIRE(U_WIRE), .AW(6), .NL(U_NL), .FRAME_CYCLES(U_FC)) u_rx (
            .rclk(rclk), .rrst_n(rr), .f_valid(rfv), .f_data(rfd), .clk(clk[T]), .rst_n(rst_n[T]), .now(now[T]), .det(DET[0]), .drel(TSW'(U_DREL)),
            .vc_valid(ovv), .vc_rec(orec), .cr_pulse(crin[T*N + s]), .fault_crc(f1), .fault_late(f2),
            .fault_ovf(f3), .stat_min_age(amin), .stat_max_age(amax), .stat_max_wait(), .stat_bundles());
        assign rxv[T*N + s] = ovv;
        assign rxr[(T*N + s)*PW +: PW] = orec;
        assign lf[s] = f0 | f1 | f2 | f3;
    end endgenerate

    initial begin : finish
        integer x, d;
        wait (&fin);
        repeat (10) @(posedge clk[0]);
        for (x = 0; x < EXCH; x = x + 1)
            for (d = 0; d < N; d = d + 1)
                $display("QX ex=%0d die=%0d issue=%0d last_in=%0d first_out=%0d last_out=%0d", x, d,
                         d ? g_die[1].issue_c[x] : g_die[0].issue_c[x], d ? g_die[1].last_in[x] : g_die[0].last_in[x],
                         d ? g_die[1].first_o[x] : g_die[0].first_o[x], d ? g_die[1].last_o[x] : g_die[0].last_o[x]);
        $display("W15QDONE seed=%0d faults=%0d link_faults=%b engine_faults=%b out_err=%b min_age=%0d/%0d max_age=%0d/%0d",
                 seed0, (|flt) || (|lf) || (|oe), lf, flt, oe, g_link[0].amin, g_link[1].amin,
                 g_link[0].amax, g_link[1].amax);
        $finish;
    end
    initial begin #(5000000.0); $display("W15QTIMEOUT fin=%b", fin); $finish; end
endmodule
