// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qkh_ktree_9.a or libot_qkh_ktree_9.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qkh_ktree_9 (
        input logic clk
        , input logic rst_n
        , input logic [511:0]  kp_in
        , input logic kpv_in
        , input logic [15:0]  gf_in
        , output logic [31:0]  sc_d
        , output logic sc_f
        , output logic g_f
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qkh_ktree_9_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qkh_ktree_9_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qkh_ktree_9_protectlib_combo_update(
        chandle handle__V
        , input logic [511:0]  kp_in
        , input logic kpv_in
        , input logic [15:0]  gf_in
        , output logic [31:0]  sc_d
        , output logic sc_f
        , output logic g_f
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qkh_ktree_9_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , input logic rst_n
        , output logic [31:0]  sc_d
        , output logic sc_f
        , output logic g_f
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qkh_ktree_9_protectlib_combo_ignore(
        chandle handle__V
        , input logic [511:0]  kp_in
        , input logic kpv_in
        , input logic [15:0]  gf_in
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qkh_ktree_9_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [31:0]  sc_d_combo__V;
    logic sc_f_combo__V;
    logic g_f_combo__V;
    logic [31:0]  sc_d_seq__V;
    logic sc_f_seq__V;
    logic g_f_seq__V;
    logic [31:0]  sc_d_tmp__V;
    logic sc_f_tmp__V;
    logic g_f_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd3154571739;

    initial begin
        ot_qkh_ktree_9_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qkh_ktree_9_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qkh_ktree_9_protectlib_combo_update(
            handle__V,
            kp_in,
            kpv_in,
            gf_in,
            sc_d_combo__V,
            sc_f_combo__V,
            g_f_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk or rst_n) begin
        ot_qkh_ktree_9_protectlib_combo_ignore(
            handle__V,
            kp_in,
            kpv_in,
            gf_in
        );
        last_seq_seqnum__V <= ot_qkh_ktree_9_protectlib_seq_update(
            handle__V,
            clk,
            rst_n,
            sc_d_tmp__V,
            sc_f_tmp__V,
            g_f_tmp__V
        );
        sc_d_seq__V <= sc_d_tmp__V;
        sc_f_seq__V <= sc_f_tmp__V;
        g_f_seq__V <= g_f_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            sc_d = sc_d_seq__V;
            sc_f = sc_f_seq__V;
            g_f = g_f_seq__V;
        end else begin
            sc_d = sc_d_combo__V;
            sc_f = sc_f_combo__V;
            g_f = g_f_combo__V;
        end
    end
    
    final ot_qkh_ktree_9_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qkh_ktree_9"
profile_data -hier-dpi "ot_qkh_ktree_9_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_ktree_9_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_ktree_9_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qkh_ktree_9_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qkh_ktree_9_protectlib_seq_update" -workers 16'd0
`verilog
`endif
