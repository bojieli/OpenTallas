`timescale 1ns/1ps
// S81-ROWX (2026-10-26): exact bench of the dsdv_svc_att held-row EXPORT (q frame type 11 ROWX) and the tile-tagged
// ROWS PK2 ingress (type 6, header spec [0] = 1), plus a lockstep regression miter ROWX = 1 vs ROWX = 0 on legacy
// traffic.  Build with -DOT_SVC_ALLQ (the 877 die define) and -DTB_MUT=<n>.
// Phase 1 (export / ingress): two shares of the same tile T in two dies, ex (DIE_ID 0) and rx (DIE_ID 1), the same
//   stack ST (CFG), get the same CFG / WIN_LOAD (wcount 128) / SEL_IDS (512 random gids; ~1/16 of them held by each
//   (die, stack)) and ROWX {XO, NXW, XB 0, LAST}; rx's die position comes from CFG [57:55] (its parameter DIE_ID is 0, as every slice on the 877 die).  Each has its own HBM model (one PC face each: credit 3 edges after a
//   request, read beats 18..33 edges later, data = an independent hash of (die, PC, sector)).
//   GOLDEN (independent of the RTL): held list = the ranks whose gid has die = DIE_ID and stack = ST, rank order; the
//   piece of rank r = bits 144 k .. 144 k + 143 of the 9 sectors (PC g[8], SB + 9 (g >> 9)) of the model, k = g[3:0];
//   export word i (NXW words on consecutive cycles) = {head = (i % 5 == 0), half(entry 2 i + 1), half(entry 2 i)},
//   half = {v, tile, rank, piece} in the ROW HALF layout of dsdv_svc_att.sv (v = 0 -> all-zero half).
//   Then ex's exported halves are re-paired with decoy halves of tile T ^ 3 (ranks held by die 2) into one PK2 ROWS
//   frame for rx only.  PASS needs: ex and rx export words exactly golden, rx land[128 + r][143:0] == ex piece and
//   pres for every ex-held rank, every rx-held rank landed with rx's own piece (fetch), no decoy rank landed, no fault.
//   Directed negatives: a PK2 word with both halves of tile T -> rx fault 29; a ROWX with NXW 7 -> ex fault 25.
// S81-ROWX2 (2026-10-26): +ro=1 runs the RANK-ORDER SLOT export (ROWX [30] RO, NP passes of NXW words, period XP)
//   and its rank-order PK2 ingress; +ro=0 (default) is the held-list export = the B = 2 NXW fallback (B = 80 at the
//   default NXW 40).  RO golden: word i of pass p = ranks 2 (p NXW + i), + 1, a half valid iff that rank's gid is held
//   by ex's (die, stack); word (p, i) at first + p XP + i.  RO ingress to rx = the slot-wise OR of ex's ACTUAL RO export
//   and a synthetic RO stream of the other 14 peers (disjoint: asserted), re-paired into rank-order PK2 words
//   (512 ranks x 4 tile pairs of the half, the other tiles' halves are decoys) = 2,048 words + 1 header sent
//   back-to-back; PASS needs every one of the 512 rx slots landed with the right piece (own fetch / ex export / peer).
//   +fix=<hex> loads the 512 gids of a fixture layer (results/rtl/s81_rowx2_1026/fix, the 1M golden token) with
//   +exd/+rxd/+st = the die positions / stack of ex / rx; +stress=N makes ex hold the first N ranks (random mode).
//   A held-list run whose ex list exceeds 2 NXW (or XN) must raise fault 26 (24): verdict PASS = overflow caught.
// Phase 2 (regression miter): a ROWX = 0 and a ROWX = 1 share, same parameters, driven by one legacy stream (CFG,
//   OWN_ROW, WIN_LOAD, SEL_IDS, pair ROWS, ATTN_Q, GO, PV, IK_ROW, SMJ) with one shared HBM model; every output port
//   is compared every cycle (PASS = 0 mismatching cycles, and the job really ran: scores / P.V words seen).
module tb_dsdv_svc_rowx;
    localparam integer T = 9, SID = 5, ST = 2, PVS = 70, GD = 16, WC = 128;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    integer XO = 8, NXW = 40, SEED = 1;
    integer RO = 0, NP = 7, XP = 320, EXD = 0, RXD = 1, STK = 2, STRESS = 0; string FIX;

    // ------------------------------------------------------------------ HBM model (one per share)
    function automatic [255:0] mem(input integer die, input integer pc, input [29:0] a);
        reg [31:0] x; reg [255:0] w;
        for (int k = 0; k < 8; k++) begin
            x = 32'(a) * 32'h9E3779B1 ^ 32'(die * 7919 + pc * 104729 + k * 15485863);
            x = x ^ (x >> 15); x = x * 32'h85EBCA6B; x = x ^ (x >> 13); x = x * 32'hC2B2AE35; x = x ^ (x >> 16);
            w[32*k +: 32] = x;
        end
        mem = w;
    endfunction

    // ------------------------------------------------------------------ stream builder
    function automatic [511:0] hdr(input [3:0] ty, input [11:0] len); reg [511:0] h; h = '0; h[511:508] = ty; h[503] = 1'b1;
        h[491:480] = len; hdr = h; endfunction
    function automatic [511:0] rnd512(); reg [511:0] x; for (int k = 0; k < 16; k++) x[32*k +: 32] = $urandom(); rnd512 = x; endfunction
    reg [31:0] gid [0:511];
    reg [29:0] SB = 30'h20000, WB = 30'h1000;
    function automatic [143:0] piece(input integer die, input [31:0] g);
        reg [9*256-1:0] blk; integer pc;
        pc = g[8];
        for (int s = 0; s < 9; s++) blk[256*s +: 256] = mem(die, pc, SB + 30'd9 * 30'(g[20:9]) + 30'(s));
        piece = blk[144 * g[3:0] +: 144];
    endfunction
    function automatic [143:0] ppiece(input [31:0] g, input integer r);   // RO bench: a synthetic peer die's piece
        reg [255:0] w; w = mem(16 + 32'(g[7:4]), 32'(g[8]), 30'(r)); ppiece = w[143:0];
    endfunction
    function automatic [255:0] half(input v, input [3:0] t, input [9:0] r, input [143:0] b);
        half = v ? {88'd0, b[127:89], 9'd0, b[88:0], b[143:128], r, t, 1'b1} : 256'd0;
    endfunction

    // ------------------------------------------------------------------ DUT harness (generic share + its HBM model)
    // q stream arrays: phase 1 ex / rx, phase 2 miter
    reg qv_e = 0, qv_r = 0; reg [511:0] qd_e = 0, qd_r = 0;
    wire [2*341-1:0] rq_e, rq_r; wire [1:0] rk_e, rk_r, rv_e, rv_r; wire [511:0] rdat_e, rdat_r; wire [33:0] rtag_e, rtag_r;
    wire [7:0] rbt_e, rbt_r;
    wire pvv_e, pvv_r; wire [512:0] pvd_e, pvd_r; wire flt_e, flt_r; wire [31:0] fc_e, fc_r;
`ifdef OT_SVC_ALLQ
    wire [9:0] pvs = 10'(PVS);
