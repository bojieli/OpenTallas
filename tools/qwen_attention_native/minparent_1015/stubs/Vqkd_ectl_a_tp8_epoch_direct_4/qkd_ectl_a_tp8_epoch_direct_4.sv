// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libqkd_ectl_a_tp8_epoch_direct_4.a or libqkd_ectl_a_tp8_epoch_direct_4.so to work
// See instructions in your simulator for how to use DPI libraries

module qkd_ectl_a_tp8_epoch_direct_4 (
        input logic ck
        , input logic rst_n
        , input logic [4:0]  cfg
        , output logic [16:0]  rq
        , input logic [1024:0]  rs
        , output logic [511:0]  t0_row
        , output logic [511:0]  t1_row
        , input logic [51:0]  x_i
        , output logic [512:0]  rs_o
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void qkd_ectl_a_tp8_epoch_direct_4_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle qkd_ectl_a_tp8_epoch_direct_4_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint qkd_ectl_a_tp8_epoch_direct_4_protectlib_combo_update(
        chandle handle__V
        , input logic [4:0]  cfg
        , output logic [16:0]  rq
        , input logic [1024:0]  rs
        , output logic [511:0]  t0_row
        , output logic [511:0]  t1_row
        , input logic [51:0]  x_i
        , output logic [512:0]  rs_o
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint qkd_ectl_a_tp8_epoch_direct_4_protectlib_seq_update(
        chandle handle__V
        , input logic ck
        , input logic rst_n
        , output logic [16:0]  rq
        , output logic [511:0]  t0_row
        , output logic [511:0]  t1_row
        , output logic [512:0]  rs_o
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void qkd_ectl_a_tp8_epoch_direct_4_protectlib_combo_ignore(
        chandle handle__V
        , input logic [4:0]  cfg
        , input logic [1024:0]  rs
        , input logic [51:0]  x_i
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void qkd_ectl_a_tp8_epoch_direct_4_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [16:0]  rq_combo__V;
    logic [511:0]  t0_row_combo__V;
    logic [511:0]  t1_row_combo__V;
    logic [512:0]  rs_o_combo__V;
    logic [16:0]  rq_seq__V;
    logic [511:0]  t0_row_seq__V;
    logic [511:0]  t1_row_seq__V;
    logic [512:0]  rs_o_seq__V;
    logic [16:0]  rq_tmp__V;
    logic [511:0]  t0_row_tmp__V;
    logic [511:0]  t1_row_tmp__V;
    logic [512:0]  rs_o_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd2029193212;

    initial begin
        qkd_ectl_a_tp8_epoch_direct_4_protectlib_check_hash(protectlib_hash__V);
        handle__V = qkd_ectl_a_tp8_epoch_direct_4_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = qkd_ectl_a_tp8_epoch_direct_4_protectlib_combo_update(
            handle__V,
            cfg,
            rq_combo__V,
            rs,
            t0_row_combo__V,
            t1_row_combo__V,
            x_i,
            rs_o_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(ck or rst_n) begin
        qkd_ectl_a_tp8_epoch_direct_4_protectlib_combo_ignore(
            handle__V,
            cfg,
            rs,
            x_i
        );
        last_seq_seqnum__V <= qkd_ectl_a_tp8_epoch_direct_4_protectlib_seq_update(
            handle__V,
            ck,
            rst_n,
            rq_tmp__V,
            t0_row_tmp__V,
            t1_row_tmp__V,
            rs_o_tmp__V
        );
        rq_seq__V <= rq_tmp__V;
        t0_row_seq__V <= t0_row_tmp__V;
        t1_row_seq__V <= t1_row_tmp__V;
        rs_o_seq__V <= rs_o_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            rq = rq_seq__V;
            t0_row = t0_row_seq__V;
            t1_row = t1_row_seq__V;
            rs_o = rs_o_seq__V;
        end else begin
            rq = rq_combo__V;
            t0_row = t0_row_combo__V;
            t1_row = t1_row_combo__V;
            rs_o = rs_o_combo__V;
        end
    end
    
    final qkd_ectl_a_tp8_epoch_direct_4_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "qkd_ectl_a_tp8_epoch_direct_4"
profile_data -hier-dpi "qkd_ectl_a_tp8_epoch_direct_4_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "qkd_ectl_a_tp8_epoch_direct_4_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "qkd_ectl_a_tp8_epoch_direct_4_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "qkd_ectl_a_tp8_epoch_direct_4_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "qkd_ectl_a_tp8_epoch_direct_4_protectlib_seq_update" -workers 16'd0
`verilog
`endif
