`timescale 1ns/1ps
`default_nettype none
// QUANT transport r3 (OWN-QDQ 2026-10-18): the controller latency becomes a STRAP instead of a parameter.
//
// Why: in the d4g split (ot_hgi_qdq_host_split_r2) the controller's read round trip RLI and write commit WCI are
//   RLI = RL (VM bank latency at the LG pins) + 4 (LG r2 rq +2 / rr +2) + 2*XR (die relay stages per direction between
//         the bank-pair groups quant_NW<k> and quant_NW_xp, equal on all four pairs)
//   WCI = WC + 2 (LG r2 wq) + XR
// and XR / RL are die-geometry facts (relay layer, landing step, the hb_idx__nwsh share2 rebind: RL 7 -> 9) that change
// between GEN iterations.  A parameter would force a re-close of the hard ctl tile on every change; here the tile is
// closed ONCE for every RLI <= NPMAX-2 and WCI <= WCMAX, and the die ties the two straps (selector ties, constant for
// the life of the die, like an ID strap).  Each strap bit is registered at its pin (one flop, its only load), so no
// case analysis is needed at the die: the strap -> tap-select paths are ordinary reg -> reg paths.
//
//   ot_hgi_qdq_transport_ctl_s    the ot_hgi_qdq_transport_ctl controller with strap-selected taps on the command
//                                 pipelines (vp/lp/sp/dp/hp at NP-1, sp at NP-3) and the commit pipelines (donep/lastp
//                                 at WC-1).  With rl_cfg == RL and wc_cfg == WC it is cycle for cycle the parameter
//                                 controller (tb_hgi_qdq_host_split_r2_lockstep proves it against the monolith).
//                                 An out-of-range strap raises the sticky fault (no silent alias).
//   ot_hgi_qdq_transport_ctl_r3   pin capture registers on every cmd_* bit and both straps (as ctl_r2) + the local
//                                 reset relay (as ctl_r2): +1 edge on the whole controller, exactly ctl_r2.
//   ot_hgi_qdq_static_transport_split_r3  wires-only parent of ctl_r3 + the closed rslice / wslice masters; RLI/WCI are
//                                 parameters of this soft parent only (they become the strap ties).
// No ready, credit or arbitration anywhere; fixed calendar edges only.

