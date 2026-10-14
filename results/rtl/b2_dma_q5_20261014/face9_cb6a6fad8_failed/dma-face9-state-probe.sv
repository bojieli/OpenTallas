    // Read-only diagnostic, enabled explicitly; no qualification depends on hierarchy probes.
    always @(posedge clk) if($test$plusargs("FACE_DEBUG") && cyc==469135)
      $display("FACE_DEBUG rq rdact=%b rdout=%d rbn=%d idfn=%d sqact=%b sqwait=%b sqe=%d sqlast=%b mpend=%b mdone=%b mready=%b mvbusy=%b cvq=%b sel=%b rdone=%b ucv=%b cdv=%b cfn=%d sfn=%d wqn=%d wrin=%d rdin=%d landpend=%b p2=%b pa=%b pe=%b pk=%b p3=%b",
       dut.u_rq.rd_act,dut.u_rq.rd_out,dut.u_rq.rb_n,dut.u_rq.idf_n,dut.u_rq.sq_act,dut.u_rq.sq_wait,dut.u_rq.sq_e,dut.u_rq.sq_last,dut.u_rq.m_pend,dut.u_rq.m_done,dut.u_rq.m_rdy,
       dut.u_mv.busy_f,dut.u_mv.cv_q,dut.u_mv.sel_s,dut.u_mv.r_done,dut.u_mv.u_cv,dut.u_mv.cd_v,dut.u_mv.cf_n,dut.u_mv.sf_n,dut.u_mv.wq_n,dut.u_mv.wr_in,dut.u_mv.rd_in,dut.u_mv.land_pending,dut.u_mv.p2_v,dut.u_mv.pa_v,dut.u_mv.pe_v,dut.u_mv.pk_v,dut.u_mv.p3_v);
