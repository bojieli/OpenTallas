`timescale 1ns/1ps
module tb_dsfd_vm_fe_reset_ack;
    reg ck=0, cks=0, clt_ck=0, fsr_ck=0;
    reg run_stream=1, run_clt=1, run_fsr=1;
    reg rst=1, rss=1, rn_clt=1, rn_fsr=1, epoch_clt=1, epoch_fsr=1;
    wire [27:0] fv; wire [3583:0] fd; wire [3:0] cf;
    reg [27:0] iv=0; reg [3583:0] id=0;
    wire [3:0] cn_rdy; wire [15:0] cn_fault;
    wire [1:0] cn_ack, cn_ack_s, cc_ack, cc_ack_s, cw_ack;
    wire clt_ack,fsr_ack;
    dsfd_vm_clt u_clt (.ck(clt_ck),.rn(rn_clt),.sok(1'b1),.gid(4'd0),.f_c(832'd0),
        .w_v(),.w_row(),.w_m(),.w_d(),.flt(cf)
`ifdef OT_SPVM_RESET_ACK
        ,.reset_epoch_n(epoch_clt),.rst_ack(clt_ack)
`endif
    );
    dsfd_vm_fsr u_fsr (.ck(fsr_ck),.rn(rn_fsr),.i_v(iv),.i_we(28'd0),.i_row(392'd0),.i_mask(112'd0),.i_d(id),.i_rf(4'd0),
        .o_v(fv),.o_we(),.o_row(),.o_mask(),.o_d(fd),.o_rf()
`ifdef OT_SPVM_RESET_ACK
        ,.reset_epoch_n(epoch_fsr),.rst_ack(fsr_ack)
`endif
    );
    dsfd_vm_fcn u_cn (.ck(ck),.rst(rst),.cks(cks),.rss(rss),.cv(1'b0),.cd(84'd0),.dv(),.dt(),
        .f_cq(64'd0),.f_p2c(1'b0),.c_wv(),.c_wd(),.c_wr(1'b1),.t_rdy(cn_rdy),.k_i(704'd0),
        .clf_i(16'd0),.so_i(1'b0),.ovr_i(1'b0),.sflt_i(1'b0),.err_i(1'b0),.s_o(),.x_o(),.arm_v(),.arm_base(),.rf_o(),.fe_flt(cn_fault),.rn_o()
`ifdef OT_SPVM_RESET_ACK
        ,.rst_ack(cn_ack),.rst_ack_s(cn_ack_s)
`endif
    );
    dsfd_vm_fcc u_cc (.ck(ck),.rni(rst),.cks(cks),.rss(rss),.rst(rst),.vwe(1'b0),.vwa(14'd0),.vwd(512'd0),
        .vre(1'b0),.vra(14'd0),.s_o(),.k_o(),.so_o(),.rn_o()
`ifdef OT_SPVM_RESET_ACK
        ,.rst_ack(cc_ack),.rst_ack_s(cc_ack_s)
`endif
    );
    dsfd_vm_fcw u_cw (.ck(ck),.rni(rst),.rst(rst),.f_swv(1'b0),.f_swd(527'd0),.t_swg(),.f_srv(1'b0),.f_srd(31'd0),
        .t_srg(),.t_ks(),.s_o(),.k_o(),.err_o(),.rn_o()
`ifdef OT_SPVM_RESET_ACK
        ,.rst_ack(cw_ack)
