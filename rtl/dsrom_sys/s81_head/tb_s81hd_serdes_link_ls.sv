`timescale 1ps/1fs
// HEAD warm-reset sequencer bench (DIE-HEAD-54, OWNER 11-02 17:55 decision 1).
// Actual unchanged ot_pdie_serdes (real KP4 codec + FIFO), no mocked bodies.
//  head  = ot_s81hd_serdes_link_ls LOCKSAFE=1      (the HEAD adoption)
//  gold  = ot_pdie_serdes_locksafe LOCKSAFE=1      (shared gated mechanism, codex/serdes-locksafe-2047)
//  dorm  = ot_s81hd_serdes_link_ls LOCKSAFE=DMUT   (identity when off)
//  ref   = ot_s81hd_serdes_link                    (unchanged released adapter)
// Every clk/rck edge: head == {gold.st, gold.rx} + pma pins; dorm == ref.
// Three epochs (cold, pma_lock loss with PMA clock stopped, rst_n warm reset with
// PMA clock stopped): core reset held while stopped, released at recovered edge 66
// (2 sync + 64 hold), native recovered reset at 68.
// Mutants: HOLD=63 (early), IGNORE_LOCK=1 (lock not wired), DMUT=1 (default not identity).
module tb_s81hd_serdes_link_ls;
    parameter integer HOLD = 64, IGNORE_LOCK = 0, DMUT = 0;
    reg clk=0,pck=0,run_pck=0,rst=1,lock=1;
    reg [511:0] tx=512'h123456;
    always #416.5 clk=~clk;
    always #416.62495 if(run_pck)pck=~pck;else pck=0;
    always @(negedge clk) tx <= {tx[510:0],tx[511]^tx[509]};
    wire [513:0] ho,dov,rov; wire [511:0] gr; wire [1:0] gs;
    wire [543:0] hp,gp,dp,rp; wire hc,gc,dc,rc;
    ot_s81hd_serdes_link_ls #(.LOCKSAFE(1),.HOLD_EDGES(HOLD)) head(.ck(clk),.rst_n(rst),.pma_lock(IGNORE_LOCK?1'b1:lock),
        .coll_i0(tx),.coll_o0(ho),.pma_tx(hp),.pma_tck(hc),.pma_rx(544'd0),.pma_rck(pck));
    ot_pdie_serdes_locksafe #(.LOCKSAFE(1)) gold(.clk(clk),.rst(rst),.pma_lock(lock),.tx(tx),.rx(gr),.st(gs),
        .pma_tx(gp),.pma_tck(gc),.pma_rx(544'd0),.pma_rck(pck));
    ot_s81hd_serdes_link_ls #(.LOCKSAFE(DMUT)) dorm(.ck(clk),.rst_n(rst),.pma_lock(1'b0),
        .coll_i0(tx),.coll_o0(dov),.pma_tx(dp),.pma_tck(dc),.pma_rx(544'd0),.pma_rck(pck));
    ot_s81hd_serdes_link refl(.ck(clk),.rst_n(rst),.coll_i0(tx),.coll_o0(rov),.pma_tx(rp),.pma_tck(rc),.pma_rx(544'd0),.pma_rck(pck));
    wire h_guard = head.core_rst_n, h_rr = head.u_link.rn_r, h_rt = head.u_link.rn_t;
    integer n,epoch,checks=0;
    always @(posedge clk or posedge pck) begin
        #0.01;
        if({dov,dp,dc,dorm.u_link.rs_t,dorm.u_link.rs_r} !== {rov,rp,rc,refl.u_link.rs_t,refl.u_link.rs_r})
            $fatal(1,"default wrapper differs from released adapter");
        if({ho,hp,hc,h_guard,h_rr,h_rt} !== {gs,gr,gp,gc,gold.core_rst_n,gold.u_core.rn_r,gold.u_core.rn_t})
            $fatal(1,"HEAD sequencer differs from shared mechanism epoch=%0d",epoch);
        checks=checks+1;
    end
    task held;
        begin
            if({h_guard,h_rr,h_rt} !== 3'd0 || ho[511:0]!==512'd2 || ho[513:512]!==2'd0)
                $fatal(1,"unsafe HEAD core reset epoch=%0d",epoch);
        end
    endtask
    task resume;
        begin
            run_pck=1;
            for(n=1;n<=68;n=n+1)begin
                @(posedge pck);#0.1;
                if(n<66 && h_guard!==0)$fatal(1,"early release guard n=%0d",n);
                if(n==66 && h_guard!==1)$fatal(1,"guard late");
                if(n<68 && h_rr!==0)$fatal(1,"early release native recovered reset n=%0d",n);
                if(n==68 && h_rr!==1)$fatal(1,"native recovered reset late");
            end
            $display("HEAD_RELEASE epoch=%0d guard_rck_edge=66 native_rck_edge=68",epoch);
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
        $display("HEAD_LOCKSAFE PASS checks=%0d actual_codec_and_fifo=1",checks);$finish;
    end
    initial begin #10000000;$fatal(1,"fixture did not finish");end
endmodule
