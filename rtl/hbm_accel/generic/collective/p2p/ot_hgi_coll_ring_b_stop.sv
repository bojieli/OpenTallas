`timescale 1ns/1ps
`default_nettype none
// HBM-RTL4 (10-18): d4g ring-B die block = the per-quadrant tile that holds the gather-only ring-B stop
// (ot_hgi_coll_ring_ag_lane) in its OWN slot beside ring A's control root (hcoll_ring_ag_ctl_1017);
// sharing ring A's 216 x 129.6 slot would put ~1.9k more pins on it (> 6/um).
// Pins: every input is flop-first, every output flop-last:
//  - ring faces cw_i/ccw_i land on the lane's pin registers, cw_o/ccw_o leave from its out registers (2-edge hop
//    unchanged, identical to ring A);
//  - the command/lp inputs from the quadrant COLL engine get one pin register here (CMD_PIPE=1): the compiler issues
//    every ring-B command (lp write, state read, inject/forward/ttl, rx reservation) ONE edge earlier than ring A's.
//    Ring timing (inject -> arrival -> publish) is unchanged, so one static timeline format drives both rings;
//  - publish ag_* and fault are the lane's output registers.
//  - qid is a strap, registered like a command.
// rst_n drives only ot_rst_relay (1 region: the reset loads are the lane's ~30 control flops); release is
// 3 edges after the port: the compiler's first ring-B command may land at the lane no earlier than edge 4.
module ot_hgi_coll_ring_b_stop #(
    parameter integer MUT_TTL=0, MUT_SRC=0, CMD_PIPE=1
)(
    input wire clk, rst_n,
    input wire [1:0] qid,
    input wire [279:0] cw_i, ccw_i,
    output wire [279:0] cw_o, ccw_o,
    input wire lp_we,
    input wire [2:0] lp_tag,
    input wire [255:0] lp_data,
    input wire state_read_tx,
    input wire [2:0] state_tx_tag,
    input wire [1:0] tx_inject, tx_forward,
    input wire [2:0] tx_tag,
    input wire [3:0] tx_ttl,
    input wire [1:0] rx_slot,
    input wire [3:0] rx_kind, rx_src,
    input wire [5:0] rx_tag,
    output wire [1:0] ag_v,
    output wire [3:0] ag_src,
    output wire [5:0] ag_tag,
    output wire [511:0] ag_d,
    output wire fault
);
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_l));
    localparam integer CW=2+1+3+256+1+3+2+2+3+4+2+4+4+6;
    wire [CW-1:0] cmd_i={qid,lp_we,lp_tag,lp_data,state_read_tx,state_tx_tag,tx_inject,tx_forward,tx_tag,tx_ttl,
                         rx_slot,rx_kind,rx_src,rx_tag};
    wire [CW-1:0] cmd;
    generate if(CMD_PIPE)begin:g_pipe
        // valid-qualified fields (lp_we, read, inject, forward, rx_slot) are reset; payload/tag fields are plain flops
        reg [CW-1:0] cmd_q;
        localparam [CW-1:0] VMASK={2'b0,1'b1,3'b0,256'b0,1'b1,3'b0,2'b11,2'b11,3'b0,4'b0,2'b11,4'b0,4'b0,6'b0};
        always @(posedge clk)cmd_q<=cmd_i;
        reg [CW-1:0] v_q;
        always @(posedge clk or negedge rst_l[0])if(!rst_l[0])v_q<=0;else v_q<=cmd_i&VMASK;
        assign cmd=(cmd_q&~VMASK)|v_q;
    end else begin:g_nopipe
        assign cmd=cmd_i;
    end endgenerate
    wire [1:0] c_qid;wire c_lp_we;wire [2:0] c_lp_tag;wire [255:0] c_lp_data;wire c_rd;wire [2:0] c_rd_tag;
    wire [1:0] c_inj,c_fwd;wire [2:0] c_tag;wire [3:0] c_ttl;wire [1:0] c_rx;wire [3:0] c_kind,c_src;wire [5:0] c_rtag;
    assign {c_qid,c_lp_we,c_lp_tag,c_lp_data,c_rd,c_rd_tag,c_inj,c_fwd,c_tag,c_ttl,c_rx,c_kind,c_src,c_rtag}=cmd;
    ot_hgi_coll_ring_ag_lane #(.MUT_TTL(MUT_TTL),.MUT_SRC(MUT_SRC)) u_lane(
        .clk(clk),.rst_n(rst_l[0]),.qid(c_qid),
        .cw_i(cw_i),.ccw_i(ccw_i),.cw_o(cw_o),.ccw_o(ccw_o),
        .lp_we(c_lp_we),.lp_tag(c_lp_tag),.lp_data(c_lp_data),
        .state_read_tx(c_rd),.state_tx_tag(c_rd_tag),
        .tx_inject(c_inj),.tx_forward(c_fwd),.tx_tag(c_tag),.tx_ttl(c_ttl),
        .rx_slot(c_rx),.rx_kind(c_kind),.rx_src(c_src),.rx_tag(c_rtag),
        .ag_v(ag_v),.ag_src(ag_src),.ag_tag(ag_tag),.ag_d(ag_d),.fault(fault));
endmodule
`default_nettype wire
