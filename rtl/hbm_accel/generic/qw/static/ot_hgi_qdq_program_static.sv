`timescale 1ns/1ps
`default_nettype none
// Actual mapped programme SRAM -> fixed QDQ beat issue -> actual decoder.
// Separate clock entries preserve the physical ability to deliver each phi-R;
// programme/engine clocks are same-domain, with matched interface phase.
// Programme format: valid0,op6:1,block14:7,src30:15,dst46:31,last47.
// The host writes canonical c7a1/PC-tagged words before launch. No normal ready,
// credit, memory-completion gate or shadow software-produced internal result.
// Shared host target decode/global launch and actual NW stations are external
// integration obligations; these explicit ports must not be tied away there.
module ot_hgi_qdq_program_static #(
    parameter integer RL=7, WC=4, MUT=0,IO_REGS=0,
    // LG=1: GEO-H four bank-pair LG port groups (ot_hgi_qdq_lg_port_group) between the engine and the VM
    // banks; adds exactly +2 read-return edges (rq,rr) and +1 write-commit edge (wq) to the fixed calendar.
    // LG=0 is the previous single-cluster boundary (unchanged behaviour).
    parameter integer LG=0,
    parameter integer LGMUT=0, // bench only: 1 binds port groups 0/1 to each other's bank-pair write slice
    parameter integer TSPLIT=0 // 1: word-sliced transport leaves (control + NS read/write slices), zero added edges
)(
    input wire clk_program,clk_transport,clk_dxl,clk_dbq,clk_daq,rst_n,
    input wire [3:0] clk_lg,
    input wire cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output wire program_active,program_done,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire [8*281-1:0] wq,
    output wire beat_done,record_done,
    output wire fault
);
    wire [47:0] command;
    wire command_v,program_fault,engine_fault;
    wire [31:0] ordinal;
    ot_vms_calendar_static #(.W(48)) program_store(
        .clk(clk_program),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .calendar(command),.calendar_v(command_v),.ordinal(ordinal),
        .active(program_active),.done(program_done),.fault(program_fault));
    wire [8*17-1:0] rq_e; wire [8*257-1:0] rr_e; wire [8*281-1:0] wq_e;
    generate if(LG!=0) begin: lg_groups
        initial if(IO_REGS==0) $fatal(1,"LG port groups require the registered constant-bank transport (IO_REGS=1)");
        for(genvar k=0;k<4;k=k+1) begin: g
            ot_hgi_qdq_lg_port_group #(.BANKS(2)) port_group(.clk(clk_lg[k]),.rst_n(rst_n),
                .rq_i(rq_e[k*34+:34]),.rq_o(rq[k*34+:34]),.rr_i(rr[k*514+:514]),.rr_o(rr_e[k*514+:514]),
                .wq_i(wq_e[k*562+:562]),.wq_o(wq[((LGMUT==1&&k<2)?(k^1):k)*562+:562]));
        end
    end else begin: single_cluster
        assign rq=rq_e; assign rr_e=rr; assign wq=wq_e;
    end endgenerate
    ot_hgi_qdq_static #(.IO_REGS(IO_REGS),.RL(RL+(LG!=0?2:0)),.WC(WC+(LG!=0?1:0)),.MUT(MUT),.TSPLIT(TSPLIT)) engine(
        .clk_transport(clk_transport),.clk_dxl(clk_dxl),.clk_dbq(clk_dbq),.clk_daq(clk_daq),.rst_n(rst_n),.cmd_v(command_v&&command[0]),
        .cmd_op(command[6:1]),.cmd_block(command[14:7]),.cmd_src(command[30:15]),
        .cmd_dst(command[46:31]),.cmd_last(command[47]),
        .rq(rq_e),.rr(rr_e),.wq(wq_e),.beat_done(beat_done),.record_done(record_done),.fault(engine_fault));
    assign fault=program_fault|engine_fault;
endmodule
`default_nettype wire
