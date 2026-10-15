// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qwen_tp8_pv256_slice.a or libot_qwen_tp8_pv256_slice.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qwen_tp8_pv256_slice (
        input logic clk
        , input logic rst_n
        , input logic take
        , input logic [6:0]  c
        , input logic init_zero
        , input logic [6:0]  init_c
        , input logic first
        , input logic [127:0]  v
        , input logic [15:0]  e
        , input logic read_leaf
        , input logic [6:0]  leaf_c
        , input logic reduce_issue
        , input logic reduce_capture
        , input logic reduce_last
        , input logic [6:0]  reduce_dst
        , output logic [511:0]  tree_sum
        , output logic [511:0]  leaf
        , output logic commit
        , output logic [6:0]  commit_c
        , output logic fault
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qwen_tp8_pv256_slice_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qwen_tp8_pv256_slice_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qwen_tp8_pv256_slice_protectlib_combo_update(
        chandle handle__V
        , input logic take
        , input logic [6:0]  c
        , input logic init_zero
        , input logic [6:0]  init_c
        , input logic first
        , input logic [127:0]  v
        , input logic [15:0]  e
        , input logic read_leaf
        , input logic [6:0]  leaf_c
        , input logic reduce_issue
        , input logic reduce_capture
        , input logic reduce_last
        , input logic [6:0]  reduce_dst
        , output logic [511:0]  tree_sum
        , output logic [511:0]  leaf
        , output logic commit
        , output logic [6:0]  commit_c
        , output logic fault
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qwen_tp8_pv256_slice_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , input logic rst_n
        , output logic [511:0]  tree_sum
        , output logic [511:0]  leaf
        , output logic commit
        , output logic [6:0]  commit_c
        , output logic fault
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qwen_tp8_pv256_slice_protectlib_combo_ignore(
        chandle handle__V
        , input logic take
        , input logic [6:0]  c
        , input logic init_zero
        , input logic [6:0]  init_c
        , input logic first
        , input logic [127:0]  v
        , input logic [15:0]  e
        , input logic read_leaf
        , input logic [6:0]  leaf_c
        , input logic reduce_issue
        , input logic reduce_capture
        , input logic reduce_last
        , input logic [6:0]  reduce_dst
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qwen_tp8_pv256_slice_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [511:0]  tree_sum_combo__V;
    logic [511:0]  leaf_combo__V;
    logic commit_combo__V;
    logic [6:0]  commit_c_combo__V;
    logic fault_combo__V;
    logic [511:0]  tree_sum_seq__V;
    logic [511:0]  leaf_seq__V;
    logic commit_seq__V;
    logic [6:0]  commit_c_seq__V;
    logic fault_seq__V;
    logic [511:0]  tree_sum_tmp__V;
    logic [511:0]  leaf_tmp__V;
    logic commit_tmp__V;
    logic [6:0]  commit_c_tmp__V;
    logic fault_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd3157830595;

    initial begin
        ot_qwen_tp8_pv256_slice_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qwen_tp8_pv256_slice_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qwen_tp8_pv256_slice_protectlib_combo_update(
            handle__V,
            take,
            c,
            init_zero,
            init_c,
            first,
            v,
            e,
            read_leaf,
            leaf_c,
            reduce_issue,
            reduce_capture,
            reduce_last,
            reduce_dst,
            tree_sum_combo__V,
            leaf_combo__V,
            commit_combo__V,
            commit_c_combo__V,
            fault_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk or rst_n) begin
        ot_qwen_tp8_pv256_slice_protectlib_combo_ignore(
            handle__V,
            take,
            c,
            init_zero,
            init_c,
            first,
            v,
            e,
            read_leaf,
            leaf_c,
            reduce_issue,
            reduce_capture,
            reduce_last,
            reduce_dst
        );
        last_seq_seqnum__V <= ot_qwen_tp8_pv256_slice_protectlib_seq_update(
            handle__V,
            clk,
            rst_n,
            tree_sum_tmp__V,
            leaf_tmp__V,
            commit_tmp__V,
            commit_c_tmp__V,
            fault_tmp__V
        );
        tree_sum_seq__V <= tree_sum_tmp__V;
        leaf_seq__V <= leaf_tmp__V;
        commit_seq__V <= commit_tmp__V;
        commit_c_seq__V <= commit_c_tmp__V;
        fault_seq__V <= fault_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            tree_sum = tree_sum_seq__V;
            leaf = leaf_seq__V;
            commit = commit_seq__V;
            commit_c = commit_c_seq__V;
            fault = fault_seq__V;
        end else begin
            tree_sum = tree_sum_combo__V;
            leaf = leaf_combo__V;
            commit = commit_combo__V;
            commit_c = commit_c_combo__V;
            fault = fault_combo__V;
        end
    end
    
    final ot_qwen_tp8_pv256_slice_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qwen_tp8_pv256_slice"
profile_data -hier-dpi "ot_qwen_tp8_pv256_slice_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qwen_tp8_pv256_slice_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qwen_tp8_pv256_slice_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qwen_tp8_pv256_slice_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qwen_tp8_pv256_slice_protectlib_seq_update" -workers 16'd0
`verilog
`endif
