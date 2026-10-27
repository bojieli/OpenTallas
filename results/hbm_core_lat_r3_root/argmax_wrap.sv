`default_nettype none
// HBM-CORE-LAT-R3 (2026-10-27): plan-pin wrapper of ot_hbm_argmax_static_sw_vm_r2 for the B2o superset-face pin table
// (planS2 cores/ot_hbm_argmax_static_sw_vm_r2__118.8x118.8__root_u_hb_argmax.json, path_hbm_superset_faces.py 2b).
// The only instance (root u_hb_argmax) binds pin_select {vm_rq: vm_rq__S, vm_rr: vm_rr__S}; unused_pins [vm_rq, vm_rr].
// Outputs: vm_rq and vm_rq__S carry the same word (each bit its own face-shell register).
// Inputs: the engine reads the bound copy vm_rr__S; vm_rr is the declared unused superset group (registered by the
// face shell, unread; never tied or stubbed in the master).  Wires only, 0 cycles.
module ot_hbm_argmax_static_sw_vm_r2 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    die_id,
    input  wire          go,
    input  wire          mode,
    input  wire [17:0]   imm_a,
    input  wire          a_mirror,
    input  wire [17:0]   a_base,
    input  wire [17:0]   n,
    input  wire [17:0]   o_base,
    input  wire [15:0]   o_is,
    output wire [135:0]  vm_rq,
    output wire [135:0]  vm_rq__S,
    input  wire [263:0]  vm_rr,
    input  wire [263:0]  vm_rr__S,
    output wire [337:0]  cq,
    output wire [1:0]    cq_seq,
    input  wire [273:0]  cr,
    output wire          busy,
    output wire          done,
    output wire          fault,
    output wire          nan_flag
);
    wire [135:0] rq;
    assign vm_rq = rq;
    assign vm_rq__S = rq;
    ot_hbm_argmax_static_sw_vm_r2__rtl #(.TP(192)) u_rtl (
        .clk(clk), .rst_n(rst_n), .die_id(die_id), .go(go), .mode(mode), .imm_a(imm_a), .a_mirror(a_mirror),
        .a_base(a_base), .n(n), .o_base(o_base), .o_is(o_is), .vm_rq(rq), .vm_rr(vm_rr__S), .cq(cq), .cq_seq(cq_seq),
        .cr(cr), .busy(busy), .done(done), .fault(fault), .nan_flag(nan_flag));
endmodule
`default_nettype wire
