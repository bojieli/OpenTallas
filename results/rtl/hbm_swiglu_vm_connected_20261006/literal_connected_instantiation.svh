 ot_hbm_accel_su_fused_vm #(.ENABLE(1),.KIND(3),.N(N),.D(D),.AW(AW),
   .PUBLISH_QUANT(1),.ROUTED(1),.ADOPTED_SWIGLU_QUANT_ONLY(1)) dut(
  .clk(clk),.rst_n(por_n),.cmd_valid(start_v),.cmd_ready(start_r),
  .source_ready(grant&&!revoke_source),.landing_reserved(retained),.busy(busy),.done(done),.fault(vm_fault),
  .job_id(held[31:0]),.held_frame(held),.q_frame(qframe),
  .xbase(10'd0),.ubase(10'd64),.wbase(10'd128),.ybase(10'd256),.gain_base(10'd0),
  .comb(512'd0),.post_pre(128'd0),.n_f(32'd0),.eps(32'd0),.lim(32'h41234567),
  .cos_t(32'd0),.sin_t(32'd0),.rd_addr(rd_addr),.rd_re(rd_re),.rd_src(rd_src),.rd_q(rd_q),
  .vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),
  .q_valid(qv),.q_index(qi),.q_codes(codes),.q_exp(scales),.q_bf16(bf16),
  .completion_id(completion_id),.reserve_events(reserve_events));
