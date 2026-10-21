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
//   ot_hgi_qdq_transport_ctl_s4   ctl_s of r3 with NO strap-selected taps (gate 1 native census: the 128:1 / 64:1 tap
//                                 muxes put 167-220 loads on each strap flop).  Ring A = ONE ot_sram_1r1w_128x64_m1_p192:
//                                 every edge {lp,vp,hp,dp,sp} is written at wp, read address wp + 1 - rl_cfg, so rd_out
//                                 is the r3 tap [NP-3] (rsel) and two flop stages give the r3 tap [NP-1].  Ring B = ONE
//                                 ot_sram_1r1w_64x16_m1 for the commit pipeline {done,last} (r3 donep/lastp [WC-1]).
//                                 SRAM content is qualified by a reset edge counter (entries older than reset release
//                                 read as r3's reset zeros), so power-up content never matters.  Bank packing uses kept
//                                 per-bank copies of the 3-bit bank bases (census: src/dst low bits 33-70 loads); four
//                                 ot_rst_relay leaves (census: one relay flop drove 475 resets).  Cycle-for-cycle the r3
//                                 controller for every strap both accept; range RLI 2..126 (NP 4..128), WCI 2..63.
//   ot_hgi_qdq_transport_ctl_r4   ctl_r3's pin capture registers (every cmd_* and strap bit) + local reset relay.
//   ot_hgi_qdq_static_transport_split_r4  wires-only parent of ctl_r4 + the closed rslice / wslice masters.
// No ready, credit or arbitration anywhere; fixed calendar edges only.

