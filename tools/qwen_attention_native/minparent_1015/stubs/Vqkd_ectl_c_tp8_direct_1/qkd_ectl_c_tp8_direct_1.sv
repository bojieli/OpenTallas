// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libqkd_ectl_c_tp8_direct_1.a or libqkd_ectl_c_tp8_direct_1.so to work
// See instructions in your simulator for how to use DPI libraries

module qkd_ectl_c_tp8_direct_1 (
        input logic ck
        , input logic rst_n
        , input logic [4:0]  cfg
        , input logic [633:0]  si
        , output logic [424:0]  so
        , output logic [15:0]  e0
        , output logic [15:0]  e1
        , output logic [15:0]  e2
        , output logic [15:0]  e3
        , input logic [33:0]  s0
        , input logic [33:0]  s1
        , input logic [33:0]  s2
        , input logic [33:0]  s3
        , output logic [518:0]  t0_q
        , output logic [518:0]  t1_q
        , input logic rsv_i
        , output logic [51:0]  x_b
        , output logic [51:0]  x_a
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void qkd_ectl_c_tp8_direct_1_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle qkd_ectl_c_tp8_direct_1_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint qkd_ectl_c_tp8_direct_1_protectlib_combo_update(
        chandle handle__V
        , input logic [4:0]  cfg
        , input logic [633:0]  si
        , output logic [424:0]  so
        , output logic [15:0]  e0
        , output logic [15:0]  e1
        , output logic [15:0]  e2
        , output logic [15:0]  e3
        , input logic [33:0]  s0
        , input logic [33:0]  s1
        , input logic [33:0]  s2
        , input logic [33:0]  s3
        , output logic [518:0]  t0_q
        , output logic [518:0]  t1_q
        , input logic rsv_i
        , output logic [51:0]  x_b
        , output logic [51:0]  x_a
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint qkd_ectl_c_tp8_direct_1_protectlib_seq_update(
        chandle handle__V
        , input logic ck
        , input logic rst_n
        , output logic [424:0]  so
        , output logic [15:0]  e0
        , output logic [15:0]  e1
        , output logic [15:0]  e2
        , output logic [15:0]  e3
        , output logic [518:0]  t0_q
        , output logic [518:0]  t1_q
        , output logic [51:0]  x_b
        , output logic [51:0]  x_a
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void qkd_ectl_c_tp8_direct_1_protectlib_combo_ignore(
        chandle handle__V
        , input logic [4:0]  cfg
        , input logic [633:0]  si
        , input logic [33:0]  s0
        , input logic [33:0]  s1
        , input logic [33:0]  s2
        , input logic [33:0]  s3
        , input logic rsv_i
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void qkd_ectl_c_tp8_direct_1_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [424:0]  so_combo__V;
    logic [15:0]  e0_combo__V;
    logic [15:0]  e1_combo__V;
    logic [15:0]  e2_combo__V;
    logic [15:0]  e3_combo__V;
    logic [518:0]  t0_q_combo__V;
    logic [518:0]  t1_q_combo__V;
    logic [51:0]  x_b_combo__V;
    logic [51:0]  x_a_combo__V;
    logic [424:0]  so_seq__V;
    logic [15:0]  e0_seq__V;
    logic [15:0]  e1_seq__V;
    logic [15:0]  e2_seq__V;
    logic [15:0]  e3_seq__V;
    logic [518:0]  t0_q_seq__V;
    logic [518:0]  t1_q_seq__V;
    logic [51:0]  x_b_seq__V;
    logic [51:0]  x_a_seq__V;
    logic [424:0]  so_tmp__V;
    logic [15:0]  e0_tmp__V;
    logic [15:0]  e1_tmp__V;
    logic [15:0]  e2_tmp__V;
    logic [15:0]  e3_tmp__V;
    logic [518:0]  t0_q_tmp__V;
    logic [518:0]  t1_q_tmp__V;
    logic [51:0]  x_b_tmp__V;
    logic [51:0]  x_a_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd2257696187;

    initial begin
        qkd_ectl_c_tp8_direct_1_protectlib_check_hash(protectlib_hash__V);
        handle__V = qkd_ectl_c_tp8_direct_1_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = qkd_ectl_c_tp8_direct_1_protectlib_combo_update(
            handle__V,
            cfg,
            si,
            so_combo__V,
            e0_combo__V,
            e1_combo__V,
            e2_combo__V,
            e3_combo__V,
            s0,
            s1,
            s2,
            s3,
            t0_q_combo__V,
            t1_q_combo__V,
            rsv_i,
            x_b_combo__V,
            x_a_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(ck or rst_n) begin
        qkd_ectl_c_tp8_direct_1_protectlib_combo_ignore(
            handle__V,
            cfg,
            si,
            s0,
            s1,
            s2,
            s3,
            rsv_i
        );
        last_seq_seqnum__V <= qkd_ectl_c_tp8_direct_1_protectlib_seq_update(
            handle__V,
            ck,
            rst_n,
            so_tmp__V,
            e0_tmp__V,
            e1_tmp__V,
            e2_tmp__V,
            e3_tmp__V,
            t0_q_tmp__V,
            t1_q_tmp__V,
            x_b_tmp__V,
            x_a_tmp__V
        );
        so_seq__V <= so_tmp__V;
        e0_seq__V <= e0_tmp__V;
        e1_seq__V <= e1_tmp__V;
        e2_seq__V <= e2_tmp__V;
        e3_seq__V <= e3_tmp__V;
        t0_q_seq__V <= t0_q_tmp__V;
        t1_q_seq__V <= t1_q_tmp__V;
        x_b_seq__V <= x_b_tmp__V;
        x_a_seq__V <= x_a_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            so = so_seq__V;
            e0 = e0_seq__V;
            e1 = e1_seq__V;
            e2 = e2_seq__V;
            e3 = e3_seq__V;
            t0_q = t0_q_seq__V;
            t1_q = t1_q_seq__V;
            x_b = x_b_seq__V;
            x_a = x_a_seq__V;
        end else begin
            so = so_combo__V;
            e0 = e0_combo__V;
            e1 = e1_combo__V;
            e2 = e2_combo__V;
            e3 = e3_combo__V;
            t0_q = t0_q_combo__V;
            t1_q = t1_q_combo__V;
            x_b = x_b_combo__V;
            x_a = x_a_combo__V;
        end
    end
    
    final qkd_ectl_c_tp8_direct_1_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "qkd_ectl_c_tp8_direct_1"
profile_data -hier-dpi "qkd_ectl_c_tp8_direct_1_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "qkd_ectl_c_tp8_direct_1_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "qkd_ectl_c_tp8_direct_1_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "qkd_ectl_c_tp8_direct_1_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "qkd_ectl_c_tp8_direct_1_protectlib_seq_update" -workers 16'd0
`verilog
`endif