module ot_hgi_qdq_transport_ctl_s #(
    parameter integer NPMAX=48, WCMAX=32, DL=25, MUT=0
)(
    input wire clk, rst_n,
    input wire [5:0] rl_cfg,            // RLI: read round trip at the controller (NP = RLI + 2)
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
    localparam integer ND=DL+1;
    // tap indices (straps are static; registered at the ctl_r3 pins)
    wire [6:0] np = {1'b0,rl_cfg} + 7'd2;
    wire [6:0] t1 = np - 7'd1;          // NP-1
    wire [6:0] t3 = np - 7'd3;          // NP-3
    wire [5:0] w1 = wc_cfg - 6'd1;      // WC-1
    wire cfg_bad = (rl_cfg < 6'd1) || (np > 7'(NPMAX)) || (wc_cfg < 6'd2) || (wc_cfg > 6'(WCMAX));
    reg vo_q,qfault_q,decode_fault_q;
    reg [7:0] rr_v_q;
    reg [2:0] write_bank_local;
    always @(posedge clk) rr_v_q<=rr_v;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin vo_q<=0;qfault_q<=0;decode_fault_q<=0;end
        else begin vo_q<=vo;qfault_q<=qfault;decode_fault_q<=decode_fault;end
    reg [NPMAX-1:0] vp, lp;
    reg [15:0] sp [0:NPMAX-1], dp [0:NPMAX-1];
    reg [13:0] hp [0:NPMAX-1];
    reg gl;
    reg [15:0] gd;
    reg [ND-1:0] dv, dl;
    reg [WCMAX-1:0] donep,lastp;
    reg [15:0] dst [0:ND-1];
    reg [7:0] expected;
    reg bad;
    // the taps (variable index = strap-selected mux)
    wire vp_t = vp[t1[5:0]];
    wire lp_t = lp[t1[5:0]];
    wire [15:0] sp_t = sp[t1[5:0]];
    wire [15:0] dp_t = dp[t1[5:0]];
    wire [13:0] hp_t = hp[t1[5:0]];
    wire [15:0] sp_t3 = sp[t3[5:0]];
    wire done_t = donep[w1[4:0]];
    wire last_t = lastp[w1[4:0]];
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
    // Constant-index request and write-header packing (as the monolith's constant_port_pack).
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
        sp[0]<=cmd_src; dp[0]<=cmd_dst; hp[0]<={cmd_op,cmd_block};
        for(integer k=1;k<NPMAX;k=k+1) begin sp[k]<=sp[k-1]; dp[k]<=dp[k-1]; hp[k]<=hp[k-1]; end
        gd<=dp_t; dec_header<='0; dec_header[127:124]<=4'd4;
        dec_header[123:118]<=hp_t[13:8]; dec_header[71:64]<=hp_t[7:0];
        dst[0]<=gd;
        for(integer k=1;k<ND;k=k+1) dst[k]<=dst[k-1];
        rsel<=sp_t3[2:0];                // == sp[NP-2] one edge later (slice read_bank_local)
        wsel<=dst[ND-3][2:0];            // == dst[ND-2] one edge later (slice write_bank_local)
        write_bank_local<=dst[ND-2][2:0];
    end
    initial if(DL<2 || NPMAX<4 || NPMAX>64 || WCMAX<2 || WCMAX>32) $fatal(1,"invalid strap QDQ controller sizing");
endmodule

module ot_hgi_qdq_transport_ctl_r3 #(
    parameter integer NPMAX=48, WCMAX=32, DL=25, MUT=0
)(
    input wire clk, rst_n,
    input wire [5:0] rl_cfg, wc_cfg,
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
    // local reset relay (as ctl_r2): the port drives only the relay
    (* async_reg = "true" *) reg rst_s1, rst_s2;
    reg rn;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rst_s1 <= 1'b0; rst_s2 <= 1'b0; rn <= 1'b0; end
        else begin rst_s1 <= 1'b1; rst_s2 <= rst_s1; rn <= rst_s2; end
    // pin capture registers (the only load of each cmd / strap pin)
    reg cv_q;
    reg [5:0] op_q; reg [7:0] blk_q; reg [15:0] src_q, dst_q; reg last_q;
    reg [5:0] rl_q, wc_q;
    always @(posedge clk or negedge rn)
        if(!rn) cv_q<=1'b0; else cv_q<=cmd_v;
    always @(posedge clk) begin op_q<=cmd_op; blk_q<=cmd_block; src_q<=cmd_src; dst_q<=cmd_dst; last_q<=cmd_last;
        rl_q<=rl_cfg; wc_q<=wc_cfg; end
    ot_hgi_qdq_transport_ctl_s #(.NPMAX(NPMAX),.WCMAX(WCMAX),.DL(DL),.MUT(MUT)) u_ctl(
        .clk(clk),.rst_n(rn),.rl_cfg(rl_q),.wc_cfg(wc_q),.cmd_v(cv_q),.cmd_op(op_q),.cmd_block(blk_q),.cmd_src(src_q),
        .cmd_dst(dst_q),.cmd_last(last_q),.rq(rq),.rr_v(rr_v),.wq_v(wq_v),.wq_addr(wq_addr),.wq_mask(wq_mask),
        .rsel(rsel),.wsel(wsel),.beat_done(beat_done),.record_done(record_done),.fault(fault),
        .dec_v(dec_v),.dec_header(dec_header),.vo(vo),.qfault(qfault),.decode_fault(decode_fault));
endmodule

module ot_hgi_qdq_static_transport_split_r3 #(
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
    initial if(NS*NW!=8 || RLI<1 || RLI>46 || WCI<2 || WCI>32) $fatal(1,"transport split r3: NS must divide 8, RLI 1..46, WCI 2..32");
    wire [7:0] rr_v, wq_v; wire [8*16-1:0] wq_addr; wire [8*8-1:0] wq_mask; wire [2:0] rsel, wsel;
    for(genvar b=0;b<8;b=b+1)begin: bank_bits
        assign rr_v[b]=rr[b*257+256];
        assign wq[b*281+280]=wq_v[b];
        assign wq[b*281+264+:16]=wq_addr[b*16+:16];
        assign wq[b*281+:8]=wq_mask[b*8+:8];
    end
    ot_hgi_qdq_transport_ctl_r3 #(.DL(DL),.MUT(MUT)) ctl(
        .clk(clk),.rst_n(rst_n),.rl_cfg(6'(RLI)),.wc_cfg(6'(WCI)),.cmd_v(cmd_v),.cmd_op(cmd_op),.cmd_block(cmd_block),
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
