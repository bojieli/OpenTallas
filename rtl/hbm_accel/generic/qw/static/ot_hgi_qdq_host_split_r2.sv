`timescale 1ns/1ps
`default_nettype none
// HBM d4g hb_quant_NW, split r2 (OWN-QDQ 2026-10-18): soft parent over hard children that are ALL closed or kitted and
// pass the native pin audit (launch <= 220, capture <= 190, 0 combinational pins, pin-flop spread <= 80 TT/FF).
// Successor of ot_hgi_qdq_host_split (claude/qdq-split-1018 1b0a71d6e), whose children failed native:
//   ctl v1 capture 304.0 ps (33 cmd pins)      -> ctl r3 = ctl_r2 pin registers + strap-selected latency (transport_r3)
//   LG v6 launch 270.7 ps (227 wq_o pins)       -> LG r2 (capture at the input pin, launch at the output pin; +1/dir)
//   qw_dxl launch 241.6 / capture 220.2 ps,
//   qw_dbq launch 255.1 ps                      -> ONE decoder tile ot_hgi_qw_dec (closed s260 2b1df5142, native PASS:
//                                                  launch 206.5, capture 188.8, spread 42.7/38.5); dec3 is the same
//                                                  ports and latency (tb_hgi_qw_dec3_equiv) but needs 3,072 seam bits
//                                                  and three slots; one tile needs neither
//   program_leaf (no view)                      -> ot_hgi_qdq_nw_program_leaf #(COMPACT1,PIN_BOUNDARY1) = the closed
//                                                  SW leaf (sw125_r6) with target 48
// Physical children (each its own clock pin):
//   program_leaf   ot_hgi_qdq_nw_program_leaf          clk_program
//   quant_NW_xp    ot_hgi_qdq_static_transport_split_r3 (soft): .ctl ctl_r3, .slice[s].rslice/.wslice   clk_transport
//   u_dec          ot_hgi_qw_dec                       clk_dec   (adjacent to quant_NW_xp: 0 relay stages, DL 25)
//   quant_NW<k>    ot_hgi_qdq_quant_bank_pair_r2 (soft) -> .lg ot_hgi_qdq_lg_port_group_r2 #(2), banks 2k/2k+1   clk_lg[k]
// Timing (all fixed edges; no ready/credit):
//   RL  = VM bank read latency measured AT THE LG BANK PINS (7 today; 9 with the hb_idx__nwsh share2 rebind)
//   XR  = die relay/landing stages PER DIRECTION between each quant_NW<k> and quant_NW_xp; the die makes it EQUAL on
//         all four pairs (pads the nearer pairs).  The controller is strapped to RLI = RL + 4 + 2*XR, WCI = WC + 2 + XR.
//   Against the IO_REGS=0 monolith ot_hgi_qdq_host_static (same RL/WC at the bank pins):
//     rq                          +3 + XR edges      (ctl_r2 +1, LG r2 +2, relays)
//     wq, beat_done, record_done  +9 + 3*XR edges    (ctl +1, LG 2+2+2, IO_REGS +2, relays 3*XR)
//     program_active/done/configured   same edge;  fault +1 edge (sticky flop of the SW-identical leaf collar)
// Ports: the monolith's, except the decoder clocks clk_dxl/clk_dbq/clk_daq -> clk_dec and one clk_lg[k] per bank-pair
// group (each group sits in its own clock region beside its banks, mm from the transport).
// Bench-only parameters: LGMUT 1 = quant_NW0/quant_NW1 write ports crossed; XR_SIM = relay stages the bench inserts
// per direction (the die relay layer inserts them in silicon; 0 = no logic).
module ot_hgi_qdq_quant_bank_pair_r2 #(parameter integer BANKS=2)(
    input wire clk, rst_n,
    input wire [BANKS*17-1:0] rq_i, output wire [BANKS*17-1:0] rq_o,
    input wire [BANKS*257-1:0] rr_i, output wire [BANKS*257-1:0] rr_o,
    input wire [BANKS*281-1:0] wq_i, output wire [BANKS*281-1:0] wq_o
);
    ot_hgi_qdq_lg_port_group_r2 #(.BANKS(BANKS)) lg(.clk(clk),.rst_n(rst_n),
        .rq_i(rq_i),.rq_o(rq_o),.rr_i(rr_i),.rr_o(rr_o),.wq_i(wq_i),.wq_o(wq_o));
endmodule

