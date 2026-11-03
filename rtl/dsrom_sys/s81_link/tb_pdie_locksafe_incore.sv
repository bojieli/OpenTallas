`timescale 1ps/1fs
// S81.RESET adoption gate for the in-core LOCKSAFE parameter of ot_pdie_serdes / ot_pdie_serdes_col.
//   dflt : new core, default parameters           == orig (the pre-change core body, renamed *_orig)  every edge
//   ins  : new core, LOCKSAFE=1 (pma_lock tied 1)  == wrap (gated ba934c4af wrapper, LOCKSAFE=1, lock=1) every edge
//   ins release timing: guard at rck edge 66, native rck reset (rn_r) at 68, after every reset epoch, with the PMA clock
//   stopped through reset assertion AND release (cold / warm-stopped) and running (warm-running).
// Actual codec, FIFO and PMA models; no mocked bodies.  HOLD=63 must fail (early-release mutant).
module tb_pdie_locksafe_incore;
    parameter integer COL = 0, HOLD = 64, DEFAULT_MUT = 0;
    reg clk=0,pck=0,run_pck=0,rst=1;
    reg [511:0] tx=512'h9abcdef;
    always #416.5 clk=~clk;
    always #416.62495 if(run_pck)pck=~pck;else pck=0;
    always @(negedge clk) tx <= {tx[510:0],tx[511]^tx[509]};
    wire [511:0] r_o,r_d,r_i,r_w; wire [1:0] s_o,s_d,s_i,s_w;
    wire [543:0] p_o,p_d,p_i,p_w; wire c_o,c_d,c_i,c_w;
    wire [3:0] rs_o,rs_d,rs_i,rs_w; wire g_i, rr_i;
    generate if(COL)begin:g_col
        ot_pdie_serdes_col_orig orig(.clk(clk),.rst(rst),.tx(tx),.rx(r_o),.st(s_o),.pma_tx(p_o),.pma_tck(c_o),.pma_rx(544'd0),.pma_rck(pck));
        ot_pdie_serdes_col #(.LOCKSAFE(DEFAULT_MUT)) dflt(.clk(clk),.rst(rst),.tx(tx),.rx(r_d),.st(s_d),.pma_tx(p_d),.pma_tck(c_d),.pma_rx(544'd0),.pma_rck(pck));
        ot_pdie_serdes_col #(.LOCKSAFE(1),.HOLD_EDGES(HOLD)) ins(.clk(clk),.rst(rst),.tx(tx),.rx(r_i),.st(s_i),.pma_tx(p_i),.pma_tck(c_i),.pma_rx(544'd0),.pma_rck(pck));
        ot_pdie_serdes_col_locksafe #(.LOCKSAFE(1)) wrap(.clk(clk),.rst(rst),.pma_lock(1'b1),.tx(tx),.rx(r_w),.st(s_w),.pma_tx(p_w),.pma_tck(c_w),.pma_rx(544'd0),.pma_rck(pck));
        assign rs_o={orig.rs_t,orig.rs_r}; assign rs_d={dflt.rs_t,dflt.rs_r}; assign rs_i={ins.rs_t,ins.rs_r};
        assign rs_w={wrap.u_core.rs_t,wrap.u_core.rs_r}; assign g_i=ins.rst_g; assign rr_i=ins.rn_r;
    end else begin:g_flat
        ot_pdie_serdes_orig orig(.clk(clk),.rst(rst),.tx(tx),.rx(r_o),.st(s_o),.pma_tx(p_o),.pma_tck(c_o),.pma_rx(544'd0),.pma_rck(pck));
        ot_pdie_serdes #(.LOCKSAFE(DEFAULT_MUT)) dflt(.clk(clk),.rst(rst),.tx(tx),.rx(r_d),.st(s_d),.pma_tx(p_d),.pma_tck(c_d),.pma_rx(544'd0),.pma_rck(pck));
        ot_pdie_serdes #(.LOCKSAFE(1),.HOLD_EDGES(HOLD)) ins(.clk(clk),.rst(rst),.tx(tx),.rx(r_i),.st(s_i),.pma_tx(p_i),.pma_tck(c_i),.pma_rx(544'd0),.pma_rck(pck));
        ot_pdie_serdes_locksafe #(.LOCKSAFE(1)) wrap(.clk(clk),.rst(rst),.pma_lock(1'b1),.tx(tx),.rx(r_w),.st(s_w),.pma_tx(p_w),.pma_tck(c_w),.pma_rx(544'd0),.pma_rck(pck));
        assign rs_o={orig.rs_t,orig.rs_r}; assign rs_d={dflt.rs_t,dflt.rs_r}; assign rs_i={ins.rs_t,ins.rs_r};
        assign rs_w={wrap.u_core.rs_t,wrap.u_core.rs_r}; assign g_i=ins.rst_g; assign rr_i=ins.rn_r;
    end endgenerate
    integer n,epoch,checks=0;
    wire cmp_ins = (HOLD == 64); // the early mutant is judged by the release-edge check, not the wrapper compare
    always @(posedge clk or posedge pck) begin
        #0.01;
        if({r_d,s_d,p_d,c_d,rs_d} !== {r_o,s_o,p_o,c_o,rs_o}) $fatal(1,"default core differs from original COL=%0d",COL);
        if(cmp_ins && {r_i,s_i,p_i,c_i,rs_i} !== {r_w,s_w,p_w,c_w,rs_w}) $fatal(1,"in-core LOCKSAFE differs from gated wrapper COL=%0d",COL);
        checks=checks+1;
    end
    task held;
        begin
            if({g_i,rr_i,rs_i} !== 6'd0 || s_i !== 2'd0 || r_i !== 512'd2)
                $fatal(1,"in-core LOCKSAFE not held COL=%0d epoch=%0d",COL,epoch);
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
            $display("INCORE_RELEASE COL=%0d epoch=%0d guard_edge=66 native_rck_edge=68",COL,epoch);
        end
    endtask
    initial begin
        // epoch 0: cold reset, PMA clock stopped through assertion and release
        epoch=0;#1 rst=0;#2;held();rst=1;
        repeat(8)@(posedge clk);#1;held();resume();
        repeat(256)@(posedge pck);
        // epoch 1: PMA clock stops mid-mission, warm reset while stopped, released while stopped, then restart
        @(negedge pck);run_pck=0;#2000;
        epoch=1;rst=0;#1;held();rst=1;repeat(8)@(posedge clk);#1;held();resume();
        repeat(64)@(posedge pck);
        // epoch 2: warm reset with the PMA clock running (assert and release between rck edges)
        epoch=2;@(negedge pck);#5 rst=0;#2;held();@(negedge pck);#5 rst=1;#1;held();resume();
        repeat(64)@(posedge pck);
        $display("LOCKSAFE_INCORE PASS COL=%0d lockstep_checks=%0d default_identity=1 incore_eq_wrapper=1",COL,checks);$finish;
    end
    initial begin #10000000;$fatal(1,"fixture did not finish");end
endmodule
