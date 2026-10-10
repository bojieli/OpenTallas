`timescale 1ns/1ps
// qwen-vm-me 2026-10-08: every port of the banked vector memory ot_qfd_sp_vector_memory_bv at once, against the token
// bench's behavioural VM semantics (rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream4.sv `vm`), plus the ME
// result path (6 x ot_qfd_res_ser -> the merge inside the memory) under the engine stall loop.
//   reference   one array; at every edge the SU operand reads presented before the edge read the array first, then the
//               writes presented before the edge (SU lane rows, reducer element, sequencer row, the engine-edge maxima
//               row) apply -- the base's registered-read / same-edge-write order.  Result bursts apply in burst order
//               (band 0 slots 0..7, band 1 ...) at their engine edge.
//   regions     x tuples / row reads [0, X) (static, X = XRN); reducer [X, X+1K); sequencer rows [X+1K, X+2K); maxima
//               [X+2K, X+3K); results [X+3K, X+8K) (rows repeat across bursts: order matters); SU reads and writes [X+8K, ELEMS) with reads
//               and writes running past ELEMS (zeros / dropped).  Every source except the results shares banks with
//               every other, so the skid queues and the merge's waits are exercised; no source reads a row another
//               source writes, so w_hazard must stay 0 (the contract).
//   engine      me_en = random 7/8 AND the band serializers' rok through the memory's me_ok and RSD more edges (the
//               stall loop RS = RSD + 2); bursts on random engine edges, random slot masks, some bands empty.
//   checked     every SU operand answer (all lanes, 1 + VL edges after the strobe); every x seat every cycle; every row
//               read; at every land_cnt step n: every result row whose last writer among the bursts so far is < n holds
//               the reference value (progress soundness); the final image of every region; no x_fault / x_hazard /
//               w_fault / w_hazard / serializer fault; bursts landed == bursts generated.
// MUT = 1: the memory's SU lane select is one lane off; SMUT = 1: a serializer swaps a slot's mask.  Both must FAIL.
module tb_qfd_vm_bv_ports;
    parameter integer ELEMS = 16384, NRB = 16, SMIN = 3, SMAX = 7, XVM = 12, BMAX = 4, SW = 8, VL = 7;
    parameter integer DB = 16, RSD = 4, CRB = 4, MUT = 0, SMUT = 0, TSR = 0, CYCLES = 30000, SEED = 5, XRN = 4096;
    parameter integer ND = 9;
    parameter [ND*8-1:0] DSET = {8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0};
    localparam integer AW = 24, RW = 20, NX = 1 << SMAX, BEAT = (NRB - 1) * 16, NB = 6, NS = 8;
    localparam integer XR0 = 0, RD0 = XRN, SQ0 = XRN + 1024, MX0 = XRN + 2048, RS0 = XRN + 3072, RSN = 5120, SU0 = XRN + 8192;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer seed;
    // ---- DUT inputs ----
    reg me_want, x_dv, w_v, r_v, rd_v, mx_we;
    wire me_en;
    reg [AW-1:0] x_dc, x_dcs, rd_addr, mx_addr;
    reg [3:0] x_dsp;
    reg [AW-5:0] w_row, r_row;
    reg [15:0] w_mask, mx_mask;
    reg [511:0] w_data, mx_data;
    reg [31:0] rd_data;
    reg [2:0] s_re0, s_re1;
    reg [3*AW-1:0] s_a0, s_a1;
    reg [SW-1:0] sw_mask;
    reg [AW-1:0] sw_a0, sw_a1;
    reg [SW*32-1:0] sw_data;
    wire [3*SW*32-1:0] s_q;
    wire [NX*32-1:0] d_xq;
    wire r_rdy, r_qv, x_fault, x_hazard, w_fault, w_hazard, me_ok;
    wire [511:0] r_q;
    wire [15:0] land_cnt;
    // band serializers
    reg  b_ov;
    reg  [NB*NS-1:0] b_we;
    reg  [NB*NS*AW-1:0] b_addr;
    reg  [NB*NS*16-1:0] b_mask;
    reg  [NB*NS*512-1:0] b_data;
    wire [NB-1:0] l_v, l_end, l_nul, l_cr, l_ok, l_fault;
    wire [NB*RW-1:0] l_row;
    wire [NB*16-1:0] l_mask;
    wire [NB*512-1:0] l_data;
    genvar gb;
    generate for (gb = 0; gb < NB; gb = gb + 1) begin : g_ser
        ot_qfd_res_ser #(.NS(NS), .W(16), .AW(AW), .RW(RW), .DB(DB), .RS(RSD + 2), .CRB(CRB), .MUT(gb == 2 ? SMUT : 0), .TSR(TSR)) u_s (
            .clk(clk), .rst_n(rst_n), .me_en(me_en), .i_ov(b_ov), .i_we(b_we[gb*NS +: NS]),
            .i_addr(b_addr[gb*NS*AW +: NS*AW]), .i_mask(b_mask[gb*NS*16 +: NS*16]), .i_data(b_data[gb*NS*512 +: NS*512]),
            .o_v(l_v[gb]), .o_end(l_end[gb]), .o_nul(l_nul[gb]), .o_row(l_row[gb*RW +: RW]), .o_mask(l_mask[gb*16 +: 16]),
            .o_data(l_data[gb*512 +: 512]), .o_cr(l_cr[gb]), .rok(l_ok[gb]), .fault(l_fault[gb]));
    end endgenerate
    ot_qfd_sp_vector_memory_bv #(.ELEMS(ELEMS), .NRB(NRB), .AW(AW), .SMIN(SMIN), .SMAX(SMAX), .XVM(XVM), .BMAX(BMAX),
        .ND(ND), .DSET(DSET), .SW(SW), .NSU(3), .NB(NB), .CRB(CRB), .MUT(MUT)) dut (
        .clk(clk), .rst_n(rst_n), .me_en(me_en), .x_dv(x_dv), .x_dc(x_dc), .x_dcs(x_dcs), .x_dsp(x_dsp), .x_q(d_xq),
        .x_rdy(), .x_fault(x_fault), .x_hazard(x_hazard),
        .s_re0(s_re0), .s_re1(s_re1), .s_a0(s_a0), .s_a1(s_a1), .s_q(s_q),
        .sw_mask(sw_mask), .sw_a0(sw_a0), .sw_a1(sw_a1), .sw_data(sw_data),
        .rd_v(rd_v), .rd_addr(rd_addr), .rd_data(rd_data),
        .w_v(w_v), .w_row(w_row), .w_mask(w_mask), .w_data(w_data),
        .r_v(r_v), .r_rdy(r_rdy), .r_row(r_row), .r_qv(r_qv), .r_q(r_q),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
        .rb_v(l_v), .rb_end(l_end), .rb_nul(l_nul), .rb_row(l_row), .rb_mask(l_mask), .rb_data(l_data), .rb_cr(l_cr),
        .rb_ok(l_ok), .me_ok(me_ok), .land_cnt(land_cnt), .w_fault(w_fault), .w_hazard(w_hazard));
    // ---- the stall loop: me_ok RSD more edges to the engine clock enable ----
    reg [RSD:0] okd;
    always @(posedge clk or negedge rst_n) if (!rst_n) okd <= 0; else okd <= {okd[RSD-1:0], me_ok};
    reg started_e;
    assign me_en = me_want && (okd[RSD-1] || !started_e);
    // ---- reference memory ----
    reg [31:0] vm [0:ELEMS-1];
    function [31:0] rv(input integer a); rv = (a < ELEMS && a >= 0) ? vm[a] : 32'd0; endfunction
    // x reference (as tb_qfd_vector_memory)
    wire [NX-1:0] vx_re;
    wire [NX*AW-1:0] vx_addr;
    ot_qfd_vm_xroot #(.AW(AW), .GT(NX * 4), .TG(4), .SMAX(SMAX), .XVM(XVM)) u_xr (.clk(clk), .rst_n(rst_n),
        .x_dv(x_dv), .x_dc(x_dc), .x_dcs(x_dcs), .x_dsp(x_dsp), .x_re(vx_re), .x_addr(vx_addr), .x_q({NX*32{1'b0}}), .xl0());
    reg [NX*32-1:0] xp_q [0:XVM-1];
    reg [NX-1:0]    xp_v [0:XVM-1];
    reg [NX*32-1:0] r_xq;
    // SU answers expected (VL + 1 edges later)
    reg [3*SW*32-1:0] sexp [0:VL];
    reg [2:0]         sev [0:VL];
    // result bookkeeping
    integer nburst, lastw [0:RSN/16-1];
    reg [511:0] rexp [0:63]; reg [5:0] rw_p, rr_p;
    integer vi, xs, l, o, q, e, s;
    integer bad_x, bad_s, bad_r, bad_land, bad_img, n_s, n_r, n_land, tuples, cyc, started;
    always @(posedge clk) if (rst_n) begin : refm
        reg [31:0] a; reg [NX*32-1:0] rq; reg [3*SW*32-1:0] sq; integer si, hl;
        // reads first
        if (me_en) begin
            rq = 0;
            for (vi = 0; vi < NX; vi = vi + 1)
                if (vx_re[vi]) begin a = vx_addr[vi*AW +: AW]; rq[vi*32 +: 32] = rv(a); end
            for (vi = 0; vi < NX; vi = vi + 1) if (xp_v[XVM-1][vi]) r_xq[vi*32 +: 32] <= xp_q[XVM-1][vi*32 +: 32];
            for (xs = XVM - 1; xs > 0; xs = xs - 1) begin xp_q[xs] <= xp_q[xs-1]; xp_v[xs] <= xp_v[xs-1]; end
            xp_q[0] <= rq; xp_v[0] <= vx_re;
        end
        sq = 0;
        for (o = 0; o < 3; o = o + 1) begin
            si = (s_re1[o] && (s_a1[o*AW +: AW] - s_a0[o*AW +: AW]) == 1) ? 1 : 0;
            for (l = 0; l < SW; l = l + 1) sq[(o*SW + l)*32 +: 32] = rv(s_a0[o*AW +: AW] + l * si);
        end
        for (e = VL; e > 0; e = e - 1) begin sexp[e] <= sexp[e-1]; sev[e] <= sev[e-1]; end
        sexp[0] <= sq; sev[0] <= s_re0;
        if (r_v && r_rdy) begin
            for (l = 0; l < 16; l = l + 1) rexp[rw_p][32*l +: 32] <= rv({r_row, 4'h0} + l);
            rw_p <= rw_p + 1'b1;
        end
        // then writes, in the base's commit order: results (engine edge), maxima, SU lanes, reducer, sequencer
        if (me_en && b_ov) begin
            for (q = 0; q < NB; q = q + 1)
                for (s = 0; s < NS; s = s + 1)
                    if (b_we[q*NS + s])
                        for (l = 0; l < 16; l = l + 1)
                            if (b_mask[(q*NS + s)*16 + l] && {b_addr[(q*NS + s)*AW +: RW], 4'h0} + l < ELEMS)
                                vm[{b_addr[(q*NS + s)*AW +: RW], 4'h0} + l] = b_data[(q*NS + s)*512 + 32*l +: 32];
            for (q = 0; q < NB; q = q + 1)
                for (s = 0; s < NS; s = s + 1)
                    if (b_we[q*NS + s]) lastw[b_addr[(q*NS + s)*AW +: RW] - RS0 / 16] = nburst;
            nburst = nburst + 1;
        end
        if (me_en && mx_we)
            for (l = 0; l < 16; l = l + 1) if (mx_mask[l]) vm[{mx_addr[RW-1:0], 4'h0} + l] = mx_data[32*l +: 32];
        if (|sw_mask) begin
            si = (sw_mask[1] && sw_a1 - sw_a0 == 1) ? 1 : 0;
            if (si == 1) begin
                for (l = 0; l < SW; l = l + 1) if (sw_mask[l] && sw_a0 + l < ELEMS) vm[sw_a0 + l] = sw_data[32*l +: 32];
            end else begin
                hl = 0; for (l = 0; l < SW; l = l + 1) if (sw_mask[l]) hl = l;
                if (sw_a0 < ELEMS) vm[sw_a0] = sw_data[32*hl +: 32];
            end
        end
        if (rd_v) vm[rd_addr] = rd_data;
        if (w_v) for (l = 0; l < 16; l = l + 1) if (w_mask[l] && {w_row, 4'h0} + l < ELEMS) vm[{w_row, 4'h0} + l] = w_data[32*l +: 32];
    end
    // ---- checks ----
    always @(posedge clk) if (rst_n) begin
        if (r_qv) begin
            if (r_q !== rexp[rr_p]) bad_r = bad_r + 1;
            rr_p <= rr_p + 1'b1; n_r = n_r + 1;
        end
    end
    // DUT image: a shadow of the per-bank write registers (every copy's macros take exactly these writes)
    localparam integer LAWT = $clog2((ELEMS / 16 + NRB - 1) / NRB);
    reg [511:0] shadow [0:ELEMS/16-1];
    integer sb, sl, srow_;
    always @(posedge clk) if (rst_n)
        for (sb = 0; sb < NRB; sb = sb + 1) if (dut.bw_we[sb]) begin
            srow_ = dut.bw_line[sb*LAWT +: LAWT] * NRB + sb;
            for (sl = 0; sl < 16; sl = sl + 1) if (dut.bw_mask[sb*16 + sl]) shadow[srow_][32*sl +: 32] <= dut.bw_data[sb*512 + 32*sl +: 32];
        end
    // diagnostics: the first hazard term that fires
    reg hz_seen = 0;
    integer hk2;
    always @(posedge clk) if (rst_n && !hz_seen && (dut.hz0 || (|dut.su_hz) || dut.waw)) begin
        hz_seen <= 1;
        $display("w_hazard term at %0t: hz0 %0d su_hz %b waw %0d lt_v %b", $time, dut.hz0, dut.su_hz, dut.waw, dut.lt_v);
        for (hk2 = 0; hk2 < 9; hk2 = hk2 + 1) if (dut.lt_v[hk2]) $display("  late row %0d: %0d", hk2, dut.lt_row[hk2*RW +: RW]);
    end
    reg [15:0] land_seen;
    // ---- stimulus ----
    function integer dset(input integer i); dset = DSET[i*8 +: 8]; endfunction
    integer hold, s_, d, b, span, since, i, k, r_, pend;
    reg [AW-1:0] base;
    reg eng_prev, en_edge;
    always @(posedge clk) en_edge <= me_en;     // the enable the last edge used
    task new_burst;
        integer qq, ss, rr, used [0:NB*NS-1];
        begin
            b_ov = 1; b_we = 0;
            for (qq = 0; qq < NB; qq = qq + 1) begin
                if (($random(seed) & 3) != 0)
                    for (ss = 0; ss < NS; ss = ss + 1) b_we[qq*NS + ss] = $random(seed) & 1;
            end
            for (qq = 0; qq < NB * NS; qq = qq + 1) begin
                // a row unique within the burst: slot-indexed band of rows (8 x 6 = 48 of the region's 320), randomly shifted
                rr = (qq + 48 * (($random(seed) & 32'h7fffffff) % (RSN / 16 / 48))) % (RSN / 16);
                b_addr[qq*AW +: AW] = RS0 / 16 + rr;
                b_mask[qq*16 +: 16] = $random(seed);
                for (ss = 0; ss < 16; ss = ss + 1) b_data[qq*512 + 32*ss +: 32] = $random(seed);
            end
        end
    endtask
    initial begin
        seed = SEED; bad_x = 0; bad_s = 0; bad_r = 0; bad_land = 0; bad_img = 0; n_s = 0; n_r = 0; n_land = 0; tuples = 0;
        started = -1; nburst = 0; land_seen = 0; rw_p = 0; rr_p = 0; started_e = 0;
        for (i = 0; i < ELEMS; i = i + 1) vm[i] = 0;
        for (i = 0; i < ELEMS / 16; i = i + 1) shadow[i] = 0;
        for (i = 0; i < RSN / 16; i = i + 1) lastw[i] = -1;
        for (i = 0; i < XVM; i = i + 1) begin xp_v[i] = 0; xp_q[i] = 0; end
        for (i = 0; i <= VL; i = i + 1) begin sev[i] = 0; sexp[i] = 0; end
        r_xq = 0;
        me_want = 1; x_dv = 0; x_dc = 0; x_dcs = 1; x_dsp = SMIN; w_v = 0; r_v = 0; w_row = 0; r_row = 0; w_mask = 0;
        w_data = 0; rd_v = 0; rd_addr = RD0; rd_data = 0; mx_we = 0; mx_addr = MX0 / 16; mx_mask = 0; mx_data = 0;
        s_re0 = 0; s_re1 = 0; s_a0 = 0; s_a1 = 0; sw_mask = 0; sw_a0 = 0; sw_a1 = 0; sw_data = 0;
        b_ov = 0; b_we = 0; b_addr = 0; b_mask = 0; b_data = 0;
        hold = 0; since = 100; pend = 0; eng_prev = 0;
        repeat (4) @(negedge clk); rst_n = 1;
        // preload everything through the sequencer row-write port (the reference takes the same writes)
        for (i = 0; i < ELEMS / 16; i = i + 1) begin
            @(negedge clk); w_v = 1; w_row = i; w_mask = 16'hffff;
            for (l = 0; l < 16; l = l + 1) w_data[32*l +: 32] = $random(seed);
        end
        @(negedge clk); w_v = 0;
        repeat (20) @(negedge clk);
        started_e = 1;
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            // ---- compare outputs of the last edge ----
            if (started >= 0 && cyc > started && d_xq !== r_xq) bad_x = bad_x + 1;
            for (o = 0; o < 3; o = o + 1) if (sev[VL][o]) begin
                n_s = n_s + 1;
                if (s_q[o*SW*32 +: SW*32] !== sexp[VL][o*SW*32 +: SW*32]) bad_s = bad_s + 1;
            end
            if (land_cnt != land_seen) begin
                // progress soundness: rows whose last writer so far is < land_cnt are in the memory
                for (r_ = 0; r_ < RSN / 16; r_ = r_ + 1)
                    if (lastw[r_] >= 0 && lastw[r_] < land_cnt) begin
                        for (l = 0; l < 16; l = l + 1)
                            if (shadow[RS0 / 16 + r_][32*l +: 32] !== vm[RS0 + r_ * 16 + l])
                                bad_land = bad_land + 1;
                    end
                land_seen = land_cnt; n_land = n_land + 1;
            end
            // ---- engine: its registers (burst, maxima, x descriptor) change only after an engine edge ----
            eng_prev = en_edge;
            me_want = ($random(seed) & 7) != 0;
            if (eng_prev) begin
                b_ov = 0; b_we = 0; mx_we = 0;
                if (($random(seed) & 3) == 0) new_burst;
                if (($random(seed) & 15) == 0) begin
                    mx_we = 1; mx_addr = MX0 / 16 + (($random(seed) & 32'h7fffffff) % 64); mx_mask = $random(seed);
                    for (l = 0; l < 16; l = l + 1) mx_data[32*l +: 32] = $random(seed);
                end
                // x tuples over the static region
                if (hold > 0) hold = hold - 1;
                since = since + 1;
                if (hold == 0) begin
                    if (($random(seed) & 15) == 0) begin x_dv = 0; hold = 1; end
                    else begin
                        s_ = SMIN + (($random(seed) & 32'h7fffffff) % (SMAX - SMIN + 1));
                        if (($random(seed) & 3) == 0) d = 1;
                        else begin
                            d = dset(($random(seed) & 32'h7fffffff) % ND);
                            while (((1 << s_) - 1) * d >= BMAX * BEAT) d = dset(($random(seed) & 32'h7fffffff) % 5);
                        end
                        span = ((1 << s_) - 1) * d;
                        b = span / BEAT + 1;
                        if (since >= b) begin
                            base = XR0 + (($random(seed) & 32'h7fffffff) % (XRN - span - 1));
                            x_dv = 1; x_dc = base; x_dcs = d; x_dsp = s_; since = 0;
                            hold = b + (($random(seed) & 3) == 0 ? ($random(seed) & 7) : 0);
                            tuples = tuples + 1;
                            if (started < 0) started = cyc + XVM + 3;
                        end else x_dv = 0;
                    end
                end
            end
            // ---- free-running ports (every cycle) ----
            s_re0 = 0; s_re1 = 0;
            for (o = 0; o < 3; o = o + 1) if (($random(seed) & 1) == 0) begin
                s_re0[o] = 1; s_re1[o] = $random(seed) & 1;
                k = SU0 + (($random(seed) & 32'h7fffffff) % (ELEMS - SU0 + 24));
                s_a0[o*AW +: AW] = k; s_a1[o*AW +: AW] = k + (($random(seed) & 3) != 0 ? 1 : 0);
            end
            sw_mask = 0;
            if (($random(seed) & 1) == 0) begin
                sw_mask = $random(seed); if (sw_mask == 0) sw_mask = 1;
                k = SU0 + (($random(seed) & 32'h7fffffff) % (ELEMS - SU0 + 8));
                sw_a0 = k; sw_a1 = k + (($random(seed) & 7) != 0 ? 1 : 0);
                for (l = 0; l < SW; l = l + 1) sw_data[32*l +: 32] = $random(seed);
            end
            rd_v = ($random(seed) & 15) == 0; rd_addr = RD0 + (($random(seed) & 32'h7fffffff) % 1024); rd_data = $random(seed);
            w_v = ($random(seed) & 15) == 0; w_row = (SQ0 / 16) + (($random(seed) & 32'h7fffffff) % 64); w_mask = $random(seed);
            for (l = 0; l < 16; l = l + 1) w_data[32*l +: 32] = $random(seed);
            r_v = ($random(seed) & 3) == 0; r_row = (XR0 / 16) + (($random(seed) & 32'h7fffffff) % (XRN / 16));
        end
        // drain: no new traffic, the engine runs until every burst landed
        b_ov = 0; b_we = 0; mx_we = 0; x_dv = 0; s_re0 = 0; sw_mask = 0; rd_v = 0; w_v = 0; r_v = 0; me_want = 1;
        for (i = 0; i < 20000 && land_cnt != nburst[15:0]; i = i + 1) @(negedge clk);
        repeat (40) @(negedge clk);
        for (i = 0; i < ELEMS; i = i + 1)
            if (shadow[i / 16][32*(i % 16) +: 32] !== vm[i]) bad_img = bad_img + 1;
        if (bad_x == 0 && bad_s == 0 && bad_r == 0 && bad_land == 0 && bad_img == 0 && !x_fault && !x_hazard && !w_fault &&
            !w_hazard && !(|l_fault) && land_cnt == nburst[15:0] && nburst > 500 && n_s > 1000 && n_r > 1000 && tuples > 500)
            $display("PASS qfd_vm_bv_ports NRB=%0d SW=%0d VL=%0d su_reads=%0d row_reads=%0d tuples=%0d bursts=%0d land_steps=%0d cycles=%0d",
                     NRB, SW, VL, n_s, n_r, tuples, nburst, n_land, CYCLES);
        else
            $display("FAIL qfd_vm_bv_ports x=%0d su=%0d row=%0d land=%0d image=%0d faults x%0d xh%0d w%0d wh%0d ser%b landed=%0d/%0d su_reads=%0d",
                     bad_x, bad_s, bad_r, bad_land, bad_img, x_fault, x_hazard, w_fault, w_hazard, l_fault, land_cnt, nburst, n_s);
        $finish;
    end
endmodule
