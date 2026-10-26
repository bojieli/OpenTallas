// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libqkd_astk_ctl_tp8_cal_d.a or libqkd_astk_ctl_tp8_cal_d.so to work
// See instructions in your simulator for how to use DPI libraries

module qkd_astk_ctl_tp8_cal_d (
        input logic [31:0]  cal
        , input logic ck
        , input logic rst_n
        , input logic [1:0]  st
        , input logic [539:0]  aq
        , output logic [20:0]  lt
        , input logic [35:0]  am
        , output logic [564:0]  ap
        , output logic af
        , output logic [571:0]  qo
        , input logic [266:0]  xi
        , output logic [5:0]  co
        , input logic [262:0]  px
        , input logic [262:0]  py
        , input logic [137:0]  zi
        , input logic fx
        , input logic fy
        , input logic fz
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void qkd_astk_ctl_tp8_cal_d_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle qkd_astk_ctl_tp8_cal_d_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint qkd_astk_ctl_tp8_cal_d_protectlib_combo_update(
        chandle handle__V
        , input logic [31:0]  cal
        , input logic rst_n
        , input logic [1:0]  st
        , input logic [539:0]  aq
        , output logic [20:0]  lt
        , input logic [35:0]  am
        , output logic [564:0]  ap
        , output logic af
        , output logic [571:0]  qo
        , input logic [266:0]  xi
        , output logic [5:0]  co
        , input logic [262:0]  px
        , input logic [262:0]  py
        , input logic [137:0]  zi
        , input logic fx
        , input logic fy
        , input logic fz
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint qkd_astk_ctl_tp8_cal_d_protectlib_seq_update(
        chandle handle__V
        , input logic ck
        , output logic [20:0]  lt
        , output logic [564:0]  ap
        , output logic af
        , output logic [571:0]  qo
        , output logic [5:0]  co
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void qkd_astk_ctl_tp8_cal_d_protectlib_combo_ignore(
        chandle handle__V
        , input logic [31:0]  cal
        , input logic rst_n
        , input logic [1:0]  st
        , input logic [539:0]  aq
        , input logic [35:0]  am
        , input logic [266:0]  xi
        , input logic [262:0]  px
        , input logic [262:0]  py
        , input logic [137:0]  zi
        , input logic fx
        , input logic fy
        , input logic fz
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void qkd_astk_ctl_tp8_cal_d_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [20:0]  lt_combo__V;
    logic [564:0]  ap_combo__V;
    logic af_combo__V;
    logic [571:0]  qo_combo__V;
    logic [5:0]  co_combo__V;
    logic [20:0]  lt_seq__V;
    logic [564:0]  ap_seq__V;
    logic af_seq__V;
    logic [571:0]  qo_seq__V;
    logic [5:0]  co_seq__V;
    logic [20:0]  lt_tmp__V;
    logic [564:0]  ap_tmp__V;
    logic af_tmp__V;
    logic [571:0]  qo_tmp__V;
    logic [5:0]  co_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd2459406506;

    initial begin
        qkd_astk_ctl_tp8_cal_d_protectlib_check_hash(protectlib_hash__V);
        handle__V = qkd_astk_ctl_tp8_cal_d_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = qkd_astk_ctl_tp8_cal_d_protectlib_combo_update(
            handle__V,
            cal,
            rst_n,
            st,
            aq,
            lt_combo__V,
            am,
            ap_combo__V,
            af_combo__V,
            qo_combo__V,
            xi,
            co_combo__V,
            px,
            py,
            zi,
            fx,
            fy,
            fz
        );
    end
    
    // Evaluate clock edges
    always @(ck) begin
        qkd_astk_ctl_tp8_cal_d_protectlib_combo_ignore(
            handle__V,
            cal,
            rst_n,
            st,
            aq,
            am,
            xi,
            px,
            py,
            zi,
            fx,
            fy,
            fz
        );
        last_seq_seqnum__V <= qkd_astk_ctl_tp8_cal_d_protectlib_seq_update(
            handle__V,
            ck,
            lt_tmp__V,
            ap_tmp__V,
            af_tmp__V,
            qo_tmp__V,
            co_tmp__V
        );
        lt_seq__V <= lt_tmp__V;
        ap_seq__V <= ap_tmp__V;
        af_seq__V <= af_tmp__V;
        qo_seq__V <= qo_tmp__V;
        co_seq__V <= co_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            lt = lt_seq__V;
            ap = ap_seq__V;
            af = af_seq__V;
            qo = qo_seq__V;
            co = co_seq__V;
        end else begin
            lt = lt_combo__V;
            ap = ap_combo__V;
            af = af_combo__V;
            qo = qo_combo__V;
            co = co_combo__V;
        end
    end
    
    final qkd_astk_ctl_tp8_cal_d_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "qkd_astk_ctl_tp8_cal_d"
profile_data -hier-dpi "qkd_astk_ctl_tp8_cal_d_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "qkd_astk_ctl_tp8_cal_d_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "qkd_astk_ctl_tp8_cal_d_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "qkd_astk_ctl_tp8_cal_d_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "qkd_astk_ctl_tp8_cal_d_protectlib_seq_update" -workers 16'd0
`verilog
`endif
