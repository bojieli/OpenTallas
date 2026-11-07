#!/usr/bin/env python3
"""DIE-QC-87 11-07 NK vR4 (OWNER 05:1x pin cycles first), PINC opt-in, default 0 = unchanged.

Measured cause (NK vB2hp routed, slew class): the n_a/n_b/t_out/n_y face flops sit on the left face behind the node macro and
drive or receive 250-300 um to the central channel in one stage.  PINC = 1 adds one stage on each: face flop n_a_q/n_b_q ->
channel flop n_a_p/n_b_p -> body, and body -> channel flop t_out_p/n_y_p -> face flop t_out_q/n_y_q.

PIN CYCLES (declared in the kit): t_out +1; n_a/n_b -> n_y +2 (+1 in, +1 out).  The node fault/valid sideband moves with the data:
mis_q/fy_q read the delayed legs.  ICG: the face activity term covers the extra input stage, or the gate could close before the
body captures the last delayed word.  Reset gating stays on both stages of the output sideband.

Bench-only `OT_PINC_MUT (must FAIL): 1 = n_b skips its stage (legs misaligned), 2 = t_out valid skips its stage (valid leads
data), 3 = the ICG activity term one edge late.
usage: pinc_patch.py RTL_DIR
"""
import sys
from pathlib import Path
R = Path(sys.argv[1])

def sub(name, old, new, count=1):
    p = R / name; s = p.read_text(); n = s.count(old)
    if n != count:
        sys.exit(f"pinc_patch: {name}: expected {count} x {old!r}, found {n}")
    p.write_text(s.replace(old, new))

B = "qfd_tile_nk_rp2_45.sv"; T = "qfd_tile_nk_a0c.sv"
sub(B, "parameter integer RSTP = 0, parameter integer LQR = 0",
       "parameter integer PINC = 0, // tools/qwen_romleaf/a0core/lqr/pinc_patch.py\n    parameter integer RSTP = 0, parameter integer LQR = 0")
sub(B, """    always @(posedge ck_fa1) n_b_q<=n_b;
""", """    always @(posedge ck_fa1) n_b_q<=n_b;
    // PINC: channel stage after the face flops
    wire [513:0] n_a_c, n_b_c;
    generate if (PINC != 0) begin : g_pinc_in
        (* keep *) reg [513:0] n_a_p, n_b_p;
        always @(posedge ck_fa0) n_a_p <= n_a_q;
        always @(posedge ck_fa1) n_b_p <= n_b_q;
        assign n_a_c = n_a_p;
`ifdef OT_PINC_MUT
        assign n_b_c = (`OT_PINC_MUT == 1) ? n_b_q : n_b_p;
`else
        assign n_b_c = n_b_p;
`endif
    end else begin : g_pinc_in0
        assign n_a_c = n_a_q;
        assign n_b_c = n_b_q;
    end endgenerate
""")
sub(B, ".n_a(n_a_q[511:0]), .n_b(n_b_q[511:0]), .n_va(n_a_q[512])", ".n_a(n_a_c[511:0]), .n_b(n_b_c[511:0]), .n_va(n_a_c[512])")
sub(B, """    (* keep *) reg [513:0] t_out_q;
    always @(posedge ck_fa2) begin
        t_out_q[511:0]<=to;
        t_out_q[513:512]<=t_out_reset_n ? {tf,tv} : 2'd0;
    end
""", """    (* keep *) reg [513:0] t_out_q;
    wire [511:0] to_c; wire [1:0] tfv_c;
    generate if (PINC != 0) begin : g_pinc_to
        (* keep *) reg [513:0] t_out_p;
        always @(posedge ck_fa2) begin
            t_out_p[511:0] <= to;
            t_out_p[513:512] <= t_out_reset_n ? {tf,tv} : 2'd0;
        end
        assign to_c = t_out_p[511:0];
`ifdef OT_PINC_MUT
        assign tfv_c = (`OT_PINC_MUT == 2) ? {t_out_p[513], tv} : t_out_p[513:512];
`else
        assign tfv_c = t_out_p[513:512];
`endif
    end else begin : g_pinc_to0
        assign to_c = to;
        assign tfv_c = {tf,tv};
    end endgenerate
    always @(posedge ck_fa2) begin
        t_out_q[511:0]<=to_c;
        t_out_q[513:512]<=t_out_reset_n ? tfv_c : 2'd0;
    end
""")
sub(B, """            mis_q <= mis_q | (n_a_q[512] ^ n_b_q[512]);
            fy_q  <= n_a_q[513] | n_b_q[513] | mis_q;
""", """            mis_q <= mis_q | (n_a_c[512] ^ n_b_c[512]);
            fy_q  <= n_a_c[513] | n_b_c[513] | mis_q;
""")
sub(B, """    (* keep *) reg [513:0] n_y_q;
    always @(posedge ck_fa3) begin
        n_y_q[511:0]<=ny;
        n_y_q[513:512]<=t_out_reset_n ? {fy_q,nvy} : 2'd0;
    end
""", """    (* keep *) reg [513:0] n_y_q;
    wire [511:0] ny_c; wire [1:0] fyv_c;
    generate if (PINC != 0) begin : g_pinc_ny
        (* keep *) reg [513:0] n_y_p;
        always @(posedge ck_fa3) begin
            n_y_p[511:0] <= ny;
            n_y_p[513:512] <= t_out_reset_n ? {fy_q,nvy} : 2'd0;
        end
        assign ny_c = n_y_p[511:0];
        assign fyv_c = n_y_p[513:512];
    end else begin : g_pinc_ny0
        assign ny_c = ny;
        assign fyv_c = {fy_q,nvy};
    end endgenerate
    always @(posedge ck_fa3) begin
        n_y_q[511:0]<=ny_c;
        n_y_q[513:512]<=t_out_reset_n ? fyv_c : 2'd0;
    end
""")
sub(T, "parameter integer RSTP = 0, parameter integer LQR = 0,",
       "parameter integer PINC = 0, // tools/qwen_romleaf/a0core/lqr/pinc_patch.py\n    parameter integer RSTP = 0, parameter integer LQR = 0,")
