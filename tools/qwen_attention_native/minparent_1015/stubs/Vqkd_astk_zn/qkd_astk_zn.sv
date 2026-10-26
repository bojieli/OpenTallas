// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libqkd_astk_zn.a or libqkd_astk_zn.so to work
// See instructions in your simulator for how to use DPI libraries

module qkd_astk_zn (
        input logic ck
        , input logic rst_n
        , input logic [3:0]  zc
        , input logic [14:0]  tc
        , input logic [137:0]  zi
        , output logic [137:0]  zo
        , input logic fi
        , output logic fo
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void qkd_astk_zn_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle qkd_astk_zn_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint qkd_astk_zn_protectlib_combo_update(
        chandle handle__V
        , input logic rst_n
        , input logic [3:0]  zc
        , input logic [14:0]  tc
        , input logic [137:0]  zi
        , output logic [137:0]  zo
        , input logic fi
        , output logic fo
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint qkd_astk_zn_protectlib_seq_update(
        chandle handle__V
        , input logic ck
        , output logic [137:0]  zo
        , output logic fo
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void qkd_astk_zn_protectlib_combo_ignore(
        chandle handle__V
        , input logic rst_n
        , input logic [3:0]  zc
        , input logic [14:0]  tc
        , input logic [137:0]  zi
        , input logic fi
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void qkd_astk_zn_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [137:0]  zo_combo__V;
    logic fo_combo__V;
    logic [137:0]  zo_seq__V;
    logic fo_seq__V;
    logic [137:0]  zo_tmp__V;
    logic fo_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd4092639280;

    initial begin
        qkd_astk_zn_protectlib_check_hash(protectlib_hash__V);
        handle__V = qkd_astk_zn_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = qkd_astk_zn_protectlib_combo_update(
            handle__V,
            rst_n,
            zc,
            tc,
            zi,
            zo_combo__V,
            fi,
            fo_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(ck) begin
        qkd_astk_zn_protectlib_combo_ignore(
            handle__V,
            rst_n,
            zc,
            tc,
            zi,
            fi
        );
        last_seq_seqnum__V <= qkd_astk_zn_protectlib_seq_update(
            handle__V,
            ck,
            zo_tmp__V,
            fo_tmp__V
        );
        zo_seq__V <= zo_tmp__V;
        fo_seq__V <= fo_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            zo = zo_seq__V;
            fo = fo_seq__V;
        end else begin
            zo = zo_combo__V;
            fo = fo_combo__V;
        end
    end
    
    final qkd_astk_zn_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "qkd_astk_zn"
profile_data -hier-dpi "qkd_astk_zn_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "qkd_astk_zn_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "qkd_astk_zn_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "qkd_astk_zn_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "qkd_astk_zn_protectlib_seq_update" -workers 16'd0
`verilog
`endif