`endif
    );
    integer edge_number=0; reg [31:0] checksum=0;
    task automatic tick;
        begin
            #2; ck=1; if(run_stream) cks=1; if(run_clt) clt_ck=1; if(run_fsr) fsr_ck=1;
            #1; edge_number=edge_number+1;
            checksum={checksum[30:0],checksum[31]} ^ fv ^ fd[31:0] ^ {12'd0,cn_fault,cn_rdy} ^ cf;
            #2; ck=0; cks=0; clt_ck=0; fsr_ck=0;
        end
    endtask
    task automatic require(input bit condition,input string message);
        if(!condition) begin $display("ACK_BAD edge=%0d %s",edge_number,message); $fatal(1,"ACK_BAD"); end
    endtask
`ifdef OT_SPVM_RESET_ACK
    task automatic await_all;
        integer count;
        begin
            count=0;
            while(!(clt_ack && fsr_ack && (&cn_ack) && (&cn_ack_s) && (&cc_ack) && (&cc_ack_s) && (&cw_ack)) && count<200) begin tick();count=count+1;end
            require(count<200,"actual consumers did not acknowledge valid reset");
        end
    endtask
`endif
    initial begin
        #1; rst=0;rss=0;rn_clt=0;rn_fsr=0;epoch_clt=0;epoch_fsr=0;
        repeat(6) tick();
        rst=1;rss=1;rn_clt=1;rn_fsr=1;epoch_clt=1;epoch_fsr=1;run_clt=0;run_fsr=0;run_stream=0;
        repeat(40) begin tick();
`ifdef OT_SPVM_RESET_ACK
            require(!clt_ack && !fsr_ack,"stopped final consumer was replaced by upstream release");
            require(!cn_ack[1] && !cc_ack[1],"stopped stream domain bypassed real adapter/FIFO online");
`endif
        end
        run_clt=1;run_fsr=1;run_stream=1;
        repeat(40) tick();
`ifdef OT_SPVM_RESET_ACK
        await_all();
        require(u_clt.rn_r && u_fsr.rn_q,"ACK not tied to actual final local reset");
`endif
        // Real payload transition: two-register FSR valid/data path remains unchanged by telemetry.
        iv=28'h05555aa;id[31:0]=32'h12345678;repeat(6) tick();
        require(fv==iv && fd[31:0]==id[31:0],"FSR numerical/data behavior changed");
        // Miss an entire request assertion while the final consumer clocks stop.
        // Their rn_r/rn_q stay HIGH from the prior epoch; this is the stale-ACK trap.
        run_clt=0;run_fsr=0;epoch_clt=0;epoch_fsr=0;#1;
`ifdef OT_SPVM_RESET_ACK
        require(!clt_ack && !fsr_ack,"request assertion did not clear ACK with clock stopped");
`endif
        repeat(3) tick();rn_clt=1;rn_fsr=1;epoch_clt=1;epoch_fsr=1;repeat(4) tick();run_clt=1;run_fsr=1;
        repeat(8) begin tick();
`ifdef OT_SPVM_RESET_ACK
            require(!clt_ack && !fsr_ack,"reset not sampled: stale HIGH final rn falsely acknowledged");
`endif
        end
        // A valid new request with running consumer clocks repairs the missing epoch.
        rn_clt=0;rn_fsr=0;epoch_clt=0;epoch_fsr=0;repeat(4) tick();
        require(fv==0 && u_clt.u_c.V==0,"actual consumer initialization was not performed");
        rn_clt=1;rn_fsr=1;epoch_clt=1;epoch_fsr=1;repeat(12) tick();
`ifdef OT_SPVM_RESET_ACK
        await_all();
`endif
        // Reassert both domain resets with stream stopped: peer online must flush,
        // and the serial ACK cannot stand in for the stopped stream endpoint.
        run_stream=0;rst=0;rss=0;repeat(4) tick();rst=1;rss=1;
        repeat(30) begin tick();
`ifdef OT_SPVM_RESET_ACK
            require(!cn_ack[1] && !cc_ack[1],"reasserted epoch reused stale CDC online");
`endif
        end
        run_stream=1;repeat(40) tick();
`ifdef OT_SPVM_RESET_ACK
        await_all(); $display("ACK_PASS final consumers + stopped clocks + missed pulse + CDC reassert");
`endif
        $display("NUM_TRACE %08x",checksum);$display("PASS");$finish;
    end
endmodule
