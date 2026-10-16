`timescale 1ns/1ps
// tb_hgi_coll_pipe (hgi-unitrate 2026-10-10): the collective block body ot_hgi_coll_ep driven by the DeepSeek-V4.1
// layer's REAL COLL.ALL_GATHER record sequence (G = 96 TU fabric, FP32 sliced gathers: x_projections qa 1,280 / kvraw
// 512, attn_out y 5,120, router gsc 384, expert_intermediate s5 s4 s3 s0 s1 s2 s6 2,304 each, ffn_out yf 5,120 words),
// issued BACK TO BACK (a record is offered as soon as the block shows rec_rdy), at one rank; the other 95 ranks are
// modelled SPMD-lockstep by a switch stub: when this rank sends flit m of its k-th gather, every peer q sends ITS flit
// m of ITS k-th gather, arriving LAT (+ q mod 5) cycles later (the 377.6 ns TU crossing = 453 cycles at 1.2 GHz), with
// switch ingress / egress credits returned CRED cycles later (113.8 ns = 137).  Peer flits carry the peer's epoch tag
// exactly as the DUT's own departures do (PIPE: dst = {5'b11111, epoch}, else 8'hFF), so a stub never invents it.
// Checks: every delivered word (formatter output {1, lanes, src, word offset, data}) lands at O_k + offset + j with the
// owning rank's value (the own slice too: bypass delivers it from the own queue), every O word of every gather
// exactly once, nothing else, no fault, every record retires in order.
// Reports per record dispatch -> retire and the whole sequence's cycles (the price: perf.coll_cycles shared per w19 op).
//   +LAT=453 +CRED=137 +RANK=r +REPS=n (sequence repetitions) +LEAD=j (peers j gathers ahead) +GAP=c (cycles this rank's
//   CP waits before each next record: with LEAD, peer flits of a gather arrive before this rank starts it -> parking)
//   defines: PIPE (pipelined endpoint), MUT_PIPE=n mutants, OLD_EP (the pre-PIPE block, no hgi_del_obase port)
module tb_hgi_coll_pipe;
    localparam integer NR = 96, LANES = 16, NPT = 8, INJ = 2, DEL = 4, FW = 32 * LANES, PWT = FW + 33, NREC = 13;
    integer lat, cred, rank, reps, lead, gap, nk_all;
    reg clk = 0, rst_n = 0;
    always #0.4166665 clk = ~clk;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    // the layer's gather sequence (tag order of ds_native L0)
    integer nwords [0:NREC-1];
    initial begin
        nwords[0] = 1280; nwords[1] = 512; nwords[2] = 5120; nwords[3] = 384;
        for (integer i = 4; i < 11; i = i + 1) nwords[i] = 2304;
        nwords[11] = 5120; nwords[12] = 2304;
    end
    // value of word w of rank q's A buffer of gather k (every rank holds the full layout; it sends its slice)
    function automatic [31:0] val(input integer k, input integer q, input integer w);
        val = 32'(k * 1000003 + q * 7919 + w * 104729) ^ 32'h5A5A0000 ^ ((w % 7 == 0) ? 32'h80000000 : 32'd0);
    endfunction
    function automatic integer slo(input integer n, input integer q); slo = (q * n) / NR; endfunction
    // ---- DUT
    reg [967:0] rec = 0; reg [39:0] cfgb = 0; wire [2:0] ret; wire [93:0] rfo; wire [79:0] vma;
    wire [INJ*16-1:0] ii; wire [INJ-1:0] ir; reg [4*INJ*FW-1:0] injq;
    wire [NPT-1:0] txv, rxc; wire [NPT*PWT-1:0] txf; reg [NPT-1:0] crr = 0, rxv = 0; reg [NPT*PWT-1:0] rxf = 0;
    wire [DEL-1:0] dv; wire [DEL*PWT-1:0] dfl; wire flt; wire [31:0] cst; wire [DEL*40-1:0] dob;
    ot_hgi_coll_ep
`ifdef PIPE
        #(.PIPE(1)
`ifdef MUT_PIPE
        , .MUT_PIPE(`MUT_PIPE)
