// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qkd_ahub_static_die_cal_3.a or libot_qkd_ahub_static_die_cal_3.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qkd_ahub_static_die_cal_3 (
        input logic [191:0]  cal
        , input logic ck_core
        , input logic ck_recip
        , input logic [3:0]  ck_zh
        , input logic rst_n
        , input logic start
        , input logic active_layer_parity
        , input logic [15:0]  request_epoch
        , input logic [5:0]  active_layer
        , input logic [13:0]  T
        , input logic [3:0]  si_valid
        , input logic [3:0]  si_g
        , input logic [3:0]  si_any
        , input logic [63:0]  si_epoch
        , input logic [23:0]  si_layer
        , input logic [7:0]  si_type
        , input logic [7:0]  si_hh
        , input logic [15:0]  si_k
        , input logic [127:0]  si_data
        , output logic [143:0]  am
        , output logic rz_valid
        , output logic [1:0]  rz_head
        , output logic [31:0]  rz_data
        , output logic [15:0]  rz_epoch
        , output logic rz_publish
        , output logic [127:0]  rz_vector
        , output logic fault
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qkd_ahub_static_die_cal_3_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qkd_ahub_static_die_cal_3_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qkd_ahub_static_die_cal_3_protectlib_combo_update(
        chandle handle__V
        , input logic [191:0]  cal
        , input logic start
        , input logic active_layer_parity
        , input logic [15:0]  request_epoch
        , input logic [5:0]  active_layer
        , input logic [13:0]  T
        , input logic [3:0]  si_valid
        , input logic [3:0]  si_g
        , input logic [3:0]  si_any
        , input logic [63:0]  si_epoch
        , input logic [23:0]  si_layer
        , input logic [7:0]  si_type
        , input logic [7:0]  si_hh
        , input logic [15:0]  si_k
        , input logic [127:0]  si_data
        , output logic [143:0]  am
        , output logic rz_valid
        , output logic [1:0]  rz_head
        , output logic [31:0]  rz_data
        , output logic [15:0]  rz_epoch
        , output logic rz_publish
        , output logic [127:0]  rz_vector
        , output logic fault
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qkd_ahub_static_die_cal_3_protectlib_seq_update(
        chandle handle__V
        , input logic ck_core
        , input logic ck_recip
        , input logic [3:0]  ck_zh
        , input logic rst_n
        , output logic [143:0]  am
        , output logic rz_valid
        , output logic [1:0]  rz_head
        , output logic [31:0]  rz_data
        , output logic [15:0]  rz_epoch
        , output logic rz_publish
        , output logic [127:0]  rz_vector
        , output logic fault
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qkd_ahub_static_die_cal_3_protectlib_combo_ignore(
        chandle handle__V
        , input logic [191:0]  cal
        , input logic start
        , input logic active_layer_parity
        , input logic [15:0]  request_epoch
        , input logic [5:0]  active_layer
        , input logic [13:0]  T
        , input logic [3:0]  si_valid
        , input logic [3:0]  si_g
        , input logic [3:0]  si_any
        , input logic [63:0]  si_epoch
        , input logic [23:0]  si_layer
        , input logic [7:0]  si_type
        , input logic [7:0]  si_hh
        , input logic [15:0]  si_k
        , input logic [127:0]  si_data
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qkd_ahub_static_die_cal_3_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [143:0]  am_combo__V;
    logic rz_valid_combo__V;
    logic [1:0]  rz_head_combo__V;
    logic [31:0]  rz_data_combo__V;
    logic [15:0]  rz_epoch_combo__V;
    logic rz_publish_combo__V;
    logic [127:0]  rz_vector_combo__V;
    logic fault_combo__V;
    logic [143:0]  am_seq__V;
    logic rz_valid_seq__V;
    logic [1:0]  rz_head_seq__V;
    logic [31:0]  rz_data_seq__V;
    logic [15:0]  rz_epoch_seq__V;
    logic rz_publish_seq__V;
    logic [127:0]  rz_vector_seq__V;
    logic fault_seq__V;
    logic [143:0]  am_tmp__V;
    logic rz_valid_tmp__V;
    logic [1:0]  rz_head_tmp__V;
    logic [31:0]  rz_data_tmp__V;
    logic [15:0]  rz_epoch_tmp__V;
    logic rz_publish_tmp__V;
    logic [127:0]  rz_vector_tmp__V;
    logic fault_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd1369631235;

    initial begin
        ot_qkd_ahub_static_die_cal_3_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qkd_ahub_static_die_cal_3_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qkd_ahub_static_die_cal_3_protectlib_combo_update(
            handle__V,
            cal,
            start,
            active_layer_parity,
            request_epoch,
            active_layer,
            T,
            si_valid,
            si_g,
            si_any,
            si_epoch,
            si_layer,
            si_type,
            si_hh,
            si_k,
            si_data,
            am_combo__V,
            rz_valid_combo__V,
            rz_head_combo__V,
            rz_data_combo__V,
            rz_epoch_combo__V,
            rz_publish_combo__V,
            rz_vector_combo__V,
            fault_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(ck_core or ck_recip or ck_zh or rst_n) begin
        ot_qkd_ahub_static_die_cal_3_protectlib_combo_ignore(
            handle__V,
            cal,
            start,
            active_layer_parity,
            request_epoch,
            active_layer,
            T,
            si_valid,
            si_g,
            si_any,
            si_epoch,
            si_layer,
            si_type,
            si_hh,
            si_k,
            si_data
        );
        last_seq_seqnum__V <= ot_qkd_ahub_static_die_cal_3_protectlib_seq_update(
            handle__V,
            ck_core,
            ck_recip,
            ck_zh,
            rst_n,
            am_tmp__V,
            rz_valid_tmp__V,
            rz_head_tmp__V,
            rz_data_tmp__V,
            rz_epoch_tmp__V,
            rz_publish_tmp__V,
            rz_vector_tmp__V,
            fault_tmp__V
        );
        am_seq__V <= am_tmp__V;
        rz_valid_seq__V <= rz_valid_tmp__V;
        rz_head_seq__V <= rz_head_tmp__V;
        rz_data_seq__V <= rz_data_tmp__V;
        rz_epoch_seq__V <= rz_epoch_tmp__V;
        rz_publish_seq__V <= rz_publish_tmp__V;
        rz_vector_seq__V <= rz_vector_tmp__V;
        fault_seq__V <= fault_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            am = am_seq__V;
            rz_valid = rz_valid_seq__V;
            rz_head = rz_head_seq__V;
            rz_data = rz_data_seq__V;
            rz_epoch = rz_epoch_seq__V;
            rz_publish = rz_publish_seq__V;
            rz_vector = rz_vector_seq__V;
            fault = fault_seq__V;
        end else begin
            am = am_combo__V;
            rz_valid = rz_valid_combo__V;
            rz_head = rz_head_combo__V;
            rz_data = rz_data_combo__V;
            rz_epoch = rz_epoch_combo__V;
            rz_publish = rz_publish_combo__V;
            rz_vector = rz_vector_combo__V;
            fault = fault_combo__V;
        end
    end
    
    final ot_qkd_ahub_static_die_cal_3_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qkd_ahub_static_die_cal_3"
profile_data -hier-dpi "ot_qkd_ahub_static_die_cal_3_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qkd_ahub_static_die_cal_3_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qkd_ahub_static_die_cal_3_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qkd_ahub_static_die_cal_3_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qkd_ahub_static_die_cal_3_protectlib_seq_update" -workers 16'd0
`verilog
`endif
