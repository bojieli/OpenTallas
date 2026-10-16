// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_nhb_zh.a or libot_nhb_zh.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_nhb_zh (
        input logic clk
        , input logic rst_n
        , input logic start
        , input logic [127:0]  zs_we
        , input logic [127:0]  sid
        , input logic [3:0]  ziv
        , input logic zg
        , input logic [5:0]  zp
        , output logic [63:0]  root
        , output logic [3:0]  zerr
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_nhb_zh_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_nhb_zh_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_nhb_zh_protectlib_combo_update(
        chandle handle__V
        , input logic start
        , input logic [127:0]  zs_we
        , input logic [127:0]  sid
        , input logic [3:0]  ziv
        , input logic zg
        , input logic [5:0]  zp
        , output logic [63:0]  root
        , output logic [3:0]  zerr
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_nhb_zh_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , input logic rst_n
        , output logic [63:0]  root
        , output logic [3:0]  zerr
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_nhb_zh_protectlib_combo_ignore(
        chandle handle__V
        , input logic start
        , input logic [127:0]  zs_we
        , input logic [127:0]  sid
        , input logic [3:0]  ziv
        , input logic zg
        , input logic [5:0]  zp
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_nhb_zh_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [63:0]  root_combo__V;
    logic [3:0]  zerr_combo__V;
    logic [63:0]  root_seq__V;
    logic [3:0]  zerr_seq__V;
    logic [63:0]  root_tmp__V;
    logic [3:0]  zerr_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd3739146447;

    initial begin
        ot_nhb_zh_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_nhb_zh_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_nhb_zh_protectlib_combo_update(
            handle__V,
            start,
            zs_we,
            sid,
            ziv,
            zg,
            zp,
            root_combo__V,
            zerr_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk or rst_n) begin
        ot_nhb_zh_protectlib_combo_ignore(
            handle__V,
            start,
            zs_we,
            sid,
            ziv,
            zg,
            zp
        );
        last_seq_seqnum__V <= ot_nhb_zh_protectlib_seq_update(
            handle__V,
            clk,
            rst_n,
            root_tmp__V,
            zerr_tmp__V
        );
        root_seq__V <= root_tmp__V;
        zerr_seq__V <= zerr_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            root = root_seq__V;
            zerr = zerr_seq__V;
        end else begin
            root = root_combo__V;
            zerr = zerr_combo__V;
        end
    end
    
    final ot_nhb_zh_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_nhb_zh"
profile_data -hier-dpi "ot_nhb_zh_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_nhb_zh_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_nhb_zh_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_nhb_zh_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_nhb_zh_protectlib_seq_update" -workers 16'd0
`verilog
`endif
