`timescale 1ns/1ps
`default_nettype none
// QUANT transport split (H-ATTQ 2026-10-15). Structural successor of the registered (IO_REGS=1) monolith
// ot_hgi_qdq_static_transport, whose single CTS root spanned the 453.6 x 345.6 um face-pinned slot at 2 % util
// (r3 gate: 5,895 sinks, TT insertion 555.6 ps, spread 62.7 ps). The datapath is bit-sliced by 32-bit word:
// read word t of every lane only ever reads word t of some bank, write word t of every bank only ever takes word t
// of some lane. So NS independent word slices (read gather + write scatter) and one control leaf replace the
// monolith; each leaf is a small, dense, separately rooted tile. The bank selects are registered one edge earlier
// in the control leaf (sp[NP-3] / dst[ND-3]) and re-registered in each slice, so every operation edge is identical to
// the monolith: zero added cycles, same fixed calendar, no ready/credit. Only validity bits are reset (control leaf).
//
//   ot_hgi_qdq_transport_ctl         command pipelines, rq, wq header (valid/address/mask), dec_v/header, fault
//   ot_hgi_qdq_transport_rslice      rr word capture + 8:1 constant-bank gather for its words (no reset)
//   ot_hgi_qdq_transport_wslice      y word capture + 4->8 constant-bank scatter for its words (no reset)
//   ot_hgi_qdq_static_transport_split  wires-only parent, same ports/parameters as the monolith (IO_REGS=1 only)

