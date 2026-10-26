// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qkh_head_stk_native_6.a or libot_qkh_head_stk_native_6.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qkh_head_stk_native_6 (
        input logic clk
        , input logic rst_n
        , input logic [31:0]  kp_i
        , input logic kpv_i
        , input logic gf_i
        , output logic [31:0]  kp_o
        , output logic kpv_o
        , output logic gf_o
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qkh_head_stk_native_6_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qkh_head_stk_native_6_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qkh_head_stk_native_6_protectlib_combo_update(
        chandle handle__V
        , input logic [31:0]  kp_i
        , input logic kpv_i
        , input logic gf_i
        , output logic [31:0]  kp_o
        , output logic kpv_o
        , output logic gf_o
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qkh_head_stk_native_6_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , input logic rst_n
        , output logic [31:0]  kp_o
        , output logic kpv_o
        , output logic gf_o
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qkh_head_stk_native_6_protectlib_combo_ignore(
        chandle handle__V
        , input logic [31:0]  kp_i
        , input logic kpv_i
        , input logic gf_i
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qkh_head_stk_native_6_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [31:0]  kp_o_combo__V;
    logic kpv_o_combo__V;
    logic gf_o_combo__V;
    logic [31:0]  kp_o_seq__V;
    logic kpv_o_seq__V;
    logic gf_o_seq__V;
    logic [31:0]  kp_o_tmp__V;
    logic kpv_o_tmp__V;
    logic gf_o_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd733225002;

    initial begin
        ot_qkh_head_stk_native_6_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qkh_head_stk_native_6_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qkh_head_stk_native_6_protectlib_combo_update(
            handle__V,
            kp_i,
            kpv_i,
            gf_i,
            kp_o_combo__V,
            kpv_o_combo__V,
            gf_o_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk or rst_n) begin
        ot_qkh_head_stk_native_6_protectlib_combo_ignore(
            handle__V,
            kp_i,
            kpv_i,
            gf_i
        );
        last_seq_seqnum__V <= ot_qkh_head_stk_native_6_protectlib_seq_update(
            handle__V,
            clk,
            rst_n,
            kp_o_tmp__V,
            kpv_o_tmp__V,
            gf_o_tmp__V
        );
        kp_o_seq__V <= kp_o_tmp__V;
        kpv_o_seq__V <= kpv_o_tmp__V;
        gf_o_seq__V <= gf_o_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            kp_o = kp_o_seq__V;
            kpv_o = kpv_o_seq__V;
            gf_o = gf_o_seq__V;
        end else begin
            kp_o = kp_o_combo__V;
            kpv_o = kpv_o_combo__V;
            gf_o = gf_o_combo__V;
        end
    end
    
    final ot_qkh_head_stk_native_6_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qkh_head_stk_native_6"
profile_data -hier-dpi "ot_qkh_head_stk_native_6_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_head_stk_native_6_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_head_stk_native_6_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qkh_head_stk_native_6_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qkh_head_stk_native_6_protectlib_seq_update" -workers 16'd0
`verilog
`endif
