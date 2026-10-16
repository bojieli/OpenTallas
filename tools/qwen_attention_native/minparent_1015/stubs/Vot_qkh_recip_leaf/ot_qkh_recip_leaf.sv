// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qkh_recip_leaf.a or libot_qkh_recip_leaf.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qkh_recip_leaf (
        input logic clk
        , input logic rst_n
        , input logic v
        , input logic [31:0]  x
        , output logic [31:0]  y
        , output logic vo
        , output logic fault
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qkh_recip_leaf_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qkh_recip_leaf_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qkh_recip_leaf_protectlib_combo_update(
        chandle handle__V
        , input logic v
        , input logic [31:0]  x
        , output logic [31:0]  y
        , output logic vo
        , output logic fault
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qkh_recip_leaf_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , input logic rst_n
        , output logic [31:0]  y
        , output logic vo
        , output logic fault
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qkh_recip_leaf_protectlib_combo_ignore(
        chandle handle__V
        , input logic v
        , input logic [31:0]  x
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qkh_recip_leaf_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [31:0]  y_combo__V;
    logic vo_combo__V;
    logic fault_combo__V;
    logic [31:0]  y_seq__V;
    logic vo_seq__V;
    logic fault_seq__V;
    logic [31:0]  y_tmp__V;
    logic vo_tmp__V;
    logic fault_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd2861403938;

    initial begin
        ot_qkh_recip_leaf_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qkh_recip_leaf_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qkh_recip_leaf_protectlib_combo_update(
            handle__V,
            v,
            x,
            y_combo__V,
            vo_combo__V,
            fault_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk or rst_n) begin
        ot_qkh_recip_leaf_protectlib_combo_ignore(
            handle__V,
            v,
            x
        );
        last_seq_seqnum__V <= ot_qkh_recip_leaf_protectlib_seq_update(
            handle__V,
            clk,
            rst_n,
            y_tmp__V,
            vo_tmp__V,
            fault_tmp__V
        );
        y_seq__V <= y_tmp__V;
        vo_seq__V <= vo_tmp__V;
        fault_seq__V <= fault_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            y = y_seq__V;
            vo = vo_seq__V;
            fault = fault_seq__V;
        end else begin
            y = y_combo__V;
            vo = vo_combo__V;
            fault = fault_combo__V;
        end
    end
    
    final ot_qkh_recip_leaf_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qkh_recip_leaf"
profile_data -hier-dpi "ot_qkh_recip_leaf_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_recip_leaf_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_recip_leaf_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qkh_recip_leaf_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qkh_recip_leaf_protectlib_seq_update" -workers 16'd0
`verilog
`endif
