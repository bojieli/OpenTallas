// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libqkd_astk_native_er_service_2.a or libqkd_astk_native_er_service_2.so to work
// See instructions in your simulator for how to use DPI libraries

module qkd_astk_native_er_service_2 (
        input logic ck
        , input logic rst_n
        , input logic read_v
        , input logic [10:0]  read_addr
        , input logic [3399:0]  engine_so
        , output logic [3399:0]  astk_so
        , input logic [5071:0]  astk_si
        , output logic [5071:0]  engine_si
        , output logic response_v
        , output logic [10:0]  response_addr
        , output logic [63:0]  response_data
        , output logic fault
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void qkd_astk_native_er_service_2_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle qkd_astk_native_er_service_2_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint qkd_astk_native_er_service_2_protectlib_combo_update(
        chandle handle__V
        , input logic read_v
        , input logic [10:0]  read_addr
        , input logic [3399:0]  engine_so
        , output logic [3399:0]  astk_so
        , input logic [5071:0]  astk_si
        , output logic [5071:0]  engine_si
        , output logic response_v
        , output logic [10:0]  response_addr
        , output logic [63:0]  response_data
        , output logic fault
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint qkd_astk_native_er_service_2_protectlib_seq_update(
        chandle handle__V
        , input logic ck
        , input logic rst_n
        , output logic [3399:0]  astk_so
        , output logic [5071:0]  engine_si
        , output logic response_v
        , output logic [10:0]  response_addr
        , output logic [63:0]  response_data
        , output logic fault
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void qkd_astk_native_er_service_2_protectlib_combo_ignore(
        chandle handle__V
        , input logic read_v
        , input logic [10:0]  read_addr
        , input logic [3399:0]  engine_so
        , input logic [5071:0]  astk_si
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void qkd_astk_native_er_service_2_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [3399:0]  astk_so_combo__V;
    logic [5071:0]  engine_si_combo__V;
    logic response_v_combo__V;
    logic [10:0]  response_addr_combo__V;
    logic [63:0]  response_data_combo__V;
    logic fault_combo__V;
    logic [3399:0]  astk_so_seq__V;
    logic [5071:0]  engine_si_seq__V;
    logic response_v_seq__V;
    logic [10:0]  response_addr_seq__V;
    logic [63:0]  response_data_seq__V;
    logic fault_seq__V;
    logic [3399:0]  astk_so_tmp__V;
    logic [5071:0]  engine_si_tmp__V;
    logic response_v_tmp__V;
    logic [10:0]  response_addr_tmp__V;
    logic [63:0]  response_data_tmp__V;
    logic fault_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd2385110709;

    initial begin
        qkd_astk_native_er_service_2_protectlib_check_hash(protectlib_hash__V);
        handle__V = qkd_astk_native_er_service_2_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = qkd_astk_native_er_service_2_protectlib_combo_update(
            handle__V,
            read_v,
            read_addr,
            engine_so,
            astk_so_combo__V,
            astk_si,
            engine_si_combo__V,
            response_v_combo__V,
            response_addr_combo__V,
            response_data_combo__V,
            fault_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(ck or rst_n) begin
        qkd_astk_native_er_service_2_protectlib_combo_ignore(
            handle__V,
            read_v,
            read_addr,
            engine_so,
            astk_si
        );
        last_seq_seqnum__V <= qkd_astk_native_er_service_2_protectlib_seq_update(
            handle__V,
            ck,
            rst_n,
            astk_so_tmp__V,
            engine_si_tmp__V,
            response_v_tmp__V,
            response_addr_tmp__V,
            response_data_tmp__V,
            fault_tmp__V
        );
        astk_so_seq__V <= astk_so_tmp__V;
        engine_si_seq__V <= engine_si_tmp__V;
        response_v_seq__V <= response_v_tmp__V;
        response_addr_seq__V <= response_addr_tmp__V;
        response_data_seq__V <= response_data_tmp__V;
        fault_seq__V <= fault_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            astk_so = astk_so_seq__V;
            engine_si = engine_si_seq__V;
            response_v = response_v_seq__V;
            response_addr = response_addr_seq__V;
            response_data = response_data_seq__V;
            fault = fault_seq__V;
        end else begin
            astk_so = astk_so_combo__V;
            engine_si = engine_si_combo__V;
            response_v = response_v_combo__V;
            response_addr = response_addr_combo__V;
            response_data = response_data_combo__V;
            fault = fault_combo__V;
        end
    end
    
    final qkd_astk_native_er_service_2_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "qkd_astk_native_er_service_2"
profile_data -hier-dpi "qkd_astk_native_er_service_2_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "qkd_astk_native_er_service_2_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "qkd_astk_native_er_service_2_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "qkd_astk_native_er_service_2_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "qkd_astk_native_er_service_2_protectlib_seq_update" -workers 16'd0
`verilog
`endif
