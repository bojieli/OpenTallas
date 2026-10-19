`timescale 1ns/1ps
`default_nettype none
// HBM d4g hb_quant_NW: soft parent composition of the CLOSED split leaves (OWNERS-HBM/QDQ 2026-10-18).
// Port-identical drop-in for ot_hgi_qdq_host_static (same port list and widths, same RL/WC/MUT/COMPACT parameters):
// the die binds hb_quant_NW to this master instead of the BLOCKED monolith (one CTS root cannot carry its SRAM and
// the 11.5 mm bank span).  Physical children, each with its own clock pin, named as the d4g grant slots:
//
//   program_leaf          ot_hgi_qdq_native_program_leaf #(COMPACT)   target48 collar + record calendar + programme SRAM
//                                                                     (no closed NW view: needs its own kit; SW twin
//                                                                     ot_hgi_qdq_sw_program_leaf is closed as sw125_r6)
//   quant_NW_xp           ot_hgi_qdq_static_transport_split #(IO_REGS1,RL+2,DL25,WC+1,NS4)  wires-only cluster:
//                           .ctl                 ot_hgi_qdq_transport_ctl #(RL+2,25,WC+1)   slot quant_NW_xp_ctl
//                           .slice[s].rslice     ot_hgi_qdq_transport_rslice #(NW2)          slot quant_NW_xp_rslice<s>
//                           .slice[s].wslice     ot_hgi_qdq_transport_wslice #(NW2)          slot quant_NW_xp_wslice<s>
//   u_dxl/u_dbq/u_daq     ot_hgi_qw_dxl / ot_hgi_qw_dbq / ot_hgi_qw_daq  the released decoder (closed qw_*_ref views)
//   quant_NW<k> k=0..3    ot_hgi_qdq_quant_bank_pair (wires-only cluster) -> .lg ot_hgi_qdq_lg_port_group #(BANKS2)
//                                                                     slot quant_NW<k>_lg, banks 2k and 2k+1
//
// RL / WC keep their monolith meaning: the fixed VM bank latency measured AT THESE PINS.  The LG groups add the priced
// fixed edges (rq +1, rr +1, wq +1) and the transport is always the registered boundary (+1 rr, +1 result), so the
// engine runs RL+2 / WC+1 internally (exactly ot_hgi_qdq_program_static LG=1).  Against the IO_REGS=0 monolith every
// port is the same stream, shifted by a fixed number of edges:
//   rq                            +1 edge   (VM read-slot reservation +1)
//   wq, beat_done, record_done    +5 edges  (VM write-slot reservation +5: IO_REGS +2, LG +3)
//   program_active/done, configured, fault-free behaviour   unchanged
// IO_REGS is accepted for drop-in compatibility only: the split IS the registered boundary.
// PIN_BOUNDARY=1 (reset collars + sticky fault flop) would be soft logic in this wires-only parent: not supported.
// The only parent gate is the two-input fault OR, exactly as in the monolith parent.
// LGMUT (bench only): 1 binds quant_NW0 / quant_NW1 to each other's write ports.
module ot_hgi_qdq_quant_bank_pair #(parameter integer BANKS=2)(
    input wire clk, rst_n,
    input wire [BANKS*17-1:0] rq_i, output wire [BANKS*17-1:0] rq_o,
    input wire [BANKS*257-1:0] rr_i, output wire [BANKS*257-1:0] rr_o,
    input wire [BANKS*281-1:0] wq_i, output wire [BANKS*281-1:0] wq_o
);
    ot_hgi_qdq_lg_port_group #(.BANKS(BANKS)) lg(.clk(clk),.rst_n(rst_n),
        .rq_i(rq_i),.rq_o(rq_o),.rr_i(rr_i),.rr_o(rr_o),.wq_i(wq_i),.wq_o(wq_o));
endmodule

