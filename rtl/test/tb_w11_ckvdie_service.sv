`timescale 1ns/1ps
// Four dies' ot_chip_v41x_ckv_die_service (TP-4) on the L20 selection: each die reads the 512 selected ids
// from its vector memory, captures its own QDQ4E row, fetches its owned rows from its four HBM stacks
// (sparse image of the W17 ckv_s<k>.hex rows), all-gathers them over behavioural links and streams the
// 512 FP4 rows twice (QK and PV descriptors).  Driven by tools/w11_ckvdie_gate.py.
//   +dir=<d>: ids.hex (32 x 512-bit words), nw.hex (16 x 1024-bit QDQ4E beats of the own row),
//   cfg.hex {n_new_gid, vmword, nwaddr0}, hbm_d<k>.hex "<stack> <sector> <256-bit>" per die k (sparse)
//   +lat (HBM), +llink (board), +lucie, +ri (cycles a row on a board link)
// Output lines: "ROW <die> <pass> <rank> <hex 2304>" for every streamed row, "HBMW <die> <stack> <sector> <hex>"
// for every owner write, "CKVDIE ..." summary.
module tb_w11_ckvdie_service;
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
    reg [63:0] sa; reg [255:0] sw; reg [31:0] stk;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("+dir missing"); $finish; end
        if ($value$plusargs("lat=%d", lat)) ;
        if ($value$plusargs("llink=%d", llink)) ;
        if ($value$plusargs("lucie=%d", lucie)) ;
        if ($value$plusargs("ri=%d", ri)) ;
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
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_die
        wire [15:0] c_len_u; wire [127:0] c_wstrb_u; wire [3:0] c_srdy_u;
        ot_chip_v41x_ckv_die_service #(.DIE_ID(g), .K(K), .POS_W(POS_W), .AW(AW), .VWA(VWA), .HAW(HAW),
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
            .ag_rx_valid(rx_v[g*3 +: 3]), .ag_rx_rank(rx_rank[g*3*KW +: 3*KW]), .ag_rx_gid(rx_gid[g*3*POS_W +: 3*POS_W]),
            .ag_rx_row(rx_row[g*3*2304 +: 3*2304]),
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
    reg [2303:0] lk_row [0:15][0:LQ-1];
    integer lk_h [0:15], lk_n [0:15], lk_free [0:15];
    integer s, r, slot, ll, pass [0:3], rows_out [0:3];
    function automatic integer link_lat(input integer a, input integer b);
        link_lat = ((a >> 1) == (b >> 1)) ? lucie : llink;
    endfunction
    function automatic integer link_ri(input integer a, input integer b);
        link_ri = ((a >> 1) == (b >> 1)) ? 1 : ri;
    endfunction
    initial begin
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
        rx_v <= 0;
        for (s = 0; s < 4; s = s + 1) begin
            if (tx_v[s] && tx_rdy[s])
                for (r = 0; r < 4; r = r + 1) if (r != s) begin
                    ll = s * 4 + r; e = (lk_h[ll] + lk_n[ll]) % LQ;
                    lk_t[ll][e] = cyc + link_lat(s, r); lk_rank[ll][e] = tx_rank[s*KW +: KW];
                    lk_gid[ll][e] = tx_gid[s*POS_W +: POS_W]; lk_row[ll][e] = tx_row[s*2304 +: 2304];
                    lk_n[ll] = lk_n[ll] + 1; lk_free[ll] = cyc + link_ri(s, r);
                end
            tx_rdy[s] <= 1'b1;
            for (r = 0; r < 4; r = r + 1) if (r != s && (lk_free[s*4 + r] > cyc + 1 || lk_n[s*4 + r] >= LQ - 2))
                tx_rdy[s] <= 1'b0;
        end
        for (r = 0; r < 4; r = r + 1) begin
            slot = 0;
            for (s = 0; s < 4; s = s + 1) if (s != r) begin
                ll = s * 4 + r;
                if (lk_n[ll] > 0 && lk_t[ll][lk_h[ll]] <= cyc) begin
                    rx_v[r*3 + slot] <= 1'b1;
                    rx_rank[(r*3 + slot)*KW +: KW] <= lk_rank[ll][lk_h[ll]];
                    rx_gid[(r*3 + slot)*POS_W +: POS_W] <= lk_gid[ll][lk_h[ll]];
                    rx_row[(r*3 + slot)*2304 +: 2304] <= lk_row[ll][lk_h[ll]];
                    lk_h[ll] = (lk_h[ll] + 1) % LQ; lk_n[ll] = lk_n[ll] - 1;
                end
                slot = slot + 1;
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
        if ((phase == 5 && &jdone) || cyc > 200000 || |flt) begin
            $display("CKVDIE cycles=%0d jobs=%0d rows=%0d,%0d,%0d,%0d ready_cycles=%0d,%0d,%0d,%0d hbm_miss=%0d hbm_writes=%0d faults=%0h,%0h,%0h,%0h timeout=%0d",
                     cyc, jobs, rows_out[0], rows_out[1], rows_out[2], rows_out[3],
                     ctr[0 +: 32], ctr[32 +: 32], ctr[64 +: 32], ctr[96 +: 32], hbm_miss, hbm_w,
                     fc[0 +: 6], fc[6 +: 6], fc[12 +: 6], fc[18 +: 6], cyc > 200000);
            $finish;
        end
    end
endmodule
