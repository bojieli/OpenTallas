    // HOST program path probes (hub_Wi.u_host = qkd_host_root_admission_obsx_bo1 -> u_plain = qkd_host_root_admission)
    `define H dut.u_host.u_plain
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
    always @(posedge dut.u_host.u_plain.ck_program_loader) c_w <= c_w + p_w;
    always @(posedge clk) if (core_cyc % 250 == 0) $display("HOSTP_HB core %0d prog_rx %0d normal_rx %0d words %0d raw_pr %h", core_cyc, c_prx, c_nrx, c_w, `H.raw_pr[15:0]);
