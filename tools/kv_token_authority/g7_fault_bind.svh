// Source-derived continuous fault checks. No trace_on, A0 or active mask.
reg kva_fault_init_0=0, kva_fault_seen_0=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t0__m_0__g0_s14[0] === 1'b0) kva_fault_init_0 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_0 && !kva_fault_seen_0 && dut.ectl_WS_0.fault !== 1'b0) begin
 kva_fault_seen_0=1; smoke_err("actual source fault ectl_WS_0 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.ectl_WS_0.fault value=%b",cyc,dut.ectl_WS_0.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_1=0, kva_fault_seen_1=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t1__m_0__g0_s31[0] === 1'b0) kva_fault_init_1 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_1 && !kva_fault_seen_1 && dut.ectl_WS_1.fault !== 1'b0) begin
 kva_fault_seen_1=1; smoke_err("actual source fault ectl_WS_1 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.ectl_WS_1.fault value=%b",cyc,dut.ectl_WS_1.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_2=0, kva_fault_seen_2=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t1__m_0__g0_s11[0] === 1'b0) kva_fault_init_2 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_2 && !kva_fault_seen_2 && dut.ectl_WS_2.fault !== 1'b0) begin
 kva_fault_seen_2=1; smoke_err("actual source fault ectl_WS_2 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.ectl_WS_2.fault value=%b",cyc,dut.ectl_WS_2.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_3=0, kva_fault_seen_3=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t2__m_0__g2_s5[0] === 1'b0) kva_fault_init_3 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_3 && !kva_fault_seen_3 && dut.ectl_WS_3.fault !== 1'b0) begin
 kva_fault_seen_3=1; smoke_err("actual source fault ectl_WS_3 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.ectl_WS_3.fault value=%b",cyc,dut.ectl_WS_3.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_4=0, kva_fault_seen_4=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t0__m_0__g0_s35[0] === 1'b0) kva_fault_init_4 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_4 && !kva_fault_seen_4 && dut.ectl_WS_4.fault !== 1'b0) begin
 kva_fault_seen_4=1; smoke_err("actual source fault ectl_WS_4 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.ectl_WS_4.fault value=%b",cyc,dut.ectl_WS_4.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_5=0, kva_fault_seen_5=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t1__m_0__g0_s55[0] === 1'b0) kva_fault_init_5 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_5 && !kva_fault_seen_5 && dut.ectl_WS_5.fault !== 1'b0) begin
 kva_fault_seen_5=1; smoke_err("actual source fault ectl_WS_5 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.ectl_WS_5.fault value=%b",cyc,dut.ectl_WS_5.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_6=0, kva_fault_seen_6=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t1__m_0__g0_s40[0] === 1'b0) kva_fault_init_6 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_6 && !kva_fault_seen_6 && dut.ectl_WS_6.fault !== 1'b0) begin
 kva_fault_seen_6=1; smoke_err("actual source fault ectl_WS_6 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.ectl_WS_6.fault value=%b",cyc,dut.ectl_WS_6.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_7=0, kva_fault_seen_7=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t2__m_0__g2_s19[0] === 1'b0) kva_fault_init_7 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_7 && !kva_fault_seen_7 && dut.ectl_WS_7.fault !== 1'b0) begin
 kva_fault_seen_7=1; smoke_err("actual source fault ectl_WS_7 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.ectl_WS_7.fault value=%b",cyc,dut.ectl_WS_7.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_8=0, kva_fault_seen_8=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t1__m_0__g0_s43[0] === 1'b0) kva_fault_init_8 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_8 && !kva_fault_seen_8 && dut.vport_WS_0.fault !== 1'b0) begin
 kva_fault_seen_8=1; smoke_err("actual source fault vport_WS_0 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.vport_WS_0.fault value=%b",cyc,dut.vport_WS_0.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_9=0, kva_fault_seen_9=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t1__m_0__g0_s1[0] === 1'b0) kva_fault_init_9 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_9 && !kva_fault_seen_9 && dut.vport_WS_1.fault !== 1'b0) begin
 kva_fault_seen_9=1; smoke_err("actual source fault vport_WS_1 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.vport_WS_1.fault value=%b",cyc,dut.vport_WS_1.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_10=0, kva_fault_seen_10=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t0__m_0__g0_s21[0] === 1'b0) kva_fault_init_10 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_10 && !kva_fault_seen_10 && dut.vport_WS_2.fault !== 1'b0) begin
 kva_fault_seen_10=1; smoke_err("actual source fault vport_WS_2 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.vport_WS_2.fault value=%b",cyc,dut.vport_WS_2.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_11=0, kva_fault_seen_11=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t2__m_0__g2_s22[0] === 1'b0) kva_fault_init_11 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_11 && !kva_fault_seen_11 && dut.vport_WS_3.fault !== 1'b0) begin
 kva_fault_seen_11=1; smoke_err("actual source fault vport_WS_3 after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.vport_WS_3.fault value=%b",cyc,dut.vport_WS_3.fault);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_12=0, kva_fault_seen_12=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t1__m_0__g1_s180[0] === 1'b0) kva_fault_init_12 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_12 && !kva_fault_seen_12 && dut.n_astk_WS__af_s[0] !== 1'b0) begin
 kva_fault_seen_12=1; smoke_err("actual source fault astk_WS__u_strip_u_strip_u_ctl after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.n_astk_WS__af_s[0] value=%b",cyc,dut.n_astk_WS__af_s[0]);
 if(kva_fs < 0) kva_fs=cyc;
end
reg kva_fault_init_18=0, kva_fault_seen_18=0;
always @(posedge dut.n_clk_core_WS[0]) if (dut.n_rrs_n_rst_die_t1__m_0__g1_s171[0] === 1'b0) kva_fault_init_18 <= 1;
always @(negedge dut.n_clk_core_WS[0]) if (kva_fault_init_18 && !kva_fault_seen_18 && dut.n_astk_WS__er_fault[0] !== 1'b0) begin
 kva_fault_seen_18=1; smoke_err("actual source fault astk_WS__u_strip_g_er_chain_u_er_g_owner_7__u_owner after initialization");
 $display("KVA_SOURCE_FAULT cyc=%0d probe=dut.n_astk_WS__er_fault[0] value=%b",cyc,dut.n_astk_WS__er_fault[0]);
 if(kva_fs < 0) kva_fs=cyc;
end
