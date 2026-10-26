// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qwen_tp8_pv256_pair_c.a or libot_qwen_tp8_pv256_pair_c.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qwen_tp8_pv256_pair_c (
        input logic clk
        , input logic rst_n
        , input logic start
        , input logic [31:0]  slice_clk
        , input logic [13:0]  context_len
        , input logic [15:0]  epoch
        , input logic in_valid
        , output logic in_ready
        , input logic [1023:0]  in_v
        , input logic [63:0]  in_e
        , input logic [6:0]  in_c
        , input logic [13:0]  in_t
        , input logic [15:0]  in_epoch
        , input logic in_first
        , input logic in_last
        , output logic out_valid
        , input logic out_ready
        , output logic [16383:0]  out_leaf
        , output logic [6:0]  out_c
        , output logic [15:0]  out_epoch
        , output logic fault
        , output logic busy
        , output logic [31:0]  accepted
        , output logic [31:0]  committed
        , output logic [7:0]  peak_inflight
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qwen_tp8_pv256_pair_c_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qwen_tp8_pv256_pair_c_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qwen_tp8_pv256_pair_c_protectlib_combo_update(
        chandle handle__V
        , input logic start
        , input logic [13:0]  context_len
        , input logic [15:0]  epoch
        , input logic in_valid
        , output logic in_ready
        , input logic [1023:0]  in_v
        , input logic [63:0]  in_e
        , input logic [6:0]  in_c
        , input logic [13:0]  in_t
        , input logic [15:0]  in_epoch
        , input logic in_first
        , input logic in_last
        , output logic out_valid
        , input logic out_ready
        , output logic [16383:0]  out_leaf
        , output logic [6:0]  out_c
        , output logic [15:0]  out_epoch
        , output logic fault
        , output logic busy
        , output logic [31:0]  accepted
        , output logic [31:0]  committed
        , output logic [7:0]  peak_inflight
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qwen_tp8_pv256_pair_c_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , input logic rst_n
        , input logic [31:0]  slice_clk
        , output logic in_ready
        , output logic out_valid
        , output logic [16383:0]  out_leaf
        , output logic [6:0]  out_c
        , output logic [15:0]  out_epoch
        , output logic fault
        , output logic busy
        , output logic [31:0]  accepted
        , output logic [31:0]  committed
        , output logic [7:0]  peak_inflight
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qwen_tp8_pv256_pair_c_protectlib_combo_ignore(
        chandle handle__V
        , input logic start
        , input logic [13:0]  context_len
        , input logic [15:0]  epoch
        , input logic in_valid
        , input logic [1023:0]  in_v
        , input logic [63:0]  in_e
        , input logic [6:0]  in_c
        , input logic [13:0]  in_t
        , input logic [15:0]  in_epoch
        , input logic in_first
        , input logic in_last
        , input logic out_ready
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qwen_tp8_pv256_pair_c_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic in_ready_combo__V;
    logic out_valid_combo__V;
    logic [16383:0]  out_leaf_combo__V;
    logic [6:0]  out_c_combo__V;
    logic [15:0]  out_epoch_combo__V;
    logic fault_combo__V;
    logic busy_combo__V;
    logic [31:0]  accepted_combo__V;
    logic [31:0]  committed_combo__V;
    logic [7:0]  peak_inflight_combo__V;
    logic in_ready_seq__V;
    logic out_valid_seq__V;
    logic [16383:0]  out_leaf_seq__V;
    logic [6:0]  out_c_seq__V;
    logic [15:0]  out_epoch_seq__V;
    logic fault_seq__V;
    logic busy_seq__V;
    logic [31:0]  accepted_seq__V;
    logic [31:0]  committed_seq__V;
    logic [7:0]  peak_inflight_seq__V;
    logic in_ready_tmp__V;
    logic out_valid_tmp__V;
    logic [16383:0]  out_leaf_tmp__V;
    logic [6:0]  out_c_tmp__V;
    logic [15:0]  out_epoch_tmp__V;
    logic fault_tmp__V;
    logic busy_tmp__V;
    logic [31:0]  accepted_tmp__V;
    logic [31:0]  committed_tmp__V;
    logic [7:0]  peak_inflight_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd1209235692;

    initial begin
        ot_qwen_tp8_pv256_pair_c_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qwen_tp8_pv256_pair_c_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qwen_tp8_pv256_pair_c_protectlib_combo_update(
            handle__V,
            start,
            context_len,
            epoch,
            in_valid,
            in_ready_combo__V,
            in_v,
            in_e,
            in_c,
            in_t,
            in_epoch,
            in_first,
            in_last,
            out_valid_combo__V,
            out_ready,
            out_leaf_combo__V,
            out_c_combo__V,
            out_epoch_combo__V,
            fault_combo__V,
            busy_combo__V,
            accepted_combo__V,
            committed_combo__V,
            peak_inflight_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk or rst_n or slice_clk) begin
        ot_qwen_tp8_pv256_pair_c_protectlib_combo_ignore(
            handle__V,
            start,
            context_len,
            epoch,
            in_valid,
            in_v,
            in_e,
            in_c,
            in_t,
            in_epoch,
            in_first,
            in_last,
            out_ready
        );
        last_seq_seqnum__V <= ot_qwen_tp8_pv256_pair_c_protectlib_seq_update(
            handle__V,
            clk,
            rst_n,
            slice_clk,
            in_ready_tmp__V,
            out_valid_tmp__V,
            out_leaf_tmp__V,
            out_c_tmp__V,
            out_epoch_tmp__V,
            fault_tmp__V,
            busy_tmp__V,
            accepted_tmp__V,
            committed_tmp__V,
            peak_inflight_tmp__V
        );
        in_ready_seq__V <= in_ready_tmp__V;
        out_valid_seq__V <= out_valid_tmp__V;
        out_leaf_seq__V <= out_leaf_tmp__V;
        out_c_seq__V <= out_c_tmp__V;
        out_epoch_seq__V <= out_epoch_tmp__V;
        fault_seq__V <= fault_tmp__V;
        busy_seq__V <= busy_tmp__V;
        accepted_seq__V <= accepted_tmp__V;
        committed_seq__V <= committed_tmp__V;
        peak_inflight_seq__V <= peak_inflight_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            in_ready = in_ready_seq__V;
            out_valid = out_valid_seq__V;
            out_leaf = out_leaf_seq__V;
            out_c = out_c_seq__V;
            out_epoch = out_epoch_seq__V;
            fault = fault_seq__V;
            busy = busy_seq__V;
            accepted = accepted_seq__V;
            committed = committed_seq__V;
            peak_inflight = peak_inflight_seq__V;
        end else begin
            in_ready = in_ready_combo__V;
            out_valid = out_valid_combo__V;
            out_leaf = out_leaf_combo__V;
            out_c = out_c_combo__V;
            out_epoch = out_epoch_combo__V;
            fault = fault_combo__V;
            busy = busy_combo__V;
            accepted = accepted_combo__V;
            committed = committed_combo__V;
            peak_inflight = peak_inflight_combo__V;
        end
    end
    
    final ot_qwen_tp8_pv256_pair_c_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qwen_tp8_pv256_pair_c"
profile_data -hier-dpi "ot_qwen_tp8_pv256_pair_c_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qwen_tp8_pv256_pair_c_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qwen_tp8_pv256_pair_c_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qwen_tp8_pv256_pair_c_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qwen_tp8_pv256_pair_c_protectlib_seq_update" -workers 16'd0
`verilog
`endif
