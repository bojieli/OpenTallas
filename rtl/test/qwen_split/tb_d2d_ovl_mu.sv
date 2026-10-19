`timescale 1ns/1ps
// =====================================================================================================================
// MU-D2D-OVL 2026-10-19: 4-user compute <-> KV D2D link co-sim with OVERLAPPING request / response segments.
// On-chip RTL: both link ends ot_qwen_d2d_static_end (OVL = 1, real calendars, slot SRAM links, CRC, slot / epoch /
//   ownership checks, the per-user tags) at the GEN TXDP of the MU release seam (compute C [8,3,1,10], KV K [21,4,3,3]),
//   and both sequencers ot_qwen_d2d_ovl_seq (init image load, anchor, the two compiled start-list players a die) on
//   the compiler's frame (tools/qwen_static_schedule/mu_d2d_ovl.py: the 4-user F16 frame of record, request / response
//   / token-head segments placed in free link slots).
// Modelled (declared): the UCIe PHY pair (ot_qkvd_ucie_x64_phy_model, LAT = FDI 5 + the 2 PR pin flops of the masters),
//   the producers (every TX port answers its slot exactly TXD_p edges later: the seam + codec latency the TXDP
//   carries) and the consumers (scoreboard).  The die masters' pin flops are folded into TXD / PHY (+1 on cal_start
//   and the user pins on both dies, symmetric).  Admission (ADM) is the unchanged ot_qwen_d2d_cal_seq path: ADM = 0.
// Checks (any one -> D2DOVL_FAIL): no end / sequencer fault or epoch abort for one whole frame + wrap; every frame
//   captured at a sender is delivered in order at the receiver with its payload bit-exact, on the port, kind and beat
//   the RECEIVER's compiled calendar expects, tagged with the sender's user (rx_user == tx_user, so a request and a
//   response of two users may overlap but never mix); per frame and user: the exchanges (STATUS kind 4 at compute)
//   and tokens (last embedding word, kind 7 beat 31 at compute) equal the compiler's counts.
// Measured: H = edges between two frame starts (first C TX list start of a frame), aggregate tok/s = tokens x 1.2 GHz / H.
// Mutants (compiler, mu_d2d_ovl.py --mut): collide (a response start inside the previous response: start while running),
//   slot (one KV TX start one edge late), user (one KV RX start tagged with another user); OVL = 0 = the as-built
//   one-playhead end (RX calendar started with the TX one) on the same frame.
// =====================================================================================================================
module tb_d2d_ovl_mu;
    parameter integer OVL = 1;
    parameter CALDIR = "cal";
    `include "ovl_params.svh"
    `include "ovl_img.svh"
    localparam integer FW = 548, PW = 583, AW = 11;
    reg ck = 0; always #0.4167 ck = ~ck;
    reg rst_n = 0;
    integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;
    reg failed = 0;
    task automatic err(input string s); begin if (!failed) $display("D2DOVL_ERR cyc %0d: %s", cyc, s); failed = 1; end endtask

    // ---------------------------------------------------------------- list ROMs (synchronous read)
    reg [31:0] rom_ctx [0:(1<<AW)-1], rom_crx [0:(1<<AW)-1], rom_ktx [0:(1<<AW)-1], rom_krx [0:(1<<AW)-1];
    initial begin
        $readmemh({CALDIR, "/list_C_tx.memh"}, rom_ctx); $readmemh({CALDIR, "/list_C_rx.memh"}, rom_crx);
        $readmemh({CALDIR, "/list_K_tx.memh"}, rom_ktx); $readmemh({CALDIR, "/list_K_rx.memh"}, rom_krx);
    end
    wire [AW-1:0] a_ctx, a_crx, a_ktx, a_krx; reg [31:0] q_ctx, q_crx, q_ktx, q_krx;
    always @(posedge ck) begin q_ctx <= rom_ctx[a_ctx]; q_crx <= rom_crx[a_crx]; q_ktx <= rom_ktx[a_ktx]; q_krx <= rom_krx[a_krx]; end

    // ---------------------------------------------------------------- sequencers
    reg epoch_go = 0, eb = 0;
    wire c_abort, k_abort, c_ef, k_ef, c_sf, k_sf;
    wire c_ctw, c_crw, k_ctw, k_crw; wire [5:0] c_ca, k_ca; wire [31:0] c_cd, k_cd;
    wire c_cs, c_cg, c_crs, c_crg, k_cs, k_cg, k_crs, k_crg; wire [1:0] c_ut, c_ur, k_ut, k_ur;
    wire c_rdy, k_rdy;
    ot_qwen_d2d_ovl_seq #(.AW(AW), .TX_IMG(IMG_C_TX), .RX_IMG(IMG_C_RX), .TX_SEG1(SEG1_C_TX), .RX_SEG1(SEG1_C_RX),
        .FIRST_OFS(200)) u_cseq (.ck(ck), .rst_n(rst_n), .reload(1'b0), .epoch_go(epoch_go), .halt(c_abort | c_ef),
        .cfg_tx_we(c_ctw), .cfg_rx_we(c_crw), .cfg_addr(c_ca), .cfg_data(c_cd), .cal_start(c_cs), .cal_seg(c_cg),
        .cal_start_rx(c_crs), .cal_seg_rx(c_crg), .cal_user_tx(c_ut), .cal_user_rx(c_ur),
        .tx_rom_addr(a_ctx), .tx_rom_q(q_ctx), .rx_rom_addr(a_crx), .rx_rom_q(q_crx),
        .cal_ready(c_rdy), .adm_done(), .running(), .fault(c_sf));
    ot_qwen_d2d_ovl_seq #(.AW(AW), .TX_IMG(IMG_K_TX), .RX_IMG(IMG_K_RX), .TX_SEG1(SEG1_K_TX), .RX_SEG1(SEG1_K_RX),
        .FIRST_OFS(200)) u_kseq (.ck(ck), .rst_n(rst_n), .reload(1'b0), .epoch_go(epoch_go), .halt(k_abort | k_ef),
        .cfg_tx_we(k_ctw), .cfg_rx_we(k_crw), .cfg_addr(k_ca), .cfg_data(k_cd), .cal_start(k_cs), .cal_seg(k_cg),
        .cal_start_rx(k_crs), .cal_seg_rx(k_crg), .cal_user_tx(k_ut), .cal_user_rx(k_ur),
        .tx_rom_addr(a_ktx), .tx_rom_q(q_ktx), .rx_rom_addr(a_krx), .rx_rom_q(q_krx),
        .cal_ready(k_rdy), .adm_done(), .running(), .fault(k_sf));

    // ---------------------------------------------------------------- PHY pair
    wire c_ptx_v, k_ptx_v, c_prx_v, k_prx_v, c_up, k_up, c_lv, k_lv; wire [PW-1:0] c_ptx, k_ptx, c_prx, k_prx, c_lf, k_lf;
    ot_qkvd_ucie_x64_phy_model #(.LAT(P_PHY), .FW(PW)) u_cphy (.clk(ck), .rst_n(rst_n), .tx_up(c_up),
        .tx_v(c_ptx_v), .tx_flit(c_ptx), .rx_v(c_prx_v), .rx_flit(c_prx), .link_v(c_lv), .link_flit(c_lf), .far_v(k_lv), .far_flit(k_lf));
    ot_qkvd_ucie_x64_phy_model #(.LAT(P_PHY), .FW(PW)) u_kphy (.clk(ck), .rst_n(rst_n), .tx_up(k_up),
        .tx_v(k_ptx_v), .tx_flit(k_ptx), .rx_v(k_prx_v), .rx_flit(k_prx), .link_v(k_lv), .link_flit(k_lf), .far_v(c_lv), .far_flit(c_lf));

    // ---------------------------------------------------------------- link ends
    wire [3:0] c_txs, k_txs, c_rxe, k_rxe, c_rxs, k_rxs; wire [3:0] c_tk, k_tk, c_rk, k_rk; wire [4:0] c_tb, k_tb, c_rb, k_rb;
    wire [1:0] c_tu, k_tu, c_ru, k_ru; wire [FW-1:0] c_rxp, k_rxp; wire [3:0] c_tv, k_tv; wire [4*FW-1:0] c_tp, k_tp;
    wire [7:0] c_fc, k_fc;
    ot_qwen_d2d_static_end #(.NT(4), .NR(4), .TXD(P_TXD_C), .OVL(OVL)) u_cend (.ck({5{ck}}), .rst_n(rst_n),
        .cfg_tx_we(c_ctw), .cfg_rx_we(c_crw), .cfg_addr(c_ca), .cfg_data(c_cd), .epoch_begin(eb), .epoch(8'd1),
        .cal_start(c_cs), .cal_seg(c_cg), .cal_start_rx(c_crs), .cal_seg_rx(c_crg), .cal_user_tx(c_ut), .cal_user_rx(c_ur),
        .tx_user(c_tu), .rx_user(c_ru), .tx_slot(c_txs), .tx_kind(c_tk), .tx_beat(c_tb), .tx_valid(c_tv), .tx_payload(c_tp),
        .rx_event(c_rxe), .rx_slot(c_rxs), .rx_kind(c_rk), .rx_beat(c_rb), .rx_payload(c_rxp),
        .p_tx_up(c_up), .p_tx_v(c_ptx_v), .p_tx_flit(c_ptx), .p_rx_v(c_prx_v), .p_rx_flit(c_prx),
        .epoch_abort(c_abort), .fault_cause(c_fc), .end_fault(c_ef), .cal_running());
    ot_qwen_d2d_static_end #(.NT(4), .NR(4), .TXD(P_TXD_K), .OVL(OVL)) u_kend (.ck({5{ck}}), .rst_n(rst_n),
        .cfg_tx_we(k_ctw), .cfg_rx_we(k_crw), .cfg_addr(k_ca), .cfg_data(k_cd), .epoch_begin(eb), .epoch(8'd1),
        .cal_start(k_cs), .cal_seg(k_cg), .cal_start_rx(k_crs), .cal_seg_rx(k_crg), .cal_user_tx(k_ut), .cal_user_rx(k_ur),
        .tx_user(k_tu), .rx_user(k_ru), .tx_slot(k_txs), .tx_kind(k_tk), .tx_beat(k_tb), .tx_valid(k_tv), .tx_payload(k_tp),
        .rx_event(k_rxe), .rx_slot(k_rxs), .rx_kind(k_rk), .rx_beat(k_rb), .rx_payload(k_rxp),
        .p_tx_up(k_up), .p_tx_v(k_ptx_v), .p_tx_flit(k_ptx), .p_rx_v(k_prx_v), .p_rx_flit(k_prx),
        .epoch_abort(k_abort), .fault_cause(k_fc), .end_fault(k_ef), .cal_running());

    // ---------------------------------------------------------------- producers: TXD_p edges after the slot
    function automatic [FW-1:0] pl(input integer d, input integer n, input [1:0] u, input [2:0] p, input [3:0] k, input [4:0] b);
        integer j; reg [31:0] x; begin
            pl = '0; x = 32'(n) * 32'h9E3779B1 ^ 32'(d) * 32'h85EBCA6B;
            for (j = 0; j < 16; j = j + 1) begin x = x * 32'h01000193 + 32'h3F800007; pl[32*j +: 32] = x; end
            pl[547:512] = {2'(d), u, p, k, b, 18'(n)};
        end endfunction
    reg [FW-1:0] sb_c2k [$], sb_k2c [$];
    integer n_c = 0, n_k = 0;
    genvar gp;
    generate for (gp = 0; gp < 4; gp = gp + 1) begin : g_prod
        localparam integer DC = P_TXD_C[8*gp +: 8], DK = P_TXD_K[8*gp +: 8];
        reg [DC-1:0] cv; reg [1:0] cu [0:DC-1]; reg [3:0] ckd [0:DC-1]; reg [4:0] cb [0:DC-1];
        reg [DK-1:0] kv; reg [1:0] ku [0:DK-1]; reg [3:0] kkd [0:DK-1]; reg [4:0] kb [0:DK-1];
        integer i;
        always @(posedge ck) begin
            cv <= {cv, c_txs[gp]}; cu[0] <= c_tu; ckd[0] <= c_tk; cb[0] <= c_tb;
            for (i = 1; i < DC; i = i + 1) begin cu[i] <= cu[i-1]; ckd[i] <= ckd[i-1]; cb[i] <= cb[i-1]; end
            kv <= {kv, k_txs[gp]}; ku[0] <= k_tu; kkd[0] <= k_tk; kb[0] <= k_tb;
            for (i = 1; i < DK; i = i + 1) begin ku[i] <= ku[i-1]; kkd[i] <= kkd[i-1]; kb[i] <= kb[i-1]; end
        end
        // stage DC-1 of the slot pipeline = the end's fire edge (the end shifts tx_slot into a D-deep register)
        assign c_tv[gp] = cv[DC-1];
        assign k_tv[gp] = kv[DK-1];
        assign c_tp[gp*FW +: FW] = cv[DC-1] ? pl(0, n_c, cu[DC-1], 3'(gp), ckd[DC-1], cb[DC-1]) : '0;
        assign k_tp[gp*FW +: FW] = kv[DK-1] ? pl(1, n_k, ku[DK-1], 3'(gp), kkd[DK-1], kb[DK-1]) : '0;
    end endgenerate
    always @(posedge ck) if (rst_n) begin
        if (|c_tv) begin sb_c2k.push_back(c_tp[0 +: FW] | c_tp[FW +: FW] | c_tp[2*FW +: FW] | c_tp[3*FW +: FW]); n_c <= n_c + 1; end
        if (|k_tv) begin sb_k2c.push_back(k_tp[0 +: FW] | k_tp[FW +: FW] | k_tp[2*FW +: FW] | k_tp[3*FW +: FW]); n_k <= n_k + 1; end
    end

    // ---------------------------------------------------------------- consumers (scoreboard + compiled expectation)
    integer rx_c = 0, rx_k = 0;
    integer ex [0:3], tok [0:3], ex_f [0:3], tok_f [0:3], ex_0 [0:3], tok_0 [0:3];
    integer fstart [0:2]; integer nfs = 0;
    reg in_frame = 0;
    task automatic check_rx(input integer d, input [3:0] ev, input [3:0] slt, input [1:0] ru, input [3:0] rk, input [4:0] rb,
                            input [FW-1:0] got);
        reg [FW-1:0] e; integer p; begin
            p = ev[0] ? 0 : ev[1] ? 1 : ev[2] ? 2 : 3;
            if (ev != slt) err($sformatf("dir %0d: rx_event %b != compiled rx_slot %b", d, ev, slt));
            if (d == 0) begin if (sb_c2k.size() == 0) begin err("C->K frame with no capture"); return; end e = sb_c2k.pop_front(); end
            else begin if (sb_k2c.size() == 0) begin err("K->C frame with no capture"); return; end e = sb_k2c.pop_front(); end
            if (got !== e) err($sformatf("dir %0d: payload mismatch (seq %0d / got seq %0d)", d, e[17+512:512], got[17+512:512]));
            if (e[543:542] != ru) err($sformatf("dir %0d: rx_user %0d != sender user %0d (kind %0d)", d, ru, e[543:542], rk));
            if (e[541:539] != 3'(p) || e[538:535] != rk || e[534:530] != rb)
                err($sformatf("dir %0d: compiled port/kind/beat %0d/%0d/%0d != sent %0d/%0d/%0d", d, p, rk, rb, e[541:539], e[538:535], e[534:530]));
        end endtask
    integer u;
    initial for (u = 0; u < 4; u = u + 1) begin ex[u] = 0; tok[u] = 0; ex_f[u] = 0; tok_f[u] = 0; ex_0[u] = 0; tok_0[u] = 0; end
    always @(posedge ck) if (rst_n) begin
        if (|k_rxe) begin check_rx(0, k_rxe, k_rxs, k_ru, k_rk, k_rb, k_rxp); rx_k <= rx_k + 1; end
        else if (|k_rxs) err("KV: compiled RX slot without a frame");
        if (|c_rxe) begin
            check_rx(1, c_rxe, c_rxs, c_ru, c_rk, c_rb, c_rxp); rx_c <= rx_c + 1;
            if (c_rxe[0] && c_rk == 4'd4) ex[c_ru] = ex[c_ru] + 1;
            if (c_rxe[2] && c_rk == 4'd7 && c_rb == 5'd31) tok[c_ru] = tok[c_ru] + 1;
        end else if (|c_rxs) err("compute: compiled RX slot without a frame");
        if (c_abort || k_abort) err($sformatf("epoch abort: compute cause %b KV cause %b", c_fc, k_fc));
        if (c_ef || k_ef) err($sformatf("end fault (calendar / stray / collision): compute %0d KV %0d", c_ef, k_ef));
        if (c_sf || k_sf) err($sformatf("sequencer fault: compute %0d KV %0d", c_sf, k_sf));
    end
    // frame boundary: the C TX player takes list word 0 (a wrap) -> the next start is the frame's first
    reg [AW-1:0] a_q; reg wrap_seen = 0;
    always @(posedge ck) begin
        a_q <= a_ctx;
        if (rst_n && u_cseq.u_tx.running && a_ctx == 0 && a_q != 0) wrap_seen <= 1;
        if (c_cs && (wrap_seen || nfs == 0) && u_cseq.u_tx.running && nfs < 3) begin
            fstart[nfs] = cyc; nfs = nfs + 1; wrap_seen <= 0;
            if (nfs == 1) for (u = 0; u < 4; u = u + 1) begin ex_0[u] = ex[u]; tok_0[u] = tok[u]; end
            if (nfs == 2) for (u = 0; u < 4; u = u + 1) begin ex_f[u] = ex[u] - ex_0[u]; tok_f[u] = tok[u] - tok_0[u]; end
        end
    end

    // ---------------------------------------------------------------- sequence
    integer H, tsum, i0;
    real agg;
    initial begin
        repeat (4) @(posedge ck); rst_n = 1;
        wait (c_rdy && k_rdy && c_up && k_up); repeat (2) @(posedge ck);
        eb = 1; @(posedge ck); eb = 0; repeat (4) @(posedge ck);
        epoch_go = 1;
        // one frame (first frame start -> second) + 3,000 edges
        wait (nfs >= 2 || failed); repeat (3000) @(posedge ck);
        // counts over the measured frame [fstart0, fstart1): snapshot at fstart1 minus nothing before fstart0
        if (!failed) begin
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
            $display("D2DOVL_MEAS H %0d frames C->K %0d K->C %0d aggregate %.1f tok/s (frame start %0d)", H, rx_k, rx_c, agg, fstart[0]);
        end
        if (failed) $display("D2DOVL_FAIL OVL %0d", OVL); else $display("D2DOVL_PASS OVL %0d", OVL);
        $finish;
    end
    initial begin #(0.8333 * 12000000.0); err("timeout"); $display("D2DOVL_FAIL timeout"); $finish; end
endmodule
