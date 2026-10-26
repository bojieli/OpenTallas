// DESCRIPTION: Verilator generated Verilog
// Wrapper module for DPI protected library
// This module requires libqkd_astk_ep_cal_0.a or libqkd_astk_ep_cal_0.so to work
// See instructions in your simulator for how to use DPI libraries

module qkd_astk_ep_cal_0 (
        input logic [15:0]  cal_exp
        , input logic ck
        , input logic rst_n
        , input logic [4:0]  sq
        , input logic [424:0]  so
        , output logic [633:0]  si
        , input logic [571:0]  qi
        , input logic [266:0]  xi
        , output logic [266:0]  xo
        , input logic [650:0]  zi
        , output logic [650:0]  zo
        , input logic [521:0]  ri
        , output logic [263:0]  xa
        , input logic [135:0]  xe
        , input logic cr
        , input logic [535:0]  ui
        , output logic [535:0]  uo
        , input logic [535:0]  di
        , output logic [535:0]  do_
        , input logic [262:0]  pi
        , output logic [262:0]  po
        , input logic [5:0]  ci
        , output logic [5:0]  co
        , input logic [3:0]  kui
        , output logic [3:0]  kuo
        , input logic [3:0]  kdi
        , output logic [3:0]  kdo
        , input logic tui
        , output logic tuo
        , input logic tdi
        , output logic tdo
        , input logic fi
        , output logic fo
    );
    
    timeunit 1ns;
    timeprecision 1ps;
    // Checks to make sure the .sv wrapper and library agree
    import "DPI-C" function void qkd_astk_ep_cal_0_protectlib_check_hash(int protectlib_hash__V);
    
    // Creates an instance of the library module at initial-time
    // (one for each instance in the user's design) also evaluates
    // the library module's initial process
    import "DPI-C" function chandle qkd_astk_ep_cal_0_protectlib_create(string scope__V);
    
    // Updates all non-clock inputs and retrieves the results
    import "DPI-C" function longint qkd_astk_ep_cal_0_protectlib_combo_update(
        chandle handle__V
        , input logic [15:0]  cal_exp
        , input logic rst_n
        , input logic [4:0]  sq
        , input logic [424:0]  so
        , output logic [633:0]  si
        , input logic [571:0]  qi
        , input logic [266:0]  xi
        , output logic [266:0]  xo
        , input logic [650:0]  zi
        , output logic [650:0]  zo
        , input logic [521:0]  ri
        , output logic [263:0]  xa
        , input logic [135:0]  xe
        , input logic cr
        , input logic [535:0]  ui
        , output logic [535:0]  uo
        , input logic [535:0]  di
        , output logic [535:0]  do_
        , input logic [262:0]  pi
        , output logic [262:0]  po
        , input logic [5:0]  ci
        , output logic [5:0]  co
        , input logic [3:0]  kui
        , output logic [3:0]  kuo
        , input logic [3:0]  kdi
        , output logic [3:0]  kdo
        , input logic tui
        , output logic tuo
        , input logic tdi
        , output logic tdo
        , input logic fi
        , output logic fo
    );
    
    // Updates all clocks and retrieves the results
    import "DPI-C" function longint qkd_astk_ep_cal_0_protectlib_seq_update(
        chandle handle__V
        , input logic ck
        , output logic [633:0]  si
        , output logic [266:0]  xo
        , output logic [650:0]  zo
        , output logic [263:0]  xa
        , output logic [535:0]  uo
        , output logic [535:0]  do_
        , output logic [262:0]  po
        , output logic [5:0]  co
        , output logic [3:0]  kuo
        , output logic [3:0]  kdo
        , output logic tuo
        , output logic tdo
        , output logic fo
    );
    
    // Need to convince some simulators that the input to the module
    // must be evaluated before evaluating the clock edge
    import "DPI-C" function void qkd_astk_ep_cal_0_protectlib_combo_ignore(
        chandle handle__V
        , input logic [15:0]  cal_exp
        , input logic rst_n
        , input logic [4:0]  sq
        , input logic [424:0]  so
        , input logic [571:0]  qi
        , input logic [266:0]  xi
        , input logic [650:0]  zi
        , input logic [521:0]  ri
        , input logic [135:0]  xe
        , input logic cr
        , input logic [535:0]  ui
        , input logic [535:0]  di
        , input logic [262:0]  pi
        , input logic [5:0]  ci
        , input logic [3:0]  kui
        , input logic [3:0]  kdi
        , input logic tui
        , input logic tdi
        , input logic fi
    );
    
    // Evaluates the library module's final process
    import "DPI-C" function void qkd_astk_ep_cal_0_protectlib_final(chandle handle__V);
    
    // verilator tracing_off
    chandle handle__V;
    time last_combo_seqnum__V;
    time last_seq_seqnum__V;

    logic [633:0]  si_combo__V;
    logic [266:0]  xo_combo__V;
    logic [650:0]  zo_combo__V;
    logic [263:0]  xa_combo__V;
    logic [535:0]  uo_combo__V;
    logic [535:0]  do__combo__V;
    logic [262:0]  po_combo__V;
    logic [5:0]  co_combo__V;
    logic [3:0]  kuo_combo__V;
    logic [3:0]  kdo_combo__V;
    logic tuo_combo__V;
    logic tdo_combo__V;
    logic fo_combo__V;
    logic [633:0]  si_seq__V;
    logic [266:0]  xo_seq__V;
    logic [650:0]  zo_seq__V;
    logic [263:0]  xa_seq__V;
    logic [535:0]  uo_seq__V;
    logic [535:0]  do__seq__V;
    logic [262:0]  po_seq__V;
    logic [5:0]  co_seq__V;
    logic [3:0]  kuo_seq__V;
    logic [3:0]  kdo_seq__V;
    logic tuo_seq__V;
    logic tdo_seq__V;
    logic fo_seq__V;
    logic [633:0]  si_tmp__V;
    logic [266:0]  xo_tmp__V;
    logic [650:0]  zo_tmp__V;
    logic [263:0]  xa_tmp__V;
    logic [535:0]  uo_tmp__V;
    logic [535:0]  do__tmp__V;
    logic [262:0]  po_tmp__V;
    logic [5:0]  co_tmp__V;
    logic [3:0]  kuo_tmp__V;
    logic [3:0]  kdo_tmp__V;
    logic tuo_tmp__V;
    logic tdo_tmp__V;
    logic fo_tmp__V;
    // Hash value to make sure this file and the corresponding
    // library agree
    localparam int protectlib_hash__V = 32'd4119203238;

    initial begin
        qkd_astk_ep_cal_0_protectlib_check_hash(protectlib_hash__V);
        handle__V = qkd_astk_ep_cal_0_protectlib_create($sformatf("%m"));
    end
    
    // Combinatorially evaluate changes to inputs
    always_comb begin
        last_combo_seqnum__V = qkd_astk_ep_cal_0_protectlib_combo_update(
            handle__V,
            cal_exp,
            rst_n,
            sq,
            so,
            si_combo__V,
            qi,
            xi,
            xo_combo__V,
            zi,
            zo_combo__V,
            ri,
            xa_combo__V,
            xe,
            cr,
            ui,
            uo_combo__V,
            di,
            do__combo__V,
            pi,
            po_combo__V,
            ci,
            co_combo__V,
            kui,
            kuo_combo__V,
            kdi,
            kdo_combo__V,
            tui,
            tuo_combo__V,
            tdi,
            tdo_combo__V,
            fi,
            fo_combo__V
        );
    end
    
    // Evaluate clock edges
    always @(ck) begin
        qkd_astk_ep_cal_0_protectlib_combo_ignore(
            handle__V,
            cal_exp,
            rst_n,
            sq,
            so,
            qi,
            xi,
            zi,
            ri,
            xe,
            cr,
            ui,
            di,
            pi,
            ci,
            kui,
            kdi,
            tui,
            tdi,
            fi
        );
        last_seq_seqnum__V <= qkd_astk_ep_cal_0_protectlib_seq_update(
            handle__V,
            ck,
            si_tmp__V,
            xo_tmp__V,
            zo_tmp__V,
            xa_tmp__V,
            uo_tmp__V,
            do__tmp__V,
            po_tmp__V,
            co_tmp__V,
            kuo_tmp__V,
            kdo_tmp__V,
            tuo_tmp__V,
            tdo_tmp__V,
            fo_tmp__V
        );
        si_seq__V <= si_tmp__V;
        xo_seq__V <= xo_tmp__V;
        zo_seq__V <= zo_tmp__V;
        xa_seq__V <= xa_tmp__V;
        uo_seq__V <= uo_tmp__V;
        do__seq__V <= do__tmp__V;
        po_seq__V <= po_tmp__V;
        co_seq__V <= co_tmp__V;
        kuo_seq__V <= kuo_tmp__V;
        kdo_seq__V <= kdo_tmp__V;
        tuo_seq__V <= tuo_tmp__V;
        tdo_seq__V <= tdo_tmp__V;
        fo_seq__V <= fo_tmp__V;
    end
    
    // Select between combinatorial and sequential results
    always_comb begin
        if (last_seq_seqnum__V > last_combo_seqnum__V) begin
            si = si_seq__V;
            xo = xo_seq__V;
            zo = zo_seq__V;
            xa = xa_seq__V;
            uo = uo_seq__V;
            do_ = do__seq__V;
            po = po_seq__V;
            co = co_seq__V;
            kuo = kuo_seq__V;
            kdo = kdo_seq__V;
            tuo = tuo_seq__V;
            tdo = tdo_seq__V;
            fo = fo_seq__V;
        end else begin
            si = si_combo__V;
            xo = xo_combo__V;
            zo = zo_combo__V;
            xa = xa_combo__V;
            uo = uo_combo__V;
            do_ = do__combo__V;
            po = po_combo__V;
            co = co_combo__V;
            kuo = kuo_combo__V;
            kdo = kdo_combo__V;
            tuo = tuo_combo__V;
            tdo = tdo_combo__V;
            fo = fo_combo__V;
        end
    end
    
    final qkd_astk_ep_cal_0_protectlib_final(handle__V);
    
endmodule

`ifdef VERILATOR
`verilator_config
verilator_lib -module "qkd_astk_ep_cal_0"
profile_data -hier-dpi "qkd_astk_ep_cal_0_protectlib_combo_update" -cost 64'd0
profile_data -hier-dpi "qkd_astk_ep_cal_0_protectlib_seq_update" -cost 64'd0
profile_data -hier-dpi "qkd_astk_ep_cal_0_protectlib_combo_ignore" -cost 64'd1
hier_workers -hier-dpi "qkd_astk_ep_cal_0_protectlib_combo_update" -workers 16'd0
hier_workers -hier-dpi "qkd_astk_ep_cal_0_protectlib_seq_update" -workers 16'd0
`verilog
`endif
