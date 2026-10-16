`timescale 1ns/1ps
`default_nettype none
// QUANT transport r2 (H-SM 2026-10-15): structural successors of two native-audit failures of the closed v6 leaves.
//
//   ot_hgi_qdq_transport_ctl_r2   the closed ctl had capture 304.0 ps on 33 cmd pins (cmd_src / cmd_dst / cmd_op /
//                                 cmd_block feed the constant-port pack adders and the range-check adders before the
//                                 first flop).  r2 registers every cmd_* bit AT ITS PIN (one capture flop per pin, the
//                                 only load of the pin) and runs the unchanged controller from those registers.  +1 edge
//                                 on the whole controller (every rq / wq / dec / done output one cycle later, relative
//                                 timing unchanged), reset only on the cmd_v valid bit.
//   ot_hgi_qdq_lg_port_group_r2   the closed LG group had ONE register per bit between a W input pin and an E output pin
//                                 64.8 um apart: one flop cannot sit at both pins (launch 270.7 ps on 227 wq_o pins).
//                                 r2 = a capture register at the input pin and a launch register at the output pin per
//                                 bit; the 64.8-um crossing is a whole-cycle reg->reg path.  +1 edge per direction
//                                 (rq +1, rr +1, wq +1 over the r1 group), priced by the parent (RL +4, WC +2 at LG=2).
//   ot_hgi_qdq_static_transport_split_r2  wires-only parent of ctl_r2 + the closed rslice / wslice masters.
// No ready, credit or arbitration anywhere; fixed calendar edges only.

module ot_hgi_qdq_transport_ctl_r2 #(
    parameter integer RL=7, DL=25, WC=4, MUT=0
)(
    input wire clk, rst_n,
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
    // local reset relay (native audit of the r2 view: rst_n capture 213.8 ps, the port fanned out to every valid flop):
    // the port drives only the relay (async assert, 2-stage sync release + 1 relay = 3 edges of release latency, an
    // initialization-mode cost, no data edge); every controller flop resets from rn.
    (* async_reg = "true" *) reg rst_s1, rst_s2;
    reg rn;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rst_s1 <= 1'b0; rst_s2 <= 1'b0; rn <= 1'b0; end
        else begin rst_s1 <= 1'b1; rst_s2 <= rst_s1; rn <= rst_s2; end
    // pin capture registers (the only load of each cmd pin)
    reg cv_q;
    reg [5:0] op_q; reg [7:0] blk_q; reg [15:0] src_q, dst_q; reg last_q;
    always @(posedge clk or negedge rn)
        if(!rn) cv_q<=1'b0; else cv_q<=cmd_v;
    always @(posedge clk) begin op_q<=cmd_op; blk_q<=cmd_block; src_q<=cmd_src; dst_q<=cmd_dst; last_q<=cmd_last; end
    ot_hgi_qdq_transport_ctl #(.RL(RL),.DL(DL),.WC(WC),.MUT(MUT)) u_ctl(
        .clk(clk),.rst_n(rn),.cmd_v(cv_q),.cmd_op(op_q),.cmd_block(blk_q),.cmd_src(src_q),.cmd_dst(dst_q),
        .cmd_last(last_q),.rq(rq),.rr_v(rr_v),.wq_v(wq_v),.wq_addr(wq_addr),.wq_mask(wq_mask),.rsel(rsel),.wsel(wsel),
        .beat_done(beat_done),.record_done(record_done),.fault(fault),.dec_v(dec_v),.dec_header(dec_header),
        .vo(vo),.qfault(qfault),.decode_fault(decode_fault));
endmodule

module ot_hgi_qdq_lg_port_group_r2 #(parameter integer BANKS=2)(
    input wire clk, rst_n,
    input wire [BANKS*17-1:0] rq_i, output reg [BANKS*17-1:0] rq_o,
    input wire [BANKS*257-1:0] rr_i, output reg [BANKS*257-1:0] rr_o,
    input wire [BANKS*281-1:0] wq_i, output reg [BANKS*281-1:0] wq_o
);
    reg [BANKS*17-1:0] rq_c; reg [BANKS*257-1:0] rr_c; reg [BANKS*281-1:0] wq_c;   // capture at the input pins
    always @(posedge clk or negedge rst_n)
        if(!rst_n) for(integer b=0;b<BANKS;b=b+1) begin
            rq_c[b*17+16]<=0;rr_c[b*257+256]<=0;wq_c[b*281+280]<=0;
            rq_o[b*17+16]<=0;rr_o[b*257+256]<=0;wq_o[b*281+280]<=0;
        end else for(integer b=0;b<BANKS;b=b+1) begin
            rq_c[b*17+16]<=rq_i[b*17+16];rr_c[b*257+256]<=rr_i[b*257+256];wq_c[b*281+280]<=wq_i[b*281+280];
            rq_o[b*17+16]<=rq_c[b*17+16];rr_o[b*257+256]<=rr_c[b*257+256];wq_o[b*281+280]<=wq_c[b*281+280];
        end
    always @(posedge clk)
        for(integer b=0;b<BANKS;b=b+1) begin
            rq_c[b*17+:16]<=rq_i[b*17+:16];rr_c[b*257+:256]<=rr_i[b*257+:256];wq_c[b*281+:280]<=wq_i[b*281+:280];
            rq_o[b*17+:16]<=rq_c[b*17+:16];rr_o[b*257+:256]<=rr_c[b*257+:256];wq_o[b*281+:280]<=wq_c[b*281+:280];
        end
endmodule

module ot_hgi_qdq_static_transport_split_r2 #(
    parameter integer IO_REGS=1,
    parameter integer RL=7,
    parameter integer DL=25,
    parameter integer WC=4,
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
    initial if(IO_REGS!=1 || NS*NW!=8) $fatal(1,"split transport is the registered (IO_REGS=1) successor; NS must divide 8");
    wire [7:0] rr_v, wq_v; wire [8*16-1:0] wq_addr; wire [8*8-1:0] wq_mask; wire [2:0] rsel, wsel;
    for(genvar b=0;b<8;b=b+1)begin: bank_bits
        assign rr_v[b]=rr[b*257+256];
        assign wq[b*281+280]=wq_v[b];
        assign wq[b*281+264+:16]=wq_addr[b*16+:16];
        assign wq[b*281+:8]=wq_mask[b*8+:8];
    end
    ot_hgi_qdq_transport_ctl_r2 #(.RL(RL),.DL(DL),.WC(WC),.MUT(MUT)) ctl(
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
