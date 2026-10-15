// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qwen_tp8_pv256_finalize_static_cal_8.a or libot_qwen_tp8_pv256_finalize_static_cal_8.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qwen_tp8_pv256_finalize_static_cal_8 (
        input logic [47:0]  cal
        , input logic [31:0]  clk_join
        , input logic clk_control
        , input logic rst_n
        , input logic start
        , input logic [15:0]  epoch
        , input logic [127:0]  reciprocal
        , input logic reciprocal_valid
        , output logic reciprocal_ready
        , input logic [15:0]  reciprocal_epoch
        , input logic p0_valid
        , input logic p1_valid
        , output logic p0_ready
        , output logic p1_ready
        , input logic [15:0]  p0_epoch
        , input logic [15:0]  p1_epoch
        , input logic [16383:0]  p0_partial
        , input logic [16383:0]  p1_partial
        , output logic out_valid
        , input logic out_ready
        , output logic [16383:0]  out_data
        , output logic [15:0]  out_epoch
        , output logic fault
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_combo_update(
        chandle handle__V
        , input logic [47:0]  cal
        , input logic start
        , input logic [15:0]  epoch
        , input logic [127:0]  reciprocal
        , input logic reciprocal_valid
        , output logic reciprocal_ready
        , input logic [15:0]  reciprocal_epoch
        , input logic p0_valid
        , input logic p1_valid
        , output logic p0_ready
        , output logic p1_ready
        , input logic [15:0]  p0_epoch
        , input logic [15:0]  p1_epoch
        , input logic [16383:0]  p0_partial
        , input logic [16383:0]  p1_partial
        , output logic out_valid
        , input logic out_ready
        , output logic [16383:0]  out_data
        , output logic [15:0]  out_epoch
        , output logic fault
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_seq_update(
        chandle handle__V
        , input logic [31:0]  clk_join
        , input logic clk_control
        , input logic rst_n
        , output logic reciprocal_ready
        , output logic p0_ready
        , output logic p1_ready
        , output logic out_valid
        , output logic [16383:0]  out_data
        , output logic [15:0]  out_epoch
        , output logic fault
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_combo_ignore(
        chandle handle__V
        , input logic [47:0]  cal
        , input logic start
        , input logic [15:0]  epoch
        , input logic [127:0]  reciprocal
        , input logic reciprocal_valid
        , input logic [15:0]  reciprocal_epoch
        , input logic p0_valid
        , input logic p1_valid
        , input logic [15:0]  p0_epoch
        , input logic [15:0]  p1_epoch
        , input logic [16383:0]  p0_partial
        , input logic [16383:0]  p1_partial
        , input logic out_ready
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic reciprocal_ready_combo__V;
    logic p0_ready_combo__V;
    logic p1_ready_combo__V;
    logic out_valid_combo__V;
    logic [16383:0]  out_data_combo__V;
    logic [15:0]  out_epoch_combo__V;
    logic fault_combo__V;
    logic reciprocal_ready_seq__V;
    logic p0_ready_seq__V;
    logic p1_ready_seq__V;
    logic out_valid_seq__V;
    logic [16383:0]  out_data_seq__V;
    logic [15:0]  out_epoch_seq__V;
    logic fault_seq__V;
    logic reciprocal_ready_tmp__V;
    logic p0_ready_tmp__V;
    logic p1_ready_tmp__V;
    logic out_valid_tmp__V;
    logic [16383:0]  out_data_tmp__V;
    logic [15:0]  out_epoch_tmp__V;
    logic fault_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd1559528900;

    initial begin
        ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_combo_update(
            handle__V,
            cal,
            start,
            epoch,
            reciprocal,
            reciprocal_valid,
            reciprocal_ready_combo__V,
            reciprocal_epoch,
            p0_valid,
            p1_valid,
            p0_ready_combo__V,
            p1_ready_combo__V,
            p0_epoch,
            p1_epoch,
            p0_partial,
            p1_partial,
            out_valid_combo__V,
            out_ready,
            out_data_combo__V,
            out_epoch_combo__V,
            fault_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk_join or clk_control or rst_n) begin
        ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_combo_ignore(
            handle__V,
            cal,
            start,
            epoch,
            reciprocal,
            reciprocal_valid,
            reciprocal_epoch,
            p0_valid,
            p1_valid,
            p0_epoch,
            p1_epoch,
            p0_partial,
            p1_partial,
            out_ready
        );
        last_seq_seqnum__V <= ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_seq_update(
            handle__V,
            clk_join,
            clk_control,
            rst_n,
            reciprocal_ready_tmp__V,
            p0_ready_tmp__V,
            p1_ready_tmp__V,
            out_valid_tmp__V,
            out_data_tmp__V,
            out_epoch_tmp__V,
            fault_tmp__V
        );
        reciprocal_ready_seq__V <= reciprocal_ready_tmp__V;
        p0_ready_seq__V <= p0_ready_tmp__V;
        p1_ready_seq__V <= p1_ready_tmp__V;
        out_valid_seq__V <= out_valid_tmp__V;
        out_data_seq__V <= out_data_tmp__V;
        out_epoch_seq__V <= out_epoch_tmp__V;
        fault_seq__V <= fault_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            reciprocal_ready = reciprocal_ready_seq__V;
            p0_ready = p0_ready_seq__V;
            p1_ready = p1_ready_seq__V;
            out_valid = out_valid_seq__V;
            out_data = out_data_seq__V;
            out_epoch = out_epoch_seq__V;
            fault = fault_seq__V;
        end else begin
            reciprocal_ready = reciprocal_ready_combo__V;
            p0_ready = p0_ready_combo__V;
            p1_ready = p1_ready_combo__V;
            out_valid = out_valid_combo__V;
            out_data = out_data_combo__V;
            out_epoch = out_epoch_combo__V;
            fault = fault_combo__V;
        end
    end
    
    final ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qwen_tp8_pv256_finalize_static_cal_8"
profile_data -hier-dpi "ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qwen_tp8_pv256_finalize_static_cal_8_protectlib_seq_update" -workers 16'd0
`verilog
`endif
