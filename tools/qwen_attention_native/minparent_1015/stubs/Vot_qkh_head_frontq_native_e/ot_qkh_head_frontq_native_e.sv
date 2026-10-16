// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qkh_head_frontq_native_e.a or libot_qkh_head_frontq_native_e.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qkh_head_frontq_native_e (
        input logic clk
        , input logic rst_n
        , input logic [3:0]  c_in
        , input logic [255:0]  row_in
        , input logic [15:0]  e_in
        , input logic [11:0]  lt_in
        , input logic [1:0]  hid
        , input logic q_valid_in
        , input logic [5:0]  q_beat_in
        , input logic [511:0]  q_data_in
        , output logic [232:0]  f_t0
        , output logic [232:0]  f_t1
        , output logic [232:0]  f_t2
        , output logic [232:0]  f_t3
        , output logic pack_fault
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qkh_head_frontq_native_e_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qkh_head_frontq_native_e_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qkh_head_frontq_native_e_protectlib_combo_update(
        chandle handle__V
        , input logic [3:0]  c_in
        , input logic [255:0]  row_in
        , input logic [15:0]  e_in
        , input logic [11:0]  lt_in
        , input logic [1:0]  hid
        , input logic q_valid_in
        , input logic [5:0]  q_beat_in
        , input logic [511:0]  q_data_in
        , output logic [232:0]  f_t0
        , output logic [232:0]  f_t1
        , output logic [232:0]  f_t2
        , output logic [232:0]  f_t3
        , output logic pack_fault
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qkh_head_frontq_native_e_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , input logic rst_n
        , output logic [232:0]  f_t0
        , output logic [232:0]  f_t1
        , output logic [232:0]  f_t2
        , output logic [232:0]  f_t3
        , output logic pack_fault
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qkh_head_frontq_native_e_protectlib_combo_ignore(
        chandle handle__V
        , input logic [3:0]  c_in
        , input logic [255:0]  row_in
        , input logic [15:0]  e_in
        , input logic [11:0]  lt_in
        , input logic [1:0]  hid
        , input logic q_valid_in
        , input logic [5:0]  q_beat_in
        , input logic [511:0]  q_data_in
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qkh_head_frontq_native_e_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [232:0]  f_t0_combo__V;
    logic [232:0]  f_t1_combo__V;
    logic [232:0]  f_t2_combo__V;
    logic [232:0]  f_t3_combo__V;
    logic pack_fault_combo__V;
    logic [232:0]  f_t0_seq__V;
    logic [232:0]  f_t1_seq__V;
    logic [232:0]  f_t2_seq__V;
    logic [232:0]  f_t3_seq__V;
    logic pack_fault_seq__V;
    logic [232:0]  f_t0_tmp__V;
    logic [232:0]  f_t1_tmp__V;
    logic [232:0]  f_t2_tmp__V;
    logic [232:0]  f_t3_tmp__V;
    logic pack_fault_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd3899753476;

    initial begin
        ot_qkh_head_frontq_native_e_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qkh_head_frontq_native_e_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qkh_head_frontq_native_e_protectlib_combo_update(
            handle__V,
            c_in,
            row_in,
            e_in,
            lt_in,
            hid,
            q_valid_in,
            q_beat_in,
            q_data_in,
            f_t0_combo__V,
            f_t1_combo__V,
            f_t2_combo__V,
            f_t3_combo__V,
            pack_fault_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk or rst_n) begin
        ot_qkh_head_frontq_native_e_protectlib_combo_ignore(
            handle__V,
            c_in,
            row_in,
            e_in,
            lt_in,
            hid,
            q_valid_in,
            q_beat_in,
            q_data_in
        );
        last_seq_seqnum__V <= ot_qkh_head_frontq_native_e_protectlib_seq_update(
            handle__V,
            clk,
            rst_n,
            f_t0_tmp__V,
            f_t1_tmp__V,
            f_t2_tmp__V,
            f_t3_tmp__V,
            pack_fault_tmp__V
        );
        f_t0_seq__V <= f_t0_tmp__V;
        f_t1_seq__V <= f_t1_tmp__V;
        f_t2_seq__V <= f_t2_tmp__V;
        f_t3_seq__V <= f_t3_tmp__V;
        pack_fault_seq__V <= pack_fault_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            f_t0 = f_t0_seq__V;
            f_t1 = f_t1_seq__V;
            f_t2 = f_t2_seq__V;
            f_t3 = f_t3_seq__V;
            pack_fault = pack_fault_seq__V;
        end else begin
            f_t0 = f_t0_combo__V;
            f_t1 = f_t1_combo__V;
            f_t2 = f_t2_combo__V;
            f_t3 = f_t3_combo__V;
            pack_fault = pack_fault_combo__V;
        end
    end
    
    final ot_qkh_head_frontq_native_e_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qkh_head_frontq_native_e"
profile_data -hier-dpi "ot_qkh_head_frontq_native_e_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_head_frontq_native_e_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_head_frontq_native_e_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qkh_head_frontq_native_e_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qkh_head_frontq_native_e_protectlib_seq_update" -workers 16'd0
`verilog
`endif
