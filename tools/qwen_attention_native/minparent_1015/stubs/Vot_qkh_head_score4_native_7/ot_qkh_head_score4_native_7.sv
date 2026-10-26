// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qkh_head_score4_native_7.a or libot_qkh_head_score4_native_7.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qkh_head_score4_native_7 (
        input logic clk
        , input logic rst_n
        , input logic [31:0]  sc_i
        , input logic sf_i
        , input logic gf_i
        , input logic [3:0]  pack_fault
        , output logic [31:0]  sc_o
        , output logic sf_o
        , output logic gf_o
        , output logic kt_rst_n
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qkh_head_score4_native_7_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qkh_head_score4_native_7_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qkh_head_score4_native_7_protectlib_combo_update(
        chandle handle__V
        , input logic [31:0]  sc_i
        , input logic sf_i
        , input logic gf_i
        , input logic [3:0]  pack_fault
        , output logic [31:0]  sc_o
        , output logic sf_o
        , output logic gf_o
        , output logic kt_rst_n
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qkh_head_score4_native_7_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , input logic rst_n
        , output logic [31:0]  sc_o
        , output logic sf_o
        , output logic gf_o
        , output logic kt_rst_n
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qkh_head_score4_native_7_protectlib_combo_ignore(
        chandle handle__V
        , input logic [31:0]  sc_i
        , input logic sf_i
        , input logic gf_i
        , input logic [3:0]  pack_fault
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qkh_head_score4_native_7_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [31:0]  sc_o_combo__V;
    logic sf_o_combo__V;
    logic gf_o_combo__V;
    logic kt_rst_n_combo__V;
    logic [31:0]  sc_o_seq__V;
    logic sf_o_seq__V;
    logic gf_o_seq__V;
    logic kt_rst_n_seq__V;
    logic [31:0]  sc_o_tmp__V;
    logic sf_o_tmp__V;
    logic gf_o_tmp__V;
    logic kt_rst_n_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd3466640850;

    initial begin
        ot_qkh_head_score4_native_7_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qkh_head_score4_native_7_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qkh_head_score4_native_7_protectlib_combo_update(
            handle__V,
            sc_i,
            sf_i,
            gf_i,
            pack_fault,
            sc_o_combo__V,
            sf_o_combo__V,
            gf_o_combo__V,
            kt_rst_n_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk or rst_n) begin
        ot_qkh_head_score4_native_7_protectlib_combo_ignore(
            handle__V,
            sc_i,
            sf_i,
            gf_i,
            pack_fault
        );
        last_seq_seqnum__V <= ot_qkh_head_score4_native_7_protectlib_seq_update(
            handle__V,
            clk,
            rst_n,
            sc_o_tmp__V,
            sf_o_tmp__V,
            gf_o_tmp__V,
            kt_rst_n_tmp__V
        );
        sc_o_seq__V <= sc_o_tmp__V;
        sf_o_seq__V <= sf_o_tmp__V;
        gf_o_seq__V <= gf_o_tmp__V;
        kt_rst_n_seq__V <= kt_rst_n_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            sc_o = sc_o_seq__V;
            sf_o = sf_o_seq__V;
            gf_o = gf_o_seq__V;
            kt_rst_n = kt_rst_n_seq__V;
        end else begin
            sc_o = sc_o_combo__V;
            sf_o = sf_o_combo__V;
            gf_o = gf_o_combo__V;
            kt_rst_n = kt_rst_n_combo__V;
        end
    end
    
    final ot_qkh_head_score4_native_7_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qkh_head_score4_native_7"
profile_data -hier-dpi "ot_qkh_head_score4_native_7_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_head_score4_native_7_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_head_score4_native_7_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qkh_head_score4_native_7_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qkh_head_score4_native_7_protectlib_seq_update" -workers 16'd0
`verilog
`endif
