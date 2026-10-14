`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_pq: S81 layer-die PQ core slot (contract v15 rep/pqc/dsfd_sp_pq, 1672.248 x 449.256) as ONE hardened CLUSTER:
// wires only over the closed PQ spine tiles (physical/s81_pq_hier, el1011-ds-misc/pqc v15 hierarchical spine):
//     T_XIN x2 (x_q pin registers)   T_AQ x2 (ot_dsrom_aq12t quantiser)   T_IX x4 (BF16 x buffer)   T_QB (q buffer)
//     T_CTL (ot_pqc_t_ctl16: issuer / loader / reader / streamer + the scalar pin registers)
//     T_RET x2 (8 regions each: return decode, row write, row counts)   T_BC x8 (broadcast relay stages + out register)
// No flop and no logic at this level (constant ties only: the T_IX parity straps and the T_BC bits a relay tile does
// not carry); every pin of the cluster is a pin of
// one tile, and every tile pin is a tile register (T_CTL's rom_pa* / rom_sa are its NEXT-address outputs: the ROM macro
// registers them).
//
// SHAPE: the tiles are the fixed-name tops of the physical-screen shape (PHW 6, SAW 8, VAW 19, VRD 64, KMAX 256, R 16,
// BW 1630, PQ 1, XRV 1, XCAP 16, RPT 2), so this cluster is cycle- and bit-identical to ot_v41_pqc_spine_screen (TT = 1)
// with its three ROM fixtures taken OUT: the die holds the phase / stream ROMs in ROM macros (pqrom0..2), so the ROM
// ports leave the cluster (N face, beside T_CTL).  ROM contract (the spine's "two-cycle synchronous macro"): rom_pq0 /
// rom_pq1 / rom_sq at edge t + 2 hold the word of the address driven at edge t, i.e. a one-cycle ROM macro plus ONE
// register stage on the data return (the die's relay at the ROM).
// Floorplan / hops / cuts: tools/s81/sp_pq_plan.py (every tile-to-tile and pin-to-tile hop <= 500 um).
// Bench: tools/s81/sp_pq_lockstep.py (lockstep against the FLAT v14 screen physical/s81_pq_xrv/pinned, every output,
// every cycle, + tile mutants).
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_pq (
    input  wire          clk,
    input  wire          rst_n,
    // op issuer (registered in T_CTL)
    input  wire          go,
    input  wire [5:0]    i_ph,
    input  wire [2:0]    i_np,
    input  wire [18:0]   i_xbase,
    input  wire [18:0]   i_xps,
    input  wire [18:0]   i_obase,
    input  wire [18:0]   i_ops,
    input  wire [1:0]    i_fmt,
    input  wire          f_fault,
    output wire          o_ready,
    output wire          o_idle,
    output wire          o_fault,
    output wire          o_ev,
    // vector-memory read (valid return)
    output wire          o_x_re,
    output wire [18:0]   o_x_addr,
    input  wire          x_rv,
    input  wire [2047:0] x_q,
    // region returns (16 regions) and their row writes
    input  wire [15:0]   r_v,
    input  wire [255:0]  r_row,
    input  wire [47:0]   r_pos,
    input  wire [511:0]  r_fp32,
    input  wire [255:0]  r_bf16,
    input  wire [15:0]   r_e,
    output wire [15:0]   o_w_we,
    output wire [303:0]  o_w_addr,
    output wire [511:0]  o_w_data,
    // broadcast to the field (after 4 relay stages + the out register)
    output wire [1629:0] o_bus,
    // phase ROM (two words of a phase) and stream ROM
    output wire [6:0]    rom_pa0,
    output wire [6:0]    rom_pa1,
    input  wire [63:0]   rom_pq0,
    input  wire [63:0]   rom_pq1,
    output wire [7:0]    rom_sa,
    input  wire [47:0]   rom_sq
);
    wire          aq_vin, ba_v;
    wire [1:0]    aqf;
    wire [4:0]    aqi;
    wire [2:0]    ba_blk;
    wire [47:0]   hw;
    wire [35:0]   h_hi;
    wire [15:0]   h_b0, h_b1;
    wire [457:0]  mdr;
    wire [1:0]    q2f;
    wire [31:0]   ga;
    wire [605:0]  bc_hr;
    wire [2047:0] xq;
    wire [511:0]  aq_q;
    wire [19:0]   aq_e;
    wire [255:0]  hq0, hq1;
    wire [9:0]    he0, he1;
    wire [255:0]  ixd0, ixd1, ixd2, ixd3;
    wire [1023:0] bt_d;
    wire [1629:0] bc0;
    wire          par0 = 1'b0, par1 = 1'b1;

    ot_pqc_t_xin u_xin0 (.clk(clk), .d(x_q[1023:0]), .q(xq[1023:0]));
    ot_pqc_t_xin u_xin1 (.clk(clk), .d(x_q[2047:1024]), .q(xq[2047:1024]));

    ot_pqc_t_ctl16 u_ctl (.clk(clk), .rst_n(rst_n), .aq_vin(aq_vin), .aqf(aqf), .aqi_o(aqi), .ba_v_o(ba_v),
        .ba_blk_o(ba_blk), .hw_o(hw), .h_hi_o(h_hi), .h_b0_o(h_b0), .h_b1_o(h_b1), .mdr_o(mdr), .q2f_i(q2f), .ga_i(ga),
        .bc_hr_o(bc_hr), .go(go), .i_ph(i_ph), .i_np(i_np), .i_xbase(i_xbase), .i_xps(i_xps), .i_obase(i_obase),
        .i_ops(i_ops), .i_fmt(i_fmt), .x_rv(x_rv), .f_fault(f_fault), .o_ready(o_ready), .o_idle(o_idle),
        .o_x_re(o_x_re), .o_x_addr(o_x_addr), .o_fault(o_fault), .o_ev(o_ev), .rom_pa0(rom_pa0), .rom_pa1(rom_pa1),
        .rom_pq0(rom_pq0), .rom_pq1(rom_pq1), .rom_sa(rom_sa), .rom_sq(rom_sq));

    /* verilator lint_off PINCONNECTEMPTY */
    ot_dsrom_aq12t u_aq0 (.clk(clk), .rst_n(rst_n), .v(aq_vin), .x(xq[1023:0]), .vo(), .q(aq_q[255:0]),
                          .e(aq_e[9:0]), .y(), .fault(aqf[0]));
    ot_dsrom_aq12t u_aq1 (.clk(clk), .rst_n(rst_n), .v(aq_vin), .x(xq[2047:1024]), .vo(), .q(aq_q[511:256]),
                          .e(aq_e[19:10]), .y(), .fault(aqf[1]));
    /* verilator lint_on PINCONNECTEMPTY */

    ot_pqc_t_qb u_qb (.clk(clk), .rst_n(rst_n), .aqi_d(aqi), .aq_q(aq_q), .aq_e(aq_e), .h_b0(h_b0), .h_b1(h_b1),
                      .hw_sv(hw[13:12]), .hq0(hq0), .hq1(hq1), .he0(he0), .he1(he1));

    // T_IX g: block parity g[1], words 32 g[0] ..; its lane group u lands at bt_d[256 u + 64 g +: 64]
    ot_pqc_t_ix u_ix0 (.clk(clk), .rst_n(rst_n), .par(par0), .xw(xq[1023:0]), .ba_v(ba_v), .ba_blk(ba_blk),
                       .h_hi(h_hi), .hw7(hw[7:1]), .bt_d(ixd0));
    ot_pqc_t_ix u_ix1 (.clk(clk), .rst_n(rst_n), .par(par0), .xw(xq[2047:1024]), .ba_v(ba_v), .ba_blk(ba_blk),
                       .h_hi(h_hi), .hw7(hw[7:1]), .bt_d(ixd1));
    ot_pqc_t_ix u_ix2 (.clk(clk), .rst_n(rst_n), .par(par1), .xw(xq[1023:0]), .ba_v(ba_v), .ba_blk(ba_blk),
                       .h_hi(h_hi), .hw7(hw[7:1]), .bt_d(ixd2));
    ot_pqc_t_ix u_ix3 (.clk(clk), .rst_n(rst_n), .par(par1), .xw(xq[2047:1024]), .ba_v(ba_v), .ba_blk(ba_blk),
                       .h_hi(h_hi), .hw7(hw[7:1]), .bt_d(ixd3));
    assign bt_d = {ixd3[255:192], ixd2[255:192], ixd1[255:192], ixd0[255:192],
                   ixd3[191:128], ixd2[191:128], ixd1[191:128], ixd0[191:128],
                   ixd3[127:64],  ixd2[127:64],  ixd1[127:64],  ixd0[127:64],
                   ixd3[63:0],    ixd2[63:0],    ixd1[63:0],    ixd0[63:0]};

    ot_pqc_t_ret u_ret0 (.clk(clk), .rst_n(rst_n), .r_v(r_v[7:0]), .r_row(r_row[127:0]), .r_pos(r_pos[23:0]),
        .r_fp32(r_fp32[255:0]), .r_bf16(r_bf16[127:0]), .r_e(r_e[7:0]), .mdr(mdr), .w_we(o_w_we[7:0]),
        .w_addr(o_w_addr[151:0]), .w_data(o_w_data[255:0]), .q2f(q2f[0]), .ga(ga[15:0]));
    ot_pqc_t_ret u_ret1 (.clk(clk), .rst_n(rst_n), .r_v(r_v[15:8]), .r_row(r_row[255:128]), .r_pos(r_pos[47:24]),
        .r_fp32(r_fp32[511:256]), .r_bf16(r_bf16[255:128]), .r_e(r_e[15:8]), .mdr(mdr), .w_we(o_w_we[15:8]),
        .w_addr(o_w_addr[303:152]), .w_data(o_w_data[511:256]), .q2f(q2f[1]), .ga(ga[31:16]));

    // broadcast {bc_hr with T_QB's fields, bt_d}: BST + RPT = 4 relay stages + the out register = FIVE T_BC flops on
    // every bit, as in the screen.  The floorplan cannot bring every source within 500 um of ONE first-stage tile (the
    // two 281-um quantisers sit between the x-buffer pairs), so the five stages are laid along the way to the E face and
    // each bit takes the tiles on its own way (a T_BC is 1,630 independent flops; a bit a tile does not carry is tied):
    //   W bits (bt_d of T_IX0 / T_IX2):   u_bc0a -> u_bc1 -> u_bt1 -> u_bt2 -> u_bt3
    //   C bits (T_QB, T_CTL: [1629:1024]): u_bc0b -> u_bc1 -> u_bt1 -> u_bt2 -> u_bt3
    //   E bits (bt_d of T_IX1 / T_IX3):   u_bt1  -> u_bt2 -> u_bt3 -> u_bt4 -> u_bt5
    // Same function and latency on every bit as the five-tile chain (bench: lockstep against the flat screen).
    assign bc0 = {bc_hr[605:578], hq0, he0, hq1, he1, bc_hr[45:0], bt_d};
    wire [1629:0] d_0a, d_0b, d_1, d_t1, d_t4, d_t5, q_0a, q_0b, q_1, q_t1, q_t2, q_t3, q_t4, q_t5;
    genvar gi;
    generate for (gi = 0; gi < 1630; gi = gi + 1) begin : g_bcw
        localparam integer GE = (gi < 1024) && (((gi / 64) % 2) == 1);     // lane group of T_IX1 / T_IX3
        localparam integer GW = (gi < 1024) && (((gi / 64) % 2) == 0);     // lane group of T_IX0 / T_IX2
        assign d_0a[gi] = GW ? bc0[gi] : 1'b0;
        assign d_0b[gi] = (gi >= 1024) ? bc0[gi] : 1'b0;
        assign d_1[gi]  = GW ? q_0a[gi] : (gi >= 1024) ? q_0b[gi] : 1'b0;
        assign d_t1[gi] = GE ? bc0[gi] : q_1[gi];
        assign d_t4[gi] = GE ? q_t3[gi] : 1'b0;
        assign d_t5[gi] = GE ? q_t4[gi] : 1'b0;
        assign o_bus[gi] = GE ? q_t5[gi] : q_t3[gi];
    end endgenerate
    ot_pqc_t_bc u_bc0a (.clk(clk), .rst_n(rst_n), .d(d_0a), .q(q_0a));
    ot_pqc_t_bc u_bc0b (.clk(clk), .rst_n(rst_n), .d(d_0b), .q(q_0b));
    ot_pqc_t_bc u_bc1  (.clk(clk), .rst_n(rst_n), .d(d_1),  .q(q_1));
    ot_pqc_t_bc u_bt1  (.clk(clk), .rst_n(rst_n), .d(d_t1), .q(q_t1));
    ot_pqc_t_bc u_bt2  (.clk(clk), .rst_n(rst_n), .d(q_t1), .q(q_t2));
    ot_pqc_t_bc u_bt3  (.clk(clk), .rst_n(rst_n), .d(q_t2), .q(q_t3));
    ot_pqc_t_bc u_bt4  (.clk(clk), .rst_n(rst_n), .d(d_t4), .q(q_t4));
    ot_pqc_t_bc u_bt5  (.clk(clk), .rst_n(rst_n), .d(d_t5), .q(q_t5));
endmodule
