`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_dsrom_1m_hop_ct: the DS-ROM S81 stage hop through the successor endpoint
// ot_dsrom_link_ct (lever "hop", 2026-10-04 recovery), per-die halves scheme.
//
// A stage hop delivers the whole +bytes= residual to BOTH dies of the
// destination package.  The residual is split at byte H = ceil(bytes/2):
// source die 0 sends half A [0, H) on its own board lanes to destination die
// 0, source die 1 sends half B [H, bytes) on its lanes to destination die 1
// (two ot_dsrom_link_ct board legs, CHANNEL_CYCLES = CH, PHY pacer
// PHY_NUM/PHY_DEN = the die's stage lanes x the net lane rate).  Each
// destination die forwards the half it receives, cut-through, over the
// in-package UCIe link to its peer (two unpaced ot_dsrom_link_ct legs,
// CHANNEL_CYCLES = CHU): board.out -> ucie.in, board.out_ready = ucie.in_ready;
// the die consumes its own half on the same handshake (fork).
//
// Each half is cut into ceil(half / FB) flits of FB bytes (last zero-padded)
// offered back to back from the first cycle after reset (in_valid held).
// Payload word w (4 bytes) of the message is a hash of (seed, w); every flit
// each die receives, from either path, is compared with its expected value
// and `last` bit (bit-exact, in order, exactly once per die per half).
//
// MODE=0: one board leg only, whole message (the token return traversal).
// Error injection (non-headline): -DERRF=N -DERRR=M on the board legs.
//
// Cycle convention (tb_dsrom_1m_hop): counter advances every posedge after
// reset; last_flit = cycle of the last delivery at either die - first input
// handshake cycle; first_flit = first board out_valid - first handshake.
//
// Compile-time: -DFB= -DCH= -DCRED= -DSEQW= -DCHU= -DCREDU= -DSEQWU=
//               -DPNUM= -DPDEN= -DMODE= -DERRF= -DERRR=
// Plusargs: +bytes= +seed= +case=
// Prints one HOPCT_SUMMARY line.
// ---------------------------------------------------------------------------
`ifndef FB
`define FB 96
`endif
`ifndef CH
`define CH 156
`endif
`ifndef CRED
`define CRED 256
`endif
`ifndef SEQW
`define SEQW 9
`endif
`ifndef CHU
`define CHU 11
`endif
`ifndef CREDU
`define CREDU 64
`endif
`ifndef SEQWU
`define SEQWU 8
`endif
`ifndef PNUM
`define PNUM 3920
`endif
`ifndef PDEN
`define PDEN 51
`endif
`ifndef MODE
`define MODE 1
`endif
`ifndef ERRF
`define ERRF 0
`endif
`ifndef ERRR
`define ERRR 0
`endif
module tb_dsrom_1m_hop_ct;
    localparam integer FB = `FB;
    localparam integer W  = FB * 8;
    localparam integer NW = W / 32;
    localparam integer ND = (`MODE == 0) ? 1 : 2;   // board legs = destination dies

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #1 clk = ~clk;

    integer BYTES, seed, H;
    integer HB [0:1];      // half byte count
    integer HW0 [0:1];     // first message word of the half
    integer HN [0:1];      // flits of the half
    reg [8*32-1:0] casename;
    reg  [15:0] chcyc = 16'd0;

    // board legs (index = source/destination die = half)
    reg          b_iv [0:1];
    reg          b_il [0:1];
    reg  [W-1:0] b_id [0:1];
    wire         b_ir [0:1];
    wire         b_ov [0:1];
    wire         b_ol [0:1];
    wire [W-1:0] b_od [0:1];
    wire         b_or [0:1];
    // ucie legs (index = the half they carry; leg h goes die h -> die 1-h)
    wire         u_ov [0:1];
    wire         u_ol [0:1];
    wire [W-1:0] u_od [0:1];
    wire [31:0]  cs [0:3];
    wire         f [0:3];
    wire [3:0]   fc [0:3];
    wire [31:0]  tx [0:3], rx [0:3], crc [0:3], nak [0:3], rep [0:3], to [0:3], retx [0:3], occ [0:3];

    genvar d;
    generate for (d = 0; d < 2; d = d + 1) begin : g_leg
        if (d < ND) begin : g_on
            ot_dsrom_link_ct #(.FLIT_BYTES(FB), .TX_STAGES(2), .CHANNEL_CYCLES(`CH), .RX_STAGES(2),
                               .CREDITS(`CRED), .SEQW(`SEQW), .LINK_CLASS(1),
                               .ERR_PERIOD_FWD(`ERRF), .ERR_PERIOD_REV(`ERRR), .ERR_OFFSET(3 + 7 * d),
                               .PHY_NUM(`PNUM), .PHY_DEN(`PDEN)) u_board (
                .clk(clk), .rst_n(rst_n), .channel_cycles(chcyc),
                .in_valid(b_iv[d]), .in_ready(b_ir[d]), .in_data(b_id[d]), .in_last(b_il[d]),
                .out_valid(b_ov[d]), .out_ready(b_or[d]), .out_data(b_od[d]), .out_last(b_ol[d]),
                .credit_stalls(cs[d]), .fault(f[d]), .fault_code(fc[d]),
                .st_flits_tx(tx[d]), .st_flits_rx_ok(rx[d]), .st_crc_err(crc[d]), .st_naks(nak[d]),
                .st_replays(rep[d]), .st_timeouts(to[d]), .st_retx_flits(retx[d]), .st_max_replay_occ(occ[d]));
        end else begin : g_off
            assign b_ir[d] = 1'b0; assign b_ov[d] = 1'b0; assign b_ol[d] = 1'b0; assign b_od[d] = {W{1'b0}};
            assign cs[d] = 0; assign f[d] = 1'b0; assign fc[d] = 4'd0; assign tx[d] = 0; assign rx[d] = 0;
            assign crc[d] = 0; assign nak[d] = 0; assign rep[d] = 0; assign to[d] = 0; assign retx[d] = 0;
            assign occ[d] = 0;
        end
        if (`MODE != 0) begin : g_u
            ot_dsrom_link_ct #(.FLIT_BYTES(FB), .TX_STAGES(2), .CHANNEL_CYCLES(`CHU), .RX_STAGES(2),
                               .CREDITS(`CREDU), .SEQW(`SEQWU), .LINK_CLASS(0), .PHY_NUM(0), .PHY_DEN(1)) u_ucie (
                .clk(clk), .rst_n(rst_n), .channel_cycles(chcyc),
                .in_valid(b_ov[d]), .in_ready(b_or[d]), .in_data(b_od[d]), .in_last(b_ol[d]),
                .out_valid(u_ov[d]), .out_ready(1'b1), .out_data(u_od[d]), .out_last(u_ol[d]),
                .credit_stalls(cs[2 + d]), .fault(f[2 + d]), .fault_code(fc[2 + d]),
                .st_flits_tx(tx[2 + d]), .st_flits_rx_ok(rx[2 + d]), .st_crc_err(crc[2 + d]), .st_naks(nak[2 + d]),
                .st_replays(rep[2 + d]), .st_timeouts(to[2 + d]), .st_retx_flits(retx[2 + d]),
                .st_max_replay_occ(occ[2 + d]));
        end else begin : g_nou
            assign b_or[d] = 1'b1;
            assign u_ov[d] = 1'b0; assign u_ol[d] = 1'b0; assign u_od[d] = {W{1'b0}};
            assign cs[2 + d] = 0; assign f[2 + d] = 1'b0; assign fc[2 + d] = 4'd0; assign tx[2 + d] = 0;
            assign rx[2 + d] = 0; assign crc[2 + d] = 0; assign nak[2 + d] = 0; assign rep[2 + d] = 0;
            assign to[2 + d] = 0; assign retx[2 + d] = 0; assign occ[2 + d] = 0;
        end
    end endgenerate

    function automatic [31:0] mix(input [31:0] x0);
        reg [31:0] x;
        begin
            x = x0;
            x = x ^ (x >> 16); x = x * 32'h7feb352d;
            x = x ^ (x >> 15); x = x * 32'h846ca68b;
            x = x ^ (x >> 16);
            mix = x;
        end
    endfunction
    // flit i of half h: message words HW0[h] + i*NW + j, zero beyond the half (and beyond the message)
    function automatic [W-1:0] gen_data(input integer h, input integer i);
        integer j, w, k;
        begin
            for (j = 0; j < NW; j = j + 1) begin
                k = i * NW + j;                                  // word within the half
                w = HW0[h] + k;
                gen_data[j*32 +: 32] = (4 * k < HB[h] && 4 * w < BYTES) ? mix(w ^ mix(seed)) : 32'd0;
            end
        end
    endfunction

    integer cyc, first_in, first_ov;
    integer sent [0:1];
    integer rc [0:1][0:1];      // rc[die][half] flits received
    integer lastc [0:1][0:1];   // cycle of the last flit of half at die
    integer mism, extra, done_cyc;
    reg finished;
    integer h, dd;

    initial begin
        if (!$value$plusargs("bytes=%d", BYTES)) BYTES = 40976;
        if (!$value$plusargs("seed=%d", seed)) seed = 81;
        if (!$value$plusargs("case=%s", casename)) casename = "unnamed";
        if (`MODE == 0) begin
            HB[0] = BYTES; HB[1] = 0;
        end else begin
            HB[0] = (BYTES + 1) / 2; HB[1] = BYTES - HB[0];
        end
        if (HB[0] % 4 != 0) $fatal(1, "half A must be whole words");
        HW0[0] = 0; HW0[1] = HB[0] / 4;
        HN[0] = (HB[0] + FB - 1) / FB; HN[1] = (HB[1] + FB - 1) / FB;
        for (h = 0; h < 2; h = h + 1) begin
            b_iv[h] = 0; b_il[h] = 0; b_id[h] = 0; sent[h] = 0;
            for (dd = 0; dd < 2; dd = dd + 1) begin rc[dd][h] = 0; lastc[dd][h] = -1; end
        end
        cyc = 0; mism = 0; extra = 0; first_in = -1; first_ov = -1; done_cyc = -1; finished = 0;
        repeat (5) @(posedge clk);
        rst_n = 1'b1;
    end

    task check(input integer die, input integer half, input [W-1:0] data, input last);
        begin
            if (rc[die][half] >= HN[half]) extra = extra + 1;
            else begin
                if (data !== gen_data(half, rc[die][half]) || last !== (rc[die][half] == HN[half] - 1)) begin
                    if (mism < 5) $display("MISMATCH case=%0s die=%0d half=%0d idx=%0d", casename, die, half, rc[die][half]);
                    mism = mism + 1;
                end
                lastc[die][half] = cyc;
            end
            rc[die][half] = rc[die][half] + 1;
        end
    endtask

    integer need_done, k;
    always @(posedge clk) if (rst_n && !finished) begin
        cyc = cyc + 1;
        for (k = 0; k < ND; k = k + 1) begin
            // source die k: half k, back to back
            if (b_iv[k] && b_ir[k]) begin
                if (first_in < 0) first_in = cyc;
                sent[k] = sent[k] + 1;
            end
            if (!(b_iv[k] && !b_ir[k])) begin
                if (sent[k] < HN[k]) begin
                    b_iv[k] <= 1'b1; b_id[k] <= gen_data(k, sent[k]); b_il[k] <= (sent[k] == HN[k] - 1);
                end else begin
                    b_iv[k] <= 1'b0; b_il[k] <= 1'b0;
                end
            end
            // destination die k: own half from the board leg (fork with the UCIe forward)
            if (b_ov[k] && first_ov < 0) first_ov = cyc;
            if (b_ov[k] && b_or[k]) check(k, k, b_od[k], b_ol[k]);
            // destination die 1-k: half k over UCIe
            if (`MODE != 0 && u_ov[k]) check(1 - k, k, u_od[k], u_ol[k]);
        end
        need_done = 1;
        for (dd = 0; dd < ND; dd = dd + 1)
            for (h = 0; h < ND; h = h + 1)
                if (rc[dd][h] < HN[h]) need_done = 0;
        if (need_done && done_cyc < 0) done_cyc = cyc;
        if ((done_cyc >= 0 && cyc - done_cyc > 4 * (`CH + `CHU) + 600) || cyc > 400000) begin
            finished = 1;
            report();
            $finish;
        end
    end

    task report;
        reg pass;
        integer last_all, last_own, last_peer, nd2;
        begin
            pass = (mism == 0) && (extra == 0);
            last_all = -1; last_own = -1; last_peer = -1;
            for (dd = 0; dd < ND; dd = dd + 1)
                for (h = 0; h < ND; h = h + 1) begin
                    if (rc[dd][h] != HN[h]) pass = 0;
                    if (lastc[dd][h] > last_all) last_all = lastc[dd][h];
                    if (dd == h && lastc[dd][h] > last_own) last_own = lastc[dd][h];
                    if (dd != h && lastc[dd][h] > last_peer) last_peer = lastc[dd][h];
                end
            for (k = 0; k < ND; k = k + 1) if (sent[k] != HN[k]) pass = 0;
            for (k = 0; k < 4; k = k + 1) if (f[k]) pass = 0;
            $display("HOPCT_SUMMARY case=%0s result=%0s mode=%0d bytes=%0d half_a=%0d half_b=%0d flits_a=%0d flits_b=%0d fb=%0d ch=%0d chu=%0d credits=%0d seqw=%0d credits_u=%0d seqw_u=%0d pnum=%0d pden=%0d errf=%0d errr=%0d sent_a=%0d sent_b=%0d mism=%0d extra=%0d faults=%0d%0d%0d%0d first_in=%0d first_flit=%0d last_flit=%0d own_last_flit=%0d peer_last_flit=%0d credit_stalls=%0d,%0d,%0d,%0d retx=%0d,%0d,%0d,%0d crc=%0d,%0d,%0d,%0d replays=%0d,%0d timeouts=%0d,%0d max_replay_occ=%0d,%0d,%0d,%0d tx=%0d,%0d seed=%0d",
                casename, pass ? "PASS" : "FAIL", `MODE, BYTES, HB[0], HB[1], HN[0], HN[1], FB, `CH, `CHU, `CRED, `SEQW,
                `CREDU, `SEQWU, `PNUM, `PDEN, `ERRF, `ERRR, sent[0], sent[1], mism, extra, f[0], f[1], f[2], f[3],
                first_in, first_ov - first_in, last_all - first_in, last_own - first_in,
                (last_peer < 0) ? -1 : last_peer - first_in, cs[0], cs[1], cs[2], cs[3],
                retx[0], retx[1], retx[2], retx[3], crc[0], crc[1], crc[2], crc[3], rep[0], rep[1], to[0], to[1],
                occ[0], occ[1], occ[2], occ[3], tx[0], tx[1], seed);
        end
    endtask
endmodule
