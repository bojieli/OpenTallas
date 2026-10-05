`timescale 1ns/1ps
// SUCCESSOR bench of rtl/test/tb_w11_ckvdie_service.sv for ot_chip_v41x_ckv_die_service_cr (gap D3).
// Same stimulus, links, HBM and output lines as the original; with AG_CREDIT = 0 and no new plusargs its
// ROW/HBMW/CKVDIE output equals the original bench's.  Added (driven by rtl/test/dsrom_sys/run_ckv_credit_bench.py):
//   parameters AG_CREDIT, RXQ, LQD, NWP (passed to the successor);
//   +wpstall=<permille>  per-die per-cycle collector write-port unavailability (xorshift, +seed).  AG_CREDIT=1: the
//                        DUT's wp_stall.  AG_CREDIT=0 (no ready exists): a remote row arriving in a stalled cycle
//                        cannot be written and is lost (counted lost=) - the hazard the credits remove;
//   +jitter=<permille>   per-cycle probability that a link head (row or credit return) is held one more cycle
//                        (order per pair preserved);
//   +mutant=<1|2|3>      corrupt the 3rd row on link die1 -> die0: 1 gid^1 (table mismatch), 2 gid^16 (owner die
//                        mismatch), 3 generation-1 (stale); prints "MUT rank= present=" for die 0 at the end;
//   +maxcyc=<n>          timeout (default 200000).
// Credit returns travel back on the reverse link with the forward link's latency.
// Four dies' ot_chip_v41x_ckv_die_service (TP-4) on the L20 selection: each die reads the 512 selected ids
// from its vector memory, captures its own QDQ4E row, fetches its owned rows from its four HBM stacks
// (sparse image of the W17 ckv_s<k>.hex rows), all-gathers them over behavioural links and streams the
// 512 FP4 rows twice (QK and PV descriptors).  Driven by tools/w11_ckvdie_gate.py.
//   +dir=<d>: ids.hex (32 x 512-bit words), nw.hex (16 x 1024-bit QDQ4E beats of the own row),
//   cfg.hex {n_new_gid, vmword, nwaddr0}, hbm_d<k>.hex "<stack> <sector> <256-bit>" per die k (sparse)
//   +lat (HBM), +llink (board), +lucie, +ri (cycles a row on a board link)
// Output lines: "ROW <die> <pass> <rank> <hex 2304>" for every streamed row, "HBMW <die> <stack> <sector> <hex>"
// for every owner write, "CKVDIE ..." summary.
module tb_dsrom_ckv_credit #(
    parameter integer AG_CREDIT = 0,
    parameter integer RXQ = 16,
    parameter integer LQD = 4,
    parameter integer NWP = 5
);
    reg clk = 1'b0;
    always #1 clk = ~clk;
    localparam integer K = 512, KW = 10, POS_W = 21, AW = 30, VWA = 15, HAW = 30;
    reg [511:0] idw [0:31];
    reg [1023:0] nwm [0:15];
    reg [31:0] cfg [0:7];
    reg [255:0] hbm [longint];
    reg [1023:0] dir;
    integer lat = 100, llink = 142, lucie = 11, ri = 2;
    integer fd, d, st, cyc = 0, i;
    integer wpstall = 0, jitter = 0, mutant = 0, maxcyc = 200000, lost = 0, mut_rank = -1, mut_cnt = 0;
    reg [31:0] rng = 32'h2545f491;
    reg [3:0] wps = 0;
    localparam integer GW = 4;
    function automatic [31:0] xs(input [31:0] x);
        reg [31:0] y; y = x ^ (x << 13); y = y ^ (y >> 17); xs = y ^ (y << 5);
    endfunction
    function automatic integer s2d(input integer r0, input integer k);   // receive slot k of die r0 -> source die
        s2d = (k < r0) ? k : k + 1;
    endfunction
    function automatic integer d2s(input integer s0, input integer r0);  // destination die r0 -> slot of sender s0
        d2s = (r0 < s0) ? r0 : r0 - 1;
    endfunction
    reg [63:0] sa; reg [255:0] sw; reg [31:0] stk;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("+dir missing"); $finish; end
        if ($value$plusargs("lat=%d", lat)) ;
        if ($value$plusargs("llink=%d", llink)) ;
        if ($value$plusargs("lucie=%d", lucie)) ;
        if ($value$plusargs("ri=%d", ri)) ;
        if ($value$plusargs("wpstall=%d", wpstall)) ;
        if ($value$plusargs("jitter=%d", jitter)) ;
        if ($value$plusargs("mutant=%d", mutant)) ;
        if ($value$plusargs("maxcyc=%d", maxcyc)) ;
        if ($value$plusargs("seed=%d", i)) rng = 32'(i) ^ 32'h9e3779b9;
        if (rng == 0) rng = 1;
        $readmemh({dir, "/ids.hex"}, idw);
        $readmemh({dir, "/nw.hex"}, nwm);
        $readmemh({dir, "/cfg.hex"}, cfg);
        for (d = 0; d < 4; d = d + 1) begin
            fd = $fopen({dir, "/hbm_d", 8'(48 + d), ".hex"}, "r");
            if (fd != 0) begin
                while ($fscanf(fd, "%h %h %h\n", stk, sa, sw) == 3) hbm[{30'd0, 2'(d), 2'(stk), sa[29:0]}] = sw;
                $fclose(fd);
            end
        end
    end
    reg rst_n = 0;
    // stimulus: own-row writes, then the selection, then two attention jobs
    reg sel_v = 0, nw_we = 0; reg [AW-1:0] nw_addr = 0; reg [1023:0] nw_data = 0;
    reg job_v = 0;
    integer phase = 0, nwk = 0, jobs = 0, t_sel = 0;
    reg [3:0] jdone = 0;                // per-die job_done latched for the current job
    // per-die wires
    wire [3:0] vm_re; wire [4*VWA-1:0] vm_raddr; reg [4*512-1:0] vm_rq;
    wire [16-1:0] c_v, c_we; reg [16-1:0] c_rdy, c_sv; wire [16*HAW-1:0] c_addr; wire [16*16-1:0] c_tag;
    wire [16*256-1:0] c_wdata; reg [16*16-1:0] c_stag; reg [16*256-1:0] c_sdata;
    wire [3:0] tx_v; wire [4*KW-1:0] tx_rank; wire [4*POS_W-1:0] tx_gid; wire [4*2304-1:0] tx_row;
    reg [3:0] tx_rdy;
    reg [3*4-1:0] rx_v; reg [4*3*KW-1:0] rx_rank; reg [4*3*POS_W-1:0] rx_gid; reg [4*3*2304-1:0] rx_row;
    wire [3:0] jr, kvv, jd, flt, rr; wire [4*4-1:0] kvm; wire [4*16*265*4-1:0] kvw; wire [4*6-1:0] fc;
    wire [4*32-1:0] ctr;
    wire [4*GW-1:0] tx_gen; reg [4*3*GW-1:0] rx_gen; wire [4*3-1:0] rx_cr; reg [4*3-1:0] tx_cr;
    wire [4*6-1:0] crf; wire [4*32-1:0] txst;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_die
        wire [15:0] c_len_u; wire [127:0] c_wstrb_u; wire [3:0] c_srdy_u;
        ot_chip_v41x_ckv_die_service_cr #(.AG_CREDIT(AG_CREDIT), .RXQ(RXQ), .LQD(LQD), .NWP(NWP), .GEN_W(GW), .DIE_ID(g), .K(K), .POS_W(POS_W), .AW(AW), .VWA(VWA), .HAW(HAW),
            .TAGW(16), .CKV_BASE(1 << 22), .CKV_SECTORS(1 << 22), .NSLOT(64)) u (
            .clk(clk), .rst_n(rst_n), .sel_v(sel_v), .sel_vmword(VWA'(cfg[1])),
            .nw_we(nw_we), .nw_addr(nw_addr), .nw_data(nw_data),
            .vm_re(vm_re[g]), .vm_raddr(vm_raddr[g*VWA +: VWA]), .vm_rq(vm_rq[g*512 +: 512]), .vm_busy(),
            .c_v(c_v[g*4 +: 4]), .c_rdy(c_rdy[g*4 +: 4]), .c_addr(c_addr[g*4*HAW +: 4*HAW]), .c_len(c_len_u),
            .c_tag(c_tag[g*64 +: 64]), .c_we(c_we[g*4 +: 4]), .c_wdata(c_wdata[g*1024 +: 1024]), .c_wstrb(c_wstrb_u),
            .c_wr_done(4'd0), .c_sv(c_sv[g*4 +: 4]), .c_srdy(c_srdy_u), .c_stag(c_stag[g*64 +: 64]), .c_sbeat(16'd0),
            .c_sdata(c_sdata[g*1024 +: 1024]),
            .ag_tx_valid(tx_v[g]), .ag_tx_ready(tx_rdy[g]), .ag_tx_rank(tx_rank[g*KW +: KW]),
            .ag_tx_gid(tx_gid[g*POS_W +: POS_W]), .ag_tx_row(tx_row[g*2304 +: 2304]),
            .ag_rx_valid(rx_v[g*3 +: 3] & {3{!(AG_CREDIT == 0 && wps[g])}}), .ag_rx_rank(rx_rank[g*3*KW +: 3*KW]), .ag_rx_gid(rx_gid[g*3*POS_W +: 3*POS_W]),
            .ag_rx_row(rx_row[g*3*2304 +: 3*2304]),
            .ag_tx_gen(tx_gen[g*GW +: GW]), .ag_rx_gen(rx_gen[g*3*GW +: 3*GW]), .ag_rx_credit(rx_cr[g*3 +: 3]),
            .ag_tx_credit(tx_cr[g*3 +: 3]), .wp_stall(AG_CREDIT != 0 && wps[g]), .cr_fault_code(crf[g*6 +: 6]),
            .st_tx_credit_stall(txst[g*32 +: 32]),
            .job_v(job_v), .job_ready(jr[g]), .kv_v(kvv[g]), .kv_ready(1'b1), .kv_m(kvm[g*4 +: 4]),
            .kv_w(kvw[g*16960 +: 16960]), .job_done(jd[g]),
            .fault(flt[g]), .fault_code(fc[g*6 +: 6]), .rows_ready(rr[g]),
            .st_rows_local(), .st_rows_remote(), .st_cycles_to_ready(ctr[g*32 +: 32]));
    end endgenerate
    // HBM: per (die, stack) FIFO, fixed latency, one request a cycle
    localparam integer HQ = 512;
    integer hq_t [0:15][0:HQ-1]; reg [15:0] hq_tag [0:15][0:HQ-1]; reg [255:0] hq_dat [0:15][0:HQ-1];
    integer hq_h [0:15], hq_n [0:15];
    integer hbm_miss = 0, hbm_w = 0, p, e;
    longint key;
    // links: from die s to die r (s != r), queue of rows
    localparam integer LQ = 600;
    integer lk_t [0:15][0:LQ-1]; reg [KW-1:0] lk_rank [0:15][0:LQ-1]; reg [POS_W-1:0] lk_gid [0:15][0:LQ-1];
    reg [2303:0] lk_row [0:15][0:LQ-1]; reg [GW-1:0] lk_gen [0:15][0:LQ-1];
    // credit return: from receiver r back to sender s (index s*4+r), arrival times
    localparam integer CQ = 1024;
    integer cr_t [0:15][0:CQ-1]; integer cr_h [0:15], cr_n [0:15];
    integer lk_h [0:15], lk_n [0:15], lk_free [0:15];
    integer s, r, slot, ll, pass [0:3], rows_out [0:3];
    function automatic integer link_lat(input integer a, input integer b);
        link_lat = ((a >> 1) == (b >> 1)) ? lucie : llink;
    endfunction
    function automatic integer link_ri(input integer a, input integer b);
        link_ri = ((a >> 1) == (b >> 1)) ? 1 : ri;
    endfunction
    initial begin
        for (p = 0; p < 16; p = p + 1) begin cr_h[p] = 0; cr_n[p] = 0; end
        tx_cr = 0; rx_gen = 0;
        for (p = 0; p < 16; p = p + 1) begin hq_h[p] = 0; hq_n[p] = 0; lk_h[p] = 0; lk_n[p] = 0; lk_free[p] = 0; end
        for (d = 0; d < 4; d = d + 1) begin pass[d] = 0; rows_out[d] = 0; end
        c_rdy = 0; c_sv = 0; tx_rdy = 0; rx_v = 0; vm_rq = 0;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        sel_v <= 1'b0; job_v <= 1'b0; nw_we <= 1'b0;
        // own-row QDQ4E writes (same on every die: the replicated compressor), then the selection
        if (rst_n && phase == 0 && cyc > 8) begin
            nw_we <= 1'b1; nw_addr <= AW'(cfg[2]) + AW'(32 * nwk); nw_data <= nwm[nwk];
            nwk = nwk + 1; if (nwk == 16) phase = 1;
        end else if (phase == 1 && cyc > 40) begin sel_v <= 1'b1; t_sel = cyc; phase = 2; end
        else if (phase == 2 && cyc > t_sel + 4 && &jr) begin job_v <= 1'b1; phase = 3; jobs = jobs + 1; jdone = 0; end
        else if (phase == 3 && &jdone) phase = 4;
        else if (phase == 4 && &jr) begin job_v <= 1'b1; phase = 5; jobs = jobs + 1; jdone = 0; end
        jdone = jdone | jd;
        // VM: ids at cfg[1]
        for (d = 0; d < 4; d = d + 1)
            if (vm_re[d]) vm_rq[d*512 +: 512] <= idw[32'(vm_raddr[d*VWA +: VWA]) - 32'(cfg[1])];
        // HBM
        for (p = 0; p < 16; p = p + 1) begin
            c_sv[p] <= 1'b0;
            if (hq_n[p] > 0 && hq_t[p][hq_h[p]] <= cyc) begin
                c_sv[p] <= 1'b1; c_stag[p*16 +: 16] <= hq_tag[p][hq_h[p]]; c_sdata[p*256 +: 256] <= hq_dat[p][hq_h[p]];
                hq_h[p] = (hq_h[p] + 1) % HQ; hq_n[p] = hq_n[p] - 1;
            end
            if (c_v[p] && c_rdy[p]) begin
                key = {30'd0, 2'(p / 4), 2'(p % 4), c_addr[p*HAW +: 30]};
                if (c_we[p]) begin
                    hbm[key] = c_wdata[p*256 +: 256]; hbm_w = hbm_w + 1;
                    $display("HBMW %0d %0d %0d %064x", p / 4, p % 4, c_addr[p*HAW +: 30], c_wdata[p*256 +: 256]);
                end else begin
                    e = (hq_h[p] + hq_n[p]) % HQ;
                    hq_t[p][e] = cyc + lat; hq_tag[p][e] = c_tag[p*16 +: 16];
                    if (hbm.exists(key)) hq_dat[p][e] = hbm[key];
                    else begin hq_dat[p][e] = {256{1'b1}}; hbm_miss = hbm_miss + 1; end
                    hq_n[p] = hq_n[p] + 1;
                end
            end
            c_rdy[p] <= hq_n[p] < HQ - 4;
        end
        // all-gather links: die s broadcasts to the other three (one serializer per destination)
        // AG_CREDIT = 0 under a receive stall: no ready exists, so a row presented in a stalled cycle (masked at
        // the DUT input below) is lost; rx_v/wps here are the values presented during the cycle just ended
        if (AG_CREDIT == 0)
            for (r = 0; r < 4; r = r + 1) if (wps[r])
                for (slot = 0; slot < 3; slot = slot + 1) if (rx_v[r*3 + slot]) lost = lost + 1;
        rx_v <= 0;
        for (s = 0; s < 4; s = s + 1) begin
            if (tx_v[s] && tx_rdy[s])
                for (r = 0; r < 4; r = r + 1) if (r != s) begin
                    ll = s * 4 + r; e = (lk_h[ll] + lk_n[ll]) % LQ;
                    lk_t[ll][e] = cyc + link_lat(s, r); lk_rank[ll][e] = tx_rank[s*KW +: KW];
                    lk_gid[ll][e] = tx_gid[s*POS_W +: POS_W]; lk_row[ll][e] = tx_row[s*2304 +: 2304];
                    lk_gen[ll][e] = tx_gen[s*GW +: GW];
                    lk_n[ll] = lk_n[ll] + 1; lk_free[ll] = cyc + link_ri(s, r);
                end
            tx_rdy[s] <= 1'b1;
            for (r = 0; r < 4; r = r + 1) if (r != s && (lk_free[s*4 + r] > cyc + 1 || lk_n[s*4 + r] >= LQ - 2))
                tx_rdy[s] <= 1'b0;
        end
        // write-port stall draw for the cycle the delivered rows are presented (next cycle)
        for (r = 0; r < 4; r = r + 1) begin
            rng = xs(rng);
            wps[r] <= (wpstall > 0) && (rng % 1000) < wpstall;
        end
        for (r = 0; r < 4; r = r + 1) begin
            slot = 0;
            for (s = 0; s < 4; s = s + 1) if (s != r) begin
                ll = s * 4 + r;
                rng = xs(rng);
                if (lk_n[ll] > 0 && lk_t[ll][lk_h[ll]] <= cyc && !(jitter > 0 && (rng % 1000) < jitter)) begin
                    rx_v[r*3 + slot] <= 1'b1;
                    rx_rank[(r*3 + slot)*KW +: KW] <= lk_rank[ll][lk_h[ll]];
                    rx_gid[(r*3 + slot)*POS_W +: POS_W] <= lk_gid[ll][lk_h[ll]];
                    rx_row[(r*3 + slot)*2304 +: 2304] <= lk_row[ll][lk_h[ll]];
                    rx_gen[(r*3 + slot)*GW +: GW] <= lk_gen[ll][lk_h[ll]];
                    if (s == 1 && r == 0 && mutant != 0) begin
                        mut_cnt = mut_cnt + 1;
                        if (mut_cnt == 3) begin
                            mut_rank = lk_rank[ll][lk_h[ll]];
                            if (mutant == 1) rx_gid[(r*3 + slot)*POS_W +: POS_W] <= lk_gid[ll][lk_h[ll]] ^ 21'd1;
                            if (mutant == 2) rx_gid[(r*3 + slot)*POS_W +: POS_W] <= lk_gid[ll][lk_h[ll]] ^ 21'd16;
                            if (mutant == 3) rx_gen[(r*3 + slot)*GW +: GW] <= lk_gen[ll][lk_h[ll]] - 1'b1;
                        end
                    end
                    lk_h[ll] = (lk_h[ll] + 1) % LQ; lk_n[ll] = lk_n[ll] - 1;
                end
                slot = slot + 1;
            end
        end
        // credit returns: receiver r slot k -> sender s2d(r,k), arriving at its destination slot d2s(s,r)
        tx_cr <= 0;
        for (r = 0; r < 4; r = r + 1)
            for (slot = 0; slot < 3; slot = slot + 1) if (rx_cr[r*3 + slot]) begin
                s = s2d(r, slot); ll = s * 4 + r; e = (cr_h[ll] + cr_n[ll]) % CQ;
                cr_t[ll][e] = cyc + link_lat(r, s); cr_n[ll] = cr_n[ll] + 1;
            end
        for (s = 0; s < 4; s = s + 1)
            for (r = 0; r < 4; r = r + 1) if (r != s) begin
                ll = s * 4 + r;
                rng = xs(rng);
                if (cr_n[ll] > 0 && cr_t[ll][cr_h[ll]] <= cyc && !(jitter > 0 && (rng % 1000) < jitter)) begin
                    tx_cr[s*3 + d2s(s, r)] <= 1'b1;
                    cr_h[ll] = (cr_h[ll] + 1) % CQ; cr_n[ll] = cr_n[ll] - 1;
                end
            end
        // streamed rows
        for (d = 0; d < 4; d = d + 1) if (kvv[d]) begin
            for (i = 0; i < 4; i = i + 1) if (kvm[d*4 + i]) begin
                $write("ROW %0d %0d %0d ", d, pass[d], rows_out[d] % K);
                for (e = 15; e >= 0; e = e - 1) $write("%067x", kvw[d*16960 + (i*16 + e)*265 +: 265]);
                $write("\n");
                rows_out[d] = rows_out[d] + 1;
            end
            if (rows_out[d] % K == 0) pass[d] = pass[d] + 1;
        end
        if ((phase == 5 && &jdone) || cyc > maxcyc || |flt) begin
            if (mutant != 0)
                $display("MUT mutant=%0d rank=%0d present=%0d", mutant, mut_rank,
                         (mut_rank >= 0) ? g_die[0].u.present[mut_rank] : 1'b0);
            $display("CKVDIE cycles=%0d jobs=%0d rows=%0d,%0d,%0d,%0d ready_cycles=%0d,%0d,%0d,%0d hbm_miss=%0d hbm_writes=%0d faults=%0h,%0h,%0h,%0h timeout=%0d%s",
                     cyc, jobs, rows_out[0], rows_out[1], rows_out[2], rows_out[3],
                     ctr[0 +: 32], ctr[32 +: 32], ctr[64 +: 32], ctr[96 +: 32], hbm_miss, hbm_w,
                     fc[0 +: 6], fc[6 +: 6], fc[12 +: 6], fc[18 +: 6], cyc > maxcyc,
                     $sformatf(" lost=%0d crfault=%0h,%0h,%0h,%0h tx_credit_stall=%0d,%0d,%0d,%0d",
                               lost, crf[0 +: 6], crf[6 +: 6], crf[12 +: 6], crf[18 +: 6],
                               txst[0 +: 32], txst[32 +: 32], txst[64 +: 32], txst[96 +: 32]));
            $finish;
        end
    end
endmodule
