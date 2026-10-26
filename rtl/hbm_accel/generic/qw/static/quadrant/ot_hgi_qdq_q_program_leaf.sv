`timescale 1ns/1ps
`default_nettype none
// HBM-P4-QUANT 2026-10-23 (COORD R6(3): QUANT replicated in all 4 quadrants of the d4g die, one master for all four).
// Quadrant programme leaf = ot_hgi_qdq_nw_program_leaf (NW target48 leaf, pinned, untouched) with ONE difference: the
// configuration target id comes from the identity strap pin tgt (ot_static_program_target TGT_PIN=1, captured in a
// flop at the pin) instead of the hard-wired TARGET 48.  The parent ties tgt to the die constant 8'h30+Q
// (Q: NW 0 / NE 1 / SW 2 / SE 3 = gen_plan_v2 QS order), so NW keeps target 48 and the replicas take the unused ids
// 0x31..0x33.  Same target collar, record calendar, programme SRAM, reset collar and sticky fault flop; same edges.
module ot_hgi_qdq_q_program_leaf #(parameter integer COMPACT=1,PIN_BOUNDARY=1)(
    input wire clk,rst_n,
    input wire [7:0] tgt,              // identity strap (die constant 8'h30+Q)
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
    wire [1:0] reset_local_n;
    wire target_fault,calendar_fault;
    generate if(PIN_BOUNDARY)begin: physical_boundary
        ot_rst_relay #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) reset_collar(
            .clk(clk),.rst_n_in(rst_n),.rst_n(reset_local_n));
        reg fault_q;
        always @(posedge clk or negedge reset_local_n[1])
            if(!reset_local_n[1])fault_q<=0;
            else fault_q<=target_fault|calendar_fault;
        assign fault=fault_q;
    end else begin: original_boundary
        assign reset_local_n={2{rst_n}};
        assign fault=target_fault|calendar_fault;
    end endgenerate
    wire cfg_we,start_v;
    wire [9:0] address,base;
    wire [10:0] limit;
    wire [15:0] loops;
    wire [255:0] data_word;
    ot_static_program_target #(.TARGET(8'd48),.PCW(10),.TGT_PIN(1)) target(
        .clk(clk),.rst_n(reset_local_n[0]),.clk_cap(clk),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),
        .cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),
        .launch_v(launch_v),.program_active(active),.program_cfg_we(cfg_we),.program_cfg_addr(address),
        .program_cfg_data(data_word),.program_start_v(start_v),.program_start_base(base),
        .program_start_limit(limit),.program_start_loops(loops),.configured(configured),.fault(target_fault));
    generate if(COMPACT==0)begin: beat_programme
    ot_vms_calendar_static #(.W(48)) calendar(
        .clk(clk),.rst_n(reset_local_n[1]),.cfg_we(cfg_we),.cfg_addr(address),.cfg_data(data_word),
        .start_v(start_v),.start_base(base),.start_limit(limit),.start_loops(loops),
        .calendar(command),.calendar_v(command_v),.ordinal(ordinal),.active(active),.done(done),.fault(calendar_fault));
    end else begin: record_programme
        wire [31:0] local_cycle;
        wire record_fault;reg unsupported_loop;
        always @(posedge clk or negedge reset_local_n[1])
            if(!reset_local_n[1])unsupported_loop<=0;
            else if(start_v && loops!=1)unsupported_loop<=1;
        assign calendar_fault=record_fault|unsupported_loop;
        reg [31:0] issued;
        ot_hgi_qdq_record_calendar calendar(
            .clk(clk),.rst_n(reset_local_n[1]),.cfg_we(cfg_we),.cfg_addr(address),.cfg_data(data_word),
            .start_v(start_v),.start_base(base),.start_limit(limit),
            .command(command),.command_v(command_v),.cycle(local_cycle),.active(active),.done(done),.fault(record_fault));
        always @(posedge clk or negedge reset_local_n[1])
            if(!reset_local_n[1])issued<=0;
            else if(start_v)issued<=0;
            else if(command_v)issued<=issued+1;
        assign ordinal=issued;
    end endgenerate
endmodule
`default_nettype wire
