// Copied transport-only wiring from committed bounded fixture; no protected wrapper.
  ot_chip_v41x_kv_rope_reqmux #(.HAW(30),.TAGW(16)) mux (
    .clk(clk),.rst_n(rst_n),.w_v(wv),.w_rdy(wrdy),.w_addr(wa),.w_len(wl),.w_tag(wt),.w_we(wwe),
    .w_wdata(wd),.w_wstrb(wm),.w_wr_done(wwdone),.w_sv(wsv),.w_srdy(wsrdy),.w_stag(wst),.w_sbeat(wb),.w_sdata(wsd),
    .c_v(4'b0),.c_addr(120'b0),.c_len(16'b0),.c_tag(64'b0),.c_we(4'b0),.c_wdata(1024'b0),.c_wstrb(128'b0),.c_srdy(4'hf),
    .p_v(4'b0),.p_addr(120'b0),.p_len(16'b0),.p_tag(64'b0),.p_we(4'b0),.p_wdata(1024'b0),.p_wstrb(128'b0),.p_srdy(4'hf),
    .m_v(mv),.m_rdy(mrdy),.m_addr(ma),.m_len(ml),.m_tag(mt),.m_we(mwe),.m_wdata(md),.m_wstrb(mm),
    .m_wr_done(mwdone),.s_v(msv),.s_rdy(msrdy),.s_tag(mst),.s_beat(mb),.s_data(msd),.fault(mux_fault));
  assign mrdy[1:0]=2'b11; assign mrdy[3]=1'b1;
  assign msv[1:0]=0; assign msv[3]=0;
  assign mst[31:0]=0; assign mst[63:48]=0;
  assign mb[7:0]=0; assign mb[15:12]=0;
  assign msd[511:0]=0; assign msd[1023:768]=0;
  assign mwdone[1:0]=0; assign mwdone[3]=0;
  ot_chip_v41x_hbm_karb #(.NPC(32),.AW(30),.TAGW(16)) arb (
    .clk(clk),.rst_n(rst_n),.b_v(32'b0),.b_addr(960'b0),.b_len(128'b0),.b_tag(512'b0),.b_we(32'b0),
    .b_wdata(8192'b0),.b_wstrb(1024'b0),.b_rsp_rdy(32'hffffffff),
    .k_v(mv[2]),.k_rdy(mrdy[2]),.k_addr(ma[60+:30]),.k_len(ml[8+:4]),.k_tag(mt[32+:16]),
    .k_we(mwe[2]),.k_wdata(md[512+:256]),.k_wstrb(mm[64+:32]),.k_wr_done(mwdone[2]),
    .k_rsp_v(msv[2]),.k_rsp_rdy(msrdy[2]),.k_rsp_tag(mst[32+:16]),.k_rsp_beat(mb[8+:4]),.k_rsp_data(msd[512+:256]),
    .h_v(hv),.h_rdy(hrdy),.h_addr(ha),.h_len(hl),.h_tag(ht),.h_we(hwe),.h_wdata(hd),.h_wstrb(hm),
    .h_wr_done(hwdone),.r_v(rv),.r_rdy(rrdy),.r_tag(rt),.r_beat(rb),.r_data(rd));
  ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.TAGW(17),.LENW(4),.BEATW(4),.MEM_WORDS(BASE+2176),.MEM_MODE(0),.REFPB(3),.CLK_PS(1000)) mem (
    .clk(clk),.rst_n(rst_n),.req_v(hv),.req_rdy(hrdy),.req_addr(ha),.req_len(hl),.req_tag(ht),.req_we(hwe),
    .req_wdata(hd),.req_wstrb(hm),.wr_done(hwdone),.rsp_v(rv),.rsp_rdy(rrdy),.rsp_tag(rt),.rsp_beat(rb),.rsp_data(rd));
