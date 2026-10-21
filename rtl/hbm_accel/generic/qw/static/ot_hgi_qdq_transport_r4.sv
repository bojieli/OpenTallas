`timescale 1ns/1ps
`default_nettype none
// QUANT transport r4 (HBM-QDQ8 2026-10-20): the strap controller of r3 with a DEEP read round trip.
//
// Why: the GEN2e4 r11 die (functional_bind_l24.json lat_rows) needs hb_quant_NW.RL = 54 at the block pins
//   (ref 7 + hb_idx__nwsh share2 excess 33 + 14 relay lanes), and the r12 station plan (plan-um 300) adds ~27 % more
//   stations.  The split controller is strapped to RLI = RL + 4 + 2*XR, so RLI >= 58 today, while ctl_r3 only accepts
//   RLI <= NPMAX-2 = 46 (out of range = sticky fault).  Raising NPMAX on r3 would grow its command pipeline
//   (sp/dp/hp, 46 bits per stage) to > 5 kb of flops; the safe-design storage rule puts that in an SRAM ring.
//
//   ot_hgi_qdq_transport_ctl_s4   ctl_s of r3 with the 46-bit command metadata pipeline (sp/dp/hp) held in ONE 1R1W
//                                 SRAM macro ot_sram_1r1w_128x64_m1_p192 used as a 128-entry ring: every cycle the
//                                 current {hp,dp,sp} is written at wp and the entry written NP-2 edges earlier is read
//                                 (read address = wp + 1 - rl_cfg, strap-static).  rd_out is the r3 tap sp[NP-3]
//                                 (used for rsel); two flop stages turn it into the r3 tap [NP-1] (sp/dp/hp).  The 1-bit
//                                 valid / last pipelines vp/lp stay reset flops (128 deep, strap-selected tap) so no
//                                 SRAM content is ever qualified by itself.  Cycle-for-cycle the r3 controller for every
//                                 strap both accept; range RLI 2..126 (NP 4..128), WCI 2..63 (WCMAX 64).
//   ot_hgi_qdq_transport_ctl_r4   ctl_r3's pin capture registers (every cmd_* and strap bit) + local reset relay.
//   ot_hgi_qdq_static_transport_split_r4  wires-only parent of ctl_r4 + the closed rslice / wslice masters.
// No ready, credit or arbitration anywhere; fixed calendar edges only.

