// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qkh_head_nb_native_0.a or libot_qkh_head_nb_native_0.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qkh_head_nb_native_0 (
        input logic clk
        , input logic [63:0]  nb_i
        , output logic [63:0]  nb_o
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qkh_head_nb_native_0_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qkh_head_nb_native_0_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qkh_head_nb_native_0_protectlib_combo_update(
        chandle handle__V
        , input logic [63:0]  nb_i
        , output logic [63:0]  nb_o
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qkh_head_nb_native_0_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , output logic [63:0]  nb_o
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qkh_head_nb_native_0_protectlib_combo_ignore(
        chandle handle__V
        , input logic [63:0]  nb_i
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qkh_head_nb_native_0_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [63:0]  nb_o_combo__V;
    logic [63:0]  nb_o_seq__V;
    logic [63:0]  nb_o_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd694847454;

    initial begin
        ot_qkh_head_nb_native_0_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qkh_head_nb_native_0_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qkh_head_nb_native_0_protectlib_combo_update(
            handle__V,
            nb_i,
            nb_o_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk) begin
        ot_qkh_head_nb_native_0_protectlib_combo_ignore(
            handle__V,
            nb_i
        );
        last_seq_seqnum__V <= ot_qkh_head_nb_native_0_protectlib_seq_update(
            handle__V,
            clk,
            nb_o_tmp__V
        );
        nb_o_seq__V <= nb_o_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            nb_o = nb_o_seq__V;
        end else begin
            nb_o = nb_o_combo__V;
        end
    end
    
    final ot_qkh_head_nb_native_0_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qkh_head_nb_native_0"
profile_data -hier-dpi "ot_qkh_head_nb_native_0_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_head_nb_native_0_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_head_nb_native_0_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qkh_head_nb_native_0_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qkh_head_nb_native_0_protectlib_seq_update" -workers 16'd0
`verilog
`endif
