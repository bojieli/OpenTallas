`timescale 1ns/1ps
module tb_kv_dcal_ovl_bc;
    parameter integer DMUT=0;
    parameter ROM_DIR="rtl/qwen_sys/d2d_static_20261015/ovl_release";
    `include "ovl_release/ovl_release_img.svh"
    reg ck=0; always #0.4167 ck=~ck;
    reg rst_n=0, epoch_go=0, halt=0;
    reg bt=0,br=0; reg [5:0] ba=0; reg [31:0] bd=0;
    wire tw,rw,cs,cg,rs,rg,ready,adm,run,fault; wire[5:0] ca; wire[31:0] cd; wire[1:0] ut,ur;
    qkd_d2d_cal_seq_pin_ovl_bc #(.ROM_DIR(ROM_DIR),.MUT(DMUT)) dut (
        .ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(epoch_go),.halt(halt),
        .bcfg_tx_we(bt),.bcfg_rx_we(br),.bcfg_addr(ba),.bcfg_data(bd),
        .cfg_tx_we(tw),.cfg_rx_we(rw),.cfg_addr(ca),.cfg_data(cd),
        .cal_start(cs),.cal_seg(cg),.cal_start_rx(rs),.cal_seg_rx(rg),
        .cal_user_tx(ut),.cal_user_rx(ur),.cal_ready(ready),.adm_done(adm),.running(run),.fault(fault));
    // Independent reference has no IO stages and uses uncompensated EP_SKEW=3.
    wire[10:0] ta,ra; wire[71:0] tq,rq; reg[31:0] tc,rc;
    ot_rom_4096x72_m8 #(.VIAMAP({ROM_DIR,"/ovl_k_tx.viamap.hex"}),.INSTANCE("ref_tx")) txrom
        (.clk(ck),.ce_in(1'b1),.addr_in({1'b0,ta}),.rd_out(tq));
    ot_rom_4096x72_m8 #(.VIAMAP({ROM_DIR,"/ovl_k_rx.viamap.hex"}),.INSTANCE("ref_rx")) rxrom
        (.clk(ck),.ce_in(1'b1),.addr_in({1'b0,ra}),.rd_out(rq));
    always @(posedge ck) begin tc<=tq[31:0]; rc<=rq[31:0]; end
    wire xtw,xrw,xcs,xcg,xrs,xrg,xadm,xrun,xf; wire[5:0] xca; wire[31:0] xcd; wire[1:0] xut,xur;
    ot_qwen_d2d_ovl_seq #(.TX_IMG(OVL_K_TX_IMG),.RX_IMG(OVL_K_RX_IMG),
        .TX_SEG1(OVL_K_TX_SEG1),.RX_SEG1(OVL_K_RX_SEG1),.TX_SEG2(32'd16),.RX_SEG2(32'd16),
        .ADM(1),.ADM_OFS(72),.ADM_LEN(1100),.FIRST_OFS(1176),.EP_SKEW(3)) refseq (
        .ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(epoch_go),.halt(halt),
        .cfg_tx_we(xtw),.cfg_rx_we(xrw),.cfg_addr(xca),.cfg_data(xcd),
        .cal_start(xcs),.cal_seg(xcg),.cal_start_rx(xrs),.cal_seg_rx(xrg),.cal_user_tx(xut),.cal_user_rx(xur),
        .tx_rom_addr(ta),.tx_rom_q(tc),.rx_rom_addr(ra),.rx_rom_q(rc),
        .cal_ready(),.adm_done(xadm),.running(xrun),.fault(xf));
    integer mode=0,cyc=0,ep=-1,txcount=0,rxcount=0,bootcount=0;
    integer txbase=-1,rxbase=-1;
    reg failed=0,first=1;
    task automatic err(input string s);
        begin if(!failed) $display("KDCALOVL_ERR cyc%0d mode%0d %s",cyc,mode,s); failed=1; end
    endtask
    always @(negedge ck) begin
        cyc=cyc+1;
        if(tw||rw) begin
            if(ca==32) begin if(tw) txbase=cd; if(rw) rxbase=cd; end
            if(ep<0) begin
                bootcount++;
                if(ca<32 && tw && cd!=OVL_K_TX_IMG[32*ca+:32]) err("boot TX table payload");
                if(ca<32 && rw && cd!=OVL_K_RX_IMG[32*ca+:32]) err("boot RX table payload");
            end
        end
        if(ep>=0) begin
            if(failed && mode>0) begin $display("KDCALOVL_FAIL mode%0d",mode);$fatal(1); end
            if(fault||xf) err($sformatf("fault dut%0d ref%0d col%0d run%0d stale%0d early%0d",fault,xf,
                dut.u_core.f_col,dut.u_core.f_run,dut.u_core.f_stale,dut.u_core.f_early));
            if({cs,rs}!={xcs,xrs}) err("static TX/RX start edge mismatch");
            if(cs && {cg,ut}!={xcg,xut}) err("TX segment/user mismatch");
            if(rs && {rg,ur}!={xrg,xur}) err("RX segment/user mismatch");
            if(cs&&adm&&txbase!=OVL_K_TX_SEG1) err("runtime TX SEG1 switch missing");
            if(rs&&adm&&rxbase!=OVL_K_RX_SEG1) err("runtime RX SEG1 switch missing");
            if(cs&&adm) txcount++;
            if(rs&&adm) rxcount++;
        end
    end
    task automatic put(input bit tx,input integer addr,input reg[31:0] data);
        begin @(negedge ck); bt=tx;br=!tx;ba=6'(addr);bd=data;end
    endtask
    initial begin
        void'($value$plusargs("MUT=%d",mode));
        repeat(5) @(negedge ck);rst_n=1;
        // Boot target11 table and admission bases, not compiled init stream, feed the physical cfg pins.
        repeat(85) @(negedge ck);
        for(integer i=0;i<32;i++) begin put(1,i,OVL_K_TX_IMG[32*i+:32]);put(0,i,OVL_K_RX_IMG[32*i+:32]);end
        put(1,32,mode==2?9:16);
        if(mode!=5) put(0,32,16);
        @(negedge ck);bt=0;br=0;
        repeat(5) @(negedge ck);
        if(bootcount!= (mode==5?65:66)) err("boot passthrough count");
        epoch_go=1;ep=cyc;@(negedge ck);epoch_go=0;
        // Entire F16 list period, including long-gap NOPs and wrap, plus another first exchange.
        repeat(OVL_H+10000) begin
            @(negedge ck);
            if(mode==4 && cyc==ep+200) begin bt=1;ba=0;bd=0;end
            if(mode==4 && cyc==ep+201) bt=0;
            if(mode==3 && cyc==ep+2000) epoch_go=1;
            if(mode==3 && cyc==ep+2001) epoch_go=0;
        end
        if(txcount<1700 || rxcount<1700) err("production frame starts missing");
        if(failed) begin $display("KDCALOVL_FAIL mode%0d",mode);$fatal(1);end
        $display("KDCALOVL_PASS mode%0d tx%0d rx%0d boot%0d",mode,txcount,rxcount,bootcount);$finish;
    end
endmodule