module ot_hgi_qdq_transport_ctl_s4 #(
    parameter integer WCMAX=64, DL=25, MUT=0   // MUT (bench): 2 = write bank crossed (as r3), 3 = ring read one entry late
)(
    input wire clk, rst_n,
    input wire [6:0] rl_cfg,            // RLI: read round trip at the controller (NP = RLI + 2)
    input wire [5:0] wc_cfg,            // WCI: write commit edges after the write leaves the controller
    input wire cmd_v,
    input wire [5:0] cmd_op,
    input wire [7:0] cmd_block,
    input wire [15:0] cmd_src, cmd_dst,
    input wire cmd_last,
    output reg [8*17-1:0] rq,
    input wire [7:0] rr_v,
    output reg [7:0] wq_v,
    output reg [8*16-1:0] wq_addr,
    output reg [8*8-1:0] wq_mask,
    output reg [2:0] rsel, wsel,
    output reg beat_done, record_done,
    output reg fault,
    output reg dec_v,
    output reg [127:0] dec_header,
    input wire vo, qfault, decode_fault
);
    localparam integer NPMAX=128;       // ring depth = macro words
    localparam integer ND=DL+1;
    wire [7:0] np = {1'b0,rl_cfg} + 8'd2;
    wire [6:0] t1 = rl_cfg + 7'd1;      // NP-1 (valid when cfg ok)
    wire [5:0] w1 = wc_cfg - 6'd1;      // WC-1
    wire cfg_bad = (rl_cfg < 7'd2) || (np > 8'(NPMAX)) || (wc_cfg < 6'd2) || (7'(wc_cfg) > 7'(WCMAX));
    reg vo_q,qfault_q,decode_fault_q;
    reg [7:0] rr_v_q;
    reg [2:0] write_bank_local;
    always @(posedge clk) rr_v_q<=rr_v;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin vo_q<=0;qfault_q<=0;decode_fault_q<=0;end
        else begin vo_q<=vo;qfault_q<=qfault;decode_fault_q<=decode_fault;end
    reg [NPMAX-1:0] vp, lp;
    reg gl;
    reg [15:0] gd;
    reg [ND-1:0] dv, dl;
    reg [WCMAX-1:0] donep,lastp;
    reg [15:0] dst [0:ND-1];
    reg [7:0] expected;
    reg bad;
    // ---- command metadata ring (SRAM) -------------------------------------------------------------
    // write at wp every edge; rd_out in cycle n = entry of cycle n-rl_cfg == r3 sp/dp/hp[NP-3] (rl_cfg >= 2: never the entry written at the same edge)
    reg [6:0] wp, ra;
    wire [63:0] rd;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin wp<='0; ra<='0; end
        else begin wp<=wp+7'd1; ra<=wp+7'd2-rl_cfg+(MUT==3?7'd1:7'd0); end   // ra(n) = wp(n) + 1 - rl_cfg: rd(n+1) = entry written at edge n+1-rl_cfg
    ot_sram_1r1w_128x64_m1_p192 ring(
        .clk(clk),.r_ce_in(1'b1),.r_addr_in(ra),.rd_out(rd),
        .w_ce_in(1'b1),.w_addr_in(wp),.wd_in({18'd0,cmd_op,cmd_block,cmd_dst,cmd_src}),.w_mask_in({64{1'b1}}));
    reg [45:0] m1, m2;                  // rd delayed: m2 == r3 tap [NP-1]
    always @(posedge clk) begin m1<=rd[45:0]; m2<=m1; end
    wire vp_t = vp[t1];
    wire lp_t = lp[t1];
    wire [15:0] sp_t = m2[15:0];
    wire [15:0] dp_t = m2[31:16];
    wire [13:0] hp_t = m2[45:32];
    wire [15:0] sp_t3 = rd[15:0];
    wire done_t = donep[w1];
    wire last_t = lastp[w1];
    always @* begin
        expected='0;
        for(integer t=0;t<4;t=t+1) if(vp_t) expected[(sp_t[2:0]+t)&7]=1'b1;
        bad=1'b0;
        for(integer t=0;t<8;t=t+1) if(rr_v_q[t]!=expected[t]) bad=1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            vp<='0; lp<='0; dec_v<=0; gl<=0;
            dv<='0; dl<='0; donep<='0; lastp<='0; beat_done<=0; record_done<=0; fault<=0;
        end else begin
            vp<={vp[NPMAX-2:0],cmd_v}; lp<={lp[NPMAX-2:0],cmd_last};
            dv<={dv[ND-2:0],dec_v}; dl<={dl[ND-2:0],gl};
            dec_v<=vp_t; gl<=lp_t;
            if(cfg_bad || bad || decode_fault_q || (vo_q && qfault_q) || vo_q!=dv[ND-1]) fault<=1;
            if(cmd_v && (!(cmd_op==4 || cmd_op==5 || (cmd_op==6 && cmd_block==16)) ||
                cmd_src[15:3] != ((cmd_src+16'd3)>>3) ||
                cmd_dst[15:3] != ((cmd_dst+16'd3)>>3))) fault<=1;
            donep<={donep[WCMAX-2:0],dv[ND-1]};
            lastp<={lastp[WCMAX-2:0],dv[ND-1]&&dl[ND-1]};
            beat_done<=done_t; record_done<=last_t;
        end
    end
    reg [8*17-1:0] rq_next;
    reg [7:0] wv_next;
    reg [8*16-1:0] wa_next;
    reg [8*8-1:0] wm_next;
    always @* begin
        rq_next='0; wv_next='0; wa_next='0; wm_next='0;
        for(integer b=0;b<8;b=b+1)
            for(integer k=0;k<4;k=k+1)begin
                if(((int'(cmd_src[2:0])+k)&7)==b) rq_next[b*17+:17]={cmd_v,cmd_src+16'(k)};
                if((((int'(write_bank_local)+k)&7)^(MUT==2?1:0))==b)begin
                    wv_next[b]=dv[ND-1]; wa_next[b*16+:16]=dst[ND-1]+16'(k); wm_next[b*8+:8]=8'hff;
                end
            end
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin for(integer k=0;k<8;k=k+1) rq[k*17+16]<=0; wq_v<='0; end
        else begin for(integer k=0;k<8;k=k+1) rq[k*17+16]<=rq_next[k*17+16]; wq_v<=wv_next; end
    always @(posedge clk) begin
        for(integer k=0;k<8;k=k+1) rq[k*17+:16]<=rq_next[k*17+:16];
        wq_addr<=wa_next; wq_mask<=wm_next;
        gd<=dp_t; dec_header<='0; dec_header[127:124]<=4'd4;
        dec_header[123:118]<=hp_t[13:8]; dec_header[71:64]<=hp_t[7:0];
        dst[0]<=gd;
        for(integer k=1;k<ND;k=k+1) dst[k]<=dst[k-1];
        rsel<=sp_t3[2:0];
        wsel<=dst[ND-3][2:0];
        write_bank_local<=dst[ND-2][2:0];
    end
    initial if(DL<2 || WCMAX<2 || WCMAX>64) $fatal(1,"invalid strap QDQ controller r4 sizing");
endmodule

module ot_hgi_qdq_transport_ctl_r4 #(
    parameter integer WCMAX=64, DL=25, MUT=0
)(
    input wire clk, rst_n,
    input wire [6:0] rl_cfg,
    input wire [5:0] wc_cfg,
    input wire cmd_v,
    input wire [5:0] cmd_op,
    input wire [7:0] cmd_block,
    input wire [15:0] cmd_src, cmd_dst,
    input wire cmd_last,
    output wire [8*17-1:0] rq,
    input wire [7:0] rr_v,
    output wire [7:0] wq_v,
    output wire [8*16-1:0] wq_addr,
    output wire [8*8-1:0] wq_mask,
    output wire [2:0] rsel, wsel,
    output wire beat_done, record_done,
    output wire fault,
    output wire dec_v,
    output wire [127:0] dec_header,
    input wire vo, qfault, decode_fault
);
    (* async_reg = "true" *) reg rst_s1, rst_s2;
    reg rn;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rst_s1 <= 1'b0; rst_s2 <= 1'b0; rn <= 1'b0; end
        else begin rst_s1 <= 1'b1; rst_s2 <= rst_s1; rn <= rst_s2; end
    reg cv_q;
    reg [5:0] op_q; reg [7:0] blk_q; reg [15:0] src_q, dst_q; reg last_q;
    reg [6:0] rl_q; reg [5:0] wc_q;
    always @(posedge clk or negedge rn)
        if(!rn) cv_q<=1'b0; else cv_q<=cmd_v;
    always @(posedge clk) begin op_q<=cmd_op; blk_q<=cmd_block; src_q<=cmd_src; dst_q<=cmd_dst; last_q<=cmd_last;
        rl_q<=rl_cfg; wc_q<=wc_cfg; end
    ot_hgi_qdq_transport_ctl_s4 #(.WCMAX(WCMAX),.DL(DL),.MUT(MUT)) u_ctl(
        .clk(clk),.rst_n(rn),.rl_cfg(rl_q),.wc_cfg(wc_q),.cmd_v(cv_q),.cmd_op(op_q),.cmd_block(blk_q),.cmd_src(src_q),
        .cmd_dst(dst_q),.cmd_last(last_q),.rq(rq),.rr_v(rr_v),.wq_v(wq_v),.wq_addr(wq_addr),.wq_mask(wq_mask),
        .rsel(rsel),.wsel(wsel),.beat_done(beat_done),.record_done(record_done),.fault(fault),
        .dec_v(dec_v),.dec_header(dec_header),.vo(vo),.qfault(qfault),.decode_fault(decode_fault));
endmodule

module ot_hgi_qdq_static_transport_split_r4 #(
    parameter integer RLI=11,          // controller read round trip (strap tie)
    parameter integer WCI=6,           // controller write commit (strap tie)
    parameter integer DL=25,
    parameter integer MUT=0,
    parameter integer NS=4
) (
    input wire clk, rst_n,
    input wire cmd_v,
    input wire [5:0] cmd_op,
    input wire [7:0] cmd_block,
    input wire [15:0] cmd_src, cmd_dst,
    input wire cmd_last,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire [8*281-1:0] wq,
    output wire beat_done, record_done,
    output wire fault,
    output wire dec_v,
    output wire [127:0] dec_header,
    output wire [1023:0] dec_x,
    input wire vo,qfault,decode_fault,
    input wire [511:0] y
);
    localparam integer NW=8/NS;
    initial if(NS*NW!=8 || RLI<2 || RLI>126 || WCI<2 || WCI>63) $fatal(1,"transport split r4: NS must divide 8, RLI 2..126, WCI 2..63");
    wire [7:0] rr_v, wq_v; wire [8*16-1:0] wq_addr; wire [8*8-1:0] wq_mask; wire [2:0] rsel, wsel;
    for(genvar b=0;b<8;b=b+1)begin: bank_bits
        assign rr_v[b]=rr[b*257+256];
        assign wq[b*281+280]=wq_v[b];
        assign wq[b*281+264+:16]=wq_addr[b*16+:16];
        assign wq[b*281+:8]=wq_mask[b*8+:8];
    end
    ot_hgi_qdq_transport_ctl_r4 #(.DL(DL),.MUT(MUT)) ctl(
        .clk(clk),.rst_n(rst_n),.rl_cfg(7'(RLI)),.wc_cfg(6'(WCI)),.cmd_v(cmd_v),.cmd_op(cmd_op),.cmd_block(cmd_block),
        .cmd_src(cmd_src),.cmd_dst(cmd_dst),.cmd_last(cmd_last),.rq(rq),.rr_v(rr_v),.wq_v(wq_v),.wq_addr(wq_addr),
        .wq_mask(wq_mask),.rsel(rsel),.wsel(wsel),.beat_done(beat_done),.record_done(record_done),.fault(fault),
        .dec_v(dec_v),.dec_header(dec_header),.vo(vo),.qfault(qfault),.decode_fault(decode_fault));
    for(genvar s=0;s<NS;s=s+1)begin: slice
        wire [8*NW*32-1:0] rr_w; wire [4*NW*32-1:0] gx_w;
        wire [4*NW*16-1:0] y_w; wire [8*NW*16-1:0] wq_w;
        for(genvar j=0;j<NW;j=j+1)begin: word_
            for(genvar b=0;b<8;b=b+1)begin: bank
                assign rr_w[(b*NW+j)*32+:32]=rr[b*257+(s*NW+j)*32+:32];
                assign wq[b*281+8+(s*NW+j)*32+:32]={wq_w[(b*NW+j)*16+:16],16'd0};
            end
            for(genvar k=0;k<4;k=k+1)begin: lane
                assign dec_x[k*256+(s*NW+j)*32+:32]=gx_w[(k*NW+j)*32+:32];
                assign y_w[(k*NW+j)*16+:16]=y[(k*8+s*NW+j)*16+:16];
            end
        end
        ot_hgi_qdq_transport_rslice #(.NW(NW),.MUT(MUT)) rslice(.clk(clk),.rr_w(rr_w),.rsel(rsel),.gx_w(gx_w));
        ot_hgi_qdq_transport_wslice #(.NW(NW),.MUT(MUT)) wslice(.clk(clk),.y_w(y_w),.wsel(wsel),.wq_w(wq_w));
    end
endmodule
`default_nettype wire
