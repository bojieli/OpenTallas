`timescale 1ns/1ps
// =====================================================================================================================
// TOK-FUNC2-QW-OVL 2026-10-21: 4-user compute <-> KV D2D link co-sim with OVERLAPPING request / response segments on the
// RELEASE D2D MASTERS (the closed hard tiles' RTL), extending tb_d2d_ovl_mu.sv (MU-D2D-OVL 10-19, generic end).
// On-chip RTL (source assembly):
//   compute  qfd_d2d_static_ovl_sf7  #(.TXDP(P_TXD_C))  (kit qfd_d2d_static_sf7w: ot_qwen_d2d_dies.sv + safe5 + safe7):
//            pin flops, reset tree, follower recovery, SAFE7 end (two calendars, slot SRAM link, CRC), kind-15 STATUS
//            codec, KVN kind-5 codec
//   KV       qkd_d2d_static_ovl_sfm3 #(.NTX(3), .SRAMV(2), .FEG(1), .SAFE_RC(1), .TXDP(P_TXD_K)) (kit qkd_d2d_static_ovl_sfm3):
//            pin flops + fan-out copies, master recovery (HOST boot), first-epoch guard calendars, slot SRAM link,
//            STATUS decoder, KVN decoder, HOST link services
//   both     ot_qwen_d2d_ovl_seq (init image load, anchor, the two compiled start-list players a die) on the compiler's
//            frame (tools/qwen_static_schedule/mu_d2d_ovl.py: the 4-user F16 frame of record)
// Modelled (declared): the UCIe PHY pair (ot_qkvd_ucie_x64_phy_model, LAT = P_PHY - 2: the masters' own FDI pin flops are
//   real here), the 3-flop package bump of the forwarded epoch / link reset, the list ROMs, the producers at the master
//   pins (each TX port answers its slot pin exactly TXD_p - 2 edges later = the seam + codec latency the TXDP carries,
//   minus the masters' slot-out and payload-in pin flops; the KVN x3 word TXD_3 - 3 edges later: + the in-master KVN
//   codec register) and the consumers (scoreboards).  The STATUS record (C TX port 2) is produced INSIDE the compute
//   master from the result_* / level pins; the bench pulses result_v once after every compiled STATUS slot (declared
//   stimulus: the result of the segment, then carried by the next STATUS record).
// Port map (compiled calendar ports): C TX 0 native CMD/Q, 1 program witness (kind 14), 2 STATUS (kind 15), 3 KVN (kind 5);
//   C RX 0 attention RESULT/STATUS, 1 context (kind 12), 2 embedding row (kinds 8/6/7);  K TX 0 attention RESULT/STATUS,
//   1 HOST record (kind 12), 2 embedding row;  K RX 0 CMD/Q, 1 witness, 2 STATUS, 3 KVN.
// Checks (any one -> D2DOVL_FAIL): no epoch abort / master fault / sequencer fault for one whole frame + wrap; every
//   frame a sender end writes equals the bench golden of its port (producer word / STATUS encoding / KVN encoding) and is
//   delivered in order at the receiver end bit-exact, on the port, kind and beat the RECEIVER's compiled calendar expects
//   (rx_event == rx_slot every edge), tagged with the sender's user (rx_user == tx_user); at the KV master pins every
//   STATUS result (engine_result_*) and every KVN word (kvn_word_*) equals what the compute pins were given, in order;
//   the KV HOST services report the compute status levels; per frame and user: exchanges (STATUS kind 4 at compute RX
//   port 0) and tokens (embedding kind 7 beat 31 at compute RX port 2), counted at the compute master PINS with rx_user,
//   equal the compiler's counts.
// Measured: H = edges between two frame starts (first C TX list start of a frame), aggregate tok/s = tokens x 1.2 GHz / H.
// Mutants (compiler, mu_d2d_ovl.py --mut): collide, slot, user; OVL = 0 = one playhead: the RX start / segment / user pins
//   of both masters driven from the TX player (the as-built single-playhead end) on the same frame.  All must FAIL.
// =====================================================================================================================
module ovl_rel_dly #(parameter integer X = 1) (input wire ck, input wire v_i, input wire [1:0] u_i, input wire [3:0] k_i,
    input wire [4:0] b_i, output wire v_o, output wire [1:0] u_o, output wire [3:0] k_o, output wire [4:0] b_o);
    reg [X-1:0] v = '0; reg [1:0] u [0:X-1]; reg [3:0] k [0:X-1]; reg [4:0] b [0:X-1];
    integer i;
    always @(posedge ck) begin
        v <= {v, v_i}; u[0] <= u_i; k[0] <= k_i; b[0] <= b_i;
        for (i = 1; i < X; i = i + 1) begin u[i] <= u[i-1]; k[i] <= k[i-1]; b[i] <= b[i-1]; end
    end
    assign v_o = v[X-1]; assign u_o = u[X-1]; assign k_o = k[X-1]; assign b_o = b[X-1];
endmodule

module tb_d2d_ovl_mu_rel;
    parameter integer OVL = 1;
    parameter CALDIR = "cal";
    `include "ovl_params.svh"
    `include "ovl_img.svh"
    localparam integer FW = 548, PW = 583, AW = 11;
    localparam integer XC0 = P_TXD_C[7:0] - 2, XC1 = P_TXD_C[15:8] - 2, XC3 = P_TXD_C[31:24] - 3;
    localparam integer XK0 = P_TXD_K[7:0] - 2, XK1 = P_TXD_K[15:8] - 2, XK2 = P_TXD_K[23:16] - 2;
    localparam [15:0] EP16 = 16'h0421;
    localparam [58:0] KID = {EP16, 6'd5, 18'd4242, 13'd77, 6'd0};   // KVN compiled identity (TAG59)
    localparam [1:0]  KGEN = 2'd1;
    localparam [5:0]  LEV = 6'b110101;   // {admit_ready, execution_active, crom_fault, busy, coll_drained, vm_drained}
    reg ck = 0; always #0.4167 ck = ~ck;
    reg por_n = 0, rst_n = 0, seq_rst_n = 0;
    integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;
    reg failed = 0;
    task automatic err(input string s); begin if (!failed) $display("D2DOVL_ERR cyc %0d: %s", cyc, s); failed = 1; end endtask
    initial begin
        if (XC0 < 1 || XC1 < 1 || XC3 < 1 || XK0 < 1 || XK1 < 1 || XK2 < 1) begin
            $display("D2DOVL_ERR compiled TXDP below the masters' pin-flop latency"); $display("D2DOVL_FAIL"); $finish; end
    end

    // ---------------------------------------------------------------- list ROMs (synchronous read)
    reg [31:0] rom_ctx [0:(1<<AW)-1], rom_crx [0:(1<<AW)-1], rom_ktx [0:(1<<AW)-1], rom_krx [0:(1<<AW)-1];
    initial begin
        $readmemh({CALDIR, "/list_C_tx.memh"}, rom_ctx); $readmemh({CALDIR, "/list_C_rx.memh"}, rom_crx);
        $readmemh({CALDIR, "/list_K_tx.memh"}, rom_ktx); $readmemh({CALDIR, "/list_K_rx.memh"}, rom_krx);
    end
    wire [AW-1:0] a_ctx, a_crx, a_ktx, a_krx; reg [31:0] q_ctx, q_crx, q_ktx, q_krx;
    always @(posedge ck) begin q_ctx <= rom_ctx[a_ctx]; q_crx <= rom_crx[a_crx]; q_ktx <= rom_ktx[a_ktx]; q_krx <= rom_krx[a_krx]; end

    // ---------------------------------------------------------------- sequencers
    reg epoch_go = 0;
    wire c_abort, k_abort, c_f, k_f, c_sf, k_sf;
    wire c_ctw, c_crw, k_ctw, k_crw; wire [5:0] c_ca, k_ca; wire [31:0] c_cd, k_cd;
    wire c_cs, c_cg, c_crs, c_crg, k_cs, k_cg, k_crs, k_crg; wire [1:0] c_ut, c_ur, k_ut, k_ur;
    wire c_rdy, k_rdy;
    ot_qwen_d2d_ovl_seq #(.AW(AW), .TX_IMG(IMG_C_TX), .RX_IMG(IMG_C_RX), .TX_SEG1(SEG1_C_TX), .RX_SEG1(SEG1_C_RX),
        .FIRST_OFS(200)) u_cseq (.ck(ck), .rst_n(seq_rst_n), .reload(1'b0), .epoch_go(epoch_go), .halt(c_abort | c_f),
        .cfg_tx_we(c_ctw), .cfg_rx_we(c_crw), .cfg_addr(c_ca), .cfg_data(c_cd), .cal_start(c_cs), .cal_seg(c_cg),
        .cal_start_rx(c_crs), .cal_seg_rx(c_crg), .cal_user_tx(c_ut), .cal_user_rx(c_ur),
        .tx_rom_addr(a_ctx), .tx_rom_q(q_ctx), .rx_rom_addr(a_crx), .rx_rom_q(q_crx),
        .cal_ready(c_rdy), .adm_done(), .running(), .fault(c_sf));
    ot_qwen_d2d_ovl_seq #(.AW(AW), .TX_IMG(IMG_K_TX), .RX_IMG(IMG_K_RX), .TX_SEG1(SEG1_K_TX), .RX_SEG1(SEG1_K_RX),
        .FIRST_OFS(200)) u_kseq (.ck(ck), .rst_n(seq_rst_n), .reload(1'b0), .epoch_go(epoch_go), .halt(k_abort | k_f),
        .cfg_tx_we(k_ctw), .cfg_rx_we(k_crw), .cfg_addr(k_ca), .cfg_data(k_cd), .cal_start(k_cs), .cal_seg(k_cg),
        .cal_start_rx(k_crs), .cal_seg_rx(k_crg), .cal_user_tx(k_ut), .cal_user_rx(k_ur),
        .tx_rom_addr(a_ktx), .tx_rom_q(q_ktx), .rx_rom_addr(a_krx), .rx_rom_q(q_krx),
        .cal_ready(k_rdy), .adm_done(), .running(), .fault(k_sf));
    // OVL = 0 (one playhead): the RX pins follow the TX player (start, segment, user)
    wire c_rs_p = OVL ? c_crs : c_cs, c_rg_p = OVL ? c_crg : c_cg, k_rs_p = OVL ? k_crs : k_cs, k_rg_p = OVL ? k_crg : k_cg;
    wire [1:0] c_ru_p = OVL ? c_ur : c_ut, k_ru_p = OVL ? k_ur : k_ut;

    // ---------------------------------------------------------------- PHY pair + package bump (modelled)
    wire c_ptx_v, k_ptx_v, c_prx_v, k_prx_v, c_up, k_up, c_lv, k_lv; wire [PW-1:0] c_ptx, k_ptx, c_prx, k_prx, c_lf, k_lf;
    wire c_phy_rst_n, k_phy_rst_n;
    ot_qkvd_ucie_x64_phy_model #(.LAT(P_PHY - 2), .FW(PW)) u_cphy (.clk(ck), .rst_n(c_phy_rst_n), .tx_up(c_up),
        .tx_v(c_ptx_v), .tx_flit(c_ptx), .rx_v(c_prx_v), .rx_flit(c_prx), .link_v(c_lv), .link_flit(c_lf), .far_v(k_lv), .far_flit(k_lf));
    ot_qkvd_ucie_x64_phy_model #(.LAT(P_PHY - 2), .FW(PW)) u_kphy (.clk(ck), .rst_n(k_phy_rst_n), .tx_up(k_up),
        .tx_v(k_ptx_v), .tx_flit(k_ptx), .rx_v(k_prx_v), .rx_flit(k_prx), .link_v(k_lv), .link_flit(k_lf), .far_v(c_lv), .far_flit(c_lf));
    wire fwd_ep, fwd_lrst_n; reg [2:0] bump_ep = 0, bump_lr = 3'b111;
    always @(posedge ck) begin bump_ep <= {bump_ep, fwd_ep}; bump_lr <= {bump_lr, fwd_lrst_n}; end
    reg host_boot = 0;

    // ---------------------------------------------------------------- compute master
    wire c_txs0, c_wit, c_x3s; wire [3:0] c_tk; wire [4:0] c_tb; wire [1:0] c_tu, c_ru;
    wire c_rxv0, c_rxs0, c_prxv, c_embv, c_embs; wire [3:0] c_rk; wire [4:0] c_rb; wire [FW-1:0] c_rxp; wire [7:0] c_tf;
    wire c_tv0, c_tv1; wire [FW-1:0] c_tp0, c_tp1; reg [523:0] x3 = '0;
    reg res_v = 0; reg [148:0] res_f = '0;   // {cycles, value, token, gen, tag, cause, fault, done}
    qfd_d2d_static_ovl_sf7 #(.PR(1), .TXDP(P_TXD_C)) u_c (.ck(ck), .por_n(por_n), .rst_n(rst_n),
        .cfg_tx_we(c_ctw), .cfg_rx_we(c_crw), .cfg_addr(c_ca), .cfg_data(c_cd), .cal_start(c_cs), .cal_seg(c_cg),
        .cal_start_rx(c_rs_p), .cal_seg_rx(c_rg_p), .cal_user_tx(c_ut), .cal_user_rx(c_ru_p), .tx_user(c_tu), .rx_user(c_ru),
        .fwd_epoch(bump_ep[2]), .fwd_link_rst_n(bump_lr[2]),
        .native_tx_slot(c_txs0), .native_tx_slot_kind(c_tk), .native_tx_slot_beat(c_tb), .native_tx_v(c_tv0),
        .native_tx_payload(c_tp0), .rx_payload(c_rxp), .native_rx_v(c_rxv0), .native_rx_slot(c_rxs0),
        .native_rx_slot_kind(c_rk), .native_rx_slot_beat(c_rb),
        .prog_witness_slot(c_wit), .prog_head_context_slot(), .prog_auth_slot(), .prog_context_slot(),
        .prog_tx_observed_v(c_tv1), .prog_tx_record(c_tp1), .prog_rx_v(c_prxv), .emb_rx_v(c_embv), .emb_rx_slot(c_embs),
        .kv_x3_slot(c_x3s), .x3(x3), .x3_identity(KID), .x3_generation(KGEN),
        .status_epoch16(EP16), .vm_drained(LEV[0]), .collective_drained(LEV[1]), .collective_busy(LEV[2]),
        .crom_fault(LEV[3]), .execution_active(LEV[4]), .admit_ready(LEV[5]),
        .result_v(res_v), .result_done(res_f[0]), .result_fault(res_f[1]), .result_cause(res_f[5:2]), .result_tag(res_f[64:6]),
        .result_gen(res_f[66:65]), .result_token(res_f[84:67]), .result_value(res_f[116:85]), .result_cycles(res_f[148:117]),
        .fdi_tx_up(c_up), .fdi_tx_v(c_ptx_v), .fdi_tx_flit(c_ptx), .fdi_rx_v(c_prx_v), .fdi_rx_flit(c_prx),
        .phy_rst_n(c_phy_rst_n), .epoch_abort(c_abort), .transport_fault(c_tf), .fault(c_f));

    // ---------------------------------------------------------------- KV master
    wire k_txs0, k_embts; wire [1:0] k_sk; wire [3:0] k_tk; wire [4:0] k_tb; wire [1:0] k_tu, k_ru;
    wire k_rxv0, k_rxs0, k_recw, k_recv; wire [3:0] k_rk; wire [4:0] k_rb; wire [FW-1:0] k_rxp, k_rec;
    wire k_tv0, k_tv1, k_tv2; wire [FW-1:0] k_tp0, k_tp1, k_tp2;
    wire kw_v, kw_slot; wire [10:0] kw_tag; wire [511:0] kw_data; wire [58:0] kw_id; wire [1:0] kw_gen, kw_idx;
    wire [1:0] h_lu; wire [7:0] h_tf; wire h_ld, h_ls, h_rt; wire [3:0] h_ad;
    wire h_kvd, h_vmd, h_cod, h_hd, h_cb, h_kf, h_ar, h_cf, h_ea;
    wire s_rv, s_rd, s_rf; wire [3:0] s_rc; wire [58:0] s_rt; wire [1:0] s_rg; wire [17:0] s_rtok; wire [31:0] s_rval, s_rcyc, k_rcyc;
    qkd_d2d_static_ovl_sfm3 #(.NTX(3), .SAFE_RC(1), .SRAMV(2), .FEG(1), .PR(1), .TXDP(P_TXD_K)) u_k (.ck(ck), .por_n(por_n), .rst_n(rst_n),
        .cfg_tx_we(k_ctw), .cfg_rx_we(k_crw), .cfg_addr(k_ca), .cfg_data(k_cd), .cal_start(k_cs), .cal_seg(k_cg),
        .cal_start_rx(k_rs_p), .cal_seg_rx(k_rg_p), .cal_user_tx(k_ut), .cal_user_rx(k_ru_p), .tx_user(k_tu), .rx_user(k_ru),
        .host_link_reset_req(1'b0), .host_recovery_clear(1'b0), .host_boot_begin(host_boot),
        .fwd_epoch(fwd_ep), .fwd_link_rst_n(fwd_lrst_n),
        .att_tx_slot(k_txs0), .att_tx_kind(k_tk), .att_tx_beat(k_tb), .att_tx_v(k_tv0), .att_tx_payload(k_tp0),
        .att_rx_v(k_rxv0), .att_rx_slot(k_rxs0), .att_rx_kind(k_rk), .att_rx_beat(k_rb), .rx_payload(k_rxp), .rx_zero17(),
        .emb_tx_slot(k_embts), .emb_tx_v(k_tv2), .emb_tx_payload(k_tp2),
        .record_tx_observed_v(k_tv1), .record_tx(k_tp1), .record_send_kind(k_sk), .record_witness_slot(k_recw),
        .record_rx_v(k_recv), .record_rx(k_rec),
        .kvn_compiled_identity(KID), .kvn_compiled_generation(KGEN),
        .kvn_word_valid(kw_v), .kvn_word_tag(kw_tag), .kvn_word_data(kw_data), .kvn_word_identity(kw_id),
        .kvn_word_generation(kw_gen), .kvn_word_slot(kw_slot), .kvn_word_index(kw_idx),
        .status_epoch16(EP16), .serdes_up(1'b1), .kv_drained_local(1'b1), .kv_flush_local(1'b0),
        .host_drained_local(1'b1), .kv_active_local(1'b0),
        .link_up(h_lu), .transport_fault(h_tf), .native_links_drained(h_ld), .native_link_reset_seen(h_ls),
        .native_retrained(h_rt), .abort_drained(h_ad), .native_kv_drained(h_kvd), .native_vm_drained(h_vmd),
        .native_collective_drained(h_cod), .native_host_drained(h_hd), .native_collective_busy(h_cb),
        .native_kv_flush(h_kf), .native_admit_ready(h_ar), .crom_fault(h_cf), .execution_active(h_ea),
        .engine_result_v(s_rv), .engine_result_done(s_rd), .engine_result_fault(s_rf), .engine_result_cause(s_rc),
        .engine_result_tag(s_rt), .engine_result_gen(s_rg), .engine_result_token(s_rtok),
        .engine_result_value(s_rval), .engine_result_cycles(s_rcyc),
        .fdi_tx_up(k_up), .fdi_tx_v(k_ptx_v), .fdi_tx_flit(k_ptx), .fdi_rx_v(k_prx_v), .fdi_rx_flit(k_prx),
        .phy_rst_n(k_phy_rst_n), .epoch_abort(k_abort), .recovery_cycles(k_rcyc), .fault(k_f));

    // ---------------------------------------------------------------- producers at the master pins
    function automatic [FW-1:0] pl(input integer d, input integer n, input [1:0] u, input [2:0] p, input [3:0] k, input [4:0] b);
        integer j; reg [31:0] x; begin
            pl = '0; x = 32'(n) * 32'h9E3779B1 ^ 32'(d) * 32'h85EBCA6B ^ 32'(p) * 32'hC2B2AE35;
            for (j = 0; j < 16; j = j + 1) begin x = x * 32'h01000193 + 32'h3F800007; pl[32*j +: 32] = x; end
            pl[547:512] = {2'(d), u, p, k, b, 18'(n)};
        end endfunction
    // golden FIFOs per sender port: [0..3] compute TX ports, [4..6] KV TX ports
    reg [FW-1:0] gq [0:6][$];
    reg [10:0]   mq [0:6][$];        // {user, kind, beat} at the sender end's slot
    reg [148:0]  rq [$];             // results given at the compute pins
    reg [522:0]  kq [$];             // KVN {tag11, data512} given at the compute pins
    integer np [0:6];
    initial for (int i = 0; i < 7; i = i + 1) np[i] = 0;
    wire pc0_v, pc1_v, pc3_v, pk0_v, pk1_v, pk2_v; wire [1:0] pc0_u, pc1_u, pc3_u, pk0_u, pk1_u, pk2_u;
    wire [3:0] pc0_k, pc1_k, pc3_k, pk0_k, pk1_k, pk2_k; wire [4:0] pc0_b, pc1_b, pc3_b, pk0_b, pk1_b, pk2_b;
    ovl_rel_dly #(.X(XC0)) u_pc0 (.ck(ck), .v_i(c_txs0), .u_i(c_tu), .k_i(c_tk), .b_i(c_tb), .v_o(pc0_v), .u_o(pc0_u), .k_o(pc0_k), .b_o(pc0_b));
    ovl_rel_dly #(.X(XC1)) u_pc1 (.ck(ck), .v_i(c_wit),  .u_i(c_tu), .k_i(c_tk), .b_i(c_tb), .v_o(pc1_v), .u_o(pc1_u), .k_o(pc1_k), .b_o(pc1_b));
    ovl_rel_dly #(.X(XC3)) u_pc3 (.ck(ck), .v_i(c_x3s),  .u_i(c_tu), .k_i(c_tk), .b_i(c_tb), .v_o(pc3_v), .u_o(pc3_u), .k_o(pc3_k), .b_o(pc3_b));
    ovl_rel_dly #(.X(XK0)) u_pk0 (.ck(ck), .v_i(k_txs0), .u_i(k_tu), .k_i(k_tk), .b_i(k_tb), .v_o(pk0_v), .u_o(pk0_u), .k_o(pk0_k), .b_o(pk0_b));
    ovl_rel_dly #(.X(XK1)) u_pk1 (.ck(ck), .v_i(k_sk != 2'd0), .u_i(k_tu), .k_i(k_tk), .b_i(k_tb), .v_o(pk1_v), .u_o(pk1_u), .k_o(pk1_k), .b_o(pk1_b));
    ovl_rel_dly #(.X(XK2)) u_pk2 (.ck(ck), .v_i(k_embts), .u_i(k_tu), .k_i(k_tk), .b_i(k_tb), .v_o(pk2_v), .u_o(pk2_u), .k_o(pk2_k), .b_o(pk2_b));
    assign c_tv0 = pc0_v; assign c_tp0 = pc0_v ? pl(0, np[0], pc0_u, 3'd0, pc0_k, pc0_b) : '0;
    assign c_tv1 = pc1_v; assign c_tp1 = pc1_v ? pl(0, np[1], pc1_u, 3'd1, pc1_k, pc1_b) : '0;
    assign k_tv0 = pk0_v; assign k_tp0 = pk0_v ? pl(1, np[4], pk0_u, 3'd0, pk0_k, pk0_b) : '0;
    assign k_tv1 = pk1_v; assign k_tp1 = pk1_v ? pl(1, np[5], pk1_u, 3'd1, pk1_k, pk1_b) : '0;
    assign k_tv2 = pk2_v; assign k_tp2 = pk2_v ? pl(1, np[6], pk2_u, 3'd2, pk2_k, pk2_b) : '0;
    // KVN word at the x3 pins: {v, tag11 = {class 2, index}, data512}
    wire [FW-1:0] x3w = pl(0, np[3], pc3_u, 3'd3, pc3_k, pc3_b);
    always @* x3 = pc3_v ? {1'b1, 3'd2, 8'(np[3]), x3w[511:0]} : '0;
    function automatic [FW-1:0] kvn_enc(input [522:0] t);
        kvn_enc = {KID[55:51], 4'd5, KID[42:37], t[522:512], KGEN, KID[50:43], t[511:0]};
    endfunction
    // STATUS: result pulse 3 edges after each compiled STATUS slot of the compute end; golden = the kind-15 encoding
    reg [2:0] st_sr = 0; reg pend_g = 0; reg [148:0] r_g = '0; integer nres = 0;
    function automatic [FW-1:0] st_enc(input [148:0] r, input p);
        st_enc = {5'd0, 4'd15, 6'd63, EP16, 5'd0, 356'd0, r, p, LEV};
    endfunction
    always @(posedge ck) if (rst_n) begin
        if (pc0_v) begin gq[0].push_back(c_tp0); np[0] <= np[0] + 1; end
        if (pc1_v) begin gq[1].push_back(c_tp1); np[1] <= np[1] + 1; end
        if (pc3_v) begin gq[3].push_back(kvn_enc(x3[522:0])); kq.push_back(x3[522:0]); np[3] <= np[3] + 1; end
        if (pk0_v) begin gq[4].push_back(k_tp0); np[4] <= np[4] + 1; end
        if (pk1_v) begin gq[5].push_back(k_tp1); np[5] <= np[5] + 1; end
        if (pk2_v) begin gq[6].push_back(k_tp2); np[6] <= np[6] + 1; end
        // compute STATUS slot (inside the master): golden from the held result + pend
        st_sr <= {st_sr, u_c.u_core.u_end.tx_slot[2]};
        res_v <= 1'b0;
        if (u_c.u_core.u_end.tx_slot[2]) begin gq[2].push_back(st_enc(r_g, pend_g)); pend_g = 0; end
        if (st_sr[2]) begin
            nres = nres + 1;
            res_v <= 1'b1;
            res_f <= {32'(nres * 1052), 32'(nres * 77), 18'(nres * 1001), 2'(nres), 59'(nres * 4093 + 11), 4'(nres), 1'b0, 1'b1};
            r_g = {32'(nres * 1052), 32'(nres * 77), 18'(nres * 1001), 2'(nres), 59'(nres * 4093 + 11), 4'(nres), 1'b0, 1'b1};
            pend_g = 1; rq.push_back(r_g);
        end
    end

    // ---------------------------------------------------------------- sender ends: slot meta, written frame == golden
    localparam integer DW = 2 + 3 + 4 + 5 + FW;
    reg [DW-1:0] dq [0:1][$];            // [0] C->K, [1] K->C: {user, port, kind, beat, word} in write order
    integer nw [0:1];
    initial begin nw[0] = 0; nw[1] = 0; end
    task automatic send_side(input integer d, input integer base, input integer np_, input [3:0] slot, input [3:0] fire,
                             input hlt, input [1:0] tu, input [3:0] tk, input [4:0] tb, input [FW-1:0] wsel);
        integer p; reg [10:0] m; reg [FW-1:0] g; begin
            for (p = 0; p < np_; p = p + 1) if (slot[p] && !hlt) mq[base + p].push_back({tu, tk, tb});
            for (p = 0; p < np_; p = p + 1) if (fire[p]) begin
                if (mq[base + p].size() == 0) begin err($sformatf("dir %0d port %0d: fire without a slot", d, p)); return; end
                if (gq[base + p].size() == 0) begin err($sformatf("dir %0d port %0d: fire without a producer word", d, p)); return; end
                m = mq[base + p].pop_front(); g = gq[base + p].pop_front();
                if (wsel !== g) err($sformatf("dir %0d port %0d: written frame != golden (kind %0d beat %0d)", d, p, m[8:5], m[4:0]));
                dq[d].push_back({m[10:9], 3'(p), m[8:0], g}); nw[d] = nw[d] + 1;
            end
        end endtask
    always @(posedge ck) if (rst_n) begin
        send_side(0, 0, 4, u_c.u_core.u_end.tx_slot, u_c.u_core.u_end.fire, u_c.u_core.u_end.halt, u_c.u_core.u_end.tx_user,
                  u_c.u_core.u_end.tx_kind, u_c.u_core.u_end.tx_beat, u_c.u_core.u_end.wsel);
        send_side(1, 4, 3, {1'b0, u_k.u_core.u_end.tx_slot}, {1'b0, u_k.u_core.u_end.fire}, u_k.u_core.u_end.halt,
                  u_k.u_core.u_end.tx_user, u_k.u_core.u_end.tx_kind, u_k.u_core.u_end.tx_beat, u_k.u_core.u_end.wsel);
    end

    // ---------------------------------------------------------------- receiver ends: in order, bit-exact, compiled slot, user
    integer nr [0:1];
    initial begin nr[0] = 0; nr[1] = 0; end
    task automatic recv_side(input integer d, input [3:0] ev, input [3:0] slt, input [1:0] ru, input [3:0] rk, input [4:0] rb,
                             input [FW-1:0] got);
        reg [DW-1:0] e; integer p; begin
            if (ev != slt) begin err($sformatf("dir %0d: rx_event %b != compiled rx_slot %b", d, ev, slt)); return; end
            if (ev == 0) return;
            p = ev[0] ? 0 : ev[1] ? 1 : ev[2] ? 2 : 3;
            if (dq[d].size() == 0) begin err($sformatf("dir %0d: frame with no write", d)); return; end
            e = dq[d].pop_front(); nr[d] = nr[d] + 1;
            if (got !== e[FW-1:0]) err($sformatf("dir %0d port %0d: payload mismatch (kind %0d beat %0d)", d, p, rk, rb));
            if (e[DW-1 -: 2] != ru) err($sformatf("dir %0d: rx_user %0d != sender user %0d (kind %0d)", d, ru, e[DW-1 -: 2], rk));
            if (e[DW-3 -: 3] != 3'(p) || e[FW+8 -: 4] != rk || e[FW+4 -: 5] != rb)
                err($sformatf("dir %0d: compiled port/kind/beat %0d/%0d/%0d != sent %0d/%0d/%0d", d, p, rk, rb,
                    e[DW-3 -: 3], e[FW+8 -: 4], e[FW+4 -: 5]));
        end endtask
    always @(posedge ck) if (rst_n) begin
        recv_side(0, u_k.u_core.u_end.rx_event, u_k.u_core.u_end.rx_slot, u_k.u_core.u_end.rx_user, u_k.u_core.u_end.rx_kind,
                  u_k.u_core.u_end.rx_beat, u_k.u_core.u_end.rx_payload);
        recv_side(1, u_c.u_core.u_end.rx_event, u_c.u_core.u_end.rx_slot, u_c.u_core.u_end.rx_user, u_c.u_core.u_end.rx_kind,
                  u_c.u_core.u_end.rx_beat, u_c.u_core.u_end.rx_payload);
    end

    // ---------------------------------------------------------------- master pins: KV decoders, compute consumers, counts
    integer ex [0:3], tok [0:3], ex_f [0:3], tok_f [0:3], ex_0 [0:3], tok_0 [0:3];
    integer n_res = 0, n_kvn = 0, n_pin_c = 0, n_pin_k = 0;
    integer u;
    initial for (u = 0; u < 4; u = u + 1) begin ex[u] = 0; tok[u] = 0; ex_f[u] = 0; tok_f[u] = 0; ex_0[u] = 0; tok_0[u] = 0; end
    reg [148:0] re; reg [522:0] ke;
    always @(posedge ck) if (rst_n) begin
        if (s_rv) begin
            if (rq.size() == 0) err("KV engine_result_v with no result given");
            else begin
                re = rq.pop_front(); n_res = n_res + 1;
                if ({s_rcyc, s_rval, s_rtok, s_rg, s_rt, s_rc, s_rf, s_rd} !== re) err("KV engine_result fields != the compute result pins");
            end
        end
        if (kw_v) begin
            if (kq.size() == 0) err("KV kvn_word_valid with no KVN word given");
            else begin
                ke = kq.pop_front(); n_kvn = n_kvn + 1;
                if (kw_tag !== ke[522:512] || kw_data !== ke[511:0] || kw_id !== KID || kw_gen !== KGEN || !kw_slot)
                    err("KV kvn_word != the compute x3 pins");
            end
        end
        if (c_rxv0 != c_rxs0) err("compute pins: native_rx_v != native_rx_slot");
        if (c_embv != c_embs) err("compute pins: emb_rx_v != emb_rx_slot");
        if (k_rxv0 != k_rxs0) err("KV pins: att_rx_v != att_rx_slot");
        if (k_recw != (k_recv && k_rk == 4'd14)) err("KV pins: witness slot != received kind14 record");
        if (k_recv && k_rec !== k_rxp) err("KV pins: record_rx != rx_payload");
        if (c_rxv0 || c_prxv || c_embv) n_pin_c = n_pin_c + 1;
        if (k_rxv0 || k_recv) n_pin_k = n_pin_k + 1;
        if (c_rxv0 && c_rk == 4'd4) ex[c_ru] = ex[c_ru] + 1;
        if (c_embv && c_rk == 4'd7 && c_rb == 5'd31) tok[c_ru] = tok[c_ru] + 1;
        if (c_abort || k_abort) err($sformatf("epoch abort: compute cause %b KV cause %b", c_tf, h_tf));
        if (c_f || k_f) err($sformatf("master fault (calendar / stray / collision / codec): compute %0d KV %0d", c_f, k_f));
        if (c_sf || k_sf) err($sformatf("sequencer fault: compute %0d KV %0d", c_sf, k_sf));
    end
    // frame boundary: the C TX player takes list word 0 (a wrap) -> the next start is the frame's first
    integer fstart [0:2]; integer nfs = 0;
    reg [AW-1:0] a_q; reg wrap_seen = 0;
    always @(posedge ck) begin
        a_q <= a_ctx;
        if (seq_rst_n && u_cseq.u_tx.running && a_ctx == 0 && a_q != 0) wrap_seen <= 1;
        if (c_cs && (wrap_seen || nfs == 0) && u_cseq.u_tx.running && nfs < 3) begin
            fstart[nfs] = cyc; nfs = nfs + 1; wrap_seen <= 0;
            if (nfs == 1) for (u = 0; u < 4; u = u + 1) begin ex_0[u] = ex[u]; tok_0[u] = tok[u]; end
            if (nfs == 2) for (u = 0; u < 4; u = u + 1) begin ex_f[u] = ex[u] - ex_0[u]; tok_f[u] = tok[u] - tok_0[u]; end
        end
    end

    // ---------------------------------------------------------------- sequence
    integer H, tsum;
    real agg;
    initial begin
        repeat (4) @(posedge ck); por_n = 1;
        repeat (4) @(posedge ck); rst_n = 1;
        repeat (8) @(posedge ck); seq_rst_n = 1;
        wait (c_rdy && k_rdy && c_up && k_up); repeat (4) @(posedge ck);
        host_boot = 1;
        wait (u_c.u_core.ep == 8'd1 && u_k.u_core.ep == 8'd1); repeat (8) @(posedge ck);
        epoch_go = 1;
        wait (nfs >= 2 || failed); repeat (3000) @(posedge ck);
        if (!failed) begin
            if (h_vmd !== LEV[0] || h_cod !== LEV[1] || h_cb !== LEV[2] || h_cf !== LEV[3] || h_ar !== LEV[5] || !h_ea ||
                h_lu !== 2'b11 || h_tf !== 8'd0)
                err($sformatf("KV HOST services: vm%b co%b cb%b cf%b ar%b ea%b lu%b tf%h", h_vmd, h_cod, h_cb, h_cf, h_ar, h_ea, h_lu, h_tf));
            if (n_res == 0 || n_kvn == 0) err($sformatf("no STATUS result (%0d) / KVN word (%0d) decoded at the KV pins", n_res, n_kvn));
            H = fstart[1] - fstart[0];
            if (H != P_H) err($sformatf("measured frame %0d != compiled H %0d", H, P_H));
            tsum = 0;
            for (u = 0; u < 4; u = u + 1) begin
                tsum = tsum + tok_f[u];
                $display("D2DOVL_USER %0d exchanges %0d (compiled %0d) tokens %0d (compiled %0d) tok/s %.1f", u, ex_f[u],
                    u == 0 ? P_EX0 : u == 1 ? P_EX1 : u == 2 ? P_EX2 : P_EX3, tok_f[u],
                    u == 0 ? P_TOK0 : u == 1 ? P_TOK1 : u == 2 ? P_TOK2 : P_TOK3, tok_f[u] * 1.2e9 / H);
            end
            if (ex_f[0] != P_EX0 || ex_f[1] != P_EX1 || ex_f[2] != P_EX2 || ex_f[3] != P_EX3 ||
                tok_f[0] != P_TOK0 || tok_f[1] != P_TOK1 || tok_f[2] != P_TOK2 || tok_f[3] != P_TOK3)
                err("per-user exchanges / tokens in the measured frame differ from the compiled frame");
            agg = tsum * 1.2e9 / H;
            $display("D2DOVL_MEAS H %0d frames C->K %0d K->C %0d aggregate %.1f tok/s (frame start %0d)", H, nr[0], nr[1], agg, fstart[0]);
            $display("D2DOVL_REL written C->K %0d K->C %0d delivered C->K %0d K->C %0d; KV STATUS results %0d KVN words %0d; pin rx C %0d K %0d",
                nw[0], nw[1], nr[0], nr[1], n_res, n_kvn, n_pin_c, n_pin_k);
        end
        if (failed) $display("D2DOVL_FAIL OVL %0d", OVL); else $display("D2DOVL_PASS OVL %0d", OVL);
        $finish;
    end
    initial begin #(0.8333 * 12000000.0); err("timeout"); $display("D2DOVL_FAIL timeout"); $finish; end
endmodule