`else
    wire [7:0] pvs = 8'(PVS);
`endif
`ifndef TB_MITER   // build P1 (export / ingress); build MITER (-DTB_MITER) holds only the phase 2 miter (Verilator memory)
    dsdv_svc_att #(.MUT(`TB_MUT), .DIE_ID(0), .ROWX(1), .PFIFO(64)) u_ex (
        .clk(clk), .rst_n(rst_n), .sid(4'(SID)), .tile(4'(T)), .gd(8'(GD)), .pvs(pvs), .root(1'b0),
        .q_v(qv_e), .q_d(qd_e), .hw_v(1'b0), .hw_d(291'd0),
        .qrq(rq_e), .qrk(rk_e), .qwd(2'b00), .qrv(rv_e), .qr_data(rdat_e), .qr_tag(rtag_e), .qr_beat(rbt_e),
        .l_v(), .l_d(), .pv_ov(pvv_e), .pv_od(pvd_e), .sm_st(), .sm_kind(), .sm_jid(), .sm_rv(), .sm_rp(), .sm_rj(), .sm_rd(),
        .go_o(), .tjob_o(), .done(), .tagj(), .hcr(), .hack(), .fault(flt_e), .fault_code(fc_e),
        .pio_o(), .pvo_o(), .jc_o(), .st_o()
`ifdef OT_SVC_ALLQ
        , .allq_o()
`endif
        );
    dsdv_svc_att #(.MUT(`TB_MUT), .DIE_ID(0), .ROWX(1), .PFIFO(64)) u_rx (   // die position 1 from CFG DP (parameter DIE_ID 0 = the die's real binding)
        .clk(clk), .rst_n(rst_n), .sid(4'(SID)), .tile(4'(T)), .gd(8'(GD)), .pvs(pvs), .root(1'b0),
        .q_v(qv_r), .q_d(qd_r), .hw_v(1'b0), .hw_d(291'd0),
        .qrq(rq_r), .qrk(rk_r), .qwd(2'b00), .qrv(rv_r), .qr_data(rdat_r), .qr_tag(rtag_r), .qr_beat(rbt_r),
        .l_v(), .l_d(), .pv_ov(pvv_r), .pv_od(pvd_r), .sm_st(), .sm_kind(), .sm_jid(), .sm_rv(), .sm_rp(), .sm_rj(), .sm_rd(),
        .go_o(), .tjob_o(), .done(), .tagj(), .hcr(), .hack(), .fault(flt_r), .fault_code(fc_r),
        .pio_o(), .pvo_o(), .jc_o(), .st_o()
`ifdef OT_SVC_ALLQ
        , .allq_o()
`endif
        );
    tb_rowx_hbm #(.DIE(0)) u_he (.clk(clk), .rst_n(rst_n), .rq(rq_e), .rk(rk_e), .rv(rv_e), .rd(rdat_e), .rt(rtag_e), .rb(rbt_e));
    tb_rowx_hbm #(.DIE(1)) u_hr (.clk(clk), .rst_n(rst_n), .rq(rq_r), .rk(rk_r), .rv(rv_r), .rd(rdat_r), .rt(rtag_r), .rb(rbt_r));

    // export word capture
    reg [512:0] xw_e [$], xw_r [$]; integer xc_e [$];
    always @(posedge clk) if (rst_n) begin
        if (pvv_e) begin xw_e.push_back(pvd_e); xc_e.push_back(cyc); end
        if (pvv_r) xw_r.push_back(pvd_r);
    end

`endif
    task automatic send2(input [511:0] w, input bit e, input bit r);
        #0.2; qv_e = e; qd_e = e ? w : '0; qv_r = r; qd_r = r ? w : '0; @(posedge clk);
    endtask
    task automatic idle(input integer n); for (int k = 0; k < n; k++) send2('0, 0, 0); endtask

    integer held_e [$], held_r [$], decoy [$];
    integer err = 0, rowx_hdr_cyc = 0, neg29 = 0, neg25 = 0, neg26 = 0, ovf = 0, ing_q = 0, ing_t0 = 0, peer_n = 0;
    // ------------------------------------------------------------------ phase 2 miter (defined below)
    reg m_run = 0; integer m_mis = 0, m_sc = 0, m_pv = 0, m_cyc = 0;

    initial begin
        void'($value$plusargs("seed=%d", SEED)); void'($value$plusargs("xo=%d", XO)); void'($value$plusargs("nxw=%d", NXW));
        void'($value$plusargs("ro=%d", RO)); void'($value$plusargs("np=%d", NP)); void'($value$plusargs("xp=%d", XP));
        void'($value$plusargs("exd=%d", EXD)); void'($value$plusargs("rxd=%d", RXD)); void'($value$plusargs("st=%d", STK));
        void'($value$plusargs("stress=%d", STRESS));
        void'($urandom(SEED));
        if ($value$plusargs("fix=%s", FIX)) $readmemh(FIX, gid);
        else
        // selection: 512 gids, owner (die, stack) uniform over 16, blocks 0..63, all different rows
        for (int r = 0; r < 512; r++) begin
            reg [31:0] g; integer o;
            o = $urandom % 16; if (r % 37 == 5) o = 4'(STK) << 2 | EXD;  // a few extra ex rows (uneven owners)
            if (STRESS > 0) begin                                        // ex holds exactly the first STRESS ranks
                o = (STK << 2) | EXD; if (r >= STRESS) while (o == ((STK << 2) | EXD)) o = $urandom % 16;
            end
            g = 0; g[3:0] = 4'(r % 16); g[5:4] = 2'(o & 3); g[7:6] = 2'(o >> 2); g[8] = 1'($urandom % 2);
            g[20:9] = 12'(r / 16 + 64 * ($urandom % 4));
            gid[r] = g;
        end
        for (int r = 0; r < 512; r++) begin
            reg [31:0] g; g = gid[r];
            if (g[5:4] == 2'(EXD) && g[7:6] == 2'(STK)) held_e.push_back(r);
            else if (g[5:4] == 2'(RXD) && g[7:6] == 2'(STK)) held_r.push_back(r);
            else begin decoy.push_back(r); peer_n++; end
        end
`ifdef TB_MITER
        m_run = 1;
        wait (m_run == 0);
        if (m_mis != 0 || m_sc == 0 || m_pv == 0) err++;
        $display("ROWX build MITER miter_cycles %0d mismatches %0d scores %0d pv_words %0d verdict=%s",
                 m_cyc, m_mis, m_sc, m_pv, err == 0 ? "PASS" : "FAIL");
        $finish;
`else
        repeat (6) @(posedge clk); #0.2 rst_n = 1; repeat (4) @(posedge clk);
        begin   // CFG: WB, ST valid, ALLQ
            reg [511:0] h, hr; h = hdr(4'd12, 12'd0); h[29:0] = WB; h[32] = 1'b1; h[31:30] = 2'(STK); h[54] = 1'b1;
            hr = h; hr[57] = 1'b1; hr[56:55] = 2'(RXD);                 // rx: die position from CFG
            h[57] = 1'b1; h[56:55] = 2'(EXD);                           // ex: die position from CFG
            #0.2; qv_e = 1; qd_e = h; qv_r = 1; qd_r = hr; @(posedge clk);
        end
        begin   // WIN_LOAD: SB, wcount 128, nsel 512, first pos 0, user 0, tag 0x21
            reg [511:0] h; h = hdr(4'd2, 12'd0); h[29:0] = SB; h[88:81] = 8'(WC); h[98:89] = 10'd512; h[119:99] = 21'd0;
            h[502:495] = 8'h21; send2(h, 1, 1);
        end
        idle(4);
        begin   // SEL_IDS
            reg [511:0] h; h = hdr(4'd7, 12'd32); h[9:0] = 0; h[19:10] = 10'd512; send2(h, 1, 1);
            for (int w = 0; w < 32; w++) begin reg [511:0] x; for (int i = 0; i < 16; i++) x[32*i +: 32] = gid[16*w + i]; send2(x, 1, 1); end
        end
        idle(1400 + 4 * STRESS);                                       // scanner 512 ids + held-row fetch
        begin   // ROWX
            reg [511:0] h; h = hdr(4'd11, 12'd0); h[15:0] = 16'(XO); h[21:16] = 6'(NXW); h[28:22] = 7'd0; h[29] = 1'b1;
            if (RO) begin h[30] = 1'b1; h[34:31] = 4'(NP - 1); h[46:35] = 12'(XP); end
            rowx_hdr_cyc = cyc; send2(h, 1, 1);
        end
        idle(XO + PVS + GD + NXW + 20 + (RO ? (NP - 1) * XP : 0));
        ovf = !RO && held_e.size() > 2 * NXW;                          // held-list budget overflow expected
        // ---- export checks
        for (int d = 0; d < 2; d++) begin
            integer hl [$]; reg [512:0] got [$];
            hl = d ? held_r : held_e; got = d ? xw_r : xw_e;
            if (got.size() != (RO ? NP * NXW : NXW)) begin err++; $display("ROWX_COUNT die %0d words %0d", d, got.size()); end
            for (int i = 0; i < got.size() && i < (RO ? NP * NXW : NXW); i++) begin
                reg [512:0] g; integer k0, k1;
                if (RO) begin   // rank-order slot: ranks 2 i, 2 i + 1 (i = p NXW + word), valid iff held by this die / stack
                    reg h0, h1; reg [31:0] dd;
                    dd = d ? RXD : EXD; k0 = 2 * i; k1 = 2 * i + 1;
                    h0 = k0 < 512 && gid[k0 % 512][5:4] == 2'(dd) && gid[k0 % 512][7:6] == 2'(STK);
                    h1 = k1 < 512 && gid[k1 % 512][5:4] == 2'(dd) && gid[k1 % 512][7:6] == 2'(STK);
                    g = {(i % NXW) % 5 == 0, half(h1, 4'(T), 10'(k1), h1 ? piece(d, gid[k1 % 512]) : 144'd0),
                                             half(h0, 4'(T), 10'(k0), h0 ? piece(d, gid[k0 % 512]) : 144'd0)};
                end else begin
                k0 = 2 * i; k1 = 2 * i + 1;
                g = {i % 5 == 0, half(k1 < hl.size(), 4'(T), k1 < hl.size() ? 10'(hl[k1]) : 10'd0,
                                      k1 < hl.size() ? piece(d, gid[hl[k1]]) : 144'd0),
                                 half(k0 < hl.size(), 4'(T), k0 < hl.size() ? 10'(hl[k0]) : 10'd0,
                                      k0 < hl.size() ? piece(d, gid[hl[k0]]) : 144'd0)};
                end
                if (got[i] !== g) begin err++; if (err <= 6) $display("ROWX_WORD die %0d i %0d mismatch", d, i); end
            end
        end
        for (int i = 1; i < xc_e.size(); i++)
            if (xc_e[i] != xc_e[0] + (RO ? (i / NXW) * XP + i % NXW : i)) begin err++; if (err <= 8) $display("ROWX_GAP i %0d", i); end
        if (ovf) begin   // held-list fallback over budget: fault 26 (24 above XN) must flag it; nothing else is judged
            if (!fc_e[26] || (held_e.size() > 128 && !fc_e[24])) err++;
            $display("ROWX build P1 ro 0 nxw %0d held_ex %0d budget %0d fc26 %0d fc24 %0d (overflow caught) err %0d mut %0d verdict=%s",
                     NXW, held_e.size(), 2 * NXW, fc_e[26], fc_e[24], err, `TB_MUT, err == 0 ? "PASS" : "FAIL");
            $finish;
        end
        if (RO) begin   // ---- rank-order PK2 ingress to rx: OR merge of ex's actual export and the synthetic peers
            reg [255:0] ex_h [0:511]; integer wq;
            for (int r = 0; r < 512; r++) ex_h[r] = (r / 2 < xw_e.size()) ? xw_e[r / 2][256 * (r % 2) +: 256] : 256'd0;
            begin reg [511:0] h; h = hdr(4'd6, 12'(2048)); h[0] = 1'b1; ing_t0 = cyc; send2(h, 0, 1); end
            wq = 1;
            for (int r = 0; r < 512; r++) begin
                reg [255:0] pe, mt; reg [31:0] g; g = gid[r];
                pe = (g[7:6] == 2'(STK) && (g[5:4] == 2'(EXD) || g[5:4] == 2'(RXD))) ? 256'd0 :
                     half(1, 4'(T), 10'(r), ppiece(g, r));
                if (|(pe & ex_h[r]) || (pe != 0 && ex_h[r] != 0)) begin err++; $display("RO_MERGE_OVERLAP rank %0d", r); end
                mt = pe | ex_h[r];                                     // the slot-wise OR merge
                for (int p = 0; p < 4; p++) begin
                    reg [255:0] lo, hi; reg [3:0] t0;
                    t0 = 4'((T & 8) + 2 * p);
                    lo = (t0 == 4'(T)) ? mt : ((g[7:6] == 2'(STK) && g[5:4] == 2'(RXD)) ? 256'd0 : half(1, t0, 10'(r), {16'hd0c0, 128'(rnd512())}));
                    hi = (t0 + 1 == 4'(T)) ? mt : ((g[7:6] == 2'(STK) && g[5:4] == 2'(RXD)) ? 256'd0 : half(1, t0 + 4'd1, 10'(r), {16'hd0c1, 128'(rnd512())}));
                    send2({hi, lo}, 0, 1); wq++;
                end
            end
            ing_q = wq; idle(8);
            foreach (decoy[i]) begin
                integer s; reg [31:0] g; s = WC + decoy[i]; g = gid[decoy[i]];
                if (u_rx.land[s][143:0] !== ppiece(g, decoy[i]) || !u_rx.pres[s]) begin
                    err++; if (err <= 8) $display("RX_PEER rank %0d", decoy[i]); end
            end
        end else
        // ---- PK2 ingress to rx: ex halves re-paired with decoy halves (tile T ^ 3)
        // ---- PK2 ingress to rx: ex halves re-paired with decoy halves (tile T ^ 3)
        begin
            reg [255:0] hv [$]; integer nd = 0;
            foreach (xw_e[i]) begin
                if (xw_e[i][0]) hv.push_back(xw_e[i][255:0]);
                if (xw_e[i][256]) hv.push_back(xw_e[i][511:256]);
            end
            begin reg [511:0] h; h = hdr(4'd6, 12'(hv.size())); h[0] = 1'b1; send2(h, 0, 1); end
            foreach (hv[i]) begin
                reg [255:0] dh; integer dr;
                dr = decoy[nd % decoy.size()]; nd++;
                dh = half(1, 4'(T ^ 3), 10'(dr), {16'hbeef, 128'(rnd512())});
                send2((i % 2) ? {hv[i], dh} : {dh, hv[i]}, 0, 1);
                if (($urandom % 4) == 0) idle(1);
            end
            idle(8);
        end
        foreach (held_e[i]) begin
            integer s; s = WC + held_e[i];
            if (u_rx.land[s][143:0] !== piece(0, gid[held_e[i]]) || !u_rx.pres[s]) begin err++; if (err <= 8) $display("RX_LAND ex rank %0d", held_e[i]); end
        end
        foreach (held_r[i]) begin
            integer s; s = WC + held_r[i];
            if (u_rx.land[s][143:0] !== piece(1, gid[held_r[i]]) || !u_rx.pres[s]) begin err++; if (err <= 8) $display("RX_OWN rank %0d", held_r[i]); end
        end
        if (!RO) foreach (decoy[i]) if (u_rx.pres[WC + decoy[i]]) begin err++; if (err <= 8) $display("RX_DECOY rank %0d landed", decoy[i]); end
        if (flt_e || flt_r) begin err++; $display("ROWX_FAULT ex %08x rx %08x", fc_e, fc_r); end
        $display("ROWX_TIMING ro %0d rowx_hdr %0d first_word %0d offset %0d (gd %0d + xo %0d + pvs %0d) words %0d span %0d held ex %0d rx %0d peers %0d ingress_q %0d",
                 RO, rowx_hdr_cyc, xc_e.size() ? xc_e[0] : -1, xc_e.size() ? xc_e[0] - rowx_hdr_cyc : -1, GD, XO, PVS, xw_e.size(),
                 xc_e.size() ? xc_e[$] - xc_e[0] + 1 : 0, held_e.size(), held_r.size(), peer_n, ing_q);
        // ---- directed negatives
        begin
            reg [511:0] h; integer r1, r2; r1 = decoy[0]; r2 = decoy[1];
            h = hdr(4'd6, 12'd1); h[0] = 1'b1; send2(h, 0, 1);
            send2({half(1, 4'(T), 10'(r2), 144'd5), half(1, 4'(T), 10'(r1), 144'd3)}, 0, 1); idle(4);
            neg29 = fc_r[29];
            h = hdr(4'd11, 12'd0); h[21:16] = 6'd7; send2(h, 1, 0); idle(4);
            neg25 = fc_e[25];
            // RO coverage: one pass of NXW 40 covers 80 < nsel 512 ranks -> rx fault 26 (static frame error)
            h = hdr(4'd11, 12'd0); h[21:16] = 6'd40; h[30] = 1'b1; h[34:31] = 4'd0; h[46:35] = 12'd320; send2(h, 0, 1); idle(4);
            neg26 = fc_r[26];
        end
        if (!neg29 || !neg25 || !neg26) err++;
        $display("ROWX build P1 ro %0d nxw %0d np %0d xp %0d xo %0d held_ex %0d held_rx %0d export_words %0d ingress_q %0d err %0d neg29 %0d neg25 %0d neg26 %0d mut %0d verdict=%s",
                 RO, NXW, NP, XP, XO, held_e.size(), held_r.size(), xw_e.size(), ing_q, err, neg29, neg25, neg26, `TB_MUT, err == 0 ? "PASS" : "FAIL");
        $finish;
`endif
    end

    // ------------------------------------------------------------------ phase 2: lockstep miter ROWX 1 vs 0
`ifdef TB_MITER
    reg mq_v = 0; reg [511:0] mq_d = 0; reg mrst = 0; reg mhw_v = 0; reg [290:0] mhw_d = 0;
    wire [2*341-1:0] mrq0, mrq1; wire [1:0] mrk, mrv; wire [511:0] mrd; wire [33:0] mrt; wire [7:0] mrb;
    wire ml_v0, ml_v1; wire [2131:0] ml_d0, ml_d1; wire mpv0, mpv1; wire [512:0] mpd0, mpd1;
    wire [599:0] mo0, mo1;
    wire mf0, mf1; wire [31:0] mfc0, mfc1;
    reg [1:0] mwd = 0;
`ifdef OT_SVC_ALLQ
    `define MQ_ALLQ(x) , .allq_o(x)
`else
    `define MQ_ALLQ(x)
`endif
    `define TB_M(NAME, RX, RQ, LV, LD, PV, PD, O, F, FC) \
    dsdv_svc_att #(.MUT(0), .DIE_ID(0), .ROWX(RX), .PFIFO(64)) NAME ( \
        .clk(clk), .rst_n(mrst), .sid(4'(SID)), .tile(4'(T)), .gd(8'(GD)), .pvs(pvs), .root(1'b1), \
        .q_v(mq_v), .q_d(mq_d), .hw_v(mhw_v), .hw_d(mhw_d), \
        .qrq(RQ), .qrk(mrk), .qwd(mwd), .qrv(mrv), .qr_data(mrd), .qr_tag(mrt), .qr_beat(mrb), \
        .l_v(LV), .l_d(LD), .pv_ov(PV), .pv_od(PD), .sm_st(O[0]), .sm_kind(O[4:1]), .sm_jid(O[12:5]), .sm_rv(O[13]), \
        .sm_rp(O[14]), .sm_rj(O[17:15]), .sm_rd(O[529:18]), .go_o(O[530]), .tjob_o(O[540:531]), .done(O[541]), \
        .tagj(O[549:542]), .hcr(O[551:550]), .hack(O[553:552]), .fault(F), .fault_code(FC), \
        .pio_o(), .pvo_o(), .jc_o(O[569:554]), .st_o(O[571:570]) `MQ_ALLQ(O[572]));
    `TB_M(u_m0, 0, mrq0, ml_v0, ml_d0, mpv0, mpd0, mo0, mf0, mfc0)
    `TB_M(u_m1, 1, mrq1, ml_v1, ml_d1, mpv1, mpd1, mo1, mf1, mfc1)
    assign mo0[599:573] = '0; assign mo1[599:573] = '0;
    tb_rowx_hbm #(.DIE(5)) u_hm (.clk(clk), .rst_n(mrst), .rq(mrq0), .rk(mrk), .rv(mrv), .rd(mrd), .rt(mrt), .rb(mrb));
    always @(posedge clk) if (m_run && mrst) begin
        m_cyc++;
        if (mrq0 !== mrq1 || ml_v0 !== ml_v1 || (ml_v0 && ml_d0 !== ml_d1) || mpv0 !== mpv1 || (mpv0 && mpd0 !== mpd1) ||
            mo0 !== mo1 || mf0 !== mf1 || mfc0 !== mfc1) begin m_mis++; if (m_mis <= 4) $display("MITER_MISMATCH cyc %0d", cyc); end
        if (ml_v0) m_sc++;
        if (mpv0) m_pv++;
    end
    task automatic msend(input [511:0] w); #0.2; mq_v = 1; mq_d = w; @(posedge clk); #0.2; mq_v = 0; mq_d = '0; endtask
    task automatic midle(input integer n); repeat (n) @(posedge clk); endtask
    initial begin
        wait (m_run == 1);
        @(posedge clk); #0.2 mrst = 1; midle(4);
        begin reg [511:0] h; h = hdr(4'd12, 12'd0); h[29:0] = WB; h[32] = 1'b1; h[31:30] = 2'(ST); h[54] = 1'b1; msend(h); end
        begin   // OWN_ROW (slot 5, user 0)
            reg [511:0] h; h = hdr(4'd3, 12'd16); h[465:459] = 7'd5; msend(h); for (int b = 0; b < 16; b++) msend(rnd512());
        end
        midle(40);
        begin reg [511:0] h; h = hdr(4'd2, 12'd0); h[29:0] = SB; h[88:81] = 8'd16; h[98:89] = 10'd48; h[119:99] = 21'd3;
            h[502:495] = 8'h22; msend(h); end
        begin reg [511:0] h; h = hdr(4'd7, 12'd3); h[19:10] = 10'd48; msend(h);
            for (int w = 0; w < 3; w++) begin reg [511:0] x; for (int i = 0; i < 16; i++) x[32*i +: 32] = gid[16*w + i] & 32'h001fff3f | (32'(ST) << 6) * ((i % 3) == 0); msend(x); end
        end
        begin   // legacy pair ROWS for all 48 ranks, 8 pairs each
            reg [511:0] h; h = hdr(4'd6, 12'd384); msend(h);
            for (int r = 0; r < 48; r++) for (int p = 0; p < 8; p++) begin reg [511:0] x; x = rnd512(); x[9:0] = 10'(r); x[33:31] = 3'(p); msend(x); end
        end
        begin   // IK_ROW
            reg [511:0] h; h = hdr(4'd15, 12'd1); h[29:0] = 30'h4000; h[479:459] = 21'd5; msend(h); msend(rnd512());
        end
        begin   // ATTN_Q: 128 words
            reg [511:0] h; h = hdr(4'd1, 12'd128); msend(h); for (int w = 0; w < 128; w++) msend(rnd512() & {16{32'h3f7f3f7f}});
        end
        midle(900);
        begin reg [511:0] h; h = hdr(4'd13, 12'd0); h[15:0] = 16'd300; h[31:16] = 16'd420; msend(h); end
        midle(200);
        begin   // PV frame (legacy host P): 32 words
            reg [511:0] h; h = hdr(4'd5, 12'd32); msend(h); for (int w = 0; w < 32; w++) msend(rnd512() & {16{32'h3f7f3f7f}});
        end
        begin   // SMJ
            reg [511:0] h; h = hdr(4'd9, 12'd2); h[0] = 1'b1; h[4:1] = 4'd4; msend(h); msend(rnd512()); msend(rnd512());
        end
        midle(1500);
        m_run = 0;
    end
`endif
endmodule

// HBM model: one PC per face pair; credit 3 edges after a request, read beats from 18 + (seq % 16) edges later
// (in order per PC), data = mem(DIE, pc, addr + beat).
module tb_rowx_hbm #(parameter integer DIE = 0) (
    input wire clk, input wire rst_n, input wire [2*341-1:0] rq,
    output reg [1:0] rk, output reg [1:0] rv, output reg [511:0] rd, output reg [33:0] rt, output reg [7:0] rb);
    function automatic [255:0] mem(input integer die, input integer pc, input [29:0] a);
        reg [31:0] x; reg [255:0] w;
        for (int k = 0; k < 8; k++) begin
            x = 32'(a) * 32'h9E3779B1 ^ 32'(die * 7919 + pc * 104729 + k * 15485863);
            x = x ^ (x >> 15); x = x * 32'h85EBCA6B; x = x ^ (x >> 13); x = x * 32'hC2B2AE35; x = x ^ (x >> 16);
            w[32*k +: 32] = x;
        end
        mem = w;
    endfunction
    typedef struct { integer t; logic [29:0] a; logic [16:0] tg; integer b; } beat_t;
    beat_t q [2][$];
    integer cr [2][$];
    integer c = 0, seq = 0;
    initial begin rk = 0; rv = 0; rd = 0; rt = 0; rb = 0; end
    always @(posedge clk) begin
        reg [1:0] k, v; c++;
        k = 0; v = 0;
        for (int p = 0; p < 2; p++) begin
            reg [340:0] r; r = rq[341*p +: 341];
            if (rst_n && r[0]) begin
                integer t0;
                cr[p].push_back(c + 3);
                if (!r[1]) begin
                    t0 = c + 18 + (seq % 16); seq++;
                    if (q[p].size() && q[p][$].t >= t0) t0 = q[p][$].t + 1;
                    for (int b = 0; b < r[35:32]; b++) q[p].push_back('{t: t0 + b, a: r[31:2] + 30'(b), tg: r[52:36], b: b});
                end
            end
            if (cr[p].size() && cr[p][0] <= c) begin k[p] = 1; void'(cr[p].pop_front()); end
            if (q[p].size() && q[p][0].t <= c) begin
                v[p] = 1; rd[256*p +: 256] <= mem(DIE, p, q[p][0].a); rt[17*p +: 17] <= q[p][0].tg; rb[4*p +: 4] <= 4'(q[p][0].b);
                void'(q[p].pop_front());
            end
        end
        rk <= k; rv <= v;
    end
endmodule
