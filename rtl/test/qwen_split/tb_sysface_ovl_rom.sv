`timescale 1ns/1ps
// Hardened-list-ROM path vs direct synchronous compiler-list oracle, including admission and all users.
module tb_sysface_ovl_rom;
    parameter DIR="rtl/qwen_sys/d2d_static_20261015/ovl_release";
    parameter integer MUT=0;
    parameter integer RECOVER=0;
    `include "ovl_release/ovl_release_img.svh"
    reg ck=0; always #1 ck=~ck;
    reg rst_n=0, epoch=0, halt=0, restart_count=0, did_restart=0;
    wire [31:0] gd, dd; wire [5:0] ga, da;
    wire gw,gr,gs,gg,grs,grg,drdy,dadm,df,ds,dg,drs,drg,dw,dr;
    wire [1:0] gu,gv,du,dv;
    wire [10:0] ta,ra; reg[31:0] tq,rq;
    reg[31:0] tx[0:2047],rx[0:2047];
    initial begin $readmemh({DIR,"/list_C_tx.memh"},tx); $readmemh({DIR,"/list_C_rx.memh"},rx); end
    always @(posedge ck) begin tq<=tx[ta]; rq<=rx[ra]; end
    qfd_d2d_cal_seq_ovl #(.ROM_DIR(DIR), .MUT_HALT_REWIND(MUT==2)) dut(.ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(epoch),.halt(halt),
        .cfg_tx_we(dw),.cfg_rx_we(dr),.cfg_addr(da),.cfg_data(dd),.cal_start(ds),.cal_seg(dg),
        .cal_start_rx(drs),.cal_seg_rx(drg),.cal_user_tx(du),.cal_user_rx(dv),.cal_ready(drdy),.adm_done(dadm),.running(),.fault(df));
    wire gf;
    ot_qwen_d2d_ovl_seq #(.TX_IMG(OVL_C_TX_IMG),.RX_IMG(OVL_C_RX_IMG),.TX_SEG1(OVL_C_TX_SEG1),.RX_SEG1(OVL_C_RX_SEG1),
        .ADM(1),.TX_SEG2(32'd16),.RX_SEG2(32'd16),.FIRST_OFS(1176)) gold(.ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(epoch),.halt(halt),
        .cfg_tx_we(gw),.cfg_rx_we(gr),.cfg_addr(ga),.cfg_data(gd),.cal_start(gs),.cal_seg(gg),
        .cal_start_rx(grs),.cal_seg_rx(grg),.cal_user_tx(gu),.cal_user_rx(gv),.cal_ready(),.adm_done(),.running(),.fault(gf),
        .tx_rom_addr(ta),.tx_rom_q(tq),.rx_rom_addr(ra),.rx_rom_q(rq));
    integer c=0,nt=0,nr=0; reg[3:0] users=0;
    wire actual_rx = MUT==1 ? 1'b0 : drs;
    always @(negedge ck) if(rst_n) begin
        if(restart_count) begin c=0; nt=0; nr=0; users=0; end
        else c=c+1;
        if(df || gf || {dw,dr,da,dd,ds,dg,actual_rx,drg,du,dv} !== {gw,gr,ga,gd,gs,gg,grs,grg,gu,gv}) begin
            $display("SYSFACE_OVL_FAIL MUT=%0d cycle=%0d df=%b gf=%b",MUT,c,df,gf); $finish;
        end
        if(ds) begin nt=nt+1; users[du]=1; end
        if(drs) nr=nr+1;
        if(c==OVL_H+3200 && (!RECOVER || did_restart)) begin
            if(nt<1600 || nr<1600 || users!==4'b1111 || !drdy || !dadm) $display("SYSFACE_OVL_FAIL counts TX=%0d RX=%0d users=%b",nt,nr,users);
            else $display("SYSFACE_OVL_PASS MUT=%0d RECOVER=%0d TX=%0d RX=%0d users=%b admission1 frame4026800",MUT,RECOVER,nt,nr,users);
            $finish;
        end
    end
    initial begin
        repeat(5) @(negedge ck); rst_n=1; repeat(100) @(negedge ck); epoch=1; @(negedge ck); epoch=0;
        if(RECOVER) begin
            if(RECOVER==1) repeat(100000) @(posedge ck);
            else if(RECOVER<=4) begin
                // Halt with an outstanding ROM prefetch at each of its three age values.
                wait(ta != 0 && gold.u_tx.running && !gold.u_tx.nv && gold.u_tx.age==RECOVER-2);
                @(negedge ck);
            end else begin
                // Halt immediately before the wrap entry reloads word0.
                wait(gold.u_tx.running && gold.u_tx.cur[7] && gold.u_tx.cnt==1);
                @(negedge ck);
            end
            #0.2; halt=1;
            repeat(100) @(posedge ck); #0.2; halt=0; epoch=1; restart_count=1; did_restart=1;
            @(posedge ck); #0.2; epoch=0; restart_count=0;
        end
    end
endmodule
