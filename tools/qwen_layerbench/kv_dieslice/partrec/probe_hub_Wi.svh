    // HOST program path probes (hub_Wi.u_host = qkd_host_root_admission_obsx_bo1 -> g_mu.u_rank = qkd_host_rank_services_admission_obsx, g_mu)
    `define H dut.u_host.g_mu.u_rank.g_mu
    wire p_rx = `H.program_rx_v, n_rx = `H.rx_v, p_beg = `H.begin_image, p_w = `H.word_v, p_seal = `H.seal,
         p_auth = `H.auth_v, p_if = `H.ingress_fault, p_pf = `H.program_fault, p_done = `H.replay_done;
    integer c_prx = 0, c_nrx = 0, c_w = 0;
    reg [6:0] pq = 0; wire [6:0] pv = {p_beg, p_seal, p_auth, p_if, p_pf, p_done, 1'b0};
    always @(posedge clk_clk_host) begin c_prx <= c_prx + p_rx; c_nrx <= c_nrx + n_rx; end
    always @(posedge clk) begin
        pq <= pv;
        if (pv != pq) $display("HOSTP t %0t core %0d begin %b seal %b auth %b ingress_fault %b program_fault %b replay_done %b prog_rx %0d normal_rx %0d words %0d target %0d",
                              $realtime, core_cyc, pv[6], pv[5], pv[4], pv[3], pv[2], pv[1], c_prx, c_nrx, c_w, `H.image_target);
    end
    always @(posedge dut.u_host.g_mu.u_rank.ck_program_loader) c_w <= c_w + p_w;
    always @(posedge clk) if (core_cyc % 250 == 0) $display("HOSTP_HB core %0d prog_rx %0d normal_rx %0d words %0d raw_pr %h", core_cyc, c_prx, c_nrx, c_w, `H.raw_pr[15:0]);
    // fidelity check vs the whole-die BOOTOBS lines (host_rst_n / hbm_rst_n / boot_go to hub_C)
    wire [2:0] fo = {o_host_host_rst_n_d1[0], o_host_hbm_rst_n[0], o_host_boot_go[0]};
    reg [2:0] fo_q = 0;
    always @(posedge clk) begin fo_q <= fo; if (fo != fo_q) $display("REPOBS core %0d host_rst_n %b hbm_rst_n %b boot_go %b", core_cyc, fo[2], fo[1], fo[0]); end
    integer c_raw = 0; always @(posedge dut.u_host.g_mu.u_rank.ck_peer) c_raw <= c_raw + `H.raw_rx_v;
    final $display("HOSTP_END core %0d raw_rx(peer link in) %0d prog_rx %0d normal_rx %0d words %0d", core_cyc, c_raw, c_prx, c_nrx, c_w);
    // HOST PHY face: SerDes rx -> qfd_link_adp512_split (ck_phy) -> d_rv -> qkd_host_phy_cdc5 -> raw_rx_v (peer link)
    integer c_phy = 0, c_drv = 0;
    always @(posedge dut.u_host.g_mu.u_rank.ck_phy) begin c_phy <= c_phy + dut.u_host.g_mu.u_rank.phy_rx_v; c_drv <= c_drv + `H.d_rv; end
    reg [6:0] pf_q = 0; wire [6:0] pf = {dut.u_host.g_mu.u_rank.phy_up, `H.adapter_fault, `H.phy_faults};
    always @(posedge clk) begin pf_q <= pf; if (pf != pf_q) $display("HOSTPHY core %0d phy_up %b adapter_fault %b phy_faults %b phy_rx %0d d_rv %0d raw_rx %0d",
                                                                      core_cyc, pf[6], pf[5], pf[4:0], c_phy, c_drv, c_raw); end
    final $display("HOSTPHY_END phy_rx_v %0d adapter_out d_rv %0d raw_rx %0d d_rcr %b", c_phy, c_drv, c_raw, `H.d_rcr);
    `define AB dut.u_host.g_mu.u_rank.g_mu.u_adapter.g_slice[0].u_slice.u_body
    reg [3:0] af_q = 0; wire [3:0] af = {`AB.f_die_ovr, `AB.f_link_ovr, `AB.f_seq, `AB.f_cred};
    always @(posedge dut.u_host.g_mu.u_rank.ck_phy[0]) begin
        af_q <= af;
        if (`AB.rx_v && c_phy < 4) $display("HOSTADP core %0d rx flit seq %0d expected %0d flit[17:0] %h valid %b", core_cyc, `AB.rx_flit[7:0], `AB.rx_seq, `AB.rx_flit[17:0], `AB.rx_flit[146]);
        if (af != af_q) $display("HOSTADP core %0d fault die_ovr %b link_ovr %b seq %b cred %b", core_cyc, af[3], af[2], af[1], af[0]);
    end
    // FDI cadence at the HOST adapter input: every core edge and every ck_phy edge in a short window
    always @(posedge clk) if (core_cyc >= 480 && core_cyc < 512) $display("FDI core-edge core %0d phy_rx_v %b seq %0d", core_cyc, dut.u_host.g_mu.u_rank.phy_rx_v, dut.u_host.g_mu.u_rank.phy_rx_flit[7:0]);
    always @(posedge dut.u_host.g_mu.u_rank.ck_phy[0]) if (core_cyc >= 480 && core_cyc < 512) $display("FDI phy-edge  core %0d phy_rx_v %b seq %0d", core_cyc, dut.u_host.g_mu.u_rank.phy_rx_v, dut.u_host.g_mu.u_rank.phy_rx_flit[7:0]);
