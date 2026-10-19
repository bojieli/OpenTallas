`timescale 1ns/1ps
`default_nettype none
// HBM-NEXT-UNITS-VM 2026-10-19: hnx 2^19-word VM bank (hnx_vms_bank_q0_faces: A0 + A1 + B + C, 17-bit sector) vs the d4g
// SE/NE die master hfd_vms_bank_native_q0_faces (A + B + C, 16-bit sector).  Real SRAM models (asap7_memory_macros_v2).
//  Phase A (lockstep, NA random cycles, NB banks): both banks get the SAME schedule (random read owner 0..5 / write owner
//    0..6 every cycle, random sectors in the lower 2^18 region + mirror, partial masks, mirror wide-write egress); the hnx
//    records carry the 17-bit form of the same address (row[10] = 0).  Every output (rr0..4, pr, *_done, status) must be
//    bit-identical every edge; eg must equal the d4g eg with the row widened by one 0 bit.
//  Phase B (upper half, hnx alone, scoreboard): every one of the 2,048 quadrant rows (A0 + A1) and 1,024 mirror rows of each
//    bank is written back-to-back (1 W/cycle; all 7 write sources), then 512 partial-mask rewrites, then every row is read
//    back-to-back (1 R/cycle; all 6 read owners).  Each response must equal the model, at one constant latency, with
//    status == 0 (no CE / UE / FAULT).  A0 row r, A1 row r and mirror row r hold different data, so any alias fails.
//  Phase C: a mirror sector with row[10] = 1 (outside the 1,024-row mirror) must raise the sticky FAULT.
// MUT 5 (A1 read select dropped), 6 (sector wrap: row[10] decoded as 0), 7 (A1 check field not written) must FAIL.
module tb_hnx_vm_bank;
    parameter integer MUT = 0;
    parameter integer SEED = 1;
    parameter integer NA = 4000;
    localparam integer NB = 2, SID = 1, RG = 5, WG = 2;
    function automatic integer bidof(input integer b); bidof = (b == 0) ? 2 : 5; endfunction
    reg clk = 0; always #5 clk = ~clk;
    reg rst_n = 0;
    // ------------------------------------------------------------ logical (hnx-native) stimulus per bank
    reg rv [NB]; integer ro [NB]; reg [16:0] rs [NB]; reg [11:0] rrow [NB]; reg [7:0] rtag [NB];
    reg wv [NB]; integer wo [NB]; reg [16:0] ws [NB]; reg [11:0] wrow [NB]; reg [255:0] wd [NB]; reg [7:0] wm [NB]; reg [7:0] wtag [NB];
    function automatic [15:0] s16(input [16:0] s); s16 = {s[16], s[15:14], s[12:3], s[2:0]}; endfunction
    function automatic [10:0] r11(input [11:0] r); r11 = {r[11], r[9:0]}; endfunction
    reg [16:0]  f_rq [NB][RG]; reg [280:0] f_wq [NB][WG]; reg [280:0] f_dq [NB], f_kq [NB]; reg [275:0] f_xq [NB], f_x2 [NB]; reg [284:0] f_pq [NB];
    reg [17:0]  h_rq [NB][RG]; reg [281:0] h_wq [NB][WG]; reg [281:0] h_dq [NB], h_kq [NB]; reg [276:0] h_xq [NB], h_x2 [NB]; reg [285:0] h_pq [NB];
    reg rslot_v [NB]; reg [2:0] rslot [NB]; reg wslot_v [NB]; reg [2:0] wslot [NB];
    always @* begin
        for (integer b = 0; b < NB; b = b + 1) begin
            for (integer g = 0; g < RG; g = g + 1) begin f_rq[b][g] = '0; h_rq[b][g] = '0; end
            for (integer g = 0; g < WG; g = g + 1) begin f_wq[b][g] = '0; h_wq[b][g] = '0; end
            f_dq[b] = '0; h_dq[b] = '0; f_kq[b] = '0; h_kq[b] = '0; f_xq[b] = '0; h_xq[b] = '0;
            f_x2[b] = '0; h_x2[b] = '0; f_pq[b] = '0; h_pq[b] = '0;
            rslot_v[b] = rv[b]; rslot[b] = 3'(ro[b]); wslot_v[b] = wv[b]; wslot[b] = 3'(wo[b]);
            if (rv[b]) begin
                if (ro[b] < RG) begin f_rq[b][ro[b]] = {1'b1, s16(rs[b])}; h_rq[b][ro[b]] = {1'b1, rs[b]}; end
                else begin
                    f_pq[b] = {1'b1, 1'b0, r11(rrow[b]), 256'd0, 8'd0, rtag[b]};
                    h_pq[b] = {1'b1, 1'b0, rrow[b], 256'd0, 8'd0, rtag[b]};
                end
            end
            if (wv[b]) begin
                case (wo[b])
                    0, 1: begin f_wq[b][wo[b]] = {1'b1, s16(ws[b]), wd[b], wm[b]}; h_wq[b][wo[b]] = {1'b1, ws[b], wd[b], wm[b]}; end
                    2: begin f_kq[b] = {1'b1, s16(ws[b]), wd[b], wm[b]}; h_kq[b] = {1'b1, ws[b], wd[b], wm[b]}; end
                    3: begin f_xq[b] = {1'b1, r11(wrow[b]), wd[b], wm[b]}; h_xq[b] = {1'b1, wrow[b], wd[b], wm[b]}; end
                    4: begin f_pq[b] = {1'b1, 1'b1, r11(wrow[b]), wd[b], wm[b], wtag[b]}; h_pq[b] = {1'b1, 1'b1, wrow[b], wd[b], wm[b], wtag[b]}; end
                    5: begin f_x2[b] = {1'b1, r11(wrow[b]), wd[b], wm[b]}; h_x2[b] = {1'b1, wrow[b], wd[b], wm[b]}; end
                    6: begin f_dq[b] = {1'b1, s16(ws[b]), wd[b], wm[b]}; h_dq[b] = {1'b1, ws[b], wd[b], wm[b]}; end
                    default: begin end
                endcase
            end
        end
    end
    // ------------------------------------------------------------ banks
    wire [256:0] f_rr [NB][RG]; wire [256:0] h_rr [NB][RG];
    wire [5:0] f_done [NB]; wire [5:0] h_done [NB];
    wire [275:0] f_eg [NB]; wire [276:0] h_eg [NB];
    wire [265:0] f_pr [NB]; wire [265:0] h_pr [NB];
    wire [17:0] f_st [NB]; wire [17:0] h_st [NB];
    for (genvar b = 0; b < NB; b = b + 1) begin : bk
        hfd_vms_bank_native_q0_faces d4g (
            .rq0(f_rq[b][0]), .rr0(f_rr[b][0]), .rq1(f_rq[b][1]), .rr1(f_rr[b][1]), .rq2(f_rq[b][2]), .rr2(f_rr[b][2]),
            .rq3(f_rq[b][3]), .rr3(f_rr[b][3]), .rq4(f_rq[b][4]), .rr4(f_rr[b][4]),
            .wq0(f_wq[b][0]), .wq_done0(f_done[b][0]), .wq1(f_wq[b][1]), .wq_done1(f_done[b][1]),
            .bid(3'(bidof(b))), .sid(2'(SID)), .clk(clk), .clk_n(clk), .clk_s(clk), .clk_e(clk), .clk_w(clk),
            .clk_macro0(clk), .clk_macro1(clk), .clk_macro2(clk), .rst_n(rst_n),
            .rslot_v(rslot_v[b]), .rslot(rslot[b]), .wslot_v(wslot_v[b]), .wslot(wslot[b]),
            .dq(f_dq[b]), .dq_done(f_done[b][2]), .kq(f_kq[b]), .kq_done(f_done[b][3]), .xq(f_xq[b]), .xq_done(f_done[b][4]),
            .xq2(f_x2[b]), .xq2_done(f_done[b][5]), .eg(f_eg[b]), .pq(f_pq[b]), .pr(f_pr[b]), .status(f_st[b]));
        hnx_vms_bank_q0_faces #(.MUT(MUT)) hnx (
            .rq0(h_rq[b][0]), .rr0(h_rr[b][0]), .rq1(h_rq[b][1]), .rr1(h_rr[b][1]), .rq2(h_rq[b][2]), .rr2(h_rr[b][2]),
            .rq3(h_rq[b][3]), .rr3(h_rr[b][3]), .rq4(h_rq[b][4]), .rr4(h_rr[b][4]),
            .wq0(h_wq[b][0]), .wq_done0(h_done[b][0]), .wq1(h_wq[b][1]), .wq_done1(h_done[b][1]),
            .bid(3'(bidof(b))), .sid(2'(SID)), .clk(clk), .clk_n(clk), .clk_s(clk), .clk_e(clk), .clk_w(clk),
            .clk_macro0(clk), .clk_macro1(clk), .clk_macro2(clk), .clk_macro3(clk), .rst_n(rst_n),
            .rslot_v(rslot_v[b]), .rslot(rslot[b]), .wslot_v(wslot_v[b]), .wslot(wslot[b]),
            .dq(h_dq[b]), .dq_done(h_done[b][2]), .kq(h_kq[b]), .kq_done(h_done[b][3]), .xq(h_xq[b]), .xq_done(h_done[b][4]),
            .xq2(h_x2[b]), .xq2_done(h_done[b][5]), .eg(h_eg[b]), .pq(h_pq[b]), .pr(h_pr[b]), .status(h_st[b]));
    end
    // ------------------------------------------------------------ checking
    integer cycle = 0, lock_on = 0, sb_on = 0;
    integer lock_cmp = 0, lock_reads = 0, lock_writes = 0, lock_eg = 0, lock_pr = 0;
    // phase-B scoreboard: in-order FIFO per bank (one read per cycle, fixed latency)
    localparam integer FQ = 8192;
    reg [255:0] mdl [NB][3072];
    reg [255:0] q_dat [NB][FQ]; integer q_own [NB][FQ]; integer q_cyc [NB][FQ]; reg [7:0] q_tag [NB][FQ];
    integer q_h [NB], q_t [NB];
    integer sb_reads = 0, sb_lat = -1, sb_upper = 0, sb_mirror = 0, sb_lower = 0;
    task automatic fail(input string m);
        begin $display("TB_HNX_VM FAIL MUT=%0d cycle=%0d %s", MUT, cycle, m); $fatal(1, "TB_HNX_VM FAIL"); end
    endtask
    always @(negedge clk) if (rst_n) begin
        for (integer b = 0; b < NB; b = b + 1) begin
            if (lock_on) begin
                lock_cmp = lock_cmp + 1;
                for (integer g = 0; g < RG; g = g + 1) begin
                    if (f_rr[b][g] !== h_rr[b][g]) fail($sformatf("lockstep rr bank=%0d group=%0d d4g_v=%0d hnx_v=%0d", b, g, f_rr[b][g][256], h_rr[b][g][256]));
                    if (f_rr[b][g][256]) lock_reads = lock_reads + 1;
                end
                if (f_pr[b] !== h_pr[b]) fail($sformatf("lockstep pr bank=%0d", b));
                if (f_pr[b][265]) lock_pr = lock_pr + 1;
                if (f_done[b] !== h_done[b]) fail($sformatf("lockstep done bank=%0d d4g=%b hnx=%b", b, f_done[b], h_done[b]));
                lock_writes = lock_writes + $countones(f_done[b]);
                if (f_st[b] !== h_st[b]) fail($sformatf("lockstep status bank=%0d d4g=%h hnx=%h", b, f_st[b], h_st[b]));
                if (h_eg[b] !== {f_eg[b][275:274], 1'b0, f_eg[b][273:0]}) fail($sformatf("lockstep eg bank=%0d", b));
                if (f_eg[b][275]) lock_eg = lock_eg + 1;
            end
            if (sb_on) begin
                integer own; reg [255:0] got; own = -1; got = '0;
                if (h_st[b] !== 18'd0) fail($sformatf("status bank=%0d %h (FAULT/UE/CE) in the scoreboard phase", b, h_st[b]));
                for (integer g = 0; g < RG; g = g + 1) if (h_rr[b][g][256]) begin
                    if (own != -1) fail("two responses one edge"); own = g; got = h_rr[b][g][255:0];
                end
                if (h_pr[b][265] && !h_pr[b][264]) begin
                    if (own != -1) fail("two responses one edge"); own = RG; got = h_pr[b][255:0];
                    if (q_h[b] != q_t[b] && h_pr[b][263:256] !== q_tag[b][q_h[b] % FQ]) fail("packet tag");
                end
                if (own != -1) begin
                    integer lat;
                    if (q_h[b] == q_t[b]) fail($sformatf("unexpected response bank=%0d owner=%0d", b, own));
                    if (q_own[b][q_h[b] % FQ] != own) fail($sformatf("response owner bank=%0d got=%0d exp=%0d", b, own, q_own[b][q_h[b] % FQ]));
                    if (got !== q_dat[b][q_h[b] % FQ]) fail($sformatf("DATA bank=%0d owner=%0d issued=%0d got=%h exp=%h", b, own, q_cyc[b][q_h[b] % FQ], got, q_dat[b][q_h[b] % FQ]));
                    lat = cycle - q_cyc[b][q_h[b] % FQ];
                    if (sb_lat == -1) sb_lat = lat; else if (lat != sb_lat) fail($sformatf("latency %0d != %0d", lat, sb_lat));
                    q_h[b] = q_h[b] + 1; sb_reads = sb_reads + 1;
                end
            end
        end
    end
    // ------------------------------------------------------------ drive helpers (inputs change at posedge+1, sampled at the next posedge)
    task automatic idle_all;
        for (integer b = 0; b < NB; b = b + 1) begin
            rv[b] = 0; ro[b] = 0; rs[b] = 0; rrow[b] = 0; rtag[b] = 0;
            wv[b] = 0; wo[b] = 0; ws[b] = 0; wrow[b] = 0; wd[b] = 0; wm[b] = 0; wtag[b] = 0;
        end
    endtask
    task automatic step; begin @(posedge clk); #1; cycle = cycle + 1; end endtask
    function automatic [16:0] sec(input integer b, input bit mir, input integer row11);
        sec = {mir, (mir ? 2'd0 : 2'(SID)), 11'(row11), 3'(bidof(b))};
    endfunction
    function automatic [255:0] rnd256();
        reg [255:0] r; for (integer k = 0; k < 8; k = k + 1) r[k*32 +: 32] = $urandom; rnd256 = r;
    endfunction
    function automatic integer midx(input bit mir, input integer row11); midx = mir ? 2048 + (row11 % 1024) : row11; endfunction
    // phase-B write: owner w (0..6) of model row (mir,row11) with data d / mask m
    task automatic sb_write(input integer b, input integer w, input bit mir, input integer row11, input [255:0] d, input [7:0] m);
        begin
            wv[b] = 1; wo[b] = w; ws[b] = sec(b, mir, row11); wrow[b] = {mir, 11'(row11)}; wd[b] = d; wm[b] = m; wtag[b] = 8'h5a;
            for (integer k = 0; k < 8; k = k + 1) if (m[k]) mdl[b][midx(mir, row11)][k*32 +: 32] = d[k*32 +: 32];
        end
    endtask
    task automatic sb_read(input integer b, input integer r, input bit mir, input integer row11);
        begin
            rv[b] = 1; ro[b] = r; rs[b] = sec(b, mir, row11); rrow[b] = {mir, 11'(row11)}; rtag[b] = 8'(row11 ^ (mir ? 8'h80 : 8'h00));
            q_dat[b][q_t[b] % FQ] = mdl[b][midx(mir, row11)]; q_own[b][q_t[b] % FQ] = r; q_cyc[b][q_t[b] % FQ] = cycle + 1;
            q_tag[b][q_t[b] % FQ] = rtag[b]; q_t[b] = q_t[b] + 1;
            if (mir) sb_mirror = sb_mirror + 1; else if (row11 >= 1024) sb_upper = sb_upper + 1; else sb_lower = sb_lower + 1;
        end
    endtask
    initial begin
        integer x;
        x = $urandom(SEED);
        idle_all();
        for (integer b = 0; b < NB; b = b + 1) begin q_h[b] = 0; q_t[b] = 0; end
        repeat (3) step(); rst_n = 1; repeat (6) step();   // reset relay (3 edges) + strap pin registers
        // ---------------- Phase A: lockstep vs d4g on the lower 2^18 region + mirror
        lock_on = 1;
        for (integer t = 0; t < NA; t = t + 1) begin
            idle_all();
            for (integer b = 0; b < NB; b = b + 1) begin
                bit mir; integer row;
                if ($urandom % 10 < 7) begin
                    mir = ($urandom % 4) == 0; row = ($urandom % 50 == 0) ? int'($urandom % 1024) : int'($urandom % 48);
                    rv[b] = 1; ro[b] = $urandom % (RG + 1); rs[b] = sec(b, mir, row); rrow[b] = {mir, 1'b0, 10'(row)}; rtag[b] = 8'($urandom);
                end
                if ($urandom % 10 < 7) begin
                    mir = ($urandom % 4) == 0; row = ($urandom % 50 == 0) ? int'($urandom % 1024) : int'($urandom % 48);
                    wv[b] = 1; wo[b] = $urandom % (WG + 5);
                    if (rv[b] && ro[b] == RG && wo[b] == 4) wo[b] = 6;     // one packet op per cycle (compiler rule)
                    ws[b] = sec(b, mir, row); wrow[b] = {mir, 1'b0, 10'(row)}; wd[b] = rnd256();
                    wm[b] = ($urandom % 3 == 0) ? 8'($urandom) : 8'hff; wtag[b] = 8'($urandom);
                end
            end
            step();
        end
        idle_all(); repeat (12) step(); lock_on = 0;
        if (lock_reads < NA / 2 || lock_writes < NA / 2 || lock_eg < 10) fail($sformatf("lockstep inventory reads=%0d writes=%0d eg=%0d", lock_reads, lock_writes, lock_eg));
        $display("HNX_VM_LOCKSTEP PASS banks=%0d cycles=%0d compared_edges=%0d reads=%0d writes=%0d mirror_egress=%0d packet_resp=%0d (lower 2^18 + mirror, bit-identical to d4g)",
                 NB, NA, lock_cmp, lock_reads, lock_writes, lock_eg, lock_pr);
        // ---------------- Phase B: full 2^19 (+ mirror) fill / read-back on the hnx bank
        sb_on = 1;
        for (integer r = 0; r < 3072; r = r + 1) begin   // full-mask fill: quadrant rows 0..2047 then mirror rows 0..1023
            idle_all();
            for (integer b = 0; b < NB; b = b + 1) sb_write(b, (r + b) % (WG + 5), r >= 2048, r % 2048, rnd256(), 8'hff);
            step();
        end
        for (integer r = 0; r < 512; r = r + 1) begin    // partial-mask rewrites, A1-heavy
            idle_all();
            for (integer b = 0; b < NB; b = b + 1) begin
                integer row; bit mir; mir = ($urandom % 5) == 0; row = mir ? int'($urandom % 1024) : int'(1024 + $urandom % 1024);
                if ($urandom % 4 == 0 && !mir) row = row - 1024;
                sb_write(b, $urandom % (WG + 5), mir, row, rnd256(), 8'($urandom | 1));
            end
            step();
        end
        idle_all(); repeat (8) step();
        for (integer r = 0; r < 3072; r = r + 1) begin   // read back everything, 1 read / cycle / bank, all six owners
            idle_all();
            for (integer b = 0; b < NB; b = b + 1) begin
                integer rr_; rr_ = (r * 7 + b * 911) % 3072;      // permuted order: A0 / A1 / mirror interleaved
                sb_read(b, (r + b) % (RG + 1), rr_ >= 2048, rr_ % 2048);
            end
            step();
        end
        idle_all(); repeat (12) step();
        for (integer b = 0; b < NB; b = b + 1) if (q_h[b] != q_t[b]) fail($sformatf("missing responses bank=%0d %0d/%0d", b, q_h[b], q_t[b]));
        if (sb_reads != NB * 3072) fail($sformatf("read inventory %0d", sb_reads));
        $display("HNX_VM_UPPER PASS banks=%0d words_per_bank=%0d (A0 1024 + A1 1024 rows x 8) mirror_rows=1024 reads=%0d upper=%0d lower=%0d mirror=%0d latency=%0d edges (input pin reg + n+6) 1R+1W/cycle",
                 NB, 2048 * 8, sb_reads, sb_upper, sb_lower, sb_mirror, sb_lat);
        sb_on = 0;
        // ---------------- Phase C: mirror sector with row[10] = 1 is outside the mirror region -> sticky FAULT
        idle_all(); rv[0] = 1; ro[0] = 0; rs[0] = sec(0, 1, 1024 + 5); step(); idle_all(); repeat (12) step();
        if (h_st[0][17] !== 1'b1) fail("mirror row[10] sector did not fault");
        $display("TB_HNX_VM PASS MUT=%0d SEED=%0d lockstep_edges=%0d upper_reads=%0d mirror_row10_fault=1", MUT, SEED, lock_cmp, sb_upper);
        $finish;
    end
    initial begin #50000000; $display("TB_HNX_VM FAIL watchdog"); $fatal(1, "watchdog"); end
endmodule
`default_nettype wire