module ot_hgi_qdq_transport_ctl #(
    parameter integer RL=7, DL=25, WC=4, MUT=0
)(
    input wire clk, rst_n,
    input wire cmd_v,
    input wire [5:0] cmd_op,
    input wire [7:0] cmd_block,
    input wire [15:0] cmd_src, cmd_dst,
    input wire cmd_last,
    output reg [8*17-1:0] rq,
    input wire [7:0] rr_v,            // rr[b*257+256] of the 8 banks
    output reg [7:0] wq_v,            // wq[b*281+280]
    output reg [8*16-1:0] wq_addr,    // wq[b*281+264 +: 16]
    output reg [8*8-1:0] wq_mask,     // wq[b*281 +: 8]
    output reg [2:0] rsel, wsel,      // bank selects, one edge ahead of the slices' local copies
    output reg beat_done, record_done,
    output reg fault,
    output reg dec_v,
    output reg [127:0] dec_header,
    input wire vo, qfault, decode_fault
);
    localparam integer NP=RL+2;   // RL+1+IO_REGS
    localparam integer ND=DL+1;
    reg vo_q,qfault_q,decode_fault_q;
    reg [7:0] rr_v_q;
    reg [2:0] write_bank_local;
    always @(posedge clk) rr_v_q<=rr_v;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin vo_q<=0;qfault_q<=0;decode_fault_q<=0;end
        else begin vo_q<=vo;qfault_q<=qfault;decode_fault_q<=decode_fault;end
    reg [NP-1:0] vp, lp;
    reg [15:0] sp [0:NP-1], dp [0:NP-1];
    reg [13:0] hp [0:NP-1];
    reg gl;
    reg [15:0] gd;
    reg [ND-1:0] dv, dl;
    reg [WC-1:0] donep,lastp;
    reg [15:0] dst [0:ND-1];
    reg [7:0] expected;
    reg bad;
    always @* begin
        expected='0;
        for(integer t=0;t<4;t=t+1) if(vp[NP-1]) expected[(sp[NP-1][2:0]+t)&7]=1'b1;
        bad=1'b0;
        for(integer t=0;t<8;t=t+1) if(rr_v_q[t]!=expected[t]) bad=1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            vp<='0; lp<='0; dec_v<=0; gl<=0;
            dv<='0; dl<='0; donep<='0; lastp<='0; beat_done<=0; record_done<=0; fault<=0;
        end else begin
            vp<={vp[NP-2:0],cmd_v}; lp<={lp[NP-2:0],cmd_last};
            dv<={dv[ND-2:0],dec_v}; dl<={dl[ND-2:0],gl};
            dec_v<=vp[NP-1]; gl<=lp[NP-1];
            if(bad || decode_fault_q || (vo_q && qfault_q) || vo_q!=dv[ND-1]) fault<=1;
            if(cmd_v && (!(cmd_op==4 || cmd_op==5 || (cmd_op==6 && cmd_block==16)) ||
                cmd_src[15:3] != ((cmd_src+16'd3)>>3) ||
                cmd_dst[15:3] != ((cmd_dst+16'd3)>>3))) fault<=1;
            donep<={donep[WC-2:0],dv[ND-1]};
            lastp<={lastp[WC-2:0],dv[ND-1]&&dl[ND-1]};
            beat_done<=donep[WC-1]; record_done<=lastp[WC-1];
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
        for(integer k=1;k<NP;k=k+1) begin sp[k]<=sp[k-1]; dp[k]<=dp[k-1]; hp[k]<=hp[k-1]; end
        gd<=dp[NP-1]; dec_header<='0; dec_header[127:124]<=4'd4;
        dec_header[123:118]<=hp[NP-1][13:8]; dec_header[71:64]<=hp[NP-1][7:0];
        dst[0]<=gd;
        for(integer k=1;k<ND;k=k+1) dst[k]<=dst[k-1];
        rsel<=sp[NP-3][2:0];             // == sp[NP-2] one edge later (slice read_bank_local)
        wsel<=dst[ND-3][2:0];            // == dst[ND-2] one edge later (slice write_bank_local)
        write_bank_local<=dst[ND-2][2:0];
    end
    initial if(RL<1 || DL<2 || WC<2) $fatal(1,"invalid measured QDQ pipeline");
endmodule

// Read gather for words [W0, W0+NW): gx[k][t] <= word t of bank ((sel+k)&7)^mut, from the registered rr face.
module ot_hgi_qdq_transport_rslice #(
    parameter integer NW=2, MUT=0
)(
    input wire clk,
    input wire [8*NW*32-1:0] rr_w,     // bank b word j at [(b*NW+j)*32 +: 32]
    input wire [2:0] rsel,
    output reg [4*NW*32-1:0] gx_w      // lane k word j at [(k*NW+j)*32 +: 32]
);
    reg [8*NW*32-1:0] rr_q;
    (* keep="true", dont_touch="true" *) reg [2:0] read_bank_local[0:3][0:NW-1];
    always @(posedge clk) begin
        rr_q<=rr_w;
        for(integer k=0;k<4;k=k+1) for(integer j=0;j<NW;j=j+1) read_bank_local[k][j]<=rsel;
    end
    for(genvar k=0;k<4;k=k+1)begin: lane
        for(genvar j=0;j<NW;j=j+1)begin: word_
            reg [31:0] selected;
            always @* begin
                selected='0;
                for(integer b=0;b<8;b=b+1)
                    if((((int'(read_bank_local[k][j])+k)&7)^(MUT==1?1:0))==b)
                        selected=selected|rr_q[(b*NW+j)*32+:32];
            end
            always @(posedge clk) gx_w[(k*NW+j)*32+:32]<=selected;
        end
    end
endmodule

// Write scatter for words [W0, W0+NW): bank b word j <= {y lane k word j, 16'd0} for the k that maps to b, else 0.
module ot_hgi_qdq_transport_wslice #(
    parameter integer NW=2, MUT=0
)(
    input wire clk,
    input wire [4*NW*16-1:0] y_w,      // lane k word j at [(k*NW+j)*16 +: 16]
    input wire [2:0] wsel,
    output reg [8*NW*16-1:0] wq_w      // bank b word j BF16 at [(b*NW+j)*16 +: 16] (low 16 bits of the word are 0)
);
    reg [4*NW*16-1:0] y_q;
    (* keep="true", dont_touch="true" *) reg [2:0] write_bank_local[0:7];
    always @(posedge clk) begin
        y_q<=y_w;
        for(integer b=0;b<8;b=b+1) write_bank_local[b]<=wsel;
    end
    for(genvar b=0;b<8;b=b+1)begin: bank
        reg [NW*16-1:0] nxt;
        always @* begin
            nxt='0;
            for(integer k=0;k<4;k=k+1)
                if((((int'(write_bank_local[b])+k)&7)^(MUT==2?1:0))==b)
                    for(integer j=0;j<NW;j=j+1) nxt[j*16+:16]=y_q[(k*NW+j)*16+:16];
        end
        always @(posedge clk) wq_w[b*NW*16+:NW*16]<=nxt;
    end
endmodule

module ot_hgi_qdq_static_transport_split #(
    parameter integer IO_REGS=1,
    parameter integer RL=7,
    parameter integer DL=25,
    parameter integer WC=4,
    parameter integer MUT=0,
    parameter integer NS=4             // word slices (8 words / NS each)
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
    initial if(IO_REGS!=1 || NS*NW!=8) $fatal(1,"split transport is the registered (IO_REGS=1) successor; NS must divide 8");
    wire [7:0] rr_v, wq_v; wire [8*16-1:0] wq_addr; wire [8*8-1:0] wq_mask; wire [2:0] rsel, wsel;
    for(genvar b=0;b<8;b=b+1)begin: bank_bits
        assign rr_v[b]=rr[b*257+256];
        assign wq[b*281+280]=wq_v[b];
        assign wq[b*281+264+:16]=wq_addr[b*16+:16];
        assign wq[b*281+:8]=wq_mask[b*8+:8];
    end
    ot_hgi_qdq_transport_ctl #(.RL(RL),.DL(DL),.WC(WC),.MUT(MUT)) ctl(
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_op(cmd_op),.cmd_block(cmd_block),.cmd_src(cmd_src),
        .cmd_dst(cmd_dst),.cmd_last(cmd_last),.rq(rq),.rr_v(rr_v),.wq_v(wq_v),.wq_addr(wq_addr),.wq_mask(wq_mask),
        .rsel(rsel),.wsel(wsel),.beat_done(beat_done),.record_done(record_done),.fault(fault),
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
