`timescale 1ns/1ps
// QW-D2D SAFE5 10-19: lockstep equivalence of the structurally safe compute D2D master qfd_d2d_static_ovl_sf against
// the MU OVL master qfd_d2d_static_ovl (same TXDP, PR 1).  Identical stimulus every cycle; every output of both is
// compared on every cycle after reset release.  Stimulus: programmed TX / RX calendars (both segments, bursts,
// last flags), compiled starts with users, producers answering their slots at the compiled capture edges (native59,
// program record, KVN; STATUS is internal), result pulses, PHY loopback with injected CRC corruption and tx_up drops,
// rare stray producers and starts-while-running (faults), forwarded epoch strobes (abort / restart).
// Pass: "SFEQ_PASS ..." with coverage counters; any mismatch: "SFEQ_FAIL cycle=..." and the differing outputs.
// SFMUT (negative controls): 1 = one bypass-select copy of bank 0 takes the wrong age; 2 = the TX-start one-hot base
// of the TX calendar is off by one slot (oh_start), see ot_qwen_d2d_safe5.sv.
module tb_qfd_d2d_sf6u_equiv;
    parameter integer SFMUT = 0;
    parameter integer NCYC = 200000;
    parameter [31:0] TXDP = 32'h0a010308;
    reg ck = 0; always #1 ck = ~ck;
    reg por_n = 0, rst_n = 0;
    reg cfg_tx_we = 0, cfg_rx_we = 0; reg [5:0] cfg_addr = 0; reg [31:0] cfg_data = 0;
    reg cal_start = 0, cal_seg = 0, cal_start_rx = 0, cal_seg_rx = 0; reg [1:0] cal_user_tx = 0, cal_user_rx = 0;
    reg fwd_epoch = 0, fwd_link_rst_n = 1;
    reg native_tx_v = 0; reg [547:0] native_tx_payload = 0;
    reg prog_tx_observed_v = 0; reg [547:0] prog_tx_record = 0;
    reg [523:0] x3 = 0; reg [58:0] x3_identity = 0; reg [1:0] x3_generation = 0;
    reg [15:0] status_epoch16 = 0;
    reg vm_drained = 0, collective_drained = 0, collective_busy = 0, crom_fault = 0, execution_active = 0, admit_ready = 0;
    reg result_v = 0, result_done = 0, result_fault = 0; reg [3:0] result_cause = 0; reg [58:0] result_tag = 0;
    reg [1:0] result_gen = 0; reg [17:0] result_token = 0; reg [31:0] result_value = 0, result_cycles = 0;
    reg fdi_tx_up = 1, fdi_rx_v = 0; reg [582:0] fdi_rx_flit = 0;

    `define OVL_PORTS(P) \
        .ck(ck), .por_n(por_n), .rst_n(rst_n), .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr), \
        .cfg_data(cfg_data), .cal_start(cal_start), .cal_seg(cal_seg), .cal_start_rx(cal_start_rx), .cal_seg_rx(cal_seg_rx), \
        .cal_user_tx(cal_user_tx), .cal_user_rx(cal_user_rx), .tx_user(P``_tx_user), .rx_user(P``_rx_user), \
        .fwd_epoch(fwd_epoch), .fwd_link_rst_n(fwd_link_rst_n), .native_tx_slot(P``_native_tx_slot), \
        .native_tx_slot_kind(P``_native_tx_slot_kind), .native_tx_slot_beat(P``_native_tx_slot_beat), \
        .native_tx_v(native_tx_v), .native_tx_payload(native_tx_payload), .rx_payload(P``_rx_payload), \
        .native_rx_v(P``_native_rx_v), .native_rx_slot(P``_native_rx_slot), .native_rx_slot_kind(P``_native_rx_slot_kind), \
        .native_rx_slot_beat(P``_native_rx_slot_beat), .prog_witness_slot(P``_prog_witness_slot), \
        .prog_auth_slot(P``_prog_auth_slot), .prog_context_slot(P``_prog_context_slot), \
        .prog_tx_observed_v(prog_tx_observed_v), .prog_tx_record(prog_tx_record), .prog_rx_v(P``_prog_rx_v), \
        .emb_rx_v(P``_emb_rx_v), .emb_rx_slot(P``_emb_rx_slot), .kv_x3_slot(P``_kv_x3_slot), .x3(x3), \
        .x3_identity(x3_identity), .x3_generation(x3_generation), .status_epoch16(status_epoch16), \
        .vm_drained(vm_drained), .collective_drained(collective_drained), .collective_busy(collective_busy), \
        .crom_fault(crom_fault), .execution_active(execution_active), .admit_ready(admit_ready), .result_v(result_v), \
        .result_done(result_done), .result_fault(result_fault), .result_cause(result_cause), .result_tag(result_tag), \
        .result_gen(result_gen), .result_token(result_token), .result_value(result_value), .result_cycles(result_cycles), \
        .fdi_tx_up(fdi_tx_up), .fdi_tx_v(P``_fdi_tx_v), .fdi_tx_flit(P``_fdi_tx_flit), .fdi_rx_v(fdi_rx_v), \
        .fdi_rx_flit(fdi_rx_flit), .phy_rst_n(P``_phy_rst_n), .epoch_abort(P``_epoch_abort), \
        .transport_fault(P``_transport_fault), .fault(P``_fault)
    `define OVL_WIRES(P) \
        wire [1:0] P``_tx_user, P``_rx_user; wire P``_native_tx_slot; wire [3:0] P``_native_tx_slot_kind; \
        wire [4:0] P``_native_tx_slot_beat; wire [547:0] P``_rx_payload; wire P``_native_rx_v, P``_native_rx_slot; \
        wire [3:0] P``_native_rx_slot_kind; wire [4:0] P``_native_rx_slot_beat; \
        wire P``_prog_witness_slot, P``_prog_auth_slot, P``_prog_context_slot, P``_prog_rx_v, P``_emb_rx_v, P``_emb_rx_slot; \
        wire P``_kv_x3_slot, P``_fdi_tx_v; wire [582:0] P``_fdi_tx_flit; wire P``_phy_rst_n, P``_epoch_abort; \
        wire [7:0] P``_transport_fault; wire P``_fault; \
        wire [1174:0] P``_o = {P``_rx_payload, P``_tx_user, P``_rx_user, P``_native_tx_slot, P``_native_tx_slot_kind, P``_native_tx_slot_beat, \
            P``_native_rx_v, P``_native_rx_slot, P``_native_rx_slot_kind, P``_native_rx_slot_beat, P``_prog_witness_slot, \
            P``_prog_auth_slot, P``_prog_context_slot, P``_prog_rx_v, P``_emb_rx_v, P``_emb_rx_slot, P``_kv_x3_slot, \
            P``_fdi_tx_v, P``_fdi_tx_flit, P``_phy_rst_n, P``_epoch_abort, P``_transport_fault, P``_fault};
    `OVL_WIRES(a)
    `OVL_WIRES(b)
    qfd_d2d_static_ovl    #(.PR(1), .TXDP(TXDP))                 u_a (`OVL_PORTS(a));
    qfd_d2d_static_ovl_sf6u #(.PR(1), .TXDP(TXDP), .SFMUT(SFMUT)) u_b (`OVL_PORTS(b));

    // producers answer their (pin-registered) slots at the compiled capture edge: native59 TXD0 - 2, program TXD1 - 2,
    // KVN TXD3 - 3 (pin flop + KVN codec register)
    localparam integer D0 = TXDP[7:0] - 2, D1 = TXDP[15:8] - 2, D3 = TXDP[31:24] - 3;
    reg [63:0] h0 = 0, h1 = 0, h3 = 0;
    reg [582:0] lb [0:7]; reg [7:0] lbv = 0;
    integer nrst = 0, cyc = 0, k, kk, nslot = 0, nftx = 0, nrx = 0, nab = 0, neb = 0, nres = 0, nhit = 0, nmis = 0, nseg1 = 0;
    reg stray = 0, chaos = 0;
    // ---- epochs of EP cycles: n = 0 calibration (TX only, measures the loopback latency LB), odd n = random ports TX
    // only (one producer per epoch, rotating over all four; RX idle), even n = aligned loopback (TX port 0, RX calendar = same timing started LB
    // later, so frames arrive exactly when expected: checked RX payload path).  Calendars are re-programmed while
    // stopped at the end of every epoch, then the forwarded epoch strobe begins the next one.
    localparam integer EP = 2000, PROG0 = 1780, STROBE = 1990, START0 = 60, LAST_START = 1600;
    reg [31:0] img [0:1][0:32];
    integer ep_n = 0, ep_c = 0, lb_lat = 0, t_ev = -1, t_rx = -1, n0, n1, base, e, rx, dt, rep, beat, port, kind;
    integer pm = 0;
    task automatic make_images(input integer mode);
        begin
            pm = (pm + 1) % 4;
            n0 = 6 + $urandom % 8; base = n0 + 1 + $urandom % 4; n1 = 3 + $urandom % 6;
            if (base + n1 > 32) n1 = 32 - base;
            for (e = 0; e < 32; e = e + 1) begin
                dt = 1 + $urandom % 5; rep = ($urandom % 3 == 0) ? $urandom % 4 : 0; beat = $urandom % (32 - rep);
                port = (mode == 1) ? pm : 0; kind = (port == 2) ? 15 : $urandom % 15;   // one producer per random epoch
                if (mode == 1 && $urandom % 300 == 0) dt = 0;          // rare illegal entry (calendar fault)
                img[0][e] = {dt[13:0], (e == n0 - 1) || (e == base + n1 - 1), port[2:0], kind[3:0], beat[4:0], rep[4:0]};
                img[1][e] = {img[0][e][31:17], 3'($urandom % 4), 4'($urandom % 16), img[0][e][9:0]};
            end
            img[0][32] = {27'd0, base[4:0]}; img[1][32] = img[0][32];
        end
    endtask
    reg mode_al = 0;                     // aligned-loopback epoch
    reg [1:0] seg_hold = 0;
    initial begin
        repeat (6) @(negedge ck); por_n = 1; repeat (4) @(negedge ck); rst_n = 1;
    end
    always @(posedge ck) cyc <= cyc + 1;
    always @(negedge ck) if (cyc > 12) begin
        ep_n = (cyc - 100) / EP; ep_c = (cyc - 100) % EP;
        if (cyc < 100) begin ep_n = -1; ep_c = 0; end
        h0 <= {h0[62:0], a_native_tx_slot}; h1 <= {h1[62:0], a_prog_witness_slot}; h3 <= {h3[62:0], a_kv_x3_slot};
        stray = ($urandom % 8000 == 0) && (ep_n % 2 == 1); chaos = ($urandom % 40000 == 0);
        native_tx_v = h0[D0 - 1] ^ stray; prog_tx_observed_v = h1[D1 - 1] | chaos;
        for (k = 0; k < 18; k = k + 1) begin
            native_tx_payload[32*k +: 32] = $urandom; prog_tx_record[32*k +: 32] = $urandom; x3[32*k +: 32] = $urandom;
        end
        x3[523] = h3[D3 - 1]; x3[522:520] = (chaos) ? 3'd5 : 3'd2;
        x3_identity = {3'd0, 13'($urandom), 43'($urandom)}; x3_generation = 2'($urandom);
        status_epoch16 = 16'($urandom);
        {vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready} = 6'($urandom);
        result_v = ($urandom % 70 == 0);
        {result_done, result_fault, result_cause} = 6'($urandom);
        result_tag = {27'($urandom), 32'($urandom)}; result_gen = 2'($urandom); result_token = 18'($urandom);
        result_value = $urandom; result_cycles = $urandom;
        // PHY loopback (6 edges) in calibration / aligned epochs; rare corruption, rx_v flips and tx_up drops
        lb[cyc % 8] = a_fdi_tx_flit; lbv[cyc % 8] = a_fdi_tx_v;
        fdi_rx_v = (ep_n >= 0 && ep_n % 2 == 0) ? lbv[(cyc + 2) % 8] : 1'b0; fdi_rx_flit = lb[(cyc + 2) % 8];
        if ($urandom % 5000 == 0) fdi_rx_flit[$urandom % 583] = ~fdi_rx_flit[$urandom % 583];
        if ($urandom % 20000 == 0) fdi_rx_v = ~fdi_rx_v;
        fdi_tx_up = ($urandom % 20000 != 0);
        if (ep_n == 0 && t_ev < 0 && u_a.u_core.u_end.tv) t_ev = cyc;   // first TX calendar event
        if (ep_n == 0 && t_rx < 0 && t_ev >= 0 && fdi_rx_v) begin t_rx = cyc; lb_lat = t_rx + 1 - t_ev; end
        // programming window (calendars stopped): one image word every second cycle
        cfg_tx_we = 0; cfg_rx_we = 0; cal_start = 0; cal_start_rx = 0; fwd_epoch = 0;
        if (ep_c == PROG0 - 2 || cyc == 40) make_images((ep_n + 1) % 2 == 1 ? 1 : 0);
        if ((ep_c >= PROG0 && ep_c < PROG0 + 132) || (cyc >= 42 && cyc < 42 + 132)) begin
            e = (cyc >= 42 && cyc < 42 + 132) ? (cyc - 42) : (ep_c - PROG0);
            if (e % 2 == 0) begin
                rx = (e / 2) / 33; cfg_addr = ((e / 2) % 33 == 32) ? 6'd32 : 6'((e / 2) % 33);
                cfg_data = img[rx][(e / 2) % 33]; cfg_tx_we = (rx == 0); cfg_rx_we = (rx == 1);
            end
        end
        // calendar faults are sticky until reset: a faulted die is reset (both models) before the next epoch
        if (ep_c == STROBE - 60 && (u_a.u_core.u_end.tf | u_a.u_core.u_end.rf)) begin rst_n = 0; nrst = nrst + 1; end
        if (ep_c == STROBE - 50) rst_n = 1;
        if (ep_c == STROBE) fwd_epoch = 1;                             // forwarded epoch strobe: next epoch begins
        // compiled starts (TX every 160 cycles; RX LB later in aligned epochs); rare start-while-running
        if (ep_n >= 0 && ep_c >= START0 && ep_c <= LAST_START && (ep_c - START0) % 160 == 0) begin
            cal_start = 1; cal_seg = $urandom; seg_hold = cal_seg; cal_user_tx = $urandom;
        end
        if (ep_n > 0 && ep_n % 2 == 0 && ep_c >= START0 + lb_lat && ep_c <= LAST_START + lb_lat && (ep_c - START0 - lb_lat) % 160 == 0) begin
            cal_start_rx = 1; cal_seg_rx = seg_hold; cal_user_rx = $urandom;
        end
        if (ep_n % 2 == 1 && $urandom % 9000 == 0) cal_start = 1;
    end

    // compare
    always @(posedge ck) if (cyc > 40) begin
        if (a_o !== b_o) begin
            nmis = nmis + 1;
            if (nmis <= 4) begin
                $display("SFEQ_FAIL cycle=%0d diff_bits=%0d", cyc, $countones(a_o ^ b_o));
                for (kk = 0; kk < 1175; kk = kk + 1) if (a_o[kk] !== b_o[kk]) begin
                    $display("    bit %0d a=%b b=%b", kk, a_o[kk], b_o[kk]); kk = 1175; end
            end
        end
`ifdef SFEQ_DBG
        if (cyc % 2000 == 1000) $display("DBG cyc=%0d run=%b f=%b cnt=%0d cur=%h ef=%b ab=%b st=%b eb=%b tbl0=%h fc=%b rxv=%b lb=%0d", cyc,
            u_a.u_core.u_end.u_txcal.running, u_a.u_core.u_end.u_txcal.fault, u_a.u_core.u_end.u_txcal.cnt, u_a.u_core.u_end.u_txcal.cur,
            u_a.u_core.u_end.end_fault, a_epoch_abort, cal_start, u_a.u_core.eb, u_a.u_core.u_end.u_txcal.tbl[0], u_a.u_core.fc, fdi_rx_v, lb_lat);
`endif
        nslot = nslot + a_native_tx_slot + a_prog_witness_slot + a_kv_x3_slot;
        nftx = nftx + a_fdi_tx_v; nrx = nrx + a_native_rx_v + a_prog_rx_v + a_emb_rx_v;
        nab = nab + a_epoch_abort; neb = neb + fwd_epoch; nres = nres + result_v;
        nhit = nhit + u_a.u_core.u_end.u_link.g_bank[0].u_store.hit_age0 + u_a.u_core.u_end.u_link.g_bank[0].u_store.hit_age1;
        nseg1 = nseg1 + (cal_start & cal_seg);
        if (cyc == NCYC) begin
            if (nmis == 0 && nftx > 1000 && nslot > 1000)
                $display("SFEQ_PASS loopback=%0d cycles=%0d slots=%0d fdi_tx=%0d rx_v=%0d abort_cycles=%0d epochs=%0d results=%0d bank0_hits=%0d seg1_starts=%0d resets=%0d",
                         lb_lat, cyc, nslot, nftx, nrx, nab, neb, nres, nhit, nseg1, nrst);
            else
                $display("SFEQ_FAIL mismatching_cycles=%0d slots=%0d fdi_tx=%0d", nmis, nslot, nftx);
            $finish;
        end
    end
endmodule
