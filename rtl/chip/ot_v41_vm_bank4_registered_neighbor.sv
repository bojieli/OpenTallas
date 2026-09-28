`timescale 1ns/1ps
// Physical envelope for a four-bank VM service between registered neighbors.
// The input and output ports are observability boundaries only: closure of
// this top uses false paths on primary I/O and times producer FF -> SRAM ->
// selector FF -> consumer FF. This is one local service slice, not a die bus.
module ot_v41_vm_bank4_registered_neighbor #(
    parameter integer DEPTH_GROUPS = 3,
    parameter integer AW = 15
) (
    input wire clk,
    input wire rst_n,
    input wire rd_v,
    input wire [AW-1:0] rd_base_word,
    input wire [3:0] wr_v,
    input wire [4*AW-1:0] wr_word_addr,
    input wire [2047:0] wr_word_data,
    output reg rd_out_v,
    output reg [1:0] rd_out_rot,
    output reg [2047:0] rd_out_bank_words,
    output reg rd_fault,
    output reg wr_fault,
    output reg rw_collision_fault
);
    reg rd_v_q;
    reg [AW-1:0] rd_base_q;
    reg [3:0] wr_v_q;
    reg [4*AW-1:0] wr_addr_q;
    reg [2047:0] wr_data_q;
    wire vm_rd_v, vm_rd_fault, vm_wr_fault, vm_coll_fault;
    wire [1:0] vm_rot;
    wire [2047:0] vm_data;

    always @(posedge clk) begin
        rd_v_q <= rd_v;
        rd_base_q <= rd_base_word;
        wr_v_q <= wr_v;
        wr_addr_q <= wr_word_addr;
        wr_data_q <= wr_word_data;
        rd_out_v <= vm_rd_v;
        rd_out_rot <= vm_rot;
        rd_out_bank_words <= vm_data;
        rd_fault <= vm_rd_fault;
        wr_fault <= vm_wr_fault;
        rw_collision_fault <= vm_coll_fault;
    end

    ot_v41_vm_bank4_macro_pipe #(.DEPTH_GROUPS(DEPTH_GROUPS), .AW(AW)) u_vm (
        .clk(clk), .rst_n(rst_n),
        .rd_v(rd_v_q), .rd_base_word(rd_base_q),
        .rd_out_v(vm_rd_v), .rd_out_rot(vm_rot),
        .rd_out_bank_words(vm_data), .rd_fault(vm_rd_fault),
        .wr_v(wr_v_q), .wr_word_addr(wr_addr_q), .wr_word_data(wr_data_q),
        .wr_fault(vm_wr_fault), .rw_collision_fault(vm_coll_fault)
    );
endmodule
