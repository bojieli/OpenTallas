`ifndef OT_SU_ARST
`ifdef OT_SU_SYNC_RST
`define OT_SU_ARST(r)
`else
`define OT_SU_ARST(r) or negedge r
`endif
`endif
`timescale 1ns/1ps
// HBM-KIND9 (10-20): kept register with N-1 identical shadow copies per bit, marked as an ot_rst_split copy family (the
// Codex FP6 / HBM-QCORE9 pattern of ot_hdc_w11_cut_n32): the kit's SYNTH_CANONICALIZE_TCL (copy aliases + the unchanged
// physical/common_flow/ot_rst_copies.tcl splitter, max 32) re-points the loads of q[b] over the N family members after
// proving them identical registers.  Same D, same clock, same edge: function and timing of the copy are unchanged; the
// native census sees <= 32 loads per member.  Not keep_hierarchy (the splitter works on the flattened top), every
// member (* keep *) (ot_keep_regs: never merged).
module ot_k9_fam #(parameter integer W = 1, parameter integer N = 3) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    (* keep = 1 *) reg [W-1:0] r;
    always @(posedge clk) r <= d;
    assign q = r;
    generate if (N > 1) begin : g_fam
        for (genvar b = 0; b < W; b = b + 1) begin : g_bit
            (* keep = 1 *) reg [N-2:0] cp;
            always @(posedge clk) cp <= {(N-1){d[b]}};
            (* keep = 1, ot_rst_split = 1 *) wire [N-1:0] family = {cp, r[b]};
        end
    end endgenerate
endmodule

// valid line split over R reset leaves (each <= ceil(D/R) flops): HBM-KIND9 (it3 census: one leaf drove a 52-56 deep line)
module ot_hdc_vline_k8 #(parameter integer D = 1, parameter integer R = 2) (
    input  wire         clk,
    input  wire [R-1:0] rst_n,
    input  wire         v,
    output wire [D:0]   vd
);
    localparam integer C = (D + R - 1) / R;
    reg [D:1] line;
    genvar i;
    wire [D:0] nx = {line, v};
    generate for (i = 1; i <= D; i = i + 1) begin : g_b
        always @(posedge clk `OT_SU_ARST(rst_n[(i-1)/C])) begin
            if (!rst_n[(i-1)/C]) line[i] <= 1'b0;
            else line[i] <= nx[i-1];
        end
    end endgenerate
    assign vd = {line, v};
endmodule

// ot_sync_rst_relay (rtl/lib/ot_sync_rst_relay.sv) with the kept local relay register as an N-member ot_rst_split copy
// family (HBM-KIND9; it3 census: stage relays drove 40-56 reset loads; the n32 adders add 10 valid flops each).  Same
// two clk_sync sampling flops, same release edge (three edges to the relay, consumers at edge four); the splitter
// re-points each consumer to one member (<= 32 loads), the members sit with their consumers.
module ot_k9_rst_fam #(parameter integer N = 3) (
    input  wire clk_sync,
    input  wire clk,
    input  wire rst_n_in,
    output wire rst_n
);
    (* async_reg = "true" *) reg [1:0] sync_q;
    (* keep = "true", dont_touch = "true" *) reg local_reset_q;
    always @(posedge clk_sync) sync_q <= {sync_q[0], rst_n_in};
    always @(posedge clk) local_reset_q <= sync_q[1];
    assign rst_n = local_reset_q;
    generate if (N > 1) begin : g_fam
        (* keep = 1 *) reg [N-2:0] cp;
        always @(posedge clk) cp <= {(N-1){sync_q[1]}};
        (* keep = 1, ot_rst_split = 1 *) wire [N-1:0] family = {cp, local_reset_q};
    end endgenerate
endmodule

// ot_k9_fam with a reset (valid / control copies).  OT_SU_SYNC_RST: the synchronous clear is folded into ONE shared
// D net (dn = rst_n ? d : 0), so every member is a plain flop on the same D (the splitter's identity proof); otherwise an
// asynchronous clear on every member.
module ot_k9_famr #(parameter integer W = 1, parameter integer N = 3) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    (* keep = 1 *) reg [W-1:0] r;
`ifdef OT_SU_SYNC_RST
    wire [W-1:0] dn = rst_n ? d : {W{1'b0}};
    always @(posedge clk) r <= dn;
`else
    wire [W-1:0] dn = d;
    always @(posedge clk or negedge rst_n) if (!rst_n) r <= {W{1'b0}}; else r <= dn;
`endif
    assign q = r;
    generate if (N > 1) begin : g_fam
        for (genvar b = 0; b < W; b = b + 1) begin : g_bit
            (* keep = 1 *) reg [N-2:0] cp;
`ifdef OT_SU_SYNC_RST
            always @(posedge clk) cp <= {(N-1){dn[b]}};
`else
            always @(posedge clk or negedge rst_n) if (!rst_n) cp <= {(N-1){1'b0}}; else cp <= {(N-1){dn[b]}};
`endif
            (* keep = 1, ot_rst_split = 1 *) wire [N-1:0] family = {cp, r[b]};
        end
    end endgenerate
endmodule

// okey(a) >= okey(b) (the lane's binary32 total order, okey(v) = v[31] ? ~v : {1, v[30:0]}), exactly, WITHOUT the
// ordered-key XORs: two 31-bit magnitude compares and a sign select (HBM-KIND9; it3 census: each okey operand's sign bit
// drove its 32 key XORs and the compare, 34-41 loads).  Mixed signs: the positive operand is larger (+0 > -0, as okey);
// both negative: |a| <= |b|; both positive: |a| >= |b|.
module ot_k9_fge #(parameter integer K = 1) (
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire        ge
);
    wire ge_ab, ge_ba;
    ot_hdc_kge #(.W(31), .K(K)) u_ab (.a(a[30:0]), .b(b[30:0]), .ge(ge_ab));
    ot_hdc_kge #(.W(31), .K(K)) u_ba (.a(b[30:0]), .b(a[30:0]), .ge(ge_ba));
    assign ge = (a[31] != b[31]) ? b[31] : (a[31] ? ge_ba : ge_ab);
endmodule

// y = (c == VAL) ? a : b with its OWN decode of c (keep_hierarchy, so per-slice copies are never merged back): a wide
// code-selected mux built from slices of this loads each decode node with one slice (HBM-KIND9; it3: 34-48)
(* keep_hierarchy = "yes" *)
module ot_k9_eqmux_kh #(parameter integer W = 16, parameter integer CW = 2, parameter [CW-1:0] VAL = 0) (
    input  wire [CW-1:0] c,
    input  wire [W-1:0]  a,
    input  wire [W-1:0]  b,
    output wire [W-1:0]  y
);
    assign y = (c == VAL) ? a : b;
endmodule
