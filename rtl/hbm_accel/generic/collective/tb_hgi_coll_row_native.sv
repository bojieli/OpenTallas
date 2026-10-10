`timescale 1ns/1ps
// Native G25 full-shape bench, derived from established tb_hgi_coll_bypass: the PSG endpoint's exact gather BYPASS (review 10:45 decision 1) at one
// rank of a group, the rest of the group and one foreign group modelled by a switch stub (the established single-rank
// method of tb_hbm_accel_tu_endpoint): every departure of the DUT's flit m releases flit m of every group peer and a
// foreign rank's flit (which must be dropped).  Payload words include -0, quiet / signalling NaNs with payloads,
// subnormals and infinities: every delivered word must be bit-identical, every gi in 0 .. G*pf-1 exactly once, the DUT
// must send each of its pf flits once (header {1, FF, rank, (rank - base) * pf + m}), retire with done_valid and no fault,
// then accept a second collective (REARM) with a different pf.
//   +GN=1|2|4|8|96 +RANK=r +PF=p +SEED=s   (GN = 96: mcast_all outer group)
module tb_hgi_coll_row_native;
    parameter integer MUT_MULTI = 0, MUT_TIE = 0, MUT_ORDER = 0;
    localparam integer NC = 8, NOG = 12, PFMAX = 512, STOREMAX=1024, LANES = 16, NPT = 8, INJ = 2, DEL = 4, RXAW = 8;
    localparam integer FW = 32 * LANES, PWT = FW + 33, NR = NOG * NC;
    integer gn, rank, pf, pf2, seed, base, lat, dupe, peer, die, amx = 0; reg [31:0] exp_tok;
    reg [FW-1:0] part [0:NR*STOREMAX-1];
    reg clk = 0, rst_n = 0, go = 0, done_ready = 0;
    always #0.4166665 clk = ~clk;
    reg [15:0] pf_in;
    wire [INJ*16-1:0] ii; wire [INJ-1:0] ir; reg [INJ*FW-1:0] idata;
    wire [NPT-1:0] txv, rxc; wire [NPT*PWT-1:0] txf;
    reg [NPT-1:0] crr = 0, rxv = 0; reg [NPT*PWT-1:0] rxf = 0;
    wire [DEL-1:0] dv; wire [DEL*PWT-1:0] dfl; wire flt, start_ready, done_valid; wire [31:0] cst;
    always @(ii or rank or load_row or rst_n) for (integer i = 0; i < INJ; i = i + 1) idata[FW*i +: FW] = part[rank * STOREMAX + integer'(ii[16*i +: 16])+integer'(load_row)*words];
    ot_hgi_coll_row_native #(.ENABLE(1),.MUT_ORDER(MUT_ORDER),.PFMAX(PFMAX),.NPT(NPT),.INJ(INJ),.DEL(DEL)) dut(
      .clk(clk),.rst_n(rst_n),.rank(8'(rank)),.group_size(8'(gn)),.destinations(8'(gn)),
      .slots(16'(pf/words)),.row_words(words),.load_v(load_v),.load_r(1'b1),.load_row(load_row),.load_rows(load_rows),.start(go),.ready(start_ready),.done(done_valid),
      .inj_idx(ii),.inj_rd(ir),.inj_data(idata),.ph_tx_v(txv),.ph_tx_flit(txf),.sw_cr_ret(crr),
      .ph_rx_v(rxv),.ph_rx_flit(rxf),.rx_credit(rxc),.out_v(mv),.out_data(md),.out_row(mr),.out_word(mw),
      .fault(flt),.stat_credit_stall(cst));
    assign dv=dut.dv;assign dfl=dut.df;

    wire [DEL-1:0] mv; wire [DEL*FW-1:0] md; wire [DEL*20-1:0] mr; wire [DEL*16-1:0] mw; wire map_done,map_fault;
    wire load_v;wire [15:0] load_row,load_rows;
    wire [15:0] epoch_pf=load_rows*words;
    reg [15:0] words=32; integer mapped=0; reg [15:0] nslots;
    assign map_fault=flt;
    always @(negedge clk) if(rst_n)begin
      if(map_fault)$fatal(1,"native map fault");
      for(integer l=0;l<DEL;l=l+1)if(mv[l])begin : check_native
        integer row_, word_, src_, slot_;
        row_=mr[l*20+:20];word_=mw[l*16+:16];src_=row_%gn+base;slot_=row_/gn;
        if(row_>=gn*(pf/words)||word_>=words||md[l*FW+:FW]!==part[src_*STOREMAX+slot_*words+word_])
          $fatal(1,"native slot-major payload mismatch row=%0d word=%0d",row_,word_);
        mapped=mapped+1;
      end
    end
    function automatic [31:0] special(input integer r);
        case (r % 9)
            0: special = 32'h80000000;   // -0
            1: special = 32'h7FC12345;   // qNaN payload
            2: special = 32'hFF812345;   // sNaN, negative, payload
            3: special = 32'h00000001;   // smallest subnormal
            4: special = 32'h807FFFFF;   // negative subnormal
            5: special = 32'h7F800000;   // +inf
            6: special = 32'hFF800000;   // -inf
            7: special = 32'h00000000;   // +0
            default: special = 32'h3F800000;
        endcase
    endfunction

    // ---- switch stub: per-port egress rings (flit, release cycle), egress / ingress credit rings -----------------
    localparam integer QD = 8192;
    reg [PWT-1:0] eqf [0:NPT*QD-1]; integer eqt [0:NPT*QD-1]; integer eh [0:NPT-1]; integer et [0:NPT-1];
    integer cin [0:NPT*QD-1]; integer ch [0:NPT-1]; integer ct [0:NPT-1];
    integer ceg [0:NPT*QD-1]; integer gh [0:NPT-1]; integer gt [0:NPT-1];
    integer eg_cred [0:NPT-1];
    integer cyc = 0, ndep = 0, nforeign = 0;
    always @(posedge clk) cyc <= cyc + 1;
    initial for (integer p = 0; p < NPT; p = p + 1) begin eg_cred[p] = 1 << RXAW; eh[p] = 0; et[p] = 0; ch[p] = 0; ct[p] = 0; gh[p] = 0; gt[p] = 0; end
    task automatic sched(input integer p, input integer t, input [PWT-1:0] f);
        begin
            if (et[p] - eh[p] >= QD) $fatal(1, "stub queue overflow");
            eqf[p*QD + et[p] % QD] = f; eqt[p*QD + et[p] % QD] = t; et[p] = et[p] + 1;
        end
    endtask
    always @(posedge clk) if (rst_n) begin
        for (integer p = 0; p < NPT; p = p + 1) if (txv[p]) begin : dep
            reg [PWT-1:0] f; integer gi, m, q, mm;
            f = txf[p*PWT +: PWT]; gi = integer'(f[FW +: 16]); m = gi - (rank - base) * integer'(epoch_pf);
            ndep = ndep + 1;
            if (f[PWT-1] !== 1'b1 || f[FW+24 +: 8] !== 8'hFF || integer'(f[FW+16 +: 8]) != rank || m < 0 || m >= epoch_pf ||
                f[FW-1:0] !== part[rank * STOREMAX + integer'(load_row)*words + m])
                $fatal(1, "BYP_TX bad departure gi=%0d m=%0d src=%0d", gi, m, f[FW+16 +: 8]);
            cin[p*QD + ct[p] % QD] = cyc + 6; ct[p] = ct[p] + 1;
            for (q = base; q < base + gn; q = q + 1) if (q != rank)
                begin mm = (dupe != 0 && m == 1 && q == peer) ? 0 : m;
                sched((q + m) % NPT, cyc + lat + (q % 5), {1'b1, 8'hFF, 8'(q), 16'((q - base) * epoch_pf + mm), part[q * STOREMAX + integer'(load_row)*words + mm]}); end
            if (gn < NR) begin   // a foreign group's flit on the same fabric: must be dropped
                q = (base + gn) % NR;
                sched((q + m) % NPT, cyc + lat, {1'b1, 8'hFF, 8'(q), 16'(m), ~part[q * STOREMAX + integer'(load_row)*words + m]}); nforeign = nforeign + 1;
            end
        end
        for (integer p = 0; p < NPT; p = p + 1) begin
            while (gt[p] > gh[p] && ceg[p*QD + gh[p] % QD] <= cyc) begin gh[p] = gh[p] + 1; eg_cred[p] = eg_cred[p] + 1; end
            rxv[p] <= 1'b0;
            if (et[p] > eh[p] && eqt[p*QD + eh[p] % QD] <= cyc && eg_cred[p] > 0) begin
                rxv[p] <= 1'b1; rxf[p*PWT +: PWT] <= eqf[p*QD + eh[p] % QD];
                eh[p] = eh[p] + 1; eg_cred[p] = eg_cred[p] - 1;
            end
            if (rxc[p]) begin ceg[p*QD + gt[p] % QD] = cyc + 5; gt[p] = gt[p] + 1; end
            crr[p] <= 1'b0;
            if (ct[p] > ch[p] && cin[p*QD + ch[p] % QD] <= cyc) begin ch[p] = ch[p] + 1; crr[p] <= 1'b1; end
        end
    end

    // ---- delivery checker ------------------------------------------------------------------------------------
    reg seen [0:NR*STOREMAX-1];
    integer got = 0, mism = 0;
    always @(posedge clk) if (rst_n) for (integer l = 0; l < DEL; l = l + 1) if (dv[l]) begin : chk
        reg [PWT-1:0] f; integer gi, q, m;
        f = dfl[l*PWT +: PWT]; q=integer'(f[FW+16+:8]); m=integer'(f[FW+:16])-(q-base)*integer'(epoch_pf);
        gi=(q-base)*pf+integer'(load_row)*words+m;
        if (amx != 0) begin
            if (gi != 0 || f[FW-1:0] !== {{(FW-32){1'b0}}, exp_tok}) begin mism = mism + 1; $display("AMX_MISMATCH tok=%0d want=%0d", f[31:0], exp_tok); end
            got = got + 1;
        end else begin
        if (gi >= gn * pf || seen[gi] || integer'(f[FW+16 +: 8]) != q || f[FW-1:0] !== part[q * STOREMAX + integer'(load_row)*words + m]) begin
            mism = mism + 1; if (mism < 8) $display("BYP_MISMATCH gi=%0d src=%0d q=%0d", gi, f[FW+16 +: 8], q);
        end
        if (gi < NR * STOREMAX) seen[gi] = 1;
        got = got + 1;
        end
    end

    // ARGMAX_MERGE reference (independent of the RTL: real compares, NaN by bit pattern): larger value, NaN last,
    // equal values (or two NaNs) -> the lower id
    function automatic isnan(input [31:0] v); isnan = v[30:23] == 8'hFF && v[22:0] != 0; endfunction
    // FP32 bits -> real (normals, zeros, infinities: the values this bench uses)
    function automatic real f2r(input [31:0] v);
        reg [63:0] d;
        begin
            if (v[30:0] == 0) d = {v[31], 63'd0};
            else if (v[30:23] == 8'hFF) d = {v[31], 11'h7FF, 52'd0};
            else d = {v[31], 11'(v[30:23]) + 11'd896, v[22:0], 29'd0};
            f2r = $bitstoreal(d);
        end
    endfunction
    function automatic [31:0] amx_ref(input integer b, input integer n);
        reg [31:0] bv, bi, v, i; reg take;
        begin
            bv = part[b * STOREMAX][31:0]; bi = part[b * STOREMAX][63:32];
            for (integer q = b + 1; q < b + n; q = q + 1) begin
                v = part[q * STOREMAX][31:0]; i = part[q * STOREMAX][63:32];
                if (isnan(v) != isnan(bv)) take = isnan(bv);
                else if (isnan(v)) take = i < bi;
                else if (f2r(v) > f2r(bv)) take = 1;
                else if (f2r(v) == f2r(bv)) take = i < bi;
                else take = 0;
                if (take) begin bv = v; bi = i; end
            end
            amx_ref = bi;
        end
    endfunction
    task run(input integer p_);
        integer t;
        begin
            pf = p_; mapped=0; got = 0; ndep = 0; for (integer i = 0; i < NR * STOREMAX; i = i + 1) seen[i] = 0;
            @(negedge clk); while (!start_ready) @(negedge clk);
            pf_in = 16'(pf); go = 1; @(negedge clk); go = 0;
            t = 0; while (!done_valid && !flt && t < 200000) begin @(negedge clk); t = t + 1; end
            if (dupe) begin   // a peer's duplicate flit (its flit 0 twice, flit 1 never): the endpoint must fault, not retire
                if (flt && !done_valid) begin $display("PASS HGI_COLL_BYPASS_DUPE fault=1 gn=%0d rank=%0d pf=%0d", gn, rank, pf); $finish; end
                $fatal(1, "BYP_DUPE_NOT_DETECTED done=%0d fault=%0d got=%0d", done_valid, flt, got);
            end
            if (flt) $fatal(1, "BYP_FAULT gn=%0d rank=%0d pf=%0d got=%0d", gn, rank, pf, got);
            if (!done_valid) $fatal(1, "BYP_NO_DONE gn=%0d rank=%0d pf=%0d got=%0d of %0d ndep=%0d", gn, rank, pf, got, gn * pf, ndep);
            repeat (30) @(negedge clk);   // nothing may arrive after done
            if (amx != 0) begin
                if (got != 1 || mism != 0 || ndep != 1) $fatal(1, "AMX_COUNT got=%0d mism=%0d ndep=%0d", got, mism, ndep);
                $display("PASS HGI_COLL_ARGMAX_MERGE gn=%0d rank=%0d token=%0d", gn, rank, exp_tok); $finish;
            end
            if (mapped != gn*pf || got != gn * pf || mism != 0 || ndep != pf)
                $fatal(1, "BYP_COUNT got=%0d want=%0d mism=%0d ndep=%0d", got, gn * pf, mism, ndep);
            $display("BYP_RUN gn=%0d rank=%0d base=%0d pf=%0d delivered=%0d cycles=%0d", gn, rank, base, pf, got, t);
            @(negedge clk);
        end
    endtask

    initial begin
        if (!$value$plusargs("GN=%d", gn)) gn = 8;
        if (!$value$plusargs("RANK=%d", rank)) rank = 3;
        if (!$value$plusargs("DIE=%d", die)) die = rank; else rank = die % 96;   // record mode: die id; endpoint rank = die mod 96
        if (!$value$plusargs("PF=%d", pf2)) pf2 = 576;
        if (!$value$plusargs("WORDS=%d", words)) words=32;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("LAT=%d", lat)) lat = 40;
        if (!$value$plusargs("DUPE=%d", dupe)) dupe = 0;
        base = (gn == 96) ? 0 : (rank / gn) * gn;
        peer = (rank == base) ? base + 1 : base;
        for (integer i = 0; i < NR * STOREMAX; i = i + 1)
            for (integer w = 0; w < LANES; w = w + 1)
                part[i][32*w +: 32] = ((i + w) % 3 == 0) ? special(i * 7 + w + seed) : $random(seed);
        if (amx != 0) begin   // one flit a rank: {value, id}; ties, -0 / +0, NaNs, infinities; ids NOT in rank order
            for (integer q = 0; q < NR; q = q + 1) begin
                part[q * STOREMAX] = 0;
                case ((q + seed) % 7)
                    0, 1: part[q * STOREMAX][31:0] = 32'h40A00000;   // 5.0 (tie)
                    2: part[q * STOREMAX][31:0] = 32'h7FC00001;      // NaN
                    3: part[q * STOREMAX][31:0] = 32'h80000000;      // -0
                    4: part[q * STOREMAX][31:0] = 32'h00000000;      // +0
                    5: part[q * STOREMAX][31:0] = (seed % 2) ? 32'h7F800000 : 32'h3F800000;   // +inf or 1.0
                    default: part[q * STOREMAX][31:0] = 32'hFF800000; // -inf
                endcase
                part[q * STOREMAX][63:32] = (NR - q) * 1000 + 7;
            end
            pf2 = 1;
            exp_tok = amx_ref(base, gn);
        end
        pf_in = 0;
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        run(pf2);
        run((pf2 > words) ? pf2 - words : pf2);
        $display("PASS HGI_COLL_ROW_NATIVE gn=%0d rank=%0d pf=%0d,%0d foreign_dropped=%0d fault=%0d", gn, rank, pf2,
                 (pf2 > words) ? pf2 - words : pf2, nforeign, flt);
        $finish;
    end
endmodule
