// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qwen_tp8_attention_native_stack_cp_c.a or libot_qwen_tp8_attention_native_stack_cp_c.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qwen_tp8_attention_native_stack_cp_c (
        input logic [47:0]  cal
        , input logic [1:0]  stack_id
        , input logic clk
        , input logic rst_n
        , input logic [539:0]  aq
        , input logic [35:0]  am
        , output logic [562:0]  ap
        , input logic active_layer_parity
        , output logic [135:0]  k_request
        , input logic [8199:0]  k_response
        , input logic er_v
        , input logic [10:0]  er_addr
        , output logic er_rsp_v
        , output logic [10:0]  er_rsp_addr
        , output logic [63:0]  er_data
        , output logic [15:0]  exp_committed
        , output logic score_committed
        , output logic fault
        , output logic [7:0]  dbg
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qwen_tp8_attention_native_stack_cp_c_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qwen_tp8_attention_native_stack_cp_c_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qwen_tp8_attention_native_stack_cp_c_protectlib_combo_update(
        chandle handle__V
        , input logic [47:0]  cal
        , input logic [1:0]  stack_id
        , input logic [539:0]  aq
        , input logic [35:0]  am
        , output logic [562:0]  ap
        , input logic active_layer_parity
        , output logic [135:0]  k_request
        , input logic [8199:0]  k_response
        , input logic er_v
        , input logic [10:0]  er_addr
        , output logic er_rsp_v
        , output logic [10:0]  er_rsp_addr
        , output logic [63:0]  er_data
        , output logic [15:0]  exp_committed
        , output logic score_committed
        , output logic fault
        , output logic [7:0]  dbg
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qwen_tp8_attention_native_stack_cp_c_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , input logic rst_n
        , output logic [562:0]  ap
        , output logic [135:0]  k_request
        , output logic er_rsp_v
        , output logic [10:0]  er_rsp_addr
        , output logic [63:0]  er_data
        , output logic [15:0]  exp_committed
        , output logic score_committed
        , output logic fault
        , output logic [7:0]  dbg
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qwen_tp8_attention_native_stack_cp_c_protectlib_combo_ignore(
        chandle handle__V
        , input logic [47:0]  cal
        , input logic [1:0]  stack_id
        , input logic [539:0]  aq
        , input logic [35:0]  am
        , input logic active_layer_parity
        , input logic [8199:0]  k_response
        , input logic er_v
        , input logic [10:0]  er_addr
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qwen_tp8_attention_native_stack_cp_c_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [562:0]  ap_combo__V;
    logic [135:0]  k_request_combo__V;
    logic er_rsp_v_combo__V;
    logic [10:0]  er_rsp_addr_combo__V;
    logic [63:0]  er_data_combo__V;
    logic [15:0]  exp_committed_combo__V;
    logic score_committed_combo__V;
    logic fault_combo__V;
    logic [7:0]  dbg_combo__V;
    logic [562:0]  ap_seq__V;
    logic [135:0]  k_request_seq__V;
    logic er_rsp_v_seq__V;
    logic [10:0]  er_rsp_addr_seq__V;
    logic [63:0]  er_data_seq__V;
    logic [15:0]  exp_committed_seq__V;
    logic score_committed_seq__V;
    logic fault_seq__V;
    logic [7:0]  dbg_seq__V;
    logic [562:0]  ap_tmp__V;
    logic [135:0]  k_request_tmp__V;
    logic er_rsp_v_tmp__V;
    logic [10:0]  er_rsp_addr_tmp__V;
    logic [63:0]  er_data_tmp__V;
    logic [15:0]  exp_committed_tmp__V;
    logic score_committed_tmp__V;
    logic fault_tmp__V;
    logic [7:0]  dbg_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd4250746132;

    initial begin
        ot_qwen_tp8_attention_native_stack_cp_c_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qwen_tp8_attention_native_stack_cp_c_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qwen_tp8_attention_native_stack_cp_c_protectlib_combo_update(
            handle__V,
            cal,
            stack_id,
            aq,
            am,
            ap_combo__V,
            active_layer_parity,
            k_request_combo__V,
            k_response,
            er_v,
            er_addr,
            er_rsp_v_combo__V,
            er_rsp_addr_combo__V,
            er_data_combo__V,
            exp_committed_combo__V,
            score_committed_combo__V,
            fault_combo__V,
            dbg_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk or rst_n) begin
        ot_qwen_tp8_attention_native_stack_cp_c_protectlib_combo_ignore(
            handle__V,
            cal,
            stack_id,
            aq,
            am,
            active_layer_parity,
            k_response,
            er_v,
            er_addr
        );
        last_seq_seqnum__V <= ot_qwen_tp8_attention_native_stack_cp_c_protectlib_seq_update(
            handle__V,
            clk,
            rst_n,
            ap_tmp__V,
            k_request_tmp__V,
            er_rsp_v_tmp__V,
            er_rsp_addr_tmp__V,
            er_data_tmp__V,
            exp_committed_tmp__V,
            score_committed_tmp__V,
            fault_tmp__V,
            dbg_tmp__V
        );
        ap_seq__V <= ap_tmp__V;
        k_request_seq__V <= k_request_tmp__V;
        er_rsp_v_seq__V <= er_rsp_v_tmp__V;
        er_rsp_addr_seq__V <= er_rsp_addr_tmp__V;
        er_data_seq__V <= er_data_tmp__V;
        exp_committed_seq__V <= exp_committed_tmp__V;
        score_committed_seq__V <= score_committed_tmp__V;
        fault_seq__V <= fault_tmp__V;
        dbg_seq__V <= dbg_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            ap = ap_seq__V;
            k_request = k_request_seq__V;
            er_rsp_v = er_rsp_v_seq__V;
            er_rsp_addr = er_rsp_addr_seq__V;
            er_data = er_data_seq__V;
            exp_committed = exp_committed_seq__V;
            score_committed = score_committed_seq__V;
            fault = fault_seq__V;
            dbg = dbg_seq__V;
        end else begin
            ap = ap_combo__V;
            k_request = k_request_combo__V;
            er_rsp_v = er_rsp_v_combo__V;
            er_rsp_addr = er_rsp_addr_combo__V;
            er_data = er_data_combo__V;
            exp_committed = exp_committed_combo__V;
            score_committed = score_committed_combo__V;
            fault = fault_combo__V;
            dbg = dbg_combo__V;
        end
    end
    
    final ot_qwen_tp8_attention_native_stack_cp_c_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qwen_tp8_attention_native_stack_cp_c"
profile_data -hier-dpi "ot_qwen_tp8_attention_native_stack_cp_c_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qwen_tp8_attention_native_stack_cp_c_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qwen_tp8_attention_native_stack_cp_c_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qwen_tp8_attention_native_stack_cp_c_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qwen_tp8_attention_native_stack_cp_c_protectlib_seq_update" -workers 16'd0
`verilog
`endif
