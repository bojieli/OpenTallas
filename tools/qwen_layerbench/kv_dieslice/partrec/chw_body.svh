    // ---- TOK-QK/C 10-24: body of the closed-loop hub_Wi host-link bench (included by the generated tb_chw.sv) ----
    // lane depths (core cycles between the partitions' boundary flops; the bound lanes are W 30 / E 36 incl. those 2)
    integer LRXW = 28, LRXE = 34, LTXW = 28, LTXE = 34, LRSW = 28, LRSE = 31, LUPW = 28, LUPE = 33, mut_c1 = 0;
    initial begin
        void'($value$plusargs("LRXW=%d", LRXW)); void'($value$plusargs("LRXE=%d", LRXE));
        void'($value$plusargs("LTXW=%d", LTXW)); void'($value$plusargs("LTXE=%d", LTXE));
        if ($test$plusargs("MUT_C1")) mut_c1 = 1;
    end
    // generic delay lines (core clock), index = depth
    reg [1044:0] q_fdi [0:63]; reg [1:0] q_lrs [0:63]; reg [523:0] q_rxw [0:63]; reg [522:0] q_rxe [0:63];
    reg [1:0] q_upw [0:63]; reg q_upe [0:63];
    wire [523:0] sw_rx; wire [522:0] se_rx; wire [1:0] sw_up, se_up;
    always @(posedge clk) begin
        q_fdi[0] <= o_host_fdi; q_lrs[0] <= o_host_link_rst_n; q_rxw[0] <= sw_rx; q_rxe[0] <= se_rx; q_upw[0] <= sw_up; q_upe[0] <= se_up[0];
        for (int i = 1; i < 64; i++) begin
            q_fdi[i] <= q_fdi[i-1]; q_lrs[i] <= q_lrs[i-1]; q_rxw[i] <= q_rxw[i-1]; q_rxe[i] <= q_rxe[i-1];
            q_upw[i] <= q_upw[i-1]; q_upe[i] <= q_upe[i-1];
        end
    end
    // o_host_fdi = {epoch, flit[521:0], tx_v, flit[1042:522]} (hub_Wi u_bout); io_W3 forwards {tx_v, half} to each half
    wire [1044:0] fw = q_fdi[LTXW], fe = q_fdi[LTXE];
    wire [523:0] sw_fdi = {fw[1044], fw[521], fw[1043:522]};
    wire [522:0] se_fdi = {fe[1044], fe[521], fe[520:0]};
    // live partitions as staged (C-edited): PHY halves on clk_phy behind ot_fdi_phy_cdc
    kv3_sys_SD_part sys_SW (.clk(clk), .arst_n(r_arst_n[0]), .clk_clk_phy(ck_phy), .i_host_fdi(sw_fdi), .i_host_link_rst_n(q_lrs[LRSW]),
        .o_serdes_W_rx_flit(sw_rx), .o_serdes_W_tx_up(sw_up));
    kv3_sys_SD_v1_part sys_SE (.clk(clk), .arst_n(r_arst_n[0]), .clk_clk_phy(ck_phy), .i_host_fdi(se_fdi), .i_host_link_rst_n(q_lrs[LRSE]),
        .o_serdes_E_rx_flit(se_rx), .o_serdes_E_tx_up(se_up));
    // back into hub_Wi; +MUT_C1: the W valid bit lands 4 cycles after its data (the C1 bind bug, on the W lane)
    assign l_i_serdes_W_rx_flit = {q_rxw[LRXW][523], (mut_c1 ? q_rxw[LRXW + 4][522] : q_rxw[LRXW][522]), q_rxw[LRXW][521:0]};
    assign l_i_serdes_E_rx_flit = q_rxe[LRXE];
    assign l_i_serdes_W_tx_up = q_upw[LUPW];
    assign l_e_up = q_upe[LUPE];
    // ---- board far end (clk_phy): real host board port; the die's two TX halves deskewed by order (board PHY) ----
    wire h2d_v; wire [1042:0] h2d_flit;
    wire d2h_v; wire [1042:0] d2h_flit;
    reg por_b = 0;
    ot_fdi_join2 #(.WA(522), .WB(521), .DEPTH(16)) u_board_deskew (.clk(ck_phy), .rst_n(por_b),
        .a_v(sys_SW.u_core.tx_v), .a_d(sys_SW.u_core.tx_flit), .b_v(sys_SE.u_core.tx_v), .b_d(sys_SE.u_core.tx_flit), .o_v(d2h_v), .o_d(d2h_flit));
    reg [1042:0] d2h_q [0:3]; reg d2h_vq [0:3];
    always @(posedge ck_phy) begin
        d2h_q[0] <= d2h_flit; d2h_vq[0] <= d2h_v;
        for (int i = 1; i < 4; i++) begin d2h_q[i] <= d2h_q[i-1]; d2h_vq[i] <= d2h_vq[i-1]; end
    end
    reg host_up = 0, hc_tx_v = 0, hc_rx_cr = 0; reg [527:0] hc_tx_d = '0; wire hc_tx_cr, hc_rx_v; wire [527:0] hc_rx_d; wire [5:0] host_faults;
    qkd_host_board_port_fixture u_board (.ck_phy({8{ck_phy}}), .ck_pad(ck_phy), .ck_rx_core(clk_clk_host), .ck_tx_core(clk_clk_host),
        .rst_n(por_b), .phy_up(host_up), .phy_rx_v(d2h_vq[3]), .phy_rx_flit(d2h_q[3]), .phy_tx_v(h2d_v), .phy_tx_flit(h2d_flit),
        .core_tx_v(hc_tx_v), .core_tx_d(hc_tx_d), .core_tx_cr(hc_tx_cr), .core_rx_v(hc_rx_v), .core_rx_d(hc_rx_d), .core_rx_cr(hc_rx_cr),
        .faults(host_faults));
    reg [527:0] frames [0:16383];
    integer nfr = 0, sent = 0, credits = 4, rx_words = 0, maxcyc = 40000;
    always @(posedge clk_clk_host) begin hc_rx_cr <= hc_rx_v; if (hc_rx_v) rx_words <= rx_words + 1; end
    always @(posedge clk_clk_host) if (host_up) begin
        automatic integer c = credits + (hc_tx_cr ? 1 : 0);
        hc_tx_v <= 1'b0;
        if (sent < nfr && c > 0) begin hc_tx_v <= 1'b1; hc_tx_d <= frames[sent]; sent <= sent + 1; c = c - 1; end
        credits <= c;
    end
    // ---- die-side checks: HOST raw_rx (peer link input, after the die adapter + its CDC channels) vs the frames ----