module ot_hgi_qdq_host_split #(
    parameter integer RL=7,WC=4,MUT=0,COMPACT=0,PIN_BOUNDARY=0,IO_REGS=0,LGMUT=0
)(
    input wire clk_program,clk_transport,clk_dxl,clk_dbq,clk_daq,rst_n,
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
    initial if(PIN_BOUNDARY!=0) $fatal(1,"ot_hgi_qdq_host_split: PIN_BOUNDARY=1 needs parent soft logic; not supported");
    wire [47:0] command;
    wire command_v,pfault,efault;
    wire [31:0] ordinal;
    ot_hgi_qdq_native_program_leaf #(.COMPACT(COMPACT)) program_leaf(
        .clk(clk_program),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .command(command),.command_v(command_v),.ordinal(ordinal),.active(program_active),.done(program_done),
        .configured(configured),.fault(pfault),.installed_cfg_we(),.installed_cfg_addr());
    // engine side of the LG groups
    wire [8*17-1:0] rq_e; wire [8*257-1:0] rr_e; wire [8*281-1:0] wq_e;
    wire v,vo,qfault,decode_fault;
    wire [127:0] header; wire [1023:0] x; wire [511:0] y;
    wire [17:0] hd={header[127:118],header[71:64]};
    wire [1023:0] xs,xb,xa; wire bvo,bfo; wire [511:0] byo;
    ot_hgi_qdq_static_transport_split #(.IO_REGS(1),.RL(RL+2),.DL(25),.WC(WC+1),.MUT(MUT),.NS(4)) quant_NW_xp(
        .clk(clk_transport),.rst_n(rst_n),.cmd_v(command_v&&command[0]),.cmd_op(command[6:1]),.cmd_block(command[14:7]),
        .cmd_src(command[30:15]),.cmd_dst(command[46:31]),.cmd_last(command[47]),.rq(rq_e),.rr(rr_e),.wq(wq_e),
        .beat_done(beat_done),.record_done(record_done),.fault(efault),
        .dec_v(v),.dec_header(header),.dec_x(x),.vo(vo),.qfault(qfault),.decode_fault(decode_fault),.y(y));
    ot_hgi_qw_dxl u_dxl(.clk(clk_dxl),.x(x),.xs(xs),.xb(xb),.xa(xa));
    ot_hgi_qw_dbq u_dbq(.clk(clk_dbq),.rst_n(rst_n),.v(v),.hd(hd),.xs(xs),.xb(xb),.bvo(bvo),.bfo(bfo),.byo(byo));
    ot_hgi_qw_daq u_daq(.clk(clk_daq),.rst_n(rst_n),.v(v),.hd(hd),.xs(xs),.xa(xa),
        .bvo(bvo),.bfo(bfo),.byo(byo),.vo(vo),.y(y),.fault(qfault),.decode_fault(decode_fault));
    // four bank-pair groups: quant_NW<k> serves banks 2k, 2k+1 (rq/rr/wq slices [(2k)*W, (2k+2)*W))
    wire [2*281-1:0] wq_g [0:3];
    for(genvar k=0;k<4;k=k+1) begin: bank_pair
        localparam integer KW=(LGMUT==1&&k<2)?(k^1):k;
        assign wq[KW*2*281+:2*281]=wq_g[k];
    end
    ot_hgi_qdq_quant_bank_pair #(.BANKS(2)) quant_NW0(.clk(clk_transport),.rst_n(rst_n),
        .rq_i(rq_e[0*34+:34]),.rq_o(rq[0*34+:34]),.rr_i(rr[0*514+:514]),.rr_o(rr_e[0*514+:514]),
        .wq_i(wq_e[0*562+:562]),.wq_o(wq_g[0]));
    ot_hgi_qdq_quant_bank_pair #(.BANKS(2)) quant_NW1(.clk(clk_transport),.rst_n(rst_n),
        .rq_i(rq_e[1*34+:34]),.rq_o(rq[1*34+:34]),.rr_i(rr[1*514+:514]),.rr_o(rr_e[1*514+:514]),
        .wq_i(wq_e[1*562+:562]),.wq_o(wq_g[1]));
    ot_hgi_qdq_quant_bank_pair #(.BANKS(2)) quant_NW2(.clk(clk_transport),.rst_n(rst_n),
        .rq_i(rq_e[2*34+:34]),.rq_o(rq[2*34+:34]),.rr_i(rr[2*514+:514]),.rr_o(rr_e[2*514+:514]),
        .wq_i(wq_e[2*562+:562]),.wq_o(wq_g[2]));
    ot_hgi_qdq_quant_bank_pair #(.BANKS(2)) quant_NW3(.clk(clk_transport),.rst_n(rst_n),
        .rq_i(rq_e[3*34+:34]),.rq_o(rq[3*34+:34]),.rr_i(rr[3*514+:514]),.rr_o(rr_e[3*514+:514]),
        .wq_i(wq_e[3*562+:562]),.wq_o(wq_g[3]));
    assign fault=pfault|efault;
endmodule
`default_nettype wire
