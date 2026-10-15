// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qkh_head_native_r4_8.a or libot_qkh_head_native_r4_8.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qkh_head_native_r4_8 (
        input logic [3:0]  ck_front
        , input logic ck_score
        , input logic ck_kt
        , input logic [15:0]  ck_stin
        , input logic [15:0]  ck_stk
        , input logic [15:0]  ck_nb1
        , input logic [15:0]  ck_nb2
        , input logic [15:0]  ck_lane
        , input logic rst_n
        , input logic [3:0]  c_in
        , input logic [1023:0]  row_in
        , input logic [15:0]  e_in
        , input logic [11:0]  lt_in
        , input logic [1:0]  hid
        , input logic q_valid_in
        , input logic [5:0]  q_beat_in
        , input logic [511:0]  q_data_in
        , output logic [31:0]  sc_d
        , output logic sc_f
        , output logic g_f
        , output logic [1023:0]  nb_d
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qkh_head_native_r4_8_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qkh_head_native_r4_8_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qkh_head_native_r4_8_protectlib_combo_update(
        chandle handle__V
        , input logic [3:0]  c_in
        , input logic [1023:0]  row_in
        , input logic [15:0]  e_in
        , input logic [11:0]  lt_in
        , input logic [1:0]  hid
        , input logic q_valid_in
        , input logic [5:0]  q_beat_in
        , input logic [511:0]  q_data_in
        , output logic [31:0]  sc_d
        , output logic sc_f
        , output logic g_f
        , output logic [1023:0]  nb_d
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qkh_head_native_r4_8_protectlib_seq_update(
        chandle handle__V
        , input logic [3:0]  ck_front
        , input logic ck_score
        , input logic ck_kt
        , input logic [15:0]  ck_stin
        , input logic [15:0]  ck_stk
        , input logic [15:0]  ck_nb1
        , input logic [15:0]  ck_nb2
        , input logic [15:0]  ck_lane
        , input logic rst_n
        , output logic [31:0]  sc_d
        , output logic sc_f
        , output logic g_f
        , output logic [1023:0]  nb_d
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qkh_head_native_r4_8_protectlib_combo_ignore(
        chandle handle__V
        , input logic [3:0]  c_in
        , input logic [1023:0]  row_in
        , input logic [15:0]  e_in
        , input logic [11:0]  lt_in
        , input logic [1:0]  hid
        , input logic q_valid_in
        , input logic [5:0]  q_beat_in
        , input logic [511:0]  q_data_in
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qkh_head_native_r4_8_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [31:0]  sc_d_combo__V;
    logic sc_f_combo__V;
    logic g_f_combo__V;
    logic [1023:0]  nb_d_combo__V;
    logic [31:0]  sc_d_seq__V;
    logic sc_f_seq__V;
    logic g_f_seq__V;
    logic [1023:0]  nb_d_seq__V;
    logic [31:0]  sc_d_tmp__V;
    logic sc_f_tmp__V;
    logic g_f_tmp__V;
    logic [1023:0]  nb_d_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd4034801653;

    initial begin
        ot_qkh_head_native_r4_8_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qkh_head_native_r4_8_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qkh_head_native_r4_8_protectlib_combo_update(
            handle__V,
            c_in,
            row_in,
            e_in,
            lt_in,
            hid,
            q_valid_in,
            q_beat_in,
            q_data_in,
            sc_d_combo__V,
            sc_f_combo__V,
            g_f_combo__V,
            nb_d_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(ck_front or ck_score or ck_kt or ck_stin or ck_stk or ck_nb1 or ck_nb2 or ck_lane or rst_n) begin
        ot_qkh_head_native_r4_8_protectlib_combo_ignore(
            handle__V,
            c_in,
            row_in,
            e_in,
            lt_in,
            hid,
            q_valid_in,
            q_beat_in,
            q_data_in
        );
        last_seq_seqnum__V <= ot_qkh_head_native_r4_8_protectlib_seq_update(
            handle__V,
            ck_front,
            ck_score,
            ck_kt,
            ck_stin,
            ck_stk,
            ck_nb1,
            ck_nb2,
            ck_lane,
            rst_n,
            sc_d_tmp__V,
            sc_f_tmp__V,
            g_f_tmp__V,
            nb_d_tmp__V
        );
        sc_d_seq__V <= sc_d_tmp__V;
        sc_f_seq__V <= sc_f_tmp__V;
        g_f_seq__V <= g_f_tmp__V;
        nb_d_seq__V <= nb_d_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            sc_d = sc_d_seq__V;
            sc_f = sc_f_seq__V;
            g_f = g_f_seq__V;
            nb_d = nb_d_seq__V;
        end else begin
            sc_d = sc_d_combo__V;
            sc_f = sc_f_combo__V;
            g_f = g_f_combo__V;
            nb_d = nb_d_combo__V;
        end
    end
    
    final ot_qkh_head_native_r4_8_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qkh_head_native_r4_8"
profile_data -hier-dpi "ot_qkh_head_native_r4_8_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_head_native_r4_8_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_head_native_r4_8_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qkh_head_native_r4_8_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qkh_head_native_r4_8_protectlib_seq_update" -workers 16'd0
`verilog
`endif