module ot_hgi_qdq_transport_ctl_s4 #(
    parameter integer DL=25, MUT=0   // MUT (bench): 2 = write bank crossed (as r3), 3 = ring A read one entry late
)(
    input wire clk,
    input wire [2:0] rst_n,             // regional resets (ot_rst_relay leaves): 0 ring/count, 1 decode pipe, 2 outputs/fault
    input wire [6:0] rl_cfg,            // RLI: read round trip at the controller (NP = RLI + 2)
    input wire [5:0] wc_cfg,            // WCI: write commit edges after the write leaves the controller
    input wire cmd_v,
    input wire [5:0] cmd_op,
    input wire [7:0] cmd_block,
    input wire [15:0] cmd_src, cmd_dst,
    input wire [8*3-1:0] cmd_src_lo,    // 8 kept copies of cmd_src[2:0] (one per bank request port)
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
    localparam integer ND=DL+1;
    wire [7:0] np = {1'b0,rl_cfg} + 8'd2;
    wire cfg_bad = (rl_cfg < 7'd2) || (np > 8'd128) || (wc_cfg < 6'd2);
    reg vo_q,qfault_q,decode_fault_q;
    reg [7:0] rr_v_q;
    always @(posedge clk) rr_v_q<=rr_v;
    always @(posedge clk or negedge rst_n[2])
        if(!rst_n[2])begin vo_q<=0;qfault_q<=0;decode_fault_q<=0;end
        else begin vo_q<=vo;qfault_q<=qfault;decode_fault_q<=decode_fault;end
    // ---- edge counter since reset release: masks ring entries written before release (r3: vp/lp/donep reset to 0)
    reg [7:0] cnt;
    always @(posedge clk or negedge rst_n[0])
        if(!rst_n[0]) cnt<='0; else if(cnt!=8'hff) cnt<=cnt+8'd1;
    reg warm_a, warm_b;                 // registered: cnt >= NP / cnt >= WC one edge ahead
    always @(posedge clk or negedge rst_n[0])
        if(!rst_n[0]) begin warm_a<=0; warm_b<=0; end
        else begin warm_a<=({1'b0,cnt}+9'd1)>={1'b0,np}; warm_b<=({1'b0,cnt}+9'd1)>={3'b0,wc_cfg}; end   // 9-bit: no wrap at cnt 255
    // ---- ring A (128 x 64 SRAM): {lp,vp,hp,dp,sp} of every edge; rd in cycle n = entry of cycle n-rl_cfg (= r3 tap NP-3)
    reg [6:0] wp, ra;                   // free running: only their difference matters
    wire [63:0] rd;
    always @(posedge clk) begin wp<=wp+7'd1; ra<=wp+7'd2-rl_cfg+(MUT==3?7'd1:7'd0); end
    ot_sram_1r1w_128x64_m1_p192 ring(
        .clk(clk),.r_ce_in(1'b1),.r_addr_in(ra),.rd_out(rd),
        .w_ce_in(1'b1),.w_addr_in(wp),.wd_in({16'd0,cmd_last,cmd_v,cmd_op,cmd_block,cmd_dst,cmd_src}),.w_mask_in({64{1'b1}}));
    reg [47:0] m1, m2;                  // m2 == r3 tap NP-1
    always @(posedge clk) begin m1<=rd[47:0]; m2<=m1; end
    wire vp_t = m2[46] && warm_a;
    wire lp_t = m2[47];
    wire [15:0] sp_t = m2[15:0];
    wire [15:0] dp_t = m2[31:16];
    wire [13:0] hp_t = m2[45:32];
    // ---- decode / write pipeline (DL fixed)
    reg gl;
    reg [15:0] gd;
    reg [ND-1:0] dv, dl;
    reg [15:0] dst [0:ND-1];
    (* keep="true", dont_touch="true" *) reg [2:0] wbl [0:7];   // per-bank copies of dst[ND-1][2:0]
    reg [7:0] expected;
    reg bad;
    always @* begin
        expected='0;
        for(integer t=0;t<4;t=t+1) if(vp_t) expected[(sp_t[2:0]+t)&7]=1'b1;
        bad=1'b0;
        for(integer t=0;t<8;t=t+1) if(rr_v_q[t]!=expected[t]) bad=1'b1;
    end
    always @(posedge clk or negedge rst_n[1])
        if(!rst_n[1]) begin dv<='0; dec_v<=0; end
        else begin dv<={dv[ND-2:0],dec_v}; dec_v<=vp_t; end
    always @(posedge clk) begin dl<={dl[ND-2:0],gl}; gl<=lp_t; end
    // ---- ring B (64 x 16 SRAM): {done,last} commit pipeline; rdb in cycle n = entry of cycle n-wc_cfg (= r3 donep[WC-1])
    reg [5:0] rb;
    wire [15:0] rdb;
    always @(posedge clk) rb<=wp[5:0]+6'd2-wc_cfg;
    ot_sram_1r1w_64x16_m1 commit(
        .clk(clk),.r_ce_in(1'b1),.r_addr_in(rb),.rd_out(rdb),
        .w_ce_in(1'b1),.w_addr_in(wp[5:0]),.wd_in({14'd0,dv[ND-1]&&dl[ND-1],dv[ND-1]}),.w_mask_in({16{1'b1}}));
    always @(posedge clk or negedge rst_n[2]) begin
        if(!rst_n[2]) begin beat_done<=0; record_done<=0; fault<=0; end
        else begin
            if(cfg_bad || bad || decode_fault_q || (vo_q && qfault_q) || vo_q!=dv[ND-1]) fault<=1;
            if(cmd_v && (!(cmd_op==4 || cmd_op==5 || (cmd_op==6 && cmd_block==16)) ||
                cmd_src[15:3] != ((cmd_src+16'd3)>>3) ||
                cmd_dst[15:3] != ((cmd_dst+16'd3)>>3))) fault<=1;
            beat_done<=rdb[0]&&warm_b; record_done<=rdb[1]&&warm_b;
        end
    end
    // ---- per-bank request / write header packing (bank b: word k = (b - base) & 7 when < 4)
    reg [8*17-1:0] rq_next;
    reg [7:0] wv_next;
    reg [8*16-1:0] wa_next;
    reg [8*8-1:0] wm_next;
    reg [2:0] kr, kw;
    always @* begin
        rq_next='0; wv_next='0; wa_next='0; wm_next='0; kr='0; kw='0;
        for(integer b=0;b<8;b=b+1) begin
            kr=3'(b)-cmd_src_lo[b*3+:3];
            if(kr<3'd4) rq_next[b*17+:17]={cmd_v,{cmd_src[15:3],cmd_src_lo[b*3+:3]}+16'(kr)};
            kw=(3'(b)^(MUT==2?3'd1:3'd0))-wbl[b];
            if(kw<3'd4) begin wv_next[b]=dv[ND-1]; wa_next[b*16+:16]={dst[ND-1][15:3],wbl[b]}+16'(kw); wm_next[b*8+:8]=8'hff; end
        end
    end
    always @(posedge clk or negedge rst_n[2])
        if(!rst_n[2]) begin for(integer k=0;k<8;k=k+1) rq[k*17+16]<=0; wq_v<='0; end
        else begin for(integer k=0;k<8;k=k+1) rq[k*17+16]<=rq_next[k*17+16]; wq_v<=wv_next; end
    always @(posedge clk) begin
        for(integer k=0;k<8;k=k+1) rq[k*17+:16]<=rq_next[k*17+:16];
        wq_addr<=wa_next; wq_mask<=wm_next;
        gd<=dp_t; dec_header<='0; dec_header[127:124]<=4'd4;
        dec_header[123:118]<=hp_t[13:8]; dec_header[71:64]<=hp_t[7:0];
        dst[0]<=gd;
        for(integer k=1;k<ND;k=k+1) dst[k]<=dst[k-1];
        rsel<=rd[2:0];                   // r3 sp[NP-3]
        wsel<=dst[ND-3][2:0];
        for(integer b=0;b<8;b=b+1) wbl[b]<=dst[ND-2][2:0];
    end
    initial if(DL<4) $fatal(1,"invalid strap QDQ controller r4 sizing");
`ifdef QDQ8_DEBUG
    always @(posedge clk) if(rst_n[2] && !fault && (cfg_bad || bad || decode_fault_q || (vo_q && qfault_q) || vo_q!=dv[ND-1]))
        $display("QDQ8_DEBUG t=%0t cfg_bad=%b bad=%b exp=%b rr_v_q=%b vp_t=%b sp_t=%h dfq=%b vo_q=%b qf=%b dv=%b warm=%b cnt=%0d wp=%0d ra=%0d np=%0d",
            $time,cfg_bad,bad,expected,rr_v_q,vp_t,sp_t,decode_fault_q,vo_q,qfault_q,dv[ND-1],warm_a,cnt,wp,ra,np);
    always @(posedge clk) if(rst_n[2] && cmd_v) $display("QDQ8_CMD t=%0t src=%h wp=%0d",$time,cmd_src,wp);
    always @(posedge clk) if(rst_n[2] && |rr_v) $display("QDQ8_RR t=%0t rr_v=%b vp_t=%b m2v=%b",$time,rr_v,vp_t,m2[46]);
`endif
endmodule

module ot_hgi_qdq_transport_ctl_r4 #(
    parameter integer DL=25, MUT=0
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
    // local reset relay: the port drives only the relay; 4 kept regional leaves (release 3 edges, as ctl_r3)
    wire [3:0] rn;
    ot_rst_relay #(.REGIONS(4),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
    // pin capture registers (the only load of each cmd / strap pin, plus the per-bank cmd_src[2:0] copies)
    reg cv_q;
    reg [5:0] op_q; reg [7:0] blk_q; reg [15:0] src_q, dst_q; reg last_q;
    (* keep="true", dont_touch="true" *) reg [2:0] src_lo_q [0:7];
    reg [6:0] rl_q; reg [5:0] wc_q;
    always @(posedge clk or negedge rn[3])
        if(!rn[3]) cv_q<=1'b0; else cv_q<=cmd_v;
    always @(posedge clk) begin op_q<=cmd_op; blk_q<=cmd_block; src_q<=cmd_src; dst_q<=cmd_dst; last_q<=cmd_last;
        rl_q<=rl_cfg; wc_q<=wc_cfg; for(integer b=0;b<8;b=b+1) src_lo_q[b]<=cmd_src[2:0]; end
    wire [8*3-1:0] src_lo;
    for(genvar b=0;b<8;b=b+1) begin: g_lo assign src_lo[b*3+:3]=src_lo_q[b]; end
    ot_hgi_qdq_transport_ctl_s4 #(.DL(DL),.MUT(MUT)) u_ctl(
        .clk(clk),.rst_n(rn[2:0]),.rl_cfg(rl_q),.wc_cfg(wc_q),.cmd_v(cv_q),.cmd_op(op_q),.cmd_block(blk_q),.cmd_src(src_q),
        .cmd_dst(dst_q),.cmd_src_lo(src_lo),.cmd_last(last_q),.rq(rq),.rr_v(rr_v),.wq_v(wq_v),.wq_addr(wq_addr),.wq_mask(wq_mask),
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