`define H dut.u_host.g_mu.u_rank.g_mu
`define AB dut.u_host.g_mu.u_rank.g_mu.u_adapter.g_slice[0].u_slice.u_body
`define BB u_board.u_adapter.g_slice[0].u_slice.u_body
    integer n_raw = 0, n_mis = 0, first_raw = -1;
    always @(posedge dut.u_host.g_mu.u_rank.ck_peer) if (`H.raw_rx_v) begin
        if (`H.raw_rx_d !== frames[n_raw]) begin n_mis = n_mis + 1; if (n_mis <= 4) $display("CHW RAW_MISMATCH word %0d core %0d", n_raw, core_cyc); end
        if (first_raw < 0) first_raw = core_cyc;
        n_raw = n_raw + 1;
    end
    wire [3:0] daf = {`AB.f_die_ovr, `AB.f_link_ovr, `AB.f_seq, `AB.f_cred};
    wire [3:0] baf = {`BB.f_die_ovr, `BB.f_link_ovr, `BB.f_seq, `BB.f_cred};
    reg [3:0] daf_q = 0, baf_q = 0;
    always @(posedge clk) begin
        daf_q <= daf; baf_q <= baf;
        if (daf != daf_q) $display("CHW die adapter fault core %0d die_ovr/link_ovr/seq/cred %b (rx flits so far %0d)", core_cyc, daf, n_raw);
        if (baf != baf_q) $display("CHW board adapter fault core %0d die_ovr/link_ovr/seq/cred %b", core_cyc, baf);
    end
    integer hb = 5000;
    always @(posedge clk) if (core_cyc % hb == 0) begin
        $display("CHW_HB core %0d frames_sent %0d raw_rx %0d mism %0d die->board words %0d host_up %b link_rst_n %b host_rst_n %b",
                 core_cyc, sent, n_raw, n_mis, rx_words, host_up, o_host_link_rst_n[0], dut.w_host_host_rst_n[0]); $fflush; end
    // ---- replay + stimulus ----
    initial begin : replay
        string f; integer fd, idx, n = 0; longint tps; bit [8191:0] v; realtime now;
        if (!$value$plusargs("REP=%s", f)) $fatal(1, "+REP=<record> required");
        fd = $fopen(f, "r"); if (fd == 0) $fatal(1, "cannot open %s", f);
        while ($fscanf(fd, "%d %d %h", tps, idx, v) == 3) begin
            now = tps / 1000.0 + 0.001;
            if (now > $realtime) #(now - $realtime);
            apply(idx, v); n++;
        end
        $display("CHW replay done %0d changes at core %0d (inputs hold from here)", n, core_cyc);
    end
    initial begin : stim
        string fp; integer fd;
        if (!$value$plusargs("FRAMES=%s", fp)) $fatal(1, "+FRAMES required");
        void'($value$plusargs("MAXCYC=%d", maxcyc));
        fd = $fopen(fp, "r"); if (fd == 0) $fatal(1, "FRAMES %s", fp);
        while (!$feof(fd) && $fscanf(fd, "%h\n", frames[nfr]) == 1) nfr = nfr + 1;
        $fclose(fd);
        $display("CHW cfg frames %0d tp %0.4f ns phase %0.3f ns lanes rx W%0d E%0d tx W%0d E%0d mut_c1 %0d", nfr, tp, ph, LRXW, LRXE, LTXW, LTXE, mut_c1);
        #20 por_b = 1;
        // board link up once the die's HOST is out of reset and both PHY halves report tx_up (as tb_kvslice, C3)
        wait (dut.w_host_host_rst_n[0] && sys_SW.u_core.tx_up && sys_SE.u_core.tx_up);
        repeat (64) @(posedge clk_clk_host); host_up = 1;
        $display("CHW board link up at core %0d", core_cyc);
        while (core_cyc < maxcyc) @(posedge clk);
        begin : verdict
            integer lost; reg ok;
            lost = sys_SW.u_fdi_cdc.n_rx_lost + sys_SW.u_fdi_cdc.n_tx_lost + sys_SE.u_fdi_cdc.n_rx_lost + sys_SE.u_fdi_cdc.n_tx_lost;
            ok = n_raw > 0 && n_mis == 0 && daf == 0 && baf == 0 && lost == 0 && host_faults == 0;
            $display("CHW %s raw_rx %0d (first at core %0d) mismatches %0d frames_sent %0d/%0d die_adapter_fault %b board_adapter_fault %b board_cdc_faults %b cdc_lost %0d die->board words %0d join_skew rx %0d board %0d core %0d",
                     ok ? "PASS" : "FAIL", n_raw, first_raw, n_mis, sent, nfr, daf, baf, host_faults, lost, rx_words,
                     dut.u_fdi_join.max_skew, u_board_deskew.max_skew, core_cyc);
        end
        $finish;
    end
