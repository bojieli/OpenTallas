`timescale 1ps/1fs
// Actual unchanged flat/column core, its real codec and real FIFO. No mocked child bodies.
module tb_pdie_locksafe_native;
    parameter integer COL = 0, DEFAULT_MUT = 0;
    reg clk=0,pck=0,run_pck=0,rst=1,lock=1;
    reg [511:0] tx=512'h123456;
    always #416.5 clk=~clk;
    always #416.62495 if(run_pck)pck=~pck;else pck=0;
    always @(negedge clk) tx <= {tx[510:0],tx[511]^tx[509]};
    wire [511:0] sr,dr,rr; wire[1:0] ss,ds,rs;
    wire[543:0] sp,dp,rp; wire sc,dc,rc;
    wire safe_guard,safe_rr,safe_rt;
    wire[31:0] ptrs; wire[3:0] default_resets,reference_resets;
    generate if(COL)begin:g_col
        ot_pdie_serdes_col_locksafe #(.LOCKSAFE(1)) safe(.clk(clk),.rst(rst),.pma_lock(lock),.tx(tx),.rx(sr),.st(ss),.pma_tx(sp),.pma_tck(sc),.pma_rx(544'd0),.pma_rck(pck));
        ot_pdie_serdes_col_locksafe #(.LOCKSAFE(DEFAULT_MUT)) dormant(.clk(clk),.rst(rst),.pma_lock(1'b0),.tx(tx),.rx(dr),.st(ds),.pma_tx(dp),.pma_tck(dc),.pma_rx(544'd0),.pma_rck(pck));
        ot_pdie_serdes_col reference(.clk(clk),.rst(rst),.tx(tx),.rx(rr),.st(rs),.pma_tx(rp),.pma_tck(rc),.pma_rx(544'd0),.pma_rck(pck));
        assign safe_guard=safe.core_rst_n; assign safe_rr=safe.u_core.rn_r;assign safe_rt=safe.u_core.rn_t;
        assign ptrs={safe.u_core.u_rm.wp,safe.u_core.u_rm.rp,safe.u_core.u_rm.wp_g,safe.u_core.u_rm.rp_g,safe.u_core.u_rm.rp_g1,safe.u_core.u_rm.rp_g2,safe.u_core.u_rm.wp_g1,safe.u_core.u_rm.wp_g2};
        assign default_resets={dormant.u_core.rs_t,dormant.u_core.rs_r};
        assign reference_resets={reference.rs_t,reference.rs_r};
    end else begin:g_flat
        ot_pdie_serdes_locksafe #(.LOCKSAFE(1)) safe(.clk(clk),.rst(rst),.pma_lock(lock),.tx(tx),.rx(sr),.st(ss),.pma_tx(sp),.pma_tck(sc),.pma_rx(544'd0),.pma_rck(pck));
        ot_pdie_serdes_locksafe #(.LOCKSAFE(DEFAULT_MUT)) dormant(.clk(clk),.rst(rst),.pma_lock(1'b0),.tx(tx),.rx(dr),.st(ds),.pma_tx(dp),.pma_tck(dc),.pma_rx(544'd0),.pma_rck(pck));
        ot_pdie_serdes reference(.clk(clk),.rst(rst),.tx(tx),.rx(rr),.st(rs),.pma_tx(rp),.pma_tck(rc),.pma_rx(544'd0),.pma_rck(pck));
        assign safe_guard=safe.core_rst_n; assign safe_rr=safe.u_core.rn_r;assign safe_rt=safe.u_core.rn_t;
        assign ptrs={safe.u_core.u_rm.wp,safe.u_core.u_rm.rp,safe.u_core.u_rm.wp_g,safe.u_core.u_rm.rp_g,safe.u_core.u_rm.rp_g1,safe.u_core.u_rm.rp_g2,safe.u_core.u_rm.wp_g1,safe.u_core.u_rm.wp_g2};
        assign default_resets={dormant.u_core.rs_t,dormant.u_core.rs_r};
        assign reference_resets={reference.rs_t,reference.rs_r};
    end endgenerate
    integer n,epoch,checks=0;
    always @(posedge clk or posedge pck) begin
        #0.01;
        if({dr,ds,dp,dc,default_resets} !== {rr,rs,rp,rc,reference_resets})
            $fatal(1,"default wrapper differs COL=%0d",COL);
        checks=checks+1;
    end
    task held;
        begin
            if({safe_guard,safe_rr,safe_rt} !== 3'd0 || ptrs!==32'd0 || sr!==512'd2 || ss!==2'd0)
                $fatal(1,"unsafe actual core reset COL=%0d epoch=%0d",COL,epoch);
        end
    endtask
    task resume;
        begin
            run_pck=1;
            for(n=1;n<=68;n=n+1)begin
                @(posedge pck);#0.1;
                if(n<66 && safe_guard!==0)$fatal(1,"guard early");
                if(n==66 && safe_guard!==1)$fatal(1,"guard late");
                if(n<68 && safe_rr!==0)$fatal(1,"native recovered reset early");
                if(n==68 && safe_rr!==1)$fatal(1,"native recovered reset late");
            end
            $display("NATIVE_RELEASE COL=%0d epoch=%0d guard_edge=66 native_rck_edge=68",COL,epoch);
        end
    endtask
    initial begin
        epoch=0;#1 rst=0;#2;held();rst=1;
        repeat(8)@(posedge clk);#1;held();resume();
        repeat(256)@(posedge pck);@(negedge pck);run_pck=0;
        #2000;epoch=1;lock=0;#1;held();lock=1;
        repeat(8)@(posedge clk);#1;held();resume();
        repeat(32)@(posedge pck);@(negedge pck);run_pck=0;
        #2000;epoch=2;rst=0;#1;held();rst=1;
        repeat(8)@(posedge clk);#1;held();resume();
        $display("LOCKSAFE_NATIVE PASS COL=%0d default_checks=%0d actual_codec_and_fifo=1",COL,checks);$finish;
    end
    initial begin #10000000;$fatal(1,"fixture did not finish");end
endmodule
