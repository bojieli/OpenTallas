`timescale 1ns/1ps
// MU-QWEN-SEQ bench harness (2026-10-18): qfd_dv_cmd_cal_mu (NU playheads), optionally in LOCKSTEP with the unmodified
// qfd_dv_cmd_cal (NU must be 1: every output compared on every edge).  Driven by an event file (+EV, sorted
// "cycle kind hex", applied before posedge `cycle`):
//   0 PW {addr 10, data 64}   1 DW {addr 3, data 64}   2 START {user 2, stage 6} (start high for that one edge)
// Log (+LOG), label = the posedge just taken:
//   "c CMD u hex" (cmd != 0), "c SUI u pidx", "c XCI u", "c EMB u", "c SEG u base", "c DONE u", "c FAULT code" (rise),
//   "c MISMATCH" (lockstep), and at the end "c END fault code mismatches".
module tb_mu_cmd_cal;
    parameter integer NU = 1, MUT = 0, LOCKSTEP = 0, UVM_STRIDE = 16384, PIDX_STRIDE = 64;
    localparam integer UB = (NU > 1) ? $clog2(NU) : 1;
    reg ck = 1'b0;
    always #5 ck = ~ck;
    reg rst_n = 1'b0;
    reg pw_v = 0, dw_v = 0, start = 0; reg [9:0] pw_addr = 0; reg [63:0] pw_data = 0, dw_data = 0; reg [2:0] dw_addr = 0;
    reg [5:0] stage = 0; reg [UB-1:0] start_user = 0;
    wire [115:0] cmd; wire [UB-1:0] cmd_user, done_user; wire loc_emb, loc_seg, su_issue, xc_issue, image_ready, running, done, fault;
    wire [1087:0] tl, r_tl;
    wire [11:0] loc_base; wire [8:0] su_pidx; wire [75:0] pobs; wire [68:0] dobs; wire [NU-1:0] running_u; wire [5:0] fcode;
    wire [15:0] start_epoch=16'(cyc*13+7);
    qfd_dv_cmd_cal_mu_f16 #(.F16_CONTEXT(1),.MUT(MUT), .NU(NU), .UVM_STRIDE(UVM_STRIDE), .PIDX_STRIDE(PIDX_STRIDE)) dut (.ck(ck), .rst_n(rst_n),
        .pw_v(pw_v), .pw_addr(pw_addr), .pw_data(pw_data), .dw_v(dw_v), .dw_addr(dw_addr), .dw_data(dw_data),
        .start_epoch(start_epoch), .start(start), .stage(stage), .start_user(start_user), .start_rng(1'b0), .start_first(10'd0), .start_cnt(10'd0), .cmd(cmd), .tl(tl), .cmd_user(cmd_user), .loc_emb(loc_emb),
        .loc_seg(loc_seg), .loc_base(loc_base), .su_issue(su_issue), .su_pidx(su_pidx), .xc_issue(xc_issue),
        .program_obs(pobs), .descriptor_obs(dobs), .image_ready(image_ready), .running(running), .running_u(running_u),
        .done(done), .done_user(done_user), .fault(fault), .fault_code(fcode));
    wire [116-1:0] base_cmd;
    wire [1088-1:0] base_tl;
    wire [UB-1:0] base_cmd_user;
    wire [1-1:0] base_loc_emb;
    wire [1-1:0] base_loc_seg;
    wire [12-1:0] base_loc_base;
    wire [1-1:0] base_su_issue;
    wire [9-1:0] base_su_pidx;
    wire [1-1:0] base_xc_issue;
    wire [76-1:0] base_program_obs;
    wire [69-1:0] base_descriptor_obs;
    wire [1-1:0] base_image_ready;
    wire [1-1:0] base_running;
    wire [NU-1:0] base_running_u;
    wire [1-1:0] base_done;
    wire [UB-1:0] base_done_user;
    wire [1-1:0] base_fault;
    wire [6-1:0] base_fault_code;
    qfd_dv_cmd_cal_mu #(.MUT(MUT), .NU(NU), .UVM_STRIDE(UVM_STRIDE), .PIDX_STRIDE(PIDX_STRIDE)) base_dut (.ck(ck), .rst_n(rst_n),
        .pw_v(pw_v), .pw_addr(pw_addr), .pw_data(pw_data), .dw_v(dw_v), .dw_addr(dw_addr), .dw_data(dw_data),
        .start(start), .stage(stage), .start_user(start_user), .start_rng(1'b0), .start_first(10'd0), .start_cnt(10'd0), .cmd(base_cmd), .tl(base_tl), .cmd_user(base_cmd_user), .loc_emb(base_loc_emb),
        .loc_seg(base_loc_seg), .loc_base(base_loc_base), .su_issue(base_su_issue), .su_pidx(base_su_pidx), .xc_issue(base_xc_issue),
        .program_obs(base_program_obs), .descriptor_obs(base_descriptor_obs), .image_ready(base_image_ready), .running(base_running), .running_u(base_running_u),
        .done(base_done), .done_user(base_done_user), .fault(base_fault), .fault_code(base_fault_code));
    wire [116-1:0] off_cmd;
    wire [1088-1:0] off_tl;
    wire [UB-1:0] off_cmd_user;
    wire [1-1:0] off_loc_emb;
    wire [1-1:0] off_loc_seg;
    wire [12-1:0] off_loc_base;
    wire [1-1:0] off_su_issue;
    wire [9-1:0] off_su_pidx;
    wire [1-1:0] off_xc_issue;
    wire [76-1:0] off_program_obs;
    wire [69-1:0] off_descriptor_obs;
    wire [1-1:0] off_image_ready;
    wire [1-1:0] off_running;
    wire [NU-1:0] off_running_u;
    wire [1-1:0] off_done;
    wire [UB-1:0] off_done_user;
    wire [1-1:0] off_fault;
    wire [6-1:0] off_fault_code;
    qfd_dv_cmd_cal_mu_f16 #(.F16_CONTEXT(0),.MUT(MUT), .NU(NU), .UVM_STRIDE(UVM_STRIDE), .PIDX_STRIDE(PIDX_STRIDE)) off_dut (.ck(ck), .rst_n(rst_n),
        .pw_v(pw_v), .pw_addr(pw_addr), .pw_data(pw_data), .dw_v(dw_v), .dw_addr(dw_addr), .dw_data(dw_data),
        .start_epoch(start_epoch), .start(start), .stage(stage), .start_user(start_user), .start_rng(1'b0), .start_first(10'd0), .start_cnt(10'd0), .cmd(off_cmd), .tl(off_tl), .cmd_user(off_cmd_user), .loc_emb(off_loc_emb),
        .loc_seg(off_loc_seg), .loc_base(off_loc_base), .su_issue(off_su_issue), .su_pidx(off_su_pidx), .xc_issue(off_xc_issue),
        .program_obs(off_program_obs), .descriptor_obs(off_descriptor_obs), .image_ready(off_image_ready), .running(off_running), .running_u(off_running_u),
        .done(off_done), .done_user(off_done_user), .fault(off_fault), .fault_code(off_fault_code));
    reg [21:0] accepted_identity[0:NU-1];reg[21:0]expected_identity;
    reg expected_su;integer identity_user;integer identity_checks=0;
    always @(posedge ck) begin
      expected_su=base_dut.i_any&&!base_dut.i_loc&&base_dut.i_kind==3'd1;
      expected_identity=accepted_identity[base_dut.ru];
      if(!rst_n)for(identity_user=0;identity_user<NU;identity_user=identity_user+1)accepted_identity[identity_user]=0;
      else for(identity_user=0;identity_user<NU;identity_user=identity_user+1)
        if(base_dut.go_u[identity_user]&&!base_dut.start_bad&&base_dut.g_cnt_nz)
          accepted_identity[identity_user]=base_dut.boot_go?22'd0:{stage,start_epoch};
      #0.2;
      if(rst_n) begin
        if({base_tl,base_cmd_user,base_loc_emb,base_loc_seg,base_loc_base,base_su_issue,base_su_pidx,base_xc_issue,base_program_obs,base_descriptor_obs,base_image_ready,base_running,base_running_u,base_done,base_done_user,base_fault,base_fault_code}!=={tl,cmd_user,loc_emb,loc_seg,loc_base,su_issue,su_pidx,xc_issue,pobs,dobs,image_ready,running,running_u,done,done_user,fault,fcode})$fatal(1,"F16_CAL_FUNCTIONAL_OUTPUT");
        if({off_cmd,off_tl,off_cmd_user,off_loc_emb,off_loc_seg,off_loc_base,off_su_issue,off_su_pidx,off_xc_issue,off_program_obs,off_descriptor_obs,off_image_ready,off_running,off_running_u,off_done,off_done_user,off_fault,off_fault_code}!=={base_cmd,base_tl,base_cmd_user,base_loc_emb,base_loc_seg,base_loc_base,base_su_issue,base_su_pidx,base_xc_issue,base_program_obs,base_descriptor_obs,base_image_ready,base_running,base_running_u,base_done,base_done_user,base_fault,base_fault_code})$fatal(1,"F16_CAL_DEFAULT_OFF");
        if(expected_su)begin
          identity_checks=identity_checks+1;
          if(cmd[111:90]!==expected_identity)$fatal(1,"F16_CAL_IDENTITY got=%h expect=%h",cmd[111:90],expected_identity);
          if({cmd[115:112],cmd[89:0]}!=={base_cmd[115:112],base_cmd[89:0]})$fatal(1,"F16_CAL_SU_FUNCTIONAL_BITS");
          if(base_cmd[111:90]!==0)$fatal(1,"F16_CAL_FIXTURE_RESERVED_NONZERO");
        end else if(cmd!==base_cmd)$fatal(1,"F16_CAL_NONSY_WORD");
      end
    end
    final $display("F16_CAL_ACTUAL_IDENTITY_CHECKS %0d",identity_checks);
    // ---------------- reference: the unmodified calendar (lockstep at NU = 1)
    wire [115:0] functional_cmd=(cmd[0]&&cmd[3:1]==1&&cmd[115:112]!=14)?{cmd[115:112],22'd0,cmd[89:0]}:cmd;
    wire [115:0] r_cmd; wire r_emb, r_seg, r_sui, r_xci, r_ir, r_run, r_done, r_fault; wire [11:0] r_base; wire [8:0] r_pidx;
    wire [75:0] r_pobs; wire [68:0] r_dobs;
    generate if (LOCKSTEP != 0) begin : g_ref
        qfd_dv_cmd_cal u_ref (.ck(ck), .rst_n(rst_n), .pw_v(pw_v), .pw_addr(pw_addr), .pw_data(pw_data), .dw_v(dw_v),
            .dw_addr(dw_addr), .dw_data(dw_data), .start(start), .stage(stage), .cmd(r_cmd), .tl(r_tl), .loc_emb(r_emb),
            .loc_seg(r_seg), .loc_base(r_base), .su_issue(r_sui), .su_pidx(r_pidx), .xc_issue(r_xci),
            .program_obs(r_pobs), .descriptor_obs(r_dobs), .image_ready(r_ir), .running(r_run), .done(r_done),
            .fault(r_fault));
    end endgenerate
    integer fd, lg, cyc, ncyc, ec, ek, r, pre = 0, mism = 0;
    reg [127:0] ev; reg have; reg [1023:0] evf, lgf; reg flt_l = 0;
    initial begin
        if (!$value$plusargs("EV=%s", evf)) $fatal(1, "+EV");
        if (!$value$plusargs("LOG=%s", lgf)) $fatal(1, "+LOG");
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 4000;
        fd = $fopen(evf, "r"); lg = $fopen(lgf, "w"); cyc = 0;
        r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
    end
    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
            if (cmd != 116'd0) $fdisplay(lg, "%0d CMD %0d %h", cyc, cmd_user, functional_cmd);
            if (su_issue) $fdisplay(lg, "%0d SUI %0d %h", cyc, cmd_user, su_pidx);
            if (xc_issue) $fdisplay(lg, "%0d XCI %0d", cyc, cmd_user);
            if (tl != 1088'd0) $fdisplay(lg, "%0d TL %0d %h", cyc, cmd_user, tl);
            if (loc_emb) $fdisplay(lg, "%0d EMB %0d", cyc, cmd_user);
            if (loc_seg) $fdisplay(lg, "%0d SEG %0d %h", cyc, cmd_user, loc_base);
            if (done) $fdisplay(lg, "%0d DONE %0d", cyc, done_user);
            if (fault && !flt_l) $fdisplay(lg, "%0d FAULT %b", cyc, fcode);
            flt_l = fault;
            if (LOCKSTEP != 0) begin
                if ({tl, functional_cmd, loc_emb, loc_seg, loc_base, su_issue, su_pidx, xc_issue, pobs, dobs, image_ready, running, done, fault} !==
                    {r_tl, r_cmd, r_emb, r_seg, r_base, r_sui, r_pidx, r_xci, r_pobs, r_dobs, r_ir, r_run, r_done, r_fault}) begin
                    mism = mism + 1;
                    if (mism <= 20) $fdisplay(lg, "%0d MISMATCH", cyc);
                end
            end
            // inputs for the next posedge (cyc + 1)
            pw_v = 1'b0; dw_v = 1'b0; start = 1'b0;
            while (have && ec == cyc + 1) begin
                case (ek)
                    0: begin pw_v = 1'b1; pw_addr = ev[73:64]; pw_data = ev[63:0]; end
                    1: begin dw_v = 1'b1; dw_addr = ev[66:64]; dw_data = ev[63:0]; end
                    2: begin start = 1'b1; stage = ev[5:0]; start_user = UB'(ev[7:6]); end
                    default: $fatal(1, "bad kind %0d", ek);
                endcase
                r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
            end
            if (have && ec <= cyc) $fatal(1, "event file not sorted at cycle %0d", ec);
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                $fdisplay(lg, "%0d END %0d %b %0d", cyc, fault, fcode, mism);
                $fclose(lg);
                $finish;
            end
        end
    end
endmodule
