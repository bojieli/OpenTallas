// SOURCE-AUDIT TEMPLATE ONLY: not installed, elaborated, or simulated.
// A low sample at the actual source clock makes its one-stage reset landing known low.
// Monitor faults at negedge of the same clock after NBA; keep tags sticky through idle.
// This establishes local fault-storage initialization, not upstream startup correctness.
// dut.ectl_WS_0.fault ; effective reset dut.ectl_WS_0.u_a.u_k.rn
reg fault_init_0 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t0__m_0__g0_s14[0] === 1'b0) fault_init_0 <= 1'b1;
// dut.ectl_WS_1.fault ; effective reset dut.ectl_WS_1.u_a.u_k.rn
reg fault_init_1 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t1__m_0__g0_s31[0] === 1'b0) fault_init_1 <= 1'b1;
// dut.ectl_WS_2.fault ; effective reset dut.ectl_WS_2.u_a.u_k.rn
reg fault_init_2 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t1__m_0__g0_s11[0] === 1'b0) fault_init_2 <= 1'b1;
// dut.ectl_WS_3.fault ; effective reset dut.ectl_WS_3.u_a.u_k.rn
reg fault_init_3 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t2__m_0__g2_s5[0] === 1'b0) fault_init_3 <= 1'b1;
// dut.ectl_WS_4.fault ; effective reset dut.ectl_WS_4.u_a.u_k.rn
reg fault_init_4 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t0__m_0__g0_s35[0] === 1'b0) fault_init_4 <= 1'b1;
// dut.ectl_WS_5.fault ; effective reset dut.ectl_WS_5.u_a.u_k.rn
reg fault_init_5 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t1__m_0__g0_s55[0] === 1'b0) fault_init_5 <= 1'b1;
// dut.ectl_WS_6.fault ; effective reset dut.ectl_WS_6.u_a.u_k.rn
reg fault_init_6 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t1__m_0__g0_s40[0] === 1'b0) fault_init_6 <= 1'b1;
// dut.ectl_WS_7.fault ; effective reset dut.ectl_WS_7.u_a.u_k.rn
reg fault_init_7 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t2__m_0__g2_s19[0] === 1'b0) fault_init_7 <= 1'b1;
// dut.vport_WS_0.fault ; effective reset dut.vport_WS_0.rn
reg fault_init_8 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t1__m_0__g0_s43[0] === 1'b0) fault_init_8 <= 1'b1;
// dut.vport_WS_1.fault ; effective reset dut.vport_WS_1.rn
reg fault_init_9 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t1__m_0__g0_s1[0] === 1'b0) fault_init_9 <= 1'b1;
// dut.vport_WS_2.fault ; effective reset dut.vport_WS_2.rn
reg fault_init_10 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t0__m_0__g0_s21[0] === 1'b0) fault_init_10 <= 1'b1;
// dut.vport_WS_3.fault ; effective reset dut.vport_WS_3.rn
reg fault_init_11 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t2__m_0__g2_s22[0] === 1'b0) fault_init_11 <= 1'b1;
// dut.n_astk_WS__af_s[0] ; effective reset dut.astk_WS__u_strip_u_strip_u_ctl.rn_q
reg fault_init_12 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t1__m_0__g1_s180[0] === 1'b0) fault_init_12 <= 1'b1;
// dut.n_astk_WS__er_fault[0] ; effective reset dut.astk_WS__u_strip_g_er_chain_u_er_g_owner_7__u_owner.rst_n
reg fault_init_18 = 1'b0;
always @(posedge dut.n_clk_core_WS[0])
    if (dut.n_rrs_n_rst_die_t1__m_0__g1_s171[0] === 1'b0) fault_init_18 <= 1'b1;
