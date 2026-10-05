// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_hdc_v41x_attn_staging_3.a or libot_hdc_v41x_attn_staging_3.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_hdc_v41x_attn_staging_3 (
        input logic clk
        , input logic [3:0]  wr_en
        , input logic [7:0]  wr_addr
        , input logic [16959:0]  wr_data
        , input logic [7:0]  rd_addr
        , output logic [16959:0]  rd_data
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_hdc_v41x_attn_staging_3_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_hdc_v41x_attn_staging_3_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_hdc_v41x_attn_staging_3_protectlib_combo_update(
        chandle handle__V
        , input logic [3:0]  wr_en
        , input logic [7:0]  wr_addr
        , input logic [16959:0]  wr_data
        , input logic [7:0]  rd_addr
        , output logic [16959:0]  rd_data
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_hdc_v41x_attn_staging_3_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , output logic [16959:0]  rd_data
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_hdc_v41x_attn_staging_3_protectlib_combo_ignore(
        chandle handle__V
        , input logic [3:0]  wr_en
        , input logic [7:0]  wr_addr
        , input logic [16959:0]  wr_data
        , input logic [7:0]  rd_addr
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_hdc_v41x_attn_staging_3_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [16959:0]  rd_data_combo__V;
    logic [16959:0]  rd_data_seq__V;
    logic [16959:0]  rd_data_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd925575741;

    initial begin
        ot_hdc_v41x_attn_staging_3_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_hdc_v41x_attn_staging_3_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_hdc_v41x_attn_staging_3_protectlib_combo_update(
            handle__V,
            wr_en,
            wr_addr,
            wr_data,
            rd_addr,
            rd_data_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk) begin
        ot_hdc_v41x_attn_staging_3_protectlib_combo_ignore(
            handle__V,
            wr_en,
            wr_addr,
            wr_data,
            rd_addr
        );
        last_seq_seqnum__V <= ot_hdc_v41x_attn_staging_3_protectlib_seq_update(
            handle__V,
            clk,
            rd_data_tmp__V
        );
        rd_data_seq__V <= rd_data_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            rd_data = rd_data_seq__V;
        end else begin
            rd_data = rd_data_combo__V;
        end
    end
    
    final ot_hdc_v41x_attn_staging_3_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_hdc_v41x_attn_staging_3"
profile_data -hier-dpi "ot_hdc_v41x_attn_staging_3_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_hdc_v41x_attn_staging_3_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_hdc_v41x_attn_staging_3_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_hdc_v41x_attn_staging_3_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_hdc_v41x_attn_staging_3_protectlib_seq_update" -workers 16'd0
`verilog
`endif
