`timescale 1ns/1ps
`default_nettype none
// HBM-P4-QUANT 2026-10-23 (COORD R6(3)): quadrant-parameterised hb_quant_Q.  Same children, clocks, ports and timing
// law as ot_hgi_qdq_host_split_r3 (hb_quant_NW, pinned, untouched): rq +3+XR, wq/done +9+3*XR vs the monolith.
// Differences: (1) the programme leaf is ot_hgi_qdq_q_program_leaf with its target-id strap tied to 8'h30+Q here
// (one hardened leaf master for all four quadrants; NW = 48 as before); (2) the child instance names carry the
// quadrant-neutral 'Q' (quant_Q0..3, quant_Q_xp) so the qdq_split netmap yields the plan's synthetic replica names
// hb_quant_Q__quant_Q<k>_lg / quant_Q_xp_ctl / quant_Q_xp_slice_<k>__{r,w}slice / program_leaf / u_dec /
// hbfd_qdq_split_{and,or} (gen_plan_v2 'synthetic').  The engine serves ONLY its own quadrant's 8 VM banks (bank pair k
// = banks 2k,2k+1 of that quadrant); no port leaves the quadrant.  Static schedule, no credits / ready.
// Q: 0 NW, 1 NE, 2 SW, 3 SE (gen_plan_v2 QS order).  QMUT (bench only): strap tied to 8'h30+(Q^1).
module ot_hgi_qdq_host_split_q #(
    parameter integer Q=0,RL=7,WC=4,XR=0,MUT=0,COMPACT=1,LGMUT=0,XR_SIM=0,QMUT=0
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
    localparam [7:0] TGT=8'h30+8'((QMUT!=0)?(Q^1):Q);
    initial if(Q<0 || Q>3) $fatal(1,"host split q: Q %0d not in 0..3",Q);
    initial if(RLI>126 || WCI>63) $fatal(1,"host split q: RLI %0d / WCI %0d beyond ctl_r4 (126 / 63)",RLI,WCI);
    wire [47:0] command;
    wire command_v,pfault,efault;
    wire [31:0] ordinal;
    ot_hgi_qdq_q_program_leaf #(.COMPACT(COMPACT),.PIN_BOUNDARY(1)) program_leaf(
        .clk(clk_program),.rst_n(rst_n),.tgt(TGT),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .command(command),.command_v(command_v),.ordinal(ordinal),.active(program_active),.done(program_done),
        .configured(configured),.fault(pfault));
    wire [8*17-1:0] rq_x; wire [8*257-1:0] rr_x; wire [8*281-1:0] wq_x;
    wire v,vo,qfault,decode_fault;
    wire [127:0] header; wire [1023:0] x; wire [511:0] y;
    ot_hgi_qdq_static_transport_split_r4 #(.RLI(RLI),.WCI(WCI),.DL(25),.MUT(MUT),.NS(4)) quant_Q_xp(
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
    // four bank-pair groups: quant_Q<k> serves this quadrant's banks 2k, 2k+1
    wire [2*281-1:0] wq_g [0:3];
    for(genvar k=0;k<4;k=k+1) begin: bank_pair
        localparam integer KW=(LGMUT==1&&k<2)?(k^1):k;
        assign wq[KW*2*281+:2*281]=wq_g[k];
    end
    ot_hgi_qdq_quant_bank_pair_r2 #(.BANKS(2)) quant_Q0(.clk(clk_lg[0]),.rst_n(rst_n),
        .rq_i(rq_e[0*34+:34]),.rq_o(rq[0*34+:34]),.rr_i(rr[0*514+:514]),.rr_o(rr_e[0*514+:514]),
        .wq_i(wq_e[0*562+:562]),.wq_o(wq_g[0]));
    ot_hgi_qdq_quant_bank_pair_r2 #(.BANKS(2)) quant_Q1(.clk(clk_lg[1]),.rst_n(rst_n),
        .rq_i(rq_e[1*34+:34]),.rq_o(rq[1*34+:34]),.rr_i(rr[1*514+:514]),.rr_o(rr_e[1*514+:514]),
        .wq_i(wq_e[1*562+:562]),.wq_o(wq_g[1]));
    ot_hgi_qdq_quant_bank_pair_r2 #(.BANKS(2)) quant_Q2(.clk(clk_lg[2]),.rst_n(rst_n),
        .rq_i(rq_e[2*34+:34]),.rq_o(rq[2*34+:34]),.rr_i(rr[2*514+:514]),.rr_o(rr_e[2*514+:514]),
        .wq_i(wq_e[2*562+:562]),.wq_o(wq_g[2]));
    ot_hgi_qdq_quant_bank_pair_r2 #(.BANKS(2)) quant_Q3(.clk(clk_lg[3]),.rst_n(rst_n),
        .rq_i(rq_e[3*34+:34]),.rq_o(rq[3*34+:34]),.rr_i(rr[3*514+:514]),.rr_o(rr_e[3*514+:514]),
        .wq_i(wq_e[3*562+:562]),.wq_o(wq_g[3]));
    assign fault=pfault|efault;
endmodule
`default_nettype wire