sub(T, ".NKP(NKP), .LQR(LQR), .RSTP(RSTP)) u_g (", ".NKP(NKP), .LQR(LQR), .RSTP(RSTP), .PINC(PINC)) u_g (", 2)
sub(T, """        wire nv_act = |nv_f;
""", """        // PINC: body inputs n_a_c / n_b_c lag the n_a_q / n_b_q faces one edge, so the activity term lags with them (nv_f2).
        // nv_f shares its flops with the late face; nv_f2 is the retimed copy the ICG enable reads, tapped early (OT_B3_MID).
        // Async reset keeps it a distinct cell from n_a_p / n_b_p, which have the same D.
        reg [3:0] nv_f2;
`ifdef OT_PINC_MUT
        reg [3:0] nv_f3;
        wire nv_act = (PINC == 0) ? |nv_f : ((`OT_PINC_MUT == 3) ? |nv_f3 : |nv_f2);
`else
        wire nv_act = (PINC == 0) ? |nv_f : |nv_f2;
`endif
""")
sub(T, """        wire act = ((mut == 5) ? 1'b0 : !rst_e) | go_act | ((mut == 2) ? 1'b0 : !me_idle) | ((mut == 4) ? 1'b0 : nv_act);
""", """        always @(posedge ck or negedge rst_e) if (!rst_e) nv_f2 <= 4'd0; else nv_f2 <= nv_f;
`ifdef OT_PINC_MUT
        always @(posedge ck) nv_f3 <= nv_f2;
`endif
        wire act = ((mut == 5) ? 1'b0 : !rst_e) | go_act | ((mut == 2) ? 1'b0 : !me_idle) | ((mut == 4) ? 1'b0 : nv_act);
""")
# The ungated node has one input register plus eight valid-delay registers.
# Keep the gated output face clocking through the falling-valid edge. PINC
# adds one gated output stage; its delayed activity also moves the drain origin.
# This floor is derived only for the ICG=1, ICG_IREG=1, ICG_EREG=1 class used by vR4.
sub(T, "    wire ck_rp0;", """    localparam integer ICG_NODE_DRAIN_MIN = 9 + (PINC != 0);
    localparam integer ICG_EFFECTIVE_DRAIN = (ICG == 1 && ICG_IREG != 0 && ICG_EREG != 0 && ICG_DRAIN < ICG_NODE_DRAIN_MIN)
                                            ? ICG_NODE_DRAIN_MIN : ICG_DRAIN;
    wire ck_rp0;""")
sub(T, "8'(ICG_DRAIN)", "8'(ICG_EFFECTIVE_DRAIN)", 4)
sub(T, "8'(ICG_DRAIN - ((mut == 16) ? 0 : 1))", "8'(ICG_EFFECTIVE_DRAIN - ((mut == 16) ? 0 : 1))")

sub(T, "ICG_DRAIN < 2", "ICG_EFFECTIVE_DRAIN < 2")
sub(T, "ICG_DRAIN >= 2", "effective ICG drain >= 2")
print("PINC_PATCH_OK")
