`timescale 1ns/1ps
// tb_hgi_coll_rgx (hgi-1010/a 2026-10-10): hardware COLL.ROW_GATHER (spec G25) at full shape, one real rank.
//
// DUT = one complete rank (ot_hgi_coll_rgx: source + the real PSG endpoint in RGX mode + sink) at rank RANK of a
// group of G (96 = the DS TP96 outer group).  The other G - 1 ranks are modelled at the switch (the established
// single-rank method of tb_hbm_accel_tu_endpoint / tb_hgi_coll_bypass): every peer q scans the same list with the same
// owner rule and emits ONLY its owned rows, flit f of entry x as {1, FF, q, x F + f, data}, one flit a cycle at most,
// into the switch egress queue of the DUT port (q + ord) mod 8; a queue holds EQCAP flits (a full queue stalls the
// peer = switch back-pressure); a queue releases one flit a cycle after LAT cycles, only against the DUT's receive-buffer
// credits.  With G < 96 a foreign rank's flits are mixed in and must be dropped.  The DUT's departures are checked
// (exactly its owned flits, once, bit-exact, src = RANK, gi = x F + f); its switch ingress credits return after TXLAT
// cycles (+ random holds with +TXSTALL).  HBM: NL lanes, random accept (+HSTALL %), 40-120 cycle latency, any return
// order.  List VM port: random accept, in-order responses.  Sink write port: random w_rdy holds (+STALL %).
// Payload words include -0, NaN payloads, subnormals, infinities (sector words from a hash of rank / address / word).
// PASS: every list row x < K and flit f < F written exactly once at O row x with the owner's bytes (destinations), or
// nothing written (non-destination), the DUT sent exactly its owned flits, done without fault; then a second ROW_GATHER
// back to back (REARM) with another K.  Prints the cycles from start to done.
//   +G= +RANK= +K= +K2= +LB= +SEC= +DESTS= +SEED= +STALL= +HSTALL= +TXSTALL= +SKEW= +EQCAP= +LAT=
module tb_hgi_coll_rgx;
    parameter integer MUT_SLOT = 0, MUT_OMAJ = 0, MUT_DUP = 0, MUT_CREDIT = 0, MUT_NOGATE = 0, DEL = 4;
    localparam integer NPT = 8, NL = 2, FW = 512, PWT = FW + 33, AW = 35, NR = 96, KMAX = 2048, RXAW = 8;
    reg clk = 0, rst_n = 0;
    always #0.4166665 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // ---------------- configuration ----------------
    integer FOREIGN, G, RANK, K, K2, LB, SEC, F, DESTS, SEED, STALL, HSTALL, TXSTALL, SKEW, EQCAP, LAT, TXLAT, GBASE, RREL, NRUN;
    integer ABASE = 32'h0100_0000, ASTRIDE;
    localparam [39:0] OBASE = 40'h20_0000_0000; localparam integer OSTRIDE = 4096;   // O: HBM bytes, row stride
    reg [31:0] list [0:KMAX-1];
    integer owner_of [0:KMAX-1];                  // absolute owner rank of list entry x
    integer local_of [0:KMAX-1];
    reg [31:0] rs;                                 // bench LCG
    function automatic [31:0] rnd();
        rs = rs * 32'd1664525 + 32'd1013904223; rnd = rs ^ (rs >> 13);
    endfunction
    function automatic [31:0] mix(input [31:0] a, input [31:0] b, input [31:0] c);
        reg [31:0] h;
        h = a * 32'h9E3779B1 ^ (b + 32'h7F4A7C15) * 32'h85EBCA77 ^ (c + 32'h165667B1) * 32'hC2B2AE3D;
        h = h ^ (h >> 15); h = h * 32'h2C1B3C6D; h = h ^ (h >> 12);
        mix = h;
    endfunction
    function automatic [31:0] word(input integer rank, input integer saddr, input integer w);
        reg [31:0] h;
        h = mix(rank, saddr, w);
        case (h[3:0])
            4'd0: word = 32'h80000000;           // -0
            4'd1: word = 32'h7FC00000 | (h >> 9); // qNaN payload
            4'd2: word = 32'hFF800001 | (h >> 10);// sNaN, negative
            4'd3: word = 32'h00000001 + (h >> 12);// subnormal
            4'd4: word = 32'hFF800000;           // -inf
            default: word = h;
        endcase
    endfunction
    function automatic [255:0] sector(input integer rank, input integer saddr);
        for (integer w = 0; w < 8; w = w + 1) sector[32*w +: 32] = word(rank, saddr, w);
    endfunction
    function automatic [FW-1:0] flit_of(input integer x, input integer f);
        integer sa;
        sa = ABASE + local_of[x] * ASTRIDE + 2 * f;
        flit_of[255:0] = sector(owner_of[x], sa);
        flit_of[511:256] = (2 * f + 1 < SEC) ? sector(owner_of[x], sa + 1) : 256'd0;
    endfunction

    // ---------------- DUT ----------------
    reg start = 0; wire ready, done, fault;
    wire lq_v; reg lq_rdy = 0; wire [31:0] lq_addr; reg lr_v = 0; reg [511:0] lr_data = 0;
    wire [NL-1:0] hq_v; reg [NL-1:0] hq_rdy = 0; wire [NL*AW-1:0] hq_addr; wire [NL*8-1:0] hq_tag;
    reg [NL-1:0] hr_v = 0; reg [NL*8-1:0] hr_tag = 0; reg [NL*256-1:0] hr_data = 0;
    wire [NPT-1:0] txv, rxc; wire [NPT*PWT-1:0] txf; reg [NPT-1:0] crr = 0, rxv = 0; reg [NPT*PWT-1:0] rxf = 0;
    wire [DEL-1:0] w_v; wire [DEL*11-1:0] w_x; wire [DEL*5-1:0] w_f; wire [DEL*FW-1:0] w_data; reg [DEL-1:0] w_rdy = 0;
    wire [DEL*40-1:0] w_addr;
    wire [31:0] cst;
    reg [11:0] k_in;
`ifdef RGX_REC
    // +define+RGX_REC: the die block body ot_hgi_coll_ep (RGXHW = 1) driven by ONE normative COLL.ROW_GATHER record
    // (unit 6, op 5, param = B | 1 << 8, imm_a = K, imm_b = destinations; A = HBM row store FP32 n = 8 S, I = VM U32 list,
    // O = HBM list-order store), die_id = RANK, group size from the config bus (word 46)
    reg [967:0] rec = 0; reg [39:0] cfgb = 0; wire [2:0] ret; wire [93:0] rfo; wire [79:0] vma; wire epf;
    wire [3:0] dvx; wire [4*PWT-1:0] dflx; wire [1:0] irx; wire [31:0] iix;
    assign ready = ret[0]; assign done = ret[1]; assign fault = ret[2] | epf;
    wire rg_vm;
    ot_hgi_coll_ep #(.RGXHW(1), .DEL(DEL)) dut (.clk(clk), .rst_n(rst_n), .pclk(clk), .prst_n(rst_n), .rank(8'd0), .pf(16'd0), .go(1'b0),
        .inj_idx(iix), .inj_rd(irx), .inj_q({8*FW{1'b0}}), .ph_tx_v(txv), .ph_tx_flit(txf), .sw_cr_ret(crr),
        .ph_rx_v(rxv), .ph_rx_flit(rxf), .rx_credit(rxc), .del_valid(dvx), .del_flit(dflx), .fault(epf), .stat_credit_stall(cst),
        .hgi_rec(rec), .hgi_ret(ret), .hgi_cfg(cfgb), .hgi_rowfmt_o(rfo), .hgi_rowfmt_i(3'b000), .hgi_vmaddr(vma),
        .rg_lq_v(lq_v), .rg_lq_rdy(lq_rdy), .rg_lq_addr(lq_addr), .rg_lr_v(lr_v), .rg_lr_data(lr_data),
        .rg_hq_v(hq_v), .rg_hq_rdy(hq_rdy), .rg_hq_addr(hq_addr), .rg_hq_tag(hq_tag), .rg_hr_v(hr_v), .rg_hr_tag(hr_tag), .rg_hr_data(hr_data),
        .rg_w_v(w_v), .rg_w_addr(w_addr), .rg_w_vm(rg_vm), .rg_w_data(w_data), .rg_w_rdy(w_rdy));
    for (genvar l = 0; l < DEL; l = l + 1) begin : g_xf
        wire [39:0] off = w_addr[l*40 +: 40] - OBASE;
        assign w_x[l*11 +: 11] = 11'(off / 40'(OSTRIDE));
        assign w_f[l*5 +: 5] = 5'((off % 40'(OSTRIDE)) >> 6);
    end
    always @(posedge clk) if (rst_n && (|dvx)) $fatal(1, "FAIL a hardware ROW_GATHER delivered to the SU quarters");
    function automatic [255:0] md(input [1:0] sp, input [2:0] fmt, input [39:0] base_, input [19:0] n, input [31:0] stride);
        begin md = 256'd0; md[1:0] = sp; md[4:2] = fmt; md[47:8] = base_; md[67:48] = n; md[87:68] = 20'd1; md[119:88] = stride; end
    endfunction
    task automatic issue_record();
        reg [127:0] h;
        h = 128'd0; h[127:124] = 4'd6; h[123:118] = 6'd5; h[99:93] = 7'b1010001; h[88:64] = 25'((1 << 8) | (1 << LB));
        h[63:32] = 32'(K); h[31:0] = 32'(DESTS);
        rec = 0;
        rec[128:1] = h;
        rec[384:129] = md(2'd0, 3'd0, 40'(ABASE) * 40'd32, 20'(SEC * 8), 32'(ASTRIDE * 32));
        rec[640:385] = md(2'd0, 3'd0, OBASE, 20'd512, 32'(OSTRIDE));
        rec[896:641] = md(2'd1, 3'd5, 40'h400, 20'(K), 32'd0);
        rec[917:897] = 21'(SEC * 8); rec[938:918] = 21'd512; rec[959:939] = 21'(K); rec[967:960] = 8'(RANK);
        rec[0] = 1'b1;
        @(posedge clk); rec[0] <= 1'b0;
    endtask
`else
    ot_hgi_coll_rgx #(.DEL(DEL), .MUT_SLOT(MUT_SLOT), .MUT_OMAJ(MUT_OMAJ), .MUT_DUP(MUT_DUP), .MUT_CREDIT(MUT_CREDIT),
        .MUT_NOGATE(MUT_NOGATE)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .ready(ready), .done(done), .fault(fault),
        .cfg_rank(8'(RANK)), .cfg_g(8'(G)), .cfg_lb(3'(LB)), .cfg_k(k_in), .cfg_dests(8'(DESTS)), .cfg_abase(AW'(ABASE)),
        .cfg_astride(16'(ASTRIDE)), .cfg_sec(7'(SEC)), .cfg_lbase(32'h40),
        .lq_v(lq_v), .lq_rdy(lq_rdy), .lq_addr(lq_addr), .lr_v(lr_v), .lr_data(lr_data),
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr), .hq_tag(hq_tag), .hr_v(hr_v), .hr_tag(hr_tag), .hr_data(hr_data),
        .ph_tx_v(txv), .ph_tx_flit(txf), .sw_cr_ret(crr), .ph_rx_v(rxv), .ph_rx_flit(rxf), .rx_credit(rxc),
        .w_v(w_v), .w_x(w_x), .w_f(w_f), .w_addr(w_addr), .w_data(w_data), .w_rdy(w_rdy), .cfg_obase(OBASE), .cfg_ostride(32'(OSTRIDE)),
        .stat_credit_stall(cst));

`endif
    // ---------------- list VM port (in order, random accept / latency) ----------------
    localparam integer LQD = 64;
    integer lq_t [0:LQD-1]; integer lq_w [0:LQD-1]; integer lqh = 0, lqt = 0, lq_last = 0;
    always @(posedge clk) if (rst_n) begin
        lr_v <= 1'b0;
        if (lq_v && lq_rdy) begin
            lq_w[lqt % LQD] = integer'(lq_addr) - 32'h40;
            lq_last = (cyc + 6 + integer'(rnd() % 10) > lq_last) ? cyc + 6 + integer'(rnd() % 10) : lq_last;
            lq_t[lqt % LQD] = lq_last; lqt = lqt + 1;
        end
        lq_rdy <= (rnd() % 100) >= 15;
        if (lqt > lqh && lq_t[lqh % LQD] <= cyc) begin : lresp
            reg [511:0] d; integer w;
            w = lq_w[lqh % LQD];
            for (integer i = 0; i < 16; i = i + 1) d[32*i +: 32] = (w * 16 + i < KMAX) ? list[w * 16 + i] : 32'hDEAD0000;
            lr_v <= 1'b1; lr_data <= d; lqh = lqh + 1;
        end
    end

    // ---------------- HBM read lanes (any order) ----------------
    localparam integer HQD = 512;
    integer hp_t [0:NL-1][0:HQD-1]; integer hp_a [0:NL-1][0:HQD-1]; integer hp_g [0:NL-1][0:HQD-1]; integer hp_n [0:NL-1];
    integer nhreq = 0;
    initial for (integer l = 0; l < NL; l = l + 1) hp_n[l] = 0;
    always @(posedge clk) if (rst_n) begin
        for (integer l = 0; l < NL; l = l + 1) begin
            hr_v[l] <= 1'b0;
            if (hq_v[l] && hq_rdy[l]) begin
                if (hp_n[l] >= HQD) $fatal(1, "FAIL bench HBM queue overflow");
                hp_a[l][hp_n[l]] = integer'(hq_addr[l*AW +: AW]); hp_g[l][hp_n[l]] = integer'(hq_tag[l*8 +: 8]);
                hp_t[l][hp_n[l]] = cyc + 40 + integer'(rnd() % 80); hp_n[l] = hp_n[l] + 1; nhreq = nhreq + 1;
                if ((integer'(hq_tag[l*8 +: 8]) & 1) != l) $fatal(1, "FAIL tag parity on lane %0d", l);
            end
            hq_rdy[l] <= (rnd() % 100) >= HSTALL;
            begin : resp
                integer pick; pick = -1;
                for (integer i = 0; i < hp_n[l]; i = i + 1) if (pick < 0 && hp_t[l][i] <= cyc) pick = i;
                if (pick >= 0) begin
                    hr_v[l] <= 1'b1; hr_tag[l*8 +: 8] <= 8'(hp_g[l][pick]);
                    hr_data[l*256 +: 256] <= sector(RANK, hp_a[l][pick]);
                    for (integer i = pick; i < hp_n[l] - 1; i = i + 1) begin
                        hp_t[l][i] = hp_t[l][i+1]; hp_a[l][i] = hp_a[l][i+1]; hp_g[l][i] = hp_g[l][i+1];
                    end
                    hp_n[l] = hp_n[l] - 1;
                end
            end
        end
    end

    // ---------------- switch model: peers -> DUT egress queues; DUT departures ----------------
    localparam integer QD = 256;
    reg [PWT-1:0] eq_f [0:NPT-1][0:QD-1]; integer eq_t [0:NPT-1][0:QD-1]; integer eqh [0:NPT-1]; integer eqt [0:NPT-1];
    integer eq_last [0:NPT-1]; integer eg_cred [0:NPT-1];
    integer cr_t [0:NPT-1][0:QD*4-1]; integer crh [0:NPT-1]; integer crt [0:NPT-1];
    integer eg_ret_t [0:NPT-1][0:QD*4-1]; integer egh [0:NPT-1]; integer egt [0:NPT-1];
    integer pown [0:NR][0:KMAX-1]; integer pn [0:NR]; integer pidx [0:NR]; integer pf_ [0:NR]; integer pord [0:NR];
    integer prot = 0, peers_live = 0, npeer_sent = 0, nforeign = 0, ndep = 0;
    reg peer_go = 0;
    reg [0:65535] tx_seen;
    integer dut_owned_flits;
    always @(posedge clk) if (rst_n) begin
        // DUT departures
        for (integer p = 0; p < NPT; p = p + 1) if (txv[p]) begin : dep
            reg [PWT-1:0] fl; integer gi, x, f;
            fl = txf[p*PWT +: PWT]; gi = integer'(fl[FW +: 16]); x = gi / F; f = gi % F;
            ndep = ndep + 1;
            if (fl[PWT-1] !== 1'b1 || fl[FW+24 +: 8] !== 8'hFF || integer'(fl[FW+16 +: 8]) != RANK)
                $fatal(1, "FAIL departure header gi=%0d src=%0d", gi, fl[FW+16 +: 8]);
            if (x >= K || owner_of[x] != RANK) $fatal(1, "FAIL departure of a row the DUT does not own: gi=%0d x=%0d", gi, x);
            if (tx_seen[gi]) $fatal(1, "FAIL duplicate departure gi=%0d", gi);
            tx_seen[gi] = 1'b1;
            if (fl[FW-1:0] !== flit_of(x, f)) $fatal(1, "FAIL departure payload x=%0d f=%0d id=%h local=%0d got %h exp %h / hi %h exp %h", x, f, list[x], local_of[x],
                fl[31:0], flit_of(x, f) & 512'hFFFFFFFF, fl[287:256], flit_of(x, f) >> 256 & 512'hFFFFFFFF);
            cr_t[p][crt[p] % (QD*4)] = cyc + TXLAT + ((TXSTALL > 0 && (rnd() % 100) < TXSTALL) ? integer'(rnd() % 64) : 0);
            crt[p] = crt[p] + 1;
        end
        for (integer p = 0; p < NPT; p = p + 1) begin
            crr[p] <= 1'b0;
            if (crt[p] > crh[p] && cr_t[p][crh[p] % (QD*4)] <= cyc) begin crr[p] <= 1'b1; crh[p] = crh[p] + 1; end
            // DUT receive-buffer credits come back 5 cycles after rx_credit
            if (rxc[p]) begin eg_ret_t[p][egt[p] % (QD*4)] = cyc + 5; egt[p] = egt[p] + 1; end
            while (egt[p] > egh[p] && eg_ret_t[p][egh[p] % (QD*4)] <= cyc) begin egh[p] = egh[p] + 1; eg_cred[p] = eg_cred[p] + 1; end
            rxv[p] <= 1'b0;
            if (eqt[p] > eqh[p] && eq_t[p][eqh[p] % QD] <= cyc && eg_cred[p] > 0) begin
                rxv[p] <= 1'b1; rxf[p*PWT +: PWT] <= eq_f[p][eqh[p] % QD]; eqh[p] = eqh[p] + 1; eg_cred[p] = eg_cred[p] - 1;
            end
        end
        // peers: each owned flit once, at most one a cycle a peer, into egress queue (q + ord) mod 8 when it has room
        if (peer_go) begin
            for (integer n = 0; n <= NR; n = n + 1) begin : pe
                integer q, p, x;
                q = (prot + n) % (NR + 1);
                if (pidx[q] < pn[q] && (rnd() % 100) < 90) begin
                    p = (q + pord[q]) % NPT;
                    if (eqt[p] - eqh[p] < EQCAP) begin
                        x = pown[q][pidx[q]];
                        eq_last[p] = (cyc + LAT + (q % 5) > eq_last[p]) ? cyc + LAT + (q % 5) : eq_last[p];
                        eq_t[p][eqt[p] % QD] = eq_last[p];
                        if (q == NR) begin   // the foreign rank: a flit of another group (must be dropped)
                            eq_f[p][eqt[p] % QD] = {1'b1, 8'hFF, 8'((GBASE + G) % NR), 16'(x * F + pf_[q]), ~flit_of(x, pf_[q])};
                            nforeign = nforeign + 1;
                        end else begin
                            eq_f[p][eqt[p] % QD] = {1'b1, 8'hFF, 8'(q), 16'(x * F + pf_[q]), flit_of(x, pf_[q])};
                            npeer_sent = npeer_sent + 1;
                        end
                        eqt[p] = eqt[p] + 1; pord[q] = pord[q] + 1;
                        if (pf_[q] == F - 1) begin pf_[q] = 0; pidx[q] = pidx[q] + 1; end else pf_[q] = pf_[q] + 1;
                    end
                end
            end
            prot = (prot + 1) % (NR + 1);
        end
    end

    // ---------------- sink writes ----------------
    reg [0:65535] wseen;
    integer nwr = 0;
    always @(posedge clk) if (rst_n) begin
        for (integer l = 0; l < DEL; l = l + 1) begin
            if (w_v[l] && w_rdy[l]) begin : wr
                integer x, f, gi;
                x = integer'(w_x[l*11 +: 11]); f = integer'(w_f[l*5 +: 5]); gi = x * F + f;
                if (RREL >= DESTS) $fatal(1, "FAIL a non-destination rank wrote row %0d", x);
                if (x >= K || f >= F) $fatal(1, "FAIL write out of range x=%0d f=%0d", x, f);
                if (w_addr[l*40 +: 40] !== OBASE + 40'(x) * 40'(OSTRIDE) + 40'(f * 64)) $fatal(1, "FAIL O address x=%0d f=%0d addr=%h", x, f, w_addr[l*40 +: 40]);
                if (wseen[gi]) $fatal(1, "FAIL duplicate write x=%0d f=%0d", x, f);
                if (w_data[l*FW +: FW] !== flit_of(x, f)) $fatal(1, "FAIL payload at list row %0d flit %0d (owner %0d)", x, f, owner_of[x]);
                wseen[gi] = 1'b1; nwr = nwr + 1;
            end
            w_rdy[l] <= (rnd() % 100) >= STALL;
        end
    end
`ifdef RGX_REC
    always @(posedge clk) if (rst_n && fault) $fatal(1, "FAIL DUT fault (record %0d endpoint-block %0d)", ret[2], epf);
`else
    always @(posedge clk) if (rst_n && fault) $fatal(1, "FAIL DUT fault (cfg %0d src %0d ep %0d sink %0d)", dut.cfg_fault, dut.src_fault, dut.ep_fault, dut.sink_fault);
`endif

    // ---------------- selection + run ----------------
    task automatic make_list(input integer kk);
        integer v, ok, tries, q;
        for (integer x = 0; x < kk; x = x + 1) begin
            tries = 0;
            do begin
                v = integer'(rnd() & 32'hFFFFF);
                if (SKEW > 0 && (rnd() % 100) < SKEW) begin   // force the DUT (rank-in-group RREL) to own it
                    v = (((v >> LB) / G) * G + RREL) << LB | (v & ((1 << LB) - 1));
                    v = v & 32'hFFFFF;
                    if ((((v >> LB) % G)) != RREL) v = (RREL << LB);
                end
                ok = 1;
                for (integer y = 0; y < x; y = y + 1) if (list[y] == 32'(v)) ok = 0;
                tries = tries + 1;
            end while (!ok && tries < 1000);
            list[x] = 32'(v);
            q = (v >> LB) % G;
            owner_of[x] = GBASE + q;
            local_of[x] = (((v >> LB) / G) << LB) | (v & ((1 << LB) - 1));
        end
        for (integer x = kk; x < KMAX; x = x + 1) list[x] = 32'hFFFFFFFF;   // beyond K: never read as ids (fault if scanned)
        for (integer q = 0; q <= NR; q = q + 1) begin pn[q] = 0; pidx[q] = 0; pf_[q] = 0; pord[q] = 0; end
        dut_owned_flits = 0;
        for (integer x = 0; x < kk; x = x + 1) begin
            q = owner_of[x];
            if (q == RANK) dut_owned_flits = dut_owned_flits + F;
            else begin pown[q][pn[q]] = x; pn[q] = pn[q] + 1; end
        end
        if (G < NR && FOREIGN != 0) for (integer x = 0; x < kk; x = x + 3) begin pown[NR][pn[NR]] = x; pn[NR] = pn[NR] + 1; end
    endtask

    integer t0, run, M, cnt [0:NR-1];
    initial begin
        if (!$value$plusargs("G=%d", G)) G = 96;
        if (!$value$plusargs("RANK=%d", RANK)) RANK = 77;
        if (!$value$plusargs("K=%d", K)) K = 512;
        if (!$value$plusargs("K2=%d", K2)) K2 = 7;
        if (!$value$plusargs("LB=%d", LB)) LB = 3;
        if (!$value$plusargs("SEC=%d", SEC)) SEC = 64;
        if (!$value$plusargs("DESTS=%d", DESTS)) DESTS = (G == 96) ? 64 : G;
        if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
        if (!$value$plusargs("STALL=%d", STALL)) STALL = 0;
        if (!$value$plusargs("HSTALL=%d", HSTALL)) HSTALL = 0;
        if (!$value$plusargs("TXSTALL=%d", TXSTALL)) TXSTALL = 0;
        if (!$value$plusargs("SKEW=%d", SKEW)) SKEW = 0;
        if (!$value$plusargs("EQCAP=%d", EQCAP)) EQCAP = 64;
        if (!$value$plusargs("LAT=%d", LAT)) LAT = 40;
        if (!$value$plusargs("TXLAT=%d", TXLAT)) TXLAT = 8;
        if (!$value$plusargs("RUNS=%d", NRUN)) NRUN = 2;
        if (!$value$plusargs("FOREIGN=%d", FOREIGN)) FOREIGN = 1;
        rs = 32'(SEED) * 32'h2545F491 + 32'd7;
        F = (SEC + 1) / 2; ASTRIDE = (SEC > 32) ? 64 : (SEC > 16 ? 32 : 16);
        GBASE = (G == 96) ? 0 : (RANK & ~(G - 1)); RREL = RANK - GBASE;
        k_in = 12'(K);
        for (integer p = 0; p < NPT; p = p + 1) begin
            eqh[p] = 0; eqt[p] = 0; eq_last[p] = 0; eg_cred[p] = 1 << RXAW; crh[p] = 0; crt[p] = 0; egh[p] = 0; egt[p] = 0;
        end
        repeat (5) @(posedge clk);
        rst_n = 1;
`ifdef RGX_REC
        repeat (2) @(posedge clk);
        cfgb <= {1'b0, 1'b1, 6'd46, 32'(G)}; @(posedge clk); cfgb <= {1'b1, 1'b0, 6'd0, 32'd0}; @(posedge clk); cfgb <= 0;
        repeat (4) @(posedge clk);
`endif
        for (run = 0; run < NRUN; run = run + 1) begin
            if (run == 1) K = K2;
            make_list(K);
            k_in = 12'(K);
            tx_seen = '0; wseen = '0; nwr = 0; ndep = 0; npeer_sent = 0;
            for (integer q = 0; q < NR; q = q + 1) cnt[q] = 0;
            for (integer x = 0; x < K; x = x + 1) cnt[owner_of[x] - GBASE] = cnt[owner_of[x] - GBASE] + 1;
            M = 0; for (integer q = 0; q < G; q = q + 1) if (cnt[q] > M) M = cnt[q];
            while (!ready) @(posedge clk);
`ifdef RGX_REC
            @(posedge clk); t0 = cyc; issue_record();
`else
            @(posedge clk); start <= 1'b1; t0 = cyc;
            @(posedge clk); start <= 1'b0;
`endif
            peer_go <= 1'b1;
            while (!done) begin
                @(posedge clk);
                if (cyc - t0 > 400000) $fatal(1, "FAIL hang: no done after 400000 cycles (written %0d of %0d, departed %0d of %0d)",
                                              nwr, K * F, ndep, dut_owned_flits);
            end
            peer_go <= 1'b0;
            if (ndep != dut_owned_flits) $fatal(1, "FAIL DUT departures %0d, owned flits %0d", ndep, dut_owned_flits);
            if (RREL < DESTS && nwr != K * F) $fatal(1, "FAIL written %0d of %0d", nwr, K * F);
            for (integer q = 0; q < NR; q = q + 1) if (q != RANK && pidx[q] != pn[q]) $fatal(1, "FAIL peer %0d not drained", q);
            $display("RUN %0d PASS G=%0d RANK=%0d K=%0d F=%0d B=%0d DESTS=%0d dest=%0d M=%0d own=%0d STALL=%0d HSTALL=%0d TXSTALL=%0d SKEW=%0d foreign=%0d CYCLES=%0d",
                     run, G, RANK, K, F, 1 << LB, DESTS, RREL < DESTS, M, dut_owned_flits / F, STALL, HSTALL, TXSTALL, SKEW, nforeign, cyc - t0);
            repeat (20) @(posedge clk);
        end
        $display("PASS tb_hgi_coll_rgx");
        $finish;
    end
endmodule
