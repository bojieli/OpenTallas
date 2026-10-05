// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_hdc_v41x_attn_tile_e.a or libot_hdc_v41x_attn_tile_e.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_hdc_v41x_attn_tile_e (
        input logic clk
        , input logic rst_n
        , input logic ld_v
        , input logic ld_mode
        , input logic [1:0]  ld_bank
        , input logic [7:0]  ld_grp
        , input logic [511:0]  ld_w
        , input logic ld_w2v
        , input logic iv
        , input logic [1:0]  ibank
        , input logic [575:0]  ib
        , output logic ov
        , output logic [511:0]  oy
        , output logic [15:0]  oflt
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_hdc_v41x_attn_tile_e_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_hdc_v41x_attn_tile_e_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_hdc_v41x_attn_tile_e_protectlib_combo_update(
        chandle handle__V
        , input logic ld_v
        , input logic ld_mode
        , input logic [1:0]  ld_bank
        , input logic [7:0]  ld_grp
        , input logic [511:0]  ld_w
        , input logic ld_w2v
        , input logic iv
        , input logic [1:0]  ibank
        , input logic [575:0]  ib
        , output logic ov
        , output logic [511:0]  oy
        , output logic [15:0]  oflt
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_hdc_v41x_attn_tile_e_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , input logic rst_n
        , output logic ov
        , output logic [511:0]  oy
        , output logic [15:0]  oflt
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_hdc_v41x_attn_tile_e_protectlib_combo_ignore(
        chandle handle__V
        , input logic ld_v
        , input logic ld_mode
        , input logic [1:0]  ld_bank
        , input logic [7:0]  ld_grp
        , input logic [511:0]  ld_w
        , input logic ld_w2v
        , input logic iv
        , input logic [1:0]  ibank
        , input logic [575:0]  ib
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_hdc_v41x_attn_tile_e_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic ov_combo__V;
    logic [511:0]  oy_combo__V;
    logic [15:0]  oflt_combo__V;
    logic ov_seq__V;
    logic [511:0]  oy_seq__V;
    logic [15:0]  oflt_seq__V;
    logic ov_tmp__V;
    logic [511:0]  oy_tmp__V;
    logic [15:0]  oflt_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd3454275873;

    initial begin
        ot_hdc_v41x_attn_tile_e_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_hdc_v41x_attn_tile_e_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_hdc_v41x_attn_tile_e_protectlib_combo_update(
            handle__V,
            ld_v,
            ld_mode,
            ld_bank,
            ld_grp,
            ld_w,
            ld_w2v,
            iv,
            ibank,
            ib,
            ov_combo__V,
            oy_combo__V,
            oflt_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk or rst_n) begin
        ot_hdc_v41x_attn_tile_e_protectlib_combo_ignore(
            handle__V,
            ld_v,
            ld_mode,
            ld_bank,
            ld_grp,
            ld_w,
            ld_w2v,
            iv,
            ibank,
            ib
        );
        last_seq_seqnum__V <= ot_hdc_v41x_attn_tile_e_protectlib_seq_update(
            handle__V,
            clk,
            rst_n,
            ov_tmp__V,
            oy_tmp__V,
            oflt_tmp__V
        );
        ov_seq__V <= ov_tmp__V;
        oy_seq__V <= oy_tmp__V;
        oflt_seq__V <= oflt_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            ov = ov_seq__V;
            oy = oy_seq__V;
            oflt = oflt_seq__V;
        end else begin
            ov = ov_combo__V;
            oy = oy_combo__V;
            oflt = oflt_combo__V;
        end
    end
    
    final ot_hdc_v41x_attn_tile_e_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_hdc_v41x_attn_tile_e"
profile_data -hier-dpi "ot_hdc_v41x_attn_tile_e_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_hdc_v41x_attn_tile_e_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_hdc_v41x_attn_tile_e_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_hdc_v41x_attn_tile_e_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_hdc_v41x_attn_tile_e_protectlib_seq_update" -workers 16'd0
`verilog
`endif
