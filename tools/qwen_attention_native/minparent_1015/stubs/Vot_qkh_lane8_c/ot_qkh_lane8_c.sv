// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libot_qkh_lane8_c.a or libot_qkh_lane8_c.so to work
// See instructions in your simulator for how to use DPI libraries

module ot_qkh_lane8_c (
        input logic clk
        , input logic rst_n
        , input logic [3:0]  c_in
        , input logic [63:0]  row_in
        , input logic [15:0]  e_in
        , input logic [11:0]  lt_in
        , input logic [1:0]  hid
        , input logic [1:0]  bsel
        , input logic q_valid_in
        , input logic [5:0]  q_beat_in
        , input logic [127:0]  q_data_in
        , output logic [31:0]  kp
        , output logic kpv
        , output logic [63:0]  nb
        , output logic gf
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void ot_qkh_lane8_c_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle ot_qkh_lane8_c_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint ot_qkh_lane8_c_protectlib_combo_update(
        chandle handle__V
        , input logic [3:0]  c_in
        , input logic [63:0]  row_in
        , input logic [15:0]  e_in
        , input logic [11:0]  lt_in
        , input logic [1:0]  hid
        , input logic [1:0]  bsel
        , input logic q_valid_in
        , input logic [5:0]  q_beat_in
        , input logic [127:0]  q_data_in
        , output logic [31:0]  kp
        , output logic kpv
        , output logic [63:0]  nb
        , output logic gf
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint ot_qkh_lane8_c_protectlib_seq_update(
        chandle handle__V
        , input logic clk
        , input logic rst_n
        , output logic [31:0]  kp
        , output logic kpv
        , output logic [63:0]  nb
        , output logic gf
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void ot_qkh_lane8_c_protectlib_combo_ignore(
        chandle handle__V
        , input logic [3:0]  c_in
        , input logic [63:0]  row_in
        , input logic [15:0]  e_in
        , input logic [11:0]  lt_in
        , input logic [1:0]  hid
        , input logic [1:0]  bsel
        , input logic q_valid_in
        , input logic [5:0]  q_beat_in
        , input logic [127:0]  q_data_in
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void ot_qkh_lane8_c_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [31:0]  kp_combo__V;
    logic kpv_combo__V;
    logic [63:0]  nb_combo__V;
    logic gf_combo__V;
    logic [31:0]  kp_seq__V;
    logic kpv_seq__V;
    logic [63:0]  nb_seq__V;
    logic gf_seq__V;
    logic [31:0]  kp_tmp__V;
    logic kpv_tmp__V;
    logic [63:0]  nb_tmp__V;
    logic gf_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd2978020588;

    initial begin
        ot_qkh_lane8_c_protectlib_check_hash(protectlib_hash__V);
        handle__V = ot_qkh_lane8_c_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = ot_qkh_lane8_c_protectlib_combo_update(
            handle__V,
            c_in,
            row_in,
            e_in,
            lt_in,
            hid,
            bsel,
            q_valid_in,
            q_beat_in,
            q_data_in,
            kp_combo__V,
            kpv_combo__V,
            nb_combo__V,
            gf_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(clk or rst_n) begin
        ot_qkh_lane8_c_protectlib_combo_ignore(
            handle__V,
            c_in,
            row_in,
            e_in,
            lt_in,
            hid,
            bsel,
            q_valid_in,
            q_beat_in,
            q_data_in
        );
        last_seq_seqnum__V <= ot_qkh_lane8_c_protectlib_seq_update(
            handle__V,
            clk,
            rst_n,
            kp_tmp__V,
            kpv_tmp__V,
            nb_tmp__V,
            gf_tmp__V
        );
        kp_seq__V <= kp_tmp__V;
        kpv_seq__V <= kpv_tmp__V;
        nb_seq__V <= nb_tmp__V;
        gf_seq__V <= gf_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            kp = kp_seq__V;
            kpv = kpv_seq__V;
            nb = nb_seq__V;
            gf = gf_seq__V;
        end else begin
            kp = kp_combo__V;
            kpv = kpv_combo__V;
            nb = nb_combo__V;
            gf = gf_combo__V;
        end
    end
    
    final ot_qkh_lane8_c_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "ot_qkh_lane8_c"
profile_data -hier-dpi "ot_qkh_lane8_c_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_lane8_c_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "ot_qkh_lane8_c_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "ot_qkh_lane8_c_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "ot_qkh_lane8_c_protectlib_seq_update" -workers 16'd0
`verilog
`endif
