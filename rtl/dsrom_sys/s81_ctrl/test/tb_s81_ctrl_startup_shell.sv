`timescale 1ns/1ps
// Exercise the distinct physical-shell source candidate, including actual
// queued SOURCE commands, program capture and stopped-clock reset epochs.
module tb_s81_ctrl_startup_shell;
    parameter integer MUT = 0;
    reg ck=0, rs=0, run_clock=1, startup_ready=0;
    always #0.5 if (run_clock) ck=~ck;
    reg pw_v=0; reg [6:0] pw_a=0; reg [27:0] pw_d=0;
    reg hc_v=0; wire hc_r; reg [1:0] hc_op=0;
    reg [7:0] hc_user=0; reg [20:0] hc_pos=0, hc_tok=0;
    wire local_ready; wire [11:0] cv; wire [1007:0] cd;
    wire fault;
    dsfd_sp_ctrl_startup_core #(.ROLE(1), .MY_ID(1), .SRC_LO(3), .SRC_HI(3),
                              .TYPE_MASK(16'h0004)) dut (
        .ck(ck), .rs(rs), .startup_ready(MUT ? 1'b1 : startup_ready),
        .startup_local_ready(local_ready),
        .pw_v(pw_v), .pw_a(pw_a), .pw_d(pw_d), .prog_len(8'd1), .cfg_users(12'd1),
        .i_v(1'b0), .i_r(), .i_d(512'd0), .i_l(1'b0),
        .o_v(), .o_r(1'b1), .o_d(), .o_l(),
        .cv(cv), .cd(cd), .dv(12'd0), .dt(96'd0), .hop_go(1'b0),
        .vwe(), .vwa(), .vwd(), .vre(), .vra(), .vrq(512'd0), .vrv(1'b0),
        .am_v(1'b0), .am_pos(21'd0), .am_tok(21'd0), .am_val(32'd0), .boot_ok(1'b1),
        .hc_v(hc_v), .hc_r(hc_r), .hc_op(hc_op), .hc_tag(8'd1), .hc_user(hc_user),
        .hc_pos(hc_pos), .hc_tok(hc_tok), .cpl_v(), .cpl_r(1'b1), .cpl_d(),
        .flt(fault), .fvec(), .stk(), .snap());

    always @(negedge ck) if (rs && !startup_ready && |cv)
        $fatal(1, "STARTUP_SHELL_EARLY actual engine command before remote ACK barrier");

    task automatic check_local_release;
        for (integer edge_index=1; edge_index<=4; edge_index++) begin
            @(posedge ck); #0.001;
            if (local_ready !== (edge_index==4))
                $fatal(1, "STARTUP_SHELL_RELEASE edge=%0d ready=%b", edge_index, local_ready);
        end
    endtask

    task automatic host_command(input [1:0] op, input [7:0] user,
                                input [20:0] position, token);
        @(negedge ck); hc_op=op; hc_user=user; hc_pos=position; hc_tok=token; hc_v=1;
        @(posedge ck); while (!hc_r) @(posedge ck);
        @(negedge ck); hc_v=0;
    endtask

    initial begin
        repeat (5) @(negedge ck);
        #0.1; rs=1;
        check_local_release();
        // Configure only after the genuine final local release export.
        @(negedge ck); pw_v=1; pw_d=28'h0012345;
        @(negedge ck); pw_v=0;
        repeat (3) @(negedge ck);
        if (dut.u.u_seq.pmem[0] !== 28'h0012345)
            $fatal(1, "STARTUP_SHELL_PROGRAM actual first program word lost");
        host_command(1, 0, 0, 100); // PROMPT
        host_command(2, 1, 1, 1);   // LAUNCH one user, prompt one, generation one
        repeat (40) @(negedge ck);
        if (!dut.u.u_pkg.nu_ok || !dut.u.g_src.u_hq.active || dut.u.j_r || |cv)
            $fatal(1, "STARTUP_SHELL_PENDING real SOURCE scheduler request must wait for remote ACKs");
        startup_ready=1;
        begin : wait_command
            integer edges;
            edges=0;
            while (!(|cv) && edges<100) begin @(negedge ck); edges++; end
            if (!(|cv) || fault) $fatal(1, "STARTUP_SHELL_ADMISSION actual command missing or fault");
        end
        // Raw assertion reaches actual wrapper and child consumers while the
        // producer clock is stopped; a stale-high local ACK is forbidden.
        for (integer phase=0; phase<6; phase++) begin
            @(negedge ck); run_clock=0; startup_ready=0;
            #0.071; rs=0;
            #0.017;
            if (local_ready !== 0) $fatal(1, "STARTUP_SHELL_STOPPED reset assertion did not cancel ACK");
            #0.023; rs=1;
            #(0.061+0.013*phase);
            if (local_ready !== 0) $fatal(1, "STARTUP_SHELL_STALE stopped clock created release ACK");
            run_clock=1;
            check_local_release();
            if (|cv) $fatal(1, "STARTUP_SHELL_RESTART stale command survived reset epoch");
        end
        $display("STARTUP_SHELL PASS queued-command/program/6-stopped-reset-epochs");
        $finish;
    end
    initial begin #2000; $fatal(1, "STARTUP_SHELL_TIMEOUT"); end
endmodule
