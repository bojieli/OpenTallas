`timescale 1ns/1ps
`default_nettype none
// Physical leaf: actual target48 configuration collar, calendar core and mapped
// SRAM. Configuration/launch comes from the real host overlay/loader CP producer.
// PCW10 validates the PC12 host frame: out-of-range words/ranges fault, no alias.
module ot_hgi_qdq_native_program_leaf #(parameter integer COMPACT=0)(
    input wire clk,rst_n,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire [47:0] command,
    output wire command_v,
    output wire [31:0] ordinal,
    output wire active,done,configured,fault
);
    wire cfg_we,start_v;
    wire [9:0] address,base;
    wire [10:0] limit;
    wire [15:0] loops;
    wire [255:0] data_word;
    wire target_fault,calendar_fault;
    ot_static_program_target #(.TARGET(8'd48),.PCW(10)) target(
        .clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),
        .launch_v(launch_v),.program_active(active),.program_cfg_we(cfg_we),.program_cfg_addr(address),
        .program_cfg_data(data_word),.program_start_v(start_v),.program_start_base(base),
        .program_start_limit(limit),.program_start_loops(loops),.configured(configured),.fault(target_fault));
    generate if(COMPACT==0)begin: beat_programme
    ot_vms_calendar_static #(.W(48)) calendar(
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(address),.cfg_data(data_word),
        .start_v(start_v),.start_base(base),.start_limit(limit),.start_loops(loops),
        .calendar(command),.calendar_v(command_v),.ordinal(ordinal),.active(active),.done(done),.fault(calendar_fault));
    end else begin: record_programme
        wire [31:0] local_cycle;
        wire record_fault;reg unsupported_loop;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)unsupported_loop<=0;
            else if(start_v && loops!=1)unsupported_loop<=1;
        assign calendar_fault=record_fault|unsupported_loop;
        reg [31:0] issued;
        ot_hgi_qdq_record_calendar calendar(
            .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(address),.cfg_data(data_word),
            .start_v(start_v),.start_base(base),.start_limit(limit),
            .command(command),.command_v(command_v),.cycle(local_cycle),.active(active),.done(done),.fault(record_fault));
        always @(posedge clk or negedge rst_n)
            if(!rst_n)issued<=0;
            else if(start_v)issued<=0;
            else if(command_v)issued<=issued+1;
        assign ordinal=issued;
    end endgenerate
    assign fault=target_fault|calendar_fault;
endmodule

// Wires-only native Quant parent; every physical child retains its own clock pin.
// Programme done reports issue completion; record_done includes fixed bank commit.
module ot_hgi_qdq_host_static #(
    parameter integer RL=7,WC=4,MUT=0,COMPACT=0
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
    wire [47:0] command;
    wire command_v,pfault,efault;
    wire [31:0] ordinal;
    ot_hgi_qdq_native_program_leaf #(.COMPACT(COMPACT)) program_leaf(
        .clk(clk_program),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .command(command),.command_v(command_v),.ordinal(ordinal),.active(program_active),.done(program_done),
        .configured(configured),.fault(pfault));
    ot_hgi_qdq_static #(.RL(RL),.WC(WC),.MUT(MUT)) engine(
        .clk_transport(clk_transport),.clk_dxl(clk_dxl),.clk_dbq(clk_dbq),.clk_daq(clk_daq),.rst_n(rst_n),
        .cmd_v(command_v&&command[0]),.cmd_op(command[6:1]),.cmd_block(command[14:7]),
        .cmd_src(command[30:15]),.cmd_dst(command[46:31]),.cmd_last(command[47]),
        .rq(rq),.rr(rr),.wq(wq),.beat_done(beat_done),.record_done(record_done),.fault(efault));
    assign fault=pfault|efault;
endmodule
`default_nettype wire
