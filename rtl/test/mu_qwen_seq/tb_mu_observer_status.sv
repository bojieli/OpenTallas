`timescale 1ns/1ps
// Smallest actual GI->GO STATUS path. No malformed head/program fixture can
// pre-assert another core fault and accidentally satisfy the observability check.
module tb_mu_observer_status;
    parameter integer MUT = 0;
    reg ck=0; always #5 ck=~ck;
    reg rst_n=0, observer=0;
    wire [61:0] dcs;
    wire [55:0] dc;
    wire cf;
    qfd_tt_ctlm_dv_gi #(.NU(1), .OPSEG(0)) gi (
        .ck(ck),.rst_n(rst_n),.dh(187'd0),.dh_user(2'd0),.ctx_x(129'd0), .init_u0(1'b0),
        .mu_fault(MUT ? 1'b0 : observer),.ss5(107'd0),.ag5(10'd0),.fab(1'b0),.dcs(dcs));
    qfd_tt_ctlm_dv_go #(.XPF_TRANSPORT_EDGES(1)) go (
        .ck(ck),.rst_n(rst_n),.pw(75'd0),.st(49'd0),.su_obs(16'd0),.me_observe(16'd0),
        .cp(56'd0),.me_image_ready(1'b0),.hr_fault(1'b0),.dcs(dcs),.dc(dc),.cf(cf));
    integer errors=0;
    task tick; begin @(posedge ck); #1; @(negedge ck); end endtask
    initial begin
        repeat(3) tick; rst_n=1; repeat(12) tick;
        if(dc[52] || cf) begin errors=errors+1; $display("BASELINE_FAULT dc=%h cf=%b",dc,cf); end
        observer=1; tick; observer=0; repeat(4) tick;
        if(!dc[52] || !cf) errors=errors+1;
        repeat(4) tick;
        if(!dc[52] || !cf) errors=errors+1;
        rst_n=0; repeat(3) tick; rst_n=1; repeat(12) tick;
        if(dc[52] || cf) errors=errors+1;
        if(errors) $display("MU_OBSERVER_STATUS FAIL errors=%0d",errors);
        else $display("MU_OBSERVER_STATUS PASS baseline_clean=1 dc52=1 cf=1 sticky=1 reset_clears=1");
        $finish;
    end
endmodule
