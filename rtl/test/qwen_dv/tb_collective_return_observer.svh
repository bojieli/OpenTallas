    // Component return observer: actual static collective output -> selected
    // two-edge return contract -> actual reset-safe LP core/status -> CTLM.
    // The declared return pipeline is not a qualification of a current bind.
    reg [517:0] status_ret0=0,status_ret1=0;
    always @(posedge clk) begin
        status_ret0 <= {ov[0],oe[0],orank[2:0],ol[0],od[511:0]};
        status_ret1 <= status_ret0;
    end
    reg [115:0] status_cmd=0;
    always @(negedge clk) begin
        status_cmd=0;
        if(cyc==80)status_cmd=(116'hf<<112)|116'd15;
        if(cyc==90)status_cmd=(116'hf<<112)|(116'd1<<52)|116'd9;
    end
    wire [106:0] status_next,status_ss5;
    wire [9:0] status_ag_next,status_ag;
    qfd_dv_slice2_lpc #(.MU_NU(1),.SU_LT(0),.HD_W130(1)) status_p (
        .ck(clk),.rst_n(rst_n),.cmd_i(status_cmd),.hr_i(453'b0),
        .rs_s0(514'b0),.rs_s1(514'b0),.rs_n0(514'b0),.rs_n1(514'b0),
        .l9_i(514'b0),.st_up_i(1088'b0),.st_dn_i(1088'b0),
        .sc_up_i(48'b0),.sc_dn_i(48'b0),.ch_up_i(1095'b0),
        .ch_dn_i({status_ret1,520'b0}),.ag_up_i(10'b0),
        .st_n(status_next),.ag_n(status_ag_next));
    qfd_dv_slice2_lps status_ps(.ck(clk),.rst_n(rst_n),
        .st_n(status_next),.ag_n(status_ag_next),.hd_fault(1'b0),
        .st(status_ss5),.ag_dn_o(status_ag));
    integer status_last_delay=0;
    reg status_last_q=0;
    always @(posedge clk)status_last_q<=status_ss5[25];
    wire [106:0] status_to_ctl={status_ss5[106:26],
        status_last_delay?status_last_q:status_ss5[25],status_ss5[24:0]};
    qfd_tt_ctlm_dv #(.HARD_HR(1),.XPF_TRANSPORT_EDGES(1)) status_c (
        .ck(clk),.rst_n(rst_n),.pw(75'b0),.dh(187'b0),
        .kok(1'b0),.kwd(1'b1),.fab(1'b0),.native_ret(95'b0),
        .ss5(status_to_ctl),.ag5(status_ag));
    reg status_prev_land=0,status_prev_last=0;
    integer status_message=-1,status_completions=0;
    initial if($value$plusargs("STATUS_LAST_DELAY=%d",status_last_delay));
    always @(negedge clk) if(rst_n) begin
        if(status_ss5[106]&&!status_prev_land)status_message=status_message+1;
        if(status_ss5[106]!=status_prev_land||status_ss5[25]!=status_prev_last)
            $display("SS5_RAW edge=%0d message=%0d ar_land=%0d ar_last=%0d",cyc,status_message,status_ss5[106],status_ss5[25]);
        if(status_c.coll_done)begin
            $display("SS5_CTL_DONE edge=%0d ordinal=%0d",cyc,status_completions);
            status_completions=status_completions+1;
        end
        status_prev_land=status_ss5[106];status_prev_last=status_ss5[25];
        if(cyc==endc-2)$display("SS5_SUMMARY completions=%0d expected=%0d last_delay=%0d",status_completions,NMSG,status_last_delay);
    end