module ot_hgi_qdq_host_split_r2 #(
    parameter integer RL=7,WC=4,XR=0,MUT=0,COMPACT=1,LGMUT=0,XR_SIM=0
)(
    input wire clk_program,clk_transport,clk_dec,rst_n,
    input wire [3:0] clk_lg,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire program_active,program_done,configured,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire [8*281-1:0] wq,
    output wire beat_done,record_done,fault
);
    localparam integer RLI=RL+4+2*XR, WCI=WC+2+XR;
    wire [47:0] command;
    wire command_v,pfault,efault;
    wire [31:0] ordinal;
    ot_hgi_qdq_nw_program_leaf #(.COMPACT(COMPACT),.PIN_BOUNDARY(1)) program_leaf(
        .clk(clk_program),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .command(command),.command_v(command_v),.ordinal(ordinal),.active(program_active),.done(program_done),
        .configured(configured),.fault(pfault));
    // transport side of the bank-pair links (after the die relays)
    wire [8*17-1:0] rq_x; wire [8*257-1:0] rr_x; wire [8*281-1:0] wq_x;
    wire v,vo,qfault,decode_fault;
    wire [127:0] header; wire [1023:0] x; wire [511:0] y;
    ot_hgi_qdq_static_transport_split_r3 #(.RLI(RLI),.WCI(WCI),.DL(25),.MUT(MUT),.NS(4)) quant_NW_xp(
        .clk(clk_transport),.rst_n(rst_n),.cmd_v(command_v&&command[0]),.cmd_op(command[6:1]),.cmd_block(command[14:7]),
        .cmd_src(command[30:15]),.cmd_dst(command[46:31]),.cmd_last(command[47]),.rq(rq_x),.rr(rr_x),.wq(wq_x),
        .beat_done(beat_done),.record_done(record_done),.fault(efault),
        .dec_v(v),.dec_header(header),.dec_x(x),.vo(vo),.qfault(qfault),.decode_fault(decode_fault),.y(y));
    ot_hgi_qw_dec u_dec(.clk(clk_dec),.rst_n(rst_n),.v(v),.header(header),.x(x),.vo(vo),.y(y),.fault(qfault),
        .decode_fault(decode_fault));
    // die relay stages per direction (bench model only; silicon: the die relay layer, equal on all four pairs)
    wire [8*17-1:0] rq_e; wire [8*257-1:0] rr_e; wire [8*281-1:0] wq_e;
    generate if(XR_SIM==0) begin: no_relay
        assign rq_e=rq_x; assign rr_x=rr_e; assign wq_e=wq_x;
    end else begin: relay_model
        reg [8*17-1:0] rq_r [0:XR_SIM-1]; reg [8*257-1:0] rr_r [0:XR_SIM-1]; reg [8*281-1:0] wq_r [0:XR_SIM-1];
        always @(posedge clk_transport) begin
            rq_r[0]<=rq_x; rr_r[0]<=rr_e; wq_r[0]<=wq_x;
            for(integer i=1;i<XR_SIM;i=i+1) begin rq_r[i]<=rq_r[i-1]; rr_r[i]<=rr_r[i-1]; wq_r[i]<=wq_r[i-1]; end
        end
        assign rq_e=rq_r[XR_SIM-1]; assign rr_x=rr_r[XR_SIM-1]; assign wq_e=wq_r[XR_SIM-1];
    end endgenerate
    // four bank-pair groups: quant_NW<k> serves banks 2k, 2k+1
    wire [2*281-1:0] wq_g [0:3];
    for(genvar k=0;k<4;k=k+1) begin: bank_pair
        localparam integer KW=(LGMUT==1&&k<2)?(k^1):k;
        assign wq[KW*2*281+:2*281]=wq_g[k];
    end
    ot_hgi_qdq_quant_bank_pair_r2 #(.BANKS(2)) quant_NW0(.clk(clk_lg[0]),.rst_n(rst_n),
        .rq_i(rq_e[0*34+:34]),.rq_o(rq[0*34+:34]),.rr_i(rr[0*514+:514]),.rr_o(rr_e[0*514+:514]),
        .wq_i(wq_e[0*562+:562]),.wq_o(wq_g[0]));
    ot_hgi_qdq_quant_bank_pair_r2 #(.BANKS(2)) quant_NW1(.clk(clk_lg[1]),.rst_n(rst_n),
        .rq_i(rq_e[1*34+:34]),.rq_o(rq[1*34+:34]),.rr_i(rr[1*514+:514]),.rr_o(rr_e[1*514+:514]),
        .wq_i(wq_e[1*562+:562]),.wq_o(wq_g[1]));
    ot_hgi_qdq_quant_bank_pair_r2 #(.BANKS(2)) quant_NW2(.clk(clk_lg[2]),.rst_n(rst_n),
        .rq_i(rq_e[2*34+:34]),.rq_o(rq[2*34+:34]),.rr_i(rr[2*514+:514]),.rr_o(rr_e[2*514+:514]),
        .wq_i(wq_e[2*562+:562]),.wq_o(wq_g[2]));
    ot_hgi_qdq_quant_bank_pair_r2 #(.BANKS(2)) quant_NW3(.clk(clk_lg[3]),.rst_n(rst_n),
        .rq_i(rq_e[3*34+:34]),.rq_o(rq[3*34+:34]),.rr_i(rr[3*514+:514]),.rr_o(rr_e[3*514+:514]),
        .wq_i(wq_e[3*562+:562]),.wq_o(wq_g[3]));
    assign fault=pfault|efault;
endmodule
`default_nettype wire
