`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-2 (2026-10-17, S81-DV p4h): dsfd_su_t_smh, the per-head SM subtree (one per regional service slice, x16 on the
// die) built from hardened REGIONAL clusters (S81U-SMH2, 10-17): WIRES ONLY, no logic of its own.
//   4 x dsfd_su_t_smhq (lane quad q: lanes 4q..4q+3 + divide pairs 2q, 2q+1; ~400 um, own clock pin + reset relay)
//   1 x dsfd_su_t_smhr (root: sum + max/den root; own clock pin + reset relay)
// The g2 single 1,037 x 769 um cluster (one clock pin: TT insertion 1.04-1.29 ns, spread 249 ps; setup -646 ps on the
// unregistered reset, -330 ps relay -> far lane) is retired.  The svc slice places the five clusters as neighbours
// around the head's tap ot_s81_su_smq; every link between them is registered at both ends (<= 405 um planned reach).
// Cycle-equivalent to ot_s81_su_smh at DOP = SRL (the SRL stations of every link are split across the hop; only reset
// release is 2 cycles later: each cluster's own reset synchroniser).
// The bit-exact gates: tools/s81_su_sm/sms_bench.sh with SMT=1 (vs the slab SM stop) and su_gate.py run --hier --smu
// with OT_SU_VDEFS=-DSU_SMU_T (the slab instantiates this top).
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_su_t_smh #(
    parameter integer SRL = 2,
    parameter integer DOP = SRL,                       // the smq tap forwards its row registered WITH the valids (DV);
                                                       // the slab's spine row is 2 cycles earlier: its -DSU_SMU_T
                                                       // embedding adds those 2 stations outside the cluster
    parameter integer MUT = 0                          // bench: 5 stale den, 6 root -> quad hop short (dsfd_su_t_smhq)
) (
    input  wire          clk,
    input  wire          rst_in,                       // the stop's reset (each cluster relays it through its own sync)
    // from the tap (registered there)
    input  wire          s_v,                          // a score vector (SE)
    input  wire          p_v,                          // a PV vector (SO)
    input  wire          c_v,                          // SE configuration pulse
    input  wire [6:0]    c_nv,
    input  wire [2:0]    c_lt,
    input  wire [31:0]   c_scale,
    input  wire [31:0]   c_sink,                       // this head's sink
    input  wire          cs_v,                         // cos / sin pair cs_i
    input  wire [4:0]    cs_i,
    input  wire [63:0]   cs_d,
    input  wire [511:0]  d,                            // this head's operand row (16 lanes x 32 b)
    // to the tap
    output wire          e_v,                          // e vector (16 lanes)
    output wire [511:0]  e_d,
    output wire          o_v,                          // o vector (16 lanes BF16)
    output wire [255:0]  o_d,
    output wire          den_v,                        // den reached the divide engines
    output wire [7:0]    f                             // the divide engines' sticky faults
);
    generate if (DOP != SRL || SRL < 1) begin : g_bad
        initial $fatal(1, "dsfd_su_t_smh: the regional clusters need DOP == SRL >= 1 (SRL %0d DOP %0d)", SRL, DOP);
    end endgenerate
    wire [3:0] q_mxv, q_ev, q_el, q_skv, qe_v, qo_v; wire [511:0] q_mx, q_e;
    wire m_v, dn_v; wire [31:0] m_nmb, dn;
    genvar q;
    generate for (q = 0; q < 4; q = q + 1) begin : g_q
        wire [1:0] CQ = q;
        dsfd_su_t_smhq #(.SRL(SRL), .MUT(MUT)) u_q (
            .clk(clk), .rst_in(rst_in), .cfg_q(CQ),
            .s_v(s_v), .p_v(p_v), .c_v(c_v), .c_nv(c_nv), .c_scale(c_scale), .c_sink(c_sink),
            .cs_v(cs_v), .cs_i(cs_i), .cs_d(cs_d), .d(d[128 * q +: 128]),
            .m_v(m_v), .m_nmb(m_nmb), .dn_v(dn_v), .dn(dn),
            .q_mxv(q_mxv[q]), .q_ev(q_ev[q]), .q_el(q_el[q]), .q_skv(q_skv[q]),
            .q_mx(q_mx[128 * q +: 128]), .q_e(q_e[128 * q +: 128]),
            .e_v(qe_v[q]), .e_d(e_d[128 * q +: 128]), .o_v(qo_v[q]), .o_d(o_d[64 * q +: 64]), .f(f[2 * q +: 2]));
    end endgenerate
    dsfd_su_t_smhr #(.SRL(SRL)) u_r (
        .clk(clk), .rst_in(rst_in), .c_v(c_v), .c_lt(c_lt),
        .q_mxv(q_mxv[0]), .q_ev(q_ev[0]), .q_el(q_el[0]), .q_skv(q_skv[0]), .q_mx(q_mx), .q_e(q_e),
        .m_v(m_v), .m_nmb(m_nmb), .dn_v(dn_v), .dn(dn), .den_v(den_v));
    assign e_v = qe_v[0];
    assign o_v = qo_v[0];
endmodule