`endif
        )
`endif
        dut (.clk(clk), .rst_n(rst_n), .pclk(clk), .prst_n(rst_n), .rank(8'd0), .pf(16'd0), .go(1'b0),
        .inj_idx(ii), .inj_rd(ir), .inj_q(injq), .ph_tx_v(txv), .ph_tx_flit(txf), .sw_cr_ret(crr),
        .ph_rx_v(rxv), .ph_rx_flit(rxf), .rx_credit(rxc), .del_valid(dv), .del_flit(dfl), .fault(flt), .stat_credit_stall(cst),
        .hgi_rec(rec), .hgi_ret(ret), .hgi_cfg(cfgb), .hgi_rowfmt_o(rfo), .hgi_rowfmt_i(3'b000), .hgi_vmaddr(vma)
`ifndef OLD_EP
        , .hgi_del_obase(dob)
`endif
        );
    function automatic [255:0] md(input [2:0] fmt, input [39:0] base_, input [19:0] n);
        begin md = 256'd0; md[1:0] = 2'd1; md[4:2] = fmt; md[47:8] = base_; md[67:48] = n; md[87:68] = 20'd1; end
    endfunction
    localparam [39:0] ABASE = 40'h10000, OSTRIDE = 40'h4000;   // gather k: A at ABASE + k*OSTRIDE, O at 0x200000 + k*OSTRIDE
    // ---- the gather each in-flight piece belongs to.  The DUT tells us nothing: we track issue order.  Injection of
    // gather k starts after its record is accepted; the inject model reads A of the gather the DUT is injecting, which
    // is the oldest accepted gather whose pf flits are not all injected (inject is in record order).
    integer acc_k = 0;               // records accepted
    integer inj_k = 0, inj_n = 0;    // gather being injected and flits injected of it
    integer pf_of [0:1023]; integer n_of [0:1023];
    // SU-quarter inject: flit f of the gather being injected: rank's slice words s_r + 16 f + j (VM read model)
    always @* begin
        injq = 0;
        for (integer i = 0; i < INJ; i = i + 1) if (ir[i]) begin
            integer f, k; f = integer'(ii[16*i +: 16]); k = inj_k;
            for (integer j = 0; j < 16; j = j + 1)
                injq[(f % 4) * INJ * FW + i * FW + 32 * j +: 32] = val(k % NREC + (k / NREC) * 17, rank, slo(n_of[k], rank) + 16 * f + j);
        end
    end
    // ---- switch stub (as tb_hgi_coll_bypass / hgi_e2e_coll_slot)
    localparam integer QD = 65536;
    reg [PWT-1:0] eqf [0:NPT*QD-1]; integer eqt [0:NPT*QD-1]; integer eh [0:NPT-1]; integer et [0:NPT-1];
    integer cin [0:NPT*QD-1]; integer ch [0:NPT-1]; integer ct [0:NPT-1];
    integer ceg [0:NPT*QD-1]; integer gh [0:NPT-1]; integer gt [0:NPT-1]; integer eg_cred [0:NPT-1];
    initial for (integer p = 0; p < NPT; p = p + 1) begin eg_cred[p] = 256; eh[p] = 0; et[p] = 0; ch[p] = 0; ct[p] = 0; gh[p] = 0; gt[p] = 0; end
    task automatic sched(input integer p, input integer t, input [PWT-1:0] f);
        begin
            if (et[p] - eh[p] >= QD) $fatal(1, "stub queue overflow");
            eqf[p*QD + et[p] % QD] = f; eqt[p*QD + et[p] % QD] = t; et[p] = et[p] + 1;
        end
    endtask
    integer dep_k = 0, dep_n = 0;    // departures: gather k, flits of it sent
    integer errors = 0;
    always @(posedge clk) if (rst_n) begin
        for (integer p = 0; p < NPT; p = p + 1) if (txv[p]) begin : dep
            reg [PWT-1:0] f; reg [511:0] d; integer gi, m, k, pfk, n;
            f = txf[p*PWT +: PWT]; gi = integer'(f[FW +: 16]); k = dep_k; pfk = pf_of[k]; n = n_of[k];
            m = gi - rank * pfk;
            if (f[PWT-1] !== 1'b1 || integer'(f[FW+16 +: 8]) != rank || m < 0 || m >= pfk) begin
                $display("ERR bad departure k %0d gi %0d src %0d pf %0d", k, gi, f[FW+16 +: 8], pfk); errors = errors + 1; end
            // peers: SPMD lockstep (LEAD 0: flit m of the same gather), or LEAD gathers ahead (gather 0's departures also
            // release gathers 0 .. LEAD; a gather's flits beyond the departing one's pf leave with its last flit)
            for (integer t = ((k == 0) ? 0 : k + lead); t <= k + lead && t < nk_all; t = t + 1)
                for (integer mm = m; mm < pf_of[t] && (mm == m || m == pfk - 1); mm = mm + 1)
                    for (integer q = 0; q < NR; q = q + 1) if (q != rank) begin
                        for (integer j = 0; j < 16; j = j + 1) d[32*j +: 32] = val(t % NREC + (t / NREC) * 17, q, slo(n_of[t], q) + 16 * mm + j);
`ifdef PIPE
                        sched((q + mm) % NPT, cyc + lat + (q % 5), {1'b1, 5'b11110, 3'(t), 8'(q), 16'(q * pf_of[t] + mm), d});
`else
                        sched((q + mm) % NPT, cyc + lat + (q % 5), {1'b1, 8'hFF, 8'(q), 16'(q * pf_of[t] + mm), d});
`endif
                    end
            cin[p*QD + ct[p] % QD] = cyc + cred; ct[p] = ct[p] + 1;
            dep_n = dep_n + 1; if (dep_n == pfk) begin dep_n = 0; dep_k = dep_k + 1; end
        end
        for (integer p = 0; p < NPT; p = p + 1) begin
            while (gt[p] > gh[p] && ceg[p*QD + gh[p] % QD] <= cyc) begin gh[p] = gh[p] + 1; eg_cred[p] = eg_cred[p] + 1; end
            rxv[p] <= 1'b0;
            if (et[p] > eh[p] && eqt[p*QD + eh[p] % QD] <= cyc && eg_cred[p] > 0) begin
                rxv[p] <= 1'b1; rxf[p*PWT +: PWT] <= eqf[p*QD + eh[p] % QD];
                eh[p] = eh[p] + 1; eg_cred[p] = eg_cred[p] - 1;
            end
            if (rxc[p]) begin ceg[p*QD + gt[p] % QD] = cyc + cred; gt[p] = gt[p] + 1; end
            crr[p] <= 1'b0;
            if (ct[p] > ch[p] && cin[p*QD + ch[p] % QD] <= cyc) begin ch[p] = ch[p] + 1; crr[p] <= 1'b1; end
        end
    end
    // inject progress (ir pulses = flits read for injection, in record order)
    always @(posedge clk) if (rst_n) for (integer i = 0; i < INJ; i = i + 1) if (ir[i]) begin
        inj_n = inj_n + 1; if (inj_n == pf_of[inj_k]) begin inj_n = 0; inj_k = inj_k + 1; end
    end
    // ---- delivery checker: the DUT's O base for each delivered flit is vma[79:40] of the gather it belongs to; the
    // checker writes into a shadow O space keyed by that base and checks the words at the end
    localparam integer OSPACE = 1 << 22;
    reg [31:0] om [0:OSPACE-1]; reg [7:0] oc [0:OSPACE-1];
    integer ndel = 0;
    always @(posedge clk) if (rst_n) for (integer l = 0; l < DEL; l = l + 1) if (dv[l]) begin : chk
        reg [PWT-1:0] f; integer w, lanes, ob;
        f = dfl[l*PWT +: PWT]; w = integer'(f[FW +: 16]); lanes = integer'(f[FW+24 +: 8]);
`ifdef OLD_EP
        ob = integer'(vma[79:40]);
`else
        ob = integer'(dob[l*40 +: 40]);
`endif
        for (integer j = 0; j < 16; j = j + 1) if (j < lanes) begin
            om[(ob + w + j) % OSPACE] = f[32*j +: 32]; oc[(ob + w + j) % OSPACE] = oc[(ob + w + j) % OSPACE] + 1;
        end
        ndel = ndel + 1;
    end
    // ---- driver: records back to back
    integer t_disp [0:1023]; integer t_ret [0:1023]; integer nret = 0, nflt = 0;
    always @(posedge clk) if (rst_n) begin
        if (ret[1]) begin t_ret[nret] = cyc; nret = nret + 1; end
        if (ret[2]) nflt = nflt + 1;
    end
    integer total, k, t0, nk, own_lo, own_hi;
    initial begin
        if (!$value$plusargs("LAT=%d", lat)) lat = 453;
        if (!$value$plusargs("CRED=%d", cred)) cred = 137;
        if (!$value$plusargs("RANK=%d", rank)) rank = 37;
        if (!$value$plusargs("REPS=%d", reps)) reps = 1;
        if (!$value$plusargs("LEAD=%d", lead)) lead = 0;
        if (!$value$plusargs("GAP=%d", gap)) gap = 0;
        for (integer x = 0; x < OSPACE; x = x + 1) oc[x] = 0;
        nk = NREC * reps; nk_all = nk;
        for (k = 0; k < nk; k = k + 1) begin
            n_of[k] = nwords[k % NREC];
            pf_of[k] = ((n_of[k] + NR - 1) / NR + 15) / 16;   // ceil(ceil(n / G) / 16)
        end
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        cfgb = {1'b0, 1'b1, 6'd46, 32'd96}; @(negedge clk); cfgb = {1'b1, 1'b0, 6'd0, 32'd0}; @(negedge clk); cfgb = 0;
        repeat (4) @(negedge clk);
        t0 = cyc;
        for (k = 0; k < nk; k = k + 1) begin : issue
            reg [127:0] h; integer t;
            h = 0; h[127:124] = 4'd6; h[123:118] = 6'd1; h[99:93] = 7'b0010001;
            t = 0; while (!ret[0] && t < 1000000) begin @(negedge clk); t = t + 1; end
            if (k > 0) repeat (gap) @(negedge clk);       // a slow CP: peers' flits of this gather may arrive first
            rec = {8'(rank), 21'd0, 21'(n_of[k]), 21'(n_of[k]), 256'd0, md(3'd0, 40'h200000 + OSTRIDE * k, 20'(n_of[k])),
                   md(3'd0, ABASE + OSTRIDE * k, 20'(n_of[k])), h, 1'b1};
            t_disp[k] = cyc; acc_k = acc_k + 1;
            @(negedge clk); rec[0] = 0; @(negedge clk);
        end
        begin : waitall integer t; t = 0; while (nret < nk && nflt == 0 && t < 2000000) begin @(negedge clk); t = t + 1; end end
        total = cyc - t0;
        repeat (600) @(negedge clk);    // nothing may arrive after the last retire
        if (nflt != 0 || flt) begin $display("ERR fault (record faults %0d, block fault %0d)", nflt, flt); errors = errors + 1; end
        if (nret != nk) begin $display("ERR retired %0d of %0d", nret, nk); errors = errors + 1; end
        // O check: every word of every gather exactly once with the owner's value; nothing else written
        begin : ocheck
            integer bad, cnt, q;
            bad = 0; cnt = 0;
            for (k = 0; k < nk; k = k + 1)
                for (integer w = 0; w < n_of[k]; w = w + 1) begin
                    integer a; a = (40'h200000 + OSTRIDE * k + w) % OSPACE;
                    q = 0; while (q + 1 < NR && slo(n_of[k], q + 1) <= w) q = q + 1;
                    cnt = cnt + 1;
                    if (oc[a] != 1 || om[a] !== val(k % NREC + (k / NREC) * 17, q, w)) begin
                        if (bad < 10) $display("ERR gather %0d word %0d (rank %0d): count %0d value %h want %h", k, w, q, oc[a], om[a],
                                               val(k % NREC + (k / NREC) * 17, q, w));
                        bad = bad + 1;
                    end
                    oc[a] = 0;
                end
            for (integer x = 0; x < OSPACE; x = x + 1) if (oc[x] != 0) begin
                if (bad < 10) $display("ERR stray delivery at %0d", x); bad = bad + 1; end
            errors = errors + bad;
            $display("checked %0d O words over %0d gathers, %0d delivery flits", cnt, nk, ndel);
        end
        for (k = 0; k < nk; k = k + 1)
            $display("REC %0d n %0d pf %0d disp %0d ret %0d service %0d", k, n_of[k], pf_of[k], t_disp[k] - t0,
                     (k < nret) ? t_ret[k] - t0 : -1, (k < nret) ? t_ret[k] - ((k > 0 && t_ret[k-1] > t_disp[k]) ? t_ret[k-1] : t_disp[k]) : -1);
        $display("SEQUENCE %0d gathers in %0d cycles (LAT %0d CRED %0d rank %0d)", nk, total, lat, cred, rank);
        if (errors == 0) $display("HGI_COLL_PIPE PASS"); else $display("HGI_COLL_PIPE FAIL errors=%0d", errors);
        $finish;
    end
endmodule
