`timescale 1ps/1fs
// S81.RESET adoption gate (DIE-S81-49, OWNER 2026-11-02 17:55) for ot_pdie_serdes_col LOCKSAFE / pma_lock.
//   dflt : new column, default parameters (LOCKSAFE=0, pma_lock floating)  == orig (released column body *_orig)  every edge
//   ins  : new column, LOCKSAFE=1 HOLD_EDGES=64 on pma_lock               == wrap (shared gated ot_pdie_serdes_col_locksafe
//          LOCKSAFE=1 around the released column, same pma_lock)           every edge, incl. the reset synchronisers
//   release timing of ins: guard (rst_g) at recovered edge 66, native rck reset (rn_r) at 68, after
//     e0 cold reset, PMA clock stopped through assertion and release
//     e1 PMA clock stops mid-mission, warm rst while stopped, released while stopped, then restart
//     e2 warm rst with the PMA clock running
//     e3 lock loss with the PMA clock running, relock
//     e4 PMA clock stops, lock lost while stopped, clock restarts unlocked (must stay held), then lock
// Actual codec, FIFO and PMA models, no mocked bodies.  Mutants: HOLD=63 (early release), IGNORE_LOCK=1 (ins sees lock
// tied 1) and DEFAULT_MUT=1 (default activation) must each fail.
module tb_s81_col_locksafe;
    parameter integer HOLD = 64, IGNORE_LOCK = 0, DEFAULT_MUT = 0;
    reg clk=0,pck=0,run_pck=0,rst=1,lock=1;
    reg [511:0] tx=512'h9abcdef;
    always #416.5 clk=~clk;
    always #416.62495 if(run_pck)pck=~pck;else pck=0;
    always @(negedge clk) tx <= {tx[510:0],tx[511]^tx[509]};
    wire [511:0] r_o,r_d,r_i,r_w; wire [1:0] s_o,s_d,s_i,s_w;
    wire [543:0] p_o,p_d,p_i,p_w; wire c_o,c_d,c_i,c_w;
    wire [3:0] rs_o,rs_d,rs_i,rs_w; wire g_i, rr_i;
    ot_pdie_serdes_col_orig orig(.clk(clk),.rst(rst),.tx(tx),.rx(r_o),.st(s_o),.pma_tx(p_o),.pma_tck(c_o),.pma_rx(544'd0),.pma_rck(pck));
    ot_pdie_serdes_col #(.LOCKSAFE(DEFAULT_MUT)) dflt(.clk(clk),.rst(rst),.tx(tx),.rx(r_d),.st(s_d),.pma_tx(p_d),.pma_tck(c_d),.pma_rx(544'd0),.pma_rck(pck));
    ot_pdie_serdes_col #(.LOCKSAFE(1),.HOLD_EDGES(HOLD)) ins(.clk(clk),.rst(rst),.tx(tx),.rx(r_i),.st(s_i),.pma_tx(p_i),.pma_tck(c_i),.pma_rx(544'd0),.pma_rck(pck),.pma_lock(IGNORE_LOCK ? 1'b1 : lock));
    ot_pdie_serdes_col_locksafe #(.LOCKSAFE(1)) wrap(.clk(clk),.rst(rst),.pma_lock(lock),.tx(tx),.rx(r_w),.st(s_w),.pma_tx(p_w),.pma_tck(c_w),.pma_rx(544'd0),.pma_rck(pck));
    assign rs_o={orig.rs_t,orig.rs_r}; assign rs_d={dflt.rs_t,dflt.rs_r}; assign rs_i={ins.rs_t,ins.rs_r};
    assign rs_w={wrap.u_core.rs_t,wrap.u_core.rs_r}; assign g_i=ins.rst_g; assign rr_i=ins.rn_r;
    integer n,epoch,checks=0,live=0;
    wire cmp_ins = (HOLD == 64); // the early mutant is judged by the release-edge check, not the wrapper compare
    always @(posedge clk or posedge pck) begin
        #0.01;
        if({r_d,s_d,p_d,c_d,rs_d} !== {r_o,s_o,p_o,c_o,rs_o}) $fatal(1,"default column differs from released column");
        if(cmp_ins && {r_i,s_i,p_i,c_i,rs_i} !== {r_w,s_w,p_w,c_w,rs_w}) $fatal(1,"in-column LOCKSAFE differs from gated shared wrapper epoch=%0d",epoch);
        if(s_i[1]) live=live+1;
        checks=checks+1;
    end
    task held;
        begin
            if({g_i,rr_i,rs_i} !== 6'd0 || s_i !== 2'd0 || r_i !== 512'd2)
                $fatal(1,"in-column LOCKSAFE not held epoch=%0d",epoch);
        end
    endtask
    task resume;
        begin
            run_pck=1;
            for(n=1;n<=68;n=n+1)begin
                @(posedge pck);#0.1;
                if(n<66 && g_i!==0)$fatal(1,"early release guard edge%0d",n);
                if(n==66 && g_i!==1)$fatal(1,"late release guard");
                if(n<68 && rr_i!==0)$fatal(1,"early release native rck reset edge%0d",n);
                if(n==68 && rr_i!==1)$fatal(1,"late release native rck reset");
            end
            $display("S81_COL_RELEASE epoch=%0d guard_edge=66 native_rck_edge=68",epoch);
        end
    endtask
    initial begin
        epoch=0;#1 rst=0;#2;held();rst=1;
        repeat(8)@(posedge clk);#1;held();resume();
        repeat(256)@(posedge pck);
        @(negedge pck);run_pck=0;#2000;
        epoch=1;rst=0;#1;held();rst=1;repeat(8)@(posedge clk);#1;held();resume();
        repeat(64)@(posedge pck);
        epoch=2;@(negedge pck);#5 rst=0;#2;held();@(negedge pck);#5 rst=1;#1;held();resume();
        repeat(64)@(posedge pck);
        epoch=3;@(negedge pck);#5 lock=0;#2;held();repeat(4)@(posedge pck);#1;held();@(negedge pck);#5 lock=1;#1;held();resume();
        repeat(64)@(posedge pck);
        epoch=4;@(negedge pck);run_pck=0;#2000;lock=0;#1;held();
        run_pck=1;repeat(80)@(posedge pck);#1;held();@(negedge pck);#5 lock=1;#1;held();resume();
        repeat(256)@(posedge pck);
        $display("S81_COL_LOCKSAFE PASS lockstep_checks=%0d live_samples=%0d default_identity=1 incol_eq_shared_wrapper=1 epochs=5",checks,live);$finish;
    end
    initial begin #20000000;$fatal(1,"fixture did not finish");end
endmodule
