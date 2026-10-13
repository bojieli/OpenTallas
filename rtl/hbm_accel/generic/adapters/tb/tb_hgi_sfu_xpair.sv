`timescale 1ns/1ps
// Minimum production GLU -> actual SM x-load pair. Shared committed VM model:
// 32 SFU lanes / 8 x-load lanes, ordered lane writes with 24-cycle commit latency.
// Baseline reads after SFU retire, stream reads from real committed watermark.
module tb_hgi_sfu_xpair;
`include "su_sizes.svh"
`ifndef MUT_WM
`define MUT_WM 0
`endif
`ifndef XFMT
`define XFMT 0
`endif
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, rec_v=0;
    reg [2196:0] recm[0:NREC-1], cur;
    reg [287:0] vmi[0:NVMI-1], vme[0:NVME-1];
    reg [255:0] mem[0:32767];
    string dir;
    integer cyc=0, errors=0;
    always @(posedge clk) cyc<=cyc+1;
    wire ready, done, fault, halted;
    wire [19:0] wm;
    wire [32*16-1:0] rq;
    reg [31:0] rc=0; reg [32*257-1:0] rr=0;
    wire [32*280-1:0] wq;
    reg [31:0] wc=0, wd=0;
    wire rg, wg;
    ot_hgi_su_unit #(.N(512), .M(128), .LV(7), .LWB(18), .GLU(1), .WIDE(1),
        .STREAM_WM(1), .MUT_WM(`MUT_WM)) u_sfu (
        .clk(clk), .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(ready), .rec_hdr(cur[127:0]), .rec_sut(cur[383:128]),
        .rec_a(cur[639:384]), .rec_b(cur[895:640]), .rec_c(cur[1151:896]), .rec_d(cur[1407:1152]),
        .rec_o(cur[1663:1408]), .rec_r(cur[1919:1664]), .rec_i(cur[2175:1920]), .rec_n_a(cur[2196:2176]),
        .rec_done(done), .rec_fault(fault), .halted(halted), .sfu_wm(wm), .vmq(), .vmr(274'd0),
        .s0_v(1'b0), .s0_idx(20'd0), .s0_data(32'd0), .am_stream(), .am_rdy(1'b0),
        .wrq(rq), .wrq_cr(rc), .wrr(rr), .wwq(wq), .wwq_cr(wc), .wwq_done(wd),
        .rg_req(rg), .rg_gnt(1'b1), .wg_req(wg), .wg_gnt(1'b1));
    integer h[0:31], t[0:31], wt[0:31][0:255];
    reg [279:0] writes[0:31][0:255];
    initial for(integer b=0;b<32;b++) begin h[b]=0;t[b]=0;end
    always @(posedge clk) begin
        rc<=0; wc<=0; wd<=0; rr<=0;
        if(rst_n) for(integer b=0;b<32;b++) begin
            if(rq[b*16+15]) begin rc[b]<=1; rr[b*257+:257]<={1'b1,mem[rq[b*16+:15]]};end
            if(wq[b*280+279]) begin
                writes[b][t[b]%256]=wq[b*280+:280]; wt[b][t[b]%256]=cyc+24; t[b]++;
                wc[b]<=1;
                if(t[b]-h[b]>128) $fatal(1,"write lane overrun");
            end
            if(h[b]<t[b] && wt[b][h[b]%256]<=cyc) begin
                for(integer w=0;w<8;w++) if(writes[b][h[b]%256][w])
                    mem[writes[b][h[b]%256][264+:15]][32*w+:32]=writes[b][h[b]%256][8+32*w+:32];
                wd[b]<=1; h[b]++;
            end
        end
    end
    reg [1:0] xv=0;
    wire [1:0] xrdy, xd, xf, xe;
    wire [13:0] xa, xg; wire [4095:0] data;
    reg [1:0] finished=0; integer finish_cyc[0:1], beats[0:1];
    reg [2047:0] captures[0:1][0:127][0:127];
    bit seen[0:1][0:127][0:127];
    wire [39:0] base={22'd0,vme[0][270:256],3'd0};
    for(genvar z=0;z<2;z++) begin:g_x
        wire [511:0] qr; reg [31:0] qc=0; reg [8223:0] qd=0; wire req;
        ot_hgi_sm_xload #(.BD(1),.BW8(1),.FW8(1),.SFU_STREAM(1)) u_x (
            .clk(clk),.rst_n(rst_n),.x_v(xv[z]),.x_rdy(xrdy[z]),.x_base(base),.x_n(21'd3072),
            .x_p(4'd1),.x_stride(32'd3072),.x_space(2'd1),.x_fmt(2'(`XFMT)),.x_xb(7'd0),
            .x_stream(z==0),.x_stag(4'd0),.sfu_wm_v(wm[19]),.sfu_wm_tag(wm[18:15]),.sfu_wm(wm[14:0]),
            .x_done(xd[z]),.x_fault(xf[z]),.xw_en(xe[z]),.xw_addr(xa[z*7+:7]),.xw_grp(xg[z*7+:7]),
            .xw_data(data[z*2048+:2048]),.vmq(),.vmr(1096'd0),.rg_req(req),.rg_gnt(1'b1),
            .wrq(qr),.wrq_cr(qc),.wrr(qd));
        always @(posedge clk) begin
            qc<=0;qd<=0;
            if(rst_n) for(integer b=0;b<8;b++) if(qr[b*16+15]) begin
                qc[b]<=1;qd[b*257+:257]<={1'b1,mem[qr[b*16+:15]]};
            end
        end
        always @(negedge clk) if(rst_n) begin
            if(xe[z]) begin
                captures[z][xa[z*7+:7]][xg[z*7+:7]]=data[z*2048+:2048];
                seen[z][xa[z*7+:7]][xg[z*7+:7]]=1; beats[z]++;
            end
            if(xd[z]) begin finished[z]=1;finish_cyc[z]=cyc;end
            if(xf[z]) $fatal(1,"xload fault z=%0d",z);
        end
    end
    integer start_cyc, ret_cyc;
    initial begin
        if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR required");
        $readmemh({dir,"/su_rec.mem"},recm);$readmemh({dir,"/su_vmi.mem"},vmi);$readmemh({dir,"/su_vme.mem"},vme);
        if(NREC!=1 || NCASE!=1 || NVME!=384) $fatal(1,"requires production GLU3072 one record");
        for(integer k=0;k<32768;k++) mem[k]=0;
        for(integer k=0;k<NVMI;k++) mem[vmi[k][287:256]]=vmi[k][255:0];
        foreach(seen[z,a,g]) seen[z][a][g]=0;
        beats[0]=0;beats[1]=0;cur=recm[0];
        repeat(4) @(negedge clk);rst_n=1;
        wait(ready);@(negedge clk);rec_v=1;@(negedge clk);rec_v=0;start_cyc=cyc;
        wait(wm[19] && wm[14:0]==0);wait(xrdy[0]);@(negedge clk);xv[0]=1;@(negedge clk);xv[0]=0;
        wait(done || fault);if(fault) $fatal(1,"SFU fault");ret_cyc=cyc;
        wait(xrdy[1]);@(negedge clk);xv[1]=1;@(negedge clk);xv[1]=0;
        wait(finished==2'b11);repeat(4) @(negedge clk);
        for(integer k=0;k<NVME;k++) if(mem[vme[k][287:256]] !== vme[k][255:0]) errors++;
        for(integer a=0;a<128;a++) for(integer g=0;g<128;g++) begin
            if(seen[0][a][g] != seen[1][a][g]) errors++;
            else if(seen[0][a][g] && captures[0][a][g] !== captures[1][a][g]) errors++;
        end
        $display("PAIR fmt=%0d SFU=%0d streamed=%0d serial=%0d beats=%0d/%0d errors=%0d",`XFMT,
            ret_cyc-start_cyc,finish_cyc[0]-start_cyc,finish_cyc[1]-start_cyc,beats[0],beats[1],errors);
        if(errors || beats[0]==0) $fatal(1,"SFU_XPAIR FAIL");
        $display("SFU_XPAIR PASS");$finish;
    end
endmodule
