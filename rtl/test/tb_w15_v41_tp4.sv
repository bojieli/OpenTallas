`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W15: the V4.1 TP-4 group (2 dies per package x 2 packages) end to end, with
// every die on its OWN clock and every die-to-die link a physical-link model:
//
//   engine  ot_rom_oneshot_die_px (the die's one-shot collective engine,
//           fixed-order FP32 ((r0+r1)+(r2+r3)) all-reduce, rank-order gather)
//   DMA     ot_chip_v41x_coll_dma + a behavioural VM per die
//   links   ot_link_tx -> ot_link_chan_model -> ot_link_rx for each of the
//           12 directed die pairs:
//             same package:  UCIe-A (VC0 direct, VC1/VC2 the relayed records
//                            of the two partner-package sources when RELAY=1)
//             across:        112G PAM4 board link, RS(272,257) codeword frames
//           credits ride the reverse link in every bundle.
//
// The exact 12-COLL layer-0 descriptor sequence (tools/rtl_v41_tp_layer0_
// collectives.py prepare) runs self-timed on every die: op 0 is issued at
// global time T0, op k+1 GAP cycles after the die's own op k completes.  Every
// VM write is checked against the golden image as it happens; the final VM
// contents are hashed.  Per op and die the bench prints issue, first transmit,
// last transmit, first and last VM commit and completion, in the die's cycles.
// ---------------------------------------------------------------------------
module tb_w15_v41_tp4 #(
    parameter integer RELAY = 1,
    parameter integer DEPTH = 256,
    // clocks (ns)
    parameter real T_CORE = 0.92,
    // UCIe-A in package
    parameter real    U_T = 1.0,
    parameter integer U_WIRE = 22, U_ENC = 0, U_DEC = 0, U_FC = 1,
    // 112G board link
    parameter real    X_T = 0.93405,
    parameter integer X_WIRE = 29, X_ENC = 4, X_DEC = 59, X_FC = 2,
    parameter integer T0 = 64, GAP = 2
);
    localparam integer N=4, FW=512, PW=547, RB=2, WA=15, GW=4, TSW=16, NL=2;
    localparam integer OPS=12, MAXW=320, MEMW=32768;
    localparam integer UNVC = RELAY ? 3 : 1;
    localparam integer UBW = TSW + UNVC + 2 + UNVC*PW, UFRW = U_FC*NL*(UBW+1) + 32;
    localparam integer XBW = TSW + 1 + 2 + PW,        XFRW = X_FC*NL*(XBW+1) + 32;
    localparam integer U_AWTX = 6, X_AWTX = 6, U_AWRX = 5, X_AWRX = 5;

    integer seed, seed0, DET, U_DREL, X_DREL;
    real U_DLY, U_JS, U_WAN, X_DLY, X_JS, X_WAN;
    string vecdir, outpath;
    reg [31:0] desc [0:OPS-1];
    reg [FW-1:0] part [0:OPS*N*MAXW-1];
    reg [FW-1:0] expected [0:OPS*N*MAXW-1];
    reg images_ready = 0, go_clk = 0;
    real ph [0:3*N-1];
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        seed0 = seed;
        if (!$value$plusargs("VEC=%s", vecdir)) $fatal(1, "missing VEC");
        if (!$value$plusargs("OUT=%s", outpath)) outpath = "w15_v41_vm.hex";
        if (!$value$plusargs("DET=%d", DET)) DET = 1;
        if (!$value$plusargs("U_DREL=%d", U_DREL)) U_DREL = 72;
        if (!$value$plusargs("X_DREL=%d", X_DREL)) X_DREL = 210;
        if (!$value$plusargs("U_DLY=%f", U_DLY)) U_DLY = 2.0;
        if (!$value$plusargs("U_JS=%f", U_JS)) U_JS = 0.5;
        if (!$value$plusargs("U_WAN=%f", U_WAN)) U_WAN = 0.05;
        if (!$value$plusargs("X_DLY=%f", X_DLY)) X_DLY = 56.868;
        if (!$value$plusargs("X_JS=%f", X_JS)) X_JS = 3.0;
        if (!$value$plusargs("X_WAN=%f", X_WAN)) X_WAN = 0.2;
        for (integer i = 0; i < 3*N; i = i + 1) ph[i] = (($unsigned($random(seed)) % 1000) / 1000.0);
        $readmemh({vecdir, "/desc.hex"}, desc);
        $readmemh({vecdir, "/part.hex"}, part);
        $readmemh({vecdir, "/expected.hex"}, expected);
        images_ready = 1;
        $display("W15CFG seed=%0d relay=%0d depth=%0d det=%0d U(T=%0.4f dly=%0.3f js=%0.3f wire=%0d enc=%0d dec=%0d drel=%0d) X(T=%0.5f dly=%0.3f js=%0.3f wire=%0d enc=%0d dec=%0d drel=%0d)",
                 seed0, RELAY, DEPTH, DET, U_T, U_DLY, U_JS, U_WIRE, U_ENC, U_DEC, U_DREL,
                 X_T, X_DLY, X_JS, X_WIRE, X_ENC, X_DEC, X_DREL);
        go_clk = 1;
    end

    // ---- clocks: one core clock per die, one UCIe and one SerDes link clock per die (TX) ------------------
    reg [N-1:0] clk = 0, lu = 0, lx = 0, rst_n = 0, rst_u = 0, rst_x = 0;
    reg [TSW-1:0] now [0:N-1];
    genvar s, t;
    generate for (s = 0; s < N; s = s + 1) begin : g_clk
        initial begin wait(go_clk); #(T_CORE * ph[3*s]);   forever #(T_CORE/2) clk[s] = ~clk[s]; end
        initial begin wait(go_clk); #(U_T * ph[3*s+1]);    forever #(U_T/2) lu[s] = ~lu[s]; end
        initial begin wait(go_clk); #(X_T * ph[3*s+2]);    forever #(X_T/2) lx[s] = ~lx[s]; end
        // common reset release / time sync at 40 ns: each counter starts at its first edge after it
        always @(posedge clk[s]) rst_n[s] <= ($realtime > 40.0) && images_ready;
        always @(posedge lu[s]) rst_u[s] <= ($realtime > 40.0);
        always @(posedge lx[s]) rst_x[s] <= ($realtime > 40.0);
        initial now[s] = 0;
        always @(posedge clk[s]) if (rst_n[s]) now[s] <= now[s] + 1'b1;
    end endgenerate

    // ---- engine / DMA / VM nets ----------------------------------------------------------------------------
    wire [N-1:0] busy, dma_fault, efault, oerr;
    wire [N*3-1:0] ecode;
    wire [N-1:0] ev, er, el, em, ov, ory, ol;
    wire [N*FW-1:0] ed;
    wire [N*32-1:0] etag;
    wire [N*PW-1:0] txrec;
    wire [N*N-1:0] txv, txready, rxv, relaytxv, relayrxv;
    wire [N*N*PW-1:0] rxrec, relaytxrec, relayrxrec;
    wire [N*GW*FW-1:0] od;
    wire [N*RB-1:0] orank;
    wire [2*N*N-1:0] crin, crout;
    reg  [N-1:0] go = 0, mode = 0, rnd = 0;
    reg  [WA-1:0] src [0:N-1], dst [0:N-1], nn [0:N-1];
    reg  [31:0] tag [0:N-1];
    integer op [0:N-1];
    reg  [N-1:0] fin = 0;
    wire [N-1:0] lfault;
    wire [N*N-1:0] lfault_st;
    reg rep = 0;

    generate for (s = 0; s < N; s = s + 1) begin : g_die
        reg [FW-1:0] vm [0:MEMW-1];
        wire re, we;
        wire [WA-1:0] raddr, waddr;
        wire [FW-1:0] wdata;
        reg [FW-1:0] rq = 0;
        wire [3:0] we4;
        wire [4*WA-1:0] waddr4;
        wire [4*FW-1:0] wdata4;
        initial begin
            for (integer k = 0; k < MEMW; k = k + 1) vm[k] = '0;
            wait(images_ready);
            for (integer o = 0; o < OPS; o = o + 1)
                for (integer k = 0; k < MAXW; k = k + 1)
                    vm[o*512+k] = part[(o*N+s)*MAXW+k];
        end
        always @(posedge clk[s]) if (re) rq <= vm[raddr];
        ot_chip_v41x_coll_dma #(.WA(WA),.FW(FW),.TAGW(32),.N(N),.GW(GW),.VM_ALWAYS_READY(1)) u_dma (
            .clk(clk[s]),.rst_n(rst_n[s]),.go(go[s]),.mode(mode[s]),.rnd(rnd[s]),.tag(tag[s]),
            .src(src[s]),.n(nn[s]),.dst(dst[s]),.busy(busy[s]),.fault(dma_fault[s]),
            .words_out(),.words_in(),
            .vm_re(re),.vm_raddr(raddr),.vm_rq(rq),.vm_we(we),.vm_waddr(waddr),.vm_wdata(wdata),
            .vm_ready4(1'b1),.vm_we4(we4),.vm_waddr4(waddr4),.vm_wdata4(wdata4),
            .e_valid(ev[s]),.e_ready(er[s]),.e_data(ed[s*FW+:FW]),.e_last(el[s]),
            .e_mode(em[s]),.e_tag(etag[s*32+:32]),.o_valid(ov[s]),.o_ready(ory[s]),
            .o_data(od[s*GW*FW+:GW*FW]),.o_last(ol[s]),.o_rank(orank[s*RB+:RB]),
            .o_err(oerr[s]),.engine_fault(efault[s]));
        ot_rom_oneshot_die_px #(.N(N),.RANK(s),.LANES(16),.TAGW(32),.DEPTH(DEPTH),
                                .PKG_DIES(2),.RELAY(RELAY),.ADD_LAT(3),.PAIRWISE(1),.GW(4),.OUT_BP(1)) u_coll (
            .clk(clk[s]),.rst_n(rst_n[s]),.in_valid(ev[s]),.in_ready(er[s]),.in_data(ed[s*FW+:FW]),
            .in_last(el[s]),.in_mode(em[s]),.in_tag(etag[s*32+:32]),
            .tx_valid(txv[s*N+:N]),.tx_rec(txrec[s*PW+:PW]),.tx_ready(txready[s*N+:N]),
            .cr_in(crin[2*s*N+:2*N]),.rx_valid(rxv[s*N+:N]),.rx_rec(rxrec[s*N*PW+:N*PW]),
            .cr_out(crout[2*s*N+:2*N]),.rl_tx_valid(relaytxv[s*N+:N]),
            .rl_tx_rec(relaytxrec[s*N*PW+:N*PW]),.rl_rx_valid(relayrxv[s*N+:N]),
            .rl_rx_rec(relayrxrec[s*N*PW+:N*PW]),.out_valid(ov[s]),.out_ready(ory[s]),
            .out_data(od[s*GW*FW+:GW*FW]),.out_last(ol[s]),.out_rank(orank[s*RB+:RB]),
            .out_err(oerr[s]),.fault(efault[s]),.fault_code(ecode[s*3+:3]));

        // ---- sequencer: self-timed issue of the 12 descriptors ----------------------------------------
        integer issue_c [0:OPS-1], ftx [0:OPS-1], ltx [0:OPS-1], fvm [0:OPS-1], lvm [0:OPS-1], done_c [0:OPS-1];
        integer wr_cnt [0:OPS-1];
        integer st = 0, waitc = 0;
        reg was_busy = 0;
        initial op[s] = -1;
        always @(posedge clk[s]) if (rst_n[s]) begin
            go[s] <= 1'b0;
            case (st)
                0: if (now[s] == T0 - 1) st <= 1;
                1: begin : issue
                    integer oi, n_;
                    oi = op[s] + 1;
                    op[s] <= oi;
                    mode[s] <= desc[oi][31]; rnd[s] <= desc[oi][30]; tag[s] <= {24'd0, desc[oi][22:15]};
                    n_ = integer'(desc[oi][14:0]); nn[s] <= WA'(n_);
                    src[s] <= WA'(oi*512); dst[s] <= WA'(8192 + oi*1536);
                    go[s] <= 1'b1; issue_c[oi] = now[s] + 1; ftx[oi] = -1; ltx[oi] = -1; fvm[oi] = -1; lvm[oi] = -1;
                    wr_cnt[oi] = 0;
                    st <= 2;
                end
                2: if (busy[s]) st <= 3;
                3: if (!busy[s]) begin
                    done_c[op[s]] = now[s];
                    if (op[s] == OPS - 1) begin fin[s] <= 1'b1; st <= 5; end
                    else begin waitc <= GAP; st <= 4; end
                end
                4: if (waitc <= 1) st <= 1; else waitc <= waitc - 1;
                default: ;
            endcase
        end
        // observe transmit and VM commits; check every write against the golden image
        always @(posedge clk[s]) if (rst_n[s] && op[s] >= 0 && st >= 2 && st <= 3) begin : observe
            integer a, j, o;
            o = op[s];
            if (ev[s] && er[s]) begin
                if (ftx[o] < 0) ftx[o] = now[s];
                if (el[s]) ltx[o] = now[s];
            end
            for (integer k = 0; k < 4; k = k + 1) if (we4[k]) begin
                a = integer'(waddr4[k*WA+:WA]);
                j = a - integer'(dst[s]);
                if (j < 0 || j >= (mode[s] ? 4*integer'(nn[s]) : integer'(nn[s])))
                    $fatal(1, "VM address op=%0d die=%0d addr=%0d", o, s, a);
                if (wdata4[k*FW+:FW] !== expected[(o*N)*MAXW+j])
                    $fatal(1, "VM mismatch op=%0d die=%0d j=%0d", o, s, j);
                vm[a] <= wdata4[k*FW+:FW];
                wr_cnt[o] = wr_cnt[o] + 1;
                if (fvm[o] < 0) fvm[o] = now[s];
                lvm[o] = now[s];
            end
        end
    end endgenerate

    // ---- links ---------------------------------------------------------------------------------------------
    generate for (s = 0; s < N; s = s + 1) begin : g_src
        for (t = 0; t < N; t = t + 1) begin : g_dst
            if (t == s) begin : g_self
                assign txready[s*N+t] = 1'b1;
                assign crin[2*(s*N+t)+:2] = 2'b00;
                assign rxv[s*N+t] = 1'b0;
                assign rxrec[(s*N+t)*PW+:PW] = {PW{1'b0}};
                assign lfault_st[s*N+t] = 1'b0;
            end else if ((s/2) == (t/2)) begin : g_ucie
                localparam integer P0 = (1 - s/2) * 2, P1 = P0 + 1;
                wire [UNVC-1:0] vv, rdy, ovv;
                wire [UNVC*PW-1:0] rec, orec;
                wire fv, rfv, rclk, f0, f1, f2, f3;
                wire [UFRW-1:0] fd, rfd;
                wire [TSW-1:0] amin, amax;
                wire [15:0] wmax;
                if (RELAY) begin : g_rl
                    assign vv = {relaytxv[s*N+P1], relaytxv[s*N+P0], txv[s*N+t]};
                    assign rec = {relaytxrec[(s*N+P1)*PW+:PW], relaytxrec[(s*N+P0)*PW+:PW], txrec[s*PW+:PW]};
                    assign relayrxv[t*N+P0] = ovv[1];
                    assign relayrxv[t*N+P1] = ovv[2];
                    assign relayrxrec[(t*N+P0)*PW+:PW] = orec[PW+:PW];
                    assign relayrxrec[(t*N+P1)*PW+:PW] = orec[2*PW+:PW];
                end else begin : g_nrl
                    assign vv = txv[s*N+t];
                    assign rec = txrec[s*PW+:PW];
                end
                assign txready[s*N+t] = rdy[0];
                ot_link_tx #(.NVC(UNVC), .PW(PW), .CW(2), .TSW(TSW), .WIRE(U_WIRE), .AW(U_AWTX), .NL(NL),
                             .FRAME_CYCLES(U_FC), .ENC_STAGES(U_ENC), .GATED({{(UNVC-1){1'b0}}, 1'b1})) u_tx (
                    .clk(clk[s]), .rst_n(rst_n[s]), .now(now[s]), .vc_valid(vv), .vc_ready(rdy), .vc_rec(rec),
                    .cr_pulse(crout[2*(s*N+t)+:2]), .lclk(lu[s]), .lrst_n(rst_u[s]), .f_valid(fv), .f_data(fd),
                    .fault(f0), .stat_bundles(), .stat_gated_stall());
                ot_link_chan_model #(.FRW(UFRW), .T_NS(U_T), .JDYN_FRAC(0.8)) u_ch (
                    .DLY_NS(U_DLY), .JSTATIC_NS(U_JS), .WANDER_NS(U_WAN), .clk_tx(lu[s]), .f_valid(fv), .f_data(fd), .seed(seed0 * 97 + s * N + t), .flip_at(-1),
                    .rclk(rclk), .rf_valid(rfv), .rf_data(rfd));
                reg rr = 0;
                always @(posedge rclk) rr <= ($realtime > 40.0);
                ot_link_rx #(.NVC(UNVC), .PW(PW), .CW(2), .TSW(TSW), .WIRE(U_WIRE), .AW(U_AWRX), .NL(NL),
                             .FRAME_CYCLES(U_FC), .DEC_STAGES(U_DEC)) u_rx (
                    .rclk(rclk), .rrst_n(rr), .f_valid(rfv), .f_data(rfd), .clk(clk[t]), .rst_n(rst_n[t]),
                    .now(now[t]), .det(DET[0]), .drel(TSW'(U_DREL)), .vc_valid(ovv), .vc_rec(orec), .cr_pulse(crin[2*(t*N+s)+:2]),
                    .fault_crc(f1), .fault_late(f2), .fault_ovf(f3), .stat_min_age(amin), .stat_max_age(amax),
                    .stat_max_wait(wmax), .stat_bundles());
                assign rxv[t*N+s] = ovv[0];
                assign rxrec[(t*N+s)*PW+:PW] = orec[0+:PW];
                assign lfault_st[s*N+t] = f0 | f1 | f2 | f3;
                always @(posedge rep) $display("LINK src=%0d dst=%0d class=ucie age_min=%0d age_max=%0d wait_max=%0d wire=%0d faults=%0d%0d%0d%0d",
                                               s, t, amin, amax, wmax, U_WIRE, f0, f1, f2, f3);
            end else begin : g_board
                wire vv, rdy, ovv;
                wire fv, rfv, rclk, f0, f1, f2, f3;
                wire [XFRW-1:0] fd, rfd;
                wire [PW-1:0] orec;
                wire [TSW-1:0] amin, amax;
                wire [15:0] wmax;
                assign vv = txv[s*N+t];
                assign txready[s*N+t] = rdy;
                ot_link_tx #(.NVC(1), .PW(PW), .CW(2), .TSW(TSW), .WIRE(X_WIRE), .AW(X_AWTX), .NL(NL),
                             .FRAME_CYCLES(X_FC), .ENC_STAGES(X_ENC)) u_tx (
                    .clk(clk[s]), .rst_n(rst_n[s]), .now(now[s]), .vc_valid(vv), .vc_ready(rdy),
                    .vc_rec(txrec[s*PW+:PW]), .cr_pulse(crout[2*(s*N+t)+:2]), .lclk(lx[s]), .lrst_n(rst_x[s]),
                    .f_valid(fv), .f_data(fd), .fault(f0), .stat_bundles(), .stat_gated_stall());
                ot_link_chan_model #(.FRW(XFRW), .T_NS(X_T), .JDYN_FRAC(0.8)) u_ch (
                    .DLY_NS(X_DLY), .JSTATIC_NS(X_JS), .WANDER_NS(X_WAN), .clk_tx(lx[s]), .f_valid(fv), .f_data(fd), .seed(seed0 * 97 + s * N + t), .flip_at(-1),
                    .rclk(rclk), .rf_valid(rfv), .rf_data(rfd));
                reg rr = 0;
                always @(posedge rclk) rr <= ($realtime > 40.0);
                ot_link_rx #(.NVC(1), .PW(PW), .CW(2), .TSW(TSW), .WIRE(X_WIRE), .AW(X_AWRX), .NL(NL),
                             .FRAME_CYCLES(X_FC), .DEC_STAGES(X_DEC)) u_rx (
                    .rclk(rclk), .rrst_n(rr), .f_valid(rfv), .f_data(rfd), .clk(clk[t]), .rst_n(rst_n[t]),
                    .now(now[t]), .det(DET[0]), .drel(TSW'(X_DREL)), .vc_valid(ovv), .vc_rec(orec), .cr_pulse(crin[2*(t*N+s)+:2]),
                    .fault_crc(f1), .fault_late(f2), .fault_ovf(f3), .stat_min_age(amin), .stat_max_age(amax),
                    .stat_max_wait(wmax), .stat_bundles());
                assign rxv[t*N+s] = ovv;
                assign rxrec[(t*N+s)*PW+:PW] = orec;
                assign lfault_st[s*N+t] = f0 | f1 | f2 | f3;
                always @(posedge rep) $display("LINK src=%0d dst=%0d class=board age_min=%0d age_max=%0d wait_max=%0d wire=%0d faults=%0d%0d%0d%0d",
                                               s, t, amin, amax, wmax, X_WIRE, f0, f1, f2, f3);
            end
            // relayed-record ports that no UCIe relay VC drives
            if (RELAY == 0 || (t/2) == (s/2)) begin : g_norelay
                assign relayrxv[s*N+t] = 1'b0;
                assign relayrxrec[(s*N+t)*PW+:PW] = {PW{1'b0}};
            end
        end
    end endgenerate

    // ---- finish: report, hash final VM, dump -------------------------------------------------------------
    initial begin : finish
        integer fd, o, d, j, cnt;
        reg [63:0] h;
        wait (&fin);
        repeat (20) @(posedge clk[0]);
        if ((|dma_fault) || (|efault) || (|oerr) || (|lfault_st))
            $display("W15FAULT dma=%b engine=%b out=%b link=%b", dma_fault, efault, oerr, lfault_st);
        for (o = 0; o < OPS; o = o + 1)
            for (d = 0; d < N; d = d + 1) begin
                cnt = desc[o][31] ? 4*integer'(desc[o][14:0]) : integer'(desc[o][14:0]);
                $display("OP op=%0d die=%0d mode=%0d words=%0d issue=%0d first_tx=%0d last_tx=%0d first_vm=%0d last_vm=%0d done=%0d writes=%0d expect=%0d",
                         o, d, desc[o][31], desc[o][14:0], g_die_issue(d, o), g_die_ftx(d, o), g_die_ltx(d, o),
                         g_die_fvm(d, o), g_die_lvm(d, o), g_die_done(d, o), g_die_wr(d, o), cnt);
            end
        h = 64'hCBF29CE484222325;
        fd = $fopen(outpath, "w");
        for (d = 0; d < N; d = d + 1)
            for (o = 0; o < OPS; o = o + 1) begin
                cnt = desc[o][31] ? 4*integer'(desc[o][14:0]) : integer'(desc[o][14:0]);
                for (j = 0; j < cnt; j = j + 1) begin
                    $fwrite(fd, "%0d %0d %0d %0128h\n", d, o, j, vm_word(d, 8192 + o*1536 + j));
                    if (vm_word(d, 8192 + o*1536 + j) !== expected[(o*N)*MAXW+j])
                        $display("W15FINALMISMATCH die=%0d op=%0d j=%0d", d, o, j);
                end
            end
        $fclose(fd);
        rep = 1; #0.01;
        $display("W15DONE seed=%0d det=%0d u_drel=%0d x_drel=%0d faults=%0d", seed0, DET, U_DREL, X_DREL, (|dma_fault) || (|efault) || (|oerr) || (|lfault_st));
        $finish;
    end
    initial begin #(2000000.0); $display("W15TIMEOUT fin=%b op0=%0d op1=%0d op2=%0d op3=%0d", fin, op[0], op[1], op[2], op[3]); $finish; end

    function automatic [FW-1:0] vm_word(input integer d, input integer a);
        case (d) 0: vm_word = g_die[0].vm[a]; 1: vm_word = g_die[1].vm[a];
                 2: vm_word = g_die[2].vm[a]; default: vm_word = g_die[3].vm[a]; endcase
    endfunction
    function automatic integer g_die_issue(input integer d, input integer o);
        case (d) 0: g_die_issue = g_die[0].issue_c[o]; 1: g_die_issue = g_die[1].issue_c[o];
                 2: g_die_issue = g_die[2].issue_c[o]; default: g_die_issue = g_die[3].issue_c[o]; endcase
    endfunction
    function automatic integer g_die_ftx(input integer d, input integer o);
        case (d) 0: g_die_ftx = g_die[0].ftx[o]; 1: g_die_ftx = g_die[1].ftx[o];
                 2: g_die_ftx = g_die[2].ftx[o]; default: g_die_ftx = g_die[3].ftx[o]; endcase
    endfunction
    function automatic integer g_die_ltx(input integer d, input integer o);
        case (d) 0: g_die_ltx = g_die[0].ltx[o]; 1: g_die_ltx = g_die[1].ltx[o];
                 2: g_die_ltx = g_die[2].ltx[o]; default: g_die_ltx = g_die[3].ltx[o]; endcase
    endfunction
    function automatic integer g_die_fvm(input integer d, input integer o);
        case (d) 0: g_die_fvm = g_die[0].fvm[o]; 1: g_die_fvm = g_die[1].fvm[o];
                 2: g_die_fvm = g_die[2].fvm[o]; default: g_die_fvm = g_die[3].fvm[o]; endcase
    endfunction
    function automatic integer g_die_lvm(input integer d, input integer o);
        case (d) 0: g_die_lvm = g_die[0].lvm[o]; 1: g_die_lvm = g_die[1].lvm[o];
                 2: g_die_lvm = g_die[2].lvm[o]; default: g_die_lvm = g_die[3].lvm[o]; endcase
    endfunction
    function automatic integer g_die_done(input integer d, input integer o);
        case (d) 0: g_die_done = g_die[0].done_c[o]; 1: g_die_done = g_die[1].done_c[o];
                 2: g_die_done = g_die[2].done_c[o]; default: g_die_done = g_die[3].done_c[o]; endcase
    endfunction
    function automatic integer g_die_wr(input integer d, input integer o);
        case (d) 0: g_die_wr = g_die[0].wr_cnt[o]; 1: g_die_wr = g_die[1].wr_cnt[o];
                 2: g_die_wr = g_die[2].wr_cnt[o]; default: g_die_wr = g_die[3].wr_cnt[o]; endcase
    endfunction
endmodule
