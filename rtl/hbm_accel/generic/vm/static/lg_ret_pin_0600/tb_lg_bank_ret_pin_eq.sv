`timescale 1ns/1ps
`default_nettype none
// H-NETLIST 0600: ot_hbm_vm_lg_static_bank RET_PIN=1 (depth 18/15, strap rret/wret) == the parameter build
// #(R,W) on every output, every edge, under random local/far/near traffic incl. faults. MUT=1: strap off by one.
module tb_lg_bank_ret_pin_eq;
    parameter integer R=10, W=7, MUT=0, SEED=3, D=4;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [16:0] lrq,frq; reg [280:0] lwq,fwq; reg lr,lw; reg [256:0] nrr; reg nwd;
    wire [16:0] a_nrq,b_nrq; wire [280:0] a_nwq,b_nwq; wire [256:0] a_lrr,b_lrr,a_frr,b_frr; wire a_lwd,b_lwd,a_fwd,b_fwd,a_f,b_f;
    ot_hbm_vm_lg_static_bank #(.READ_RETURN(R),.WRITE_RETURN(W)) ref_b(.clk(clk),.rst_n(rst_n),.rret(5'd0),.wret(5'd0),
        .local_rq(lrq),.far_rq(frq),.local_wq(lwq),.far_wq(fwq),.local_read(lr),.local_write(lw),.near_rq(a_nrq),.near_wq(a_nwq),
        .near_rr(nrr),.near_w_done(nwd),.local_rr(a_lrr),.far_rr(a_frr),.local_w_done(a_lwd),.far_w_done(a_fwd),.fault(a_f));
    ot_hbm_vm_lg_static_bank #(.READ_RETURN(18),.WRITE_RETURN(15),.RET_PIN(1)) dut(.clk(clk),.rst_n(rst_n),
        .rret(5'(R+(MUT==1))),.wret(5'(W)),
        .local_rq(lrq),.far_rq(frq),.local_wq(lwq),.far_wq(fwq),.local_read(lr),.local_write(lw),.near_rq(b_nrq),.near_wq(b_nwq),
        .near_rr(nrr),.near_w_done(nwd),.local_rr(b_lrr),.far_rr(b_frr),.local_w_done(b_lwd),.far_w_done(b_fwd),.fault(b_f));
    integer errors=0, checked=0, seed, t, lret=0, faults=0;
    reg [17:0] rd_hist, wr_hist;
    always @(negedge clk) if (rst_n) begin
        checked=checked+1;
        if ({a_nrq,a_nwq,a_lrr,a_frr,a_lwd,a_fwd,a_f} !== {b_nrq,b_nwq,b_lrr,b_frr,b_lwd,b_fwd,b_f}) begin
            errors=errors+1; if (errors<5) $display("MISMATCH t=%0t lrr %b/%b lwd %b/%b fault %b/%b", $time, a_lrr[256], b_lrr[256], a_lwd, b_lwd, a_f, b_f);
        end
        if (a_lrr[256]) lret=lret+1;
        if (a_f) faults=faults+1;
    end
    initial begin
        seed=SEED; lrq=0; frq=0; lwq=0; fwq=0; lr=0; lw=0; nrr=0; nwd=0; rd_hist=0; wr_hist=0;
        repeat(3) @(posedge clk); #1 rst_n=1;
        for (t=0; t<4000; t=t+1) begin
            @(posedge clk); #1;
            // legal calendar traffic: local read/write select with valid, far otherwise; near responses land exactly on the
            // reserved edge (derived from the reference calendar); stray responses only after edge 3000 (fault path)
            lr = ($random(seed) & 3)==0; lw = ($random(seed) & 3)==1;
            lrq = {lr, 16'($random(seed))}; frq = {(!lr && ($random(seed)&1)), 16'($random(seed))};
            lwq = {lw, 280'({9{$random(seed)}})}; fwq = {(!lw && ($random(seed)&1)), 280'({9{$random(seed)}})};
            rd_hist = {rd_hist[16:0], lr}; wr_hist = {wr_hist[16:0], lw};
            nrr = {(ref_b.read_calendar[R-2][0] ^ (t>3000 && ($random(seed)&15)==0)), 256'({9{$random(seed)}})};   // occasional far/stray responses
            nwd = ref_b.write_calendar[W-2][0] ^ (t>3000 && ($random(seed)&15)==0);   // dropped/stray -> fault path
            if (t==2000) begin rst_n=0; @(posedge clk); #1 rst_n=1; end
        end
        if (errors==0 && lret>0) $display("LG_RET_PIN_EQ PASS R=%0d W=%0d checks=%0d local_returns=%0d fault_edges=%0d", R, W, checked, lret, faults);
        else begin $display("LG_RET_PIN_EQ FAIL R=%0d W=%0d errors=%0d checks=%0d local_returns=%0d", R, W, errors, checked, lret); $fatal(1,"eq"); end
        $finish;
    end
endmodule
`default_nettype wire
