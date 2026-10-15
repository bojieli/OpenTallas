`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// tb_wfc_stg_static (claude S81 VM F7 static-wfc2, 2026-10-15): production-shape bench of the static stage WFC kit
// dsfd_wfc_stg_s (rtl/dsrom_sys/mtp/dsfd_wfc_stg_static.sv) on its die pins.
//   clocks   stream 1.2 GHz-shaped (3 ns) and serial (4 ns) on a common 12 ns epoch, both resets released before a common
//            rising edge (the x34 / x43 startup contract).
//   upstream STATIC CALENDAR: job j's HIDDEN message (header + 41 words, the stage shape of tb_mtp_rom_stg_tokpipe) on
//            consecutive stream edges from edge H0 + j * P; no ready exists.  Jobs: NUSR users interleaved, each user's
//            positions in order, token t = mix(u, p) % 129280, or replayed from JOBS (u p t per line, hex) to run the
//            exact job stream of a reference run.
//   VM       the static VM endpoint's behaviour (dsfd_vm_static_wfc): grants constant high after reset, write applied
//            WLAT (5) serial edges after it is sampled, doorbell 7fff not a VM op, RD2 pairs returned so that the kit's
//            pin flop holds them exactly RLAT edges after the launch, reads see the VM before same-edge writes.
//   core     at t_ks START: the 41 received rows must be in the VM; after T_CORE serial edges it writes the 46 outbound
//            rows word(2, ..) and pulses f_kd {done, t ^ 33, 40400000 ^ p} (as the reference bench's core).
//   checker  every outbound HIDDEN: header (dest 1, src 0, type 1, len 46, user / pos / token of the job, idx, val),
//            46 words exact, last only on word 45, no gap inside a message; t_ft must stay 0.  DUMP writes every
//            outbound flit (513 b hex) to out.hex for the reference comparison.
// PASS line: WFC_SS PASS jobs=.. period=.. rx_tx_min=.. rx_tx_max=.. done_tx_min=.. done_tx_max=..
// ---------------------------------------------------------------------------------------------------------------
module tb_wfc_stg_static;
    parameter integer NJOB = 40, NUSR = 3, P = 200, H0 = 20, T_CORE = 80, RLAT = 17, START_GAP = 4, WLAT = 5;
    parameter integer EXPECT_FAULT = 0, BADPOS = -1;     // BADPOS j: job j's header carries a position out of window
    localparam integer FLIT = 512, NW = 21, USER_W = 10, VWA = 15, RXW = 41, TXW = 46;
    localparam integer HDR_TYPE = 16, HDR_LEN = 24, HDR_USER = 32, HDR_POS = 40, HDR_IDX = 61, HDR_VAL = 82,
                       HDR_TOK = 114, HDR_USER_HI = 151;
    reg fclk = 1, sclk = 1;
    always #1.5 fclk = ~fclk;
    always #2.0 sclk = ~sclk;
    reg rst_n = 0;
    initial #11 rst_n = 1;                // first rising edges after release: t = 12, the common epoch edge
    integer cyc = 0, scyc = 0;
    always @(posedge fclk) if (rst_n) cyc <= cyc + 1;
    always @(posedge sclk) if (rst_n) scyc <= scyc + 1;
    function automatic [31:0] mix(input [31:0] h, input [31:0] x);
        reg [31:0] t; begin t = (h ^ (x * 32'h9E3779B1)) + 32'h7F4A7C15; t = t ^ (t >> 15); t = t * 32'h2C1B3C6D;
        mix = t ^ (t >> 12); end
    endfunction
    function automatic [FLIT-1:0] word(input integer s, input integer uu, input integer pp, input integer tt,
                                       input integer ww);
        integer b; reg [31:0] h; begin
            h = mix(mix(mix(mix(s, uu), pp), tt), ww);
            for (b = 0; b < FLIT / 32; b = b + 1) begin word[b*32 +: 32] = h; h = mix(h, b); end
        end
    endfunction
    // ---------------------------------------------------------------- DUT
    reg li_v = 0; reg [FLIT:0] li_d = 0;
    wire lo_v; wire [FLIT:0] lo_d;
    wire swv, srv; wire [526:0] swd; wire [30:0] srd; reg swr = 0, srr = 0, swa = 0;
    reg [1025:0] srq = 0; wire [52:0] ks; reg [53:0] kd = 0; wire [35:0] hep; wire [3:0] ft;
    wire [8:0] c_done; wire [1:0] c_st;
    dsfd_wfc_stg_s #(.RLAT(RLAT), .START_GAP(START_GAP)) u_dut (.ck(fclk), .ckv(sclk), .rst(rst_n), .rsv(rst_n),
        .c_cmd(85'd0), .c_done(c_done), .c_st(c_st), .f_liv(li_v), .f_lid(li_d), .t_lov(lo_v), .t_lod(lo_d),
        .t_swv(swv), .t_swd(swd), .f_swr(swr), .f_swa(swa), .t_srv(srv), .t_srd(srd), .f_srr(srr), .f_srq(srq),
        .t_ks(ks), .f_kd(kd), .t_hep(hep), .t_ft(ft));
    // Concrete hard ABI: reject elaboration that drops address / valid / marker bits.
    initial begin
        if ($bits(u_dut.u_x43t.s_d) != 527 || $bits(u_dut.u_x43s.o_d) != 527 ||
            $bits(u_dut.u_x43t.b0) != 528 || $bits(u_dut.u_x43s.b0) != 528 ||
            $bits(u_dut.u_x34s.s_d) != 514 || $bits(u_dut.u_x34t.o_d) != 514 ||
            $bits(u_dut.u_x34s.b0) != 515 || $bits(u_dut.u_x34t.b0) != 515)
            $fatal(1, "WFC_SS ABI width mismatch");
    end
    // ---------------------------------------------------------------- jobs
    integer job_u [0:1023], job_p [0:1023], job_t [0:1023], nxt [0:7], njob, i, fd, rc;
    reg [31:0] ju, jp, jt;
    initial begin
        for (i = 0; i < 8; i = i + 1) nxt[i] = 0;
        njob = NJOB;
`ifdef JOBS
        fd = $fopen(`JOBS, "r"); njob = 0;
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%h %h %h\n", ju, jp, jt);
            if (rc == 3) begin job_u[njob] = ju; job_p[njob] = jp; job_t[njob] = jt; njob = njob + 1; end
        end
        $fclose(fd);
`else
        for (i = 0; i < NJOB; i = i + 1) begin
            job_u[i] = mix(7, i) % NUSR; job_p[i] = nxt[job_u[i]]; nxt[job_u[i]] = nxt[job_u[i]] + 1;
            job_t[i] = mix(job_u[i], job_p[i]) % 129280;
        end
`endif
    end
    // ---------------------------------------------------------------- upstream static calendar
    integer cj = 0, ck_ = -1, h_edge [0:1023];
    always @(posedge fclk) if (rst_n) begin
        li_v <= 1'b0;
        if (ck_ < 0 && cj < njob && cyc >= H0 + cj * P) begin
            li_v <= 1'b1; li_d <= 0;
            li_d[7:0] <= 8'd1; li_d[HDR_TYPE +: 4] <= 4'd1; li_d[HDR_LEN +: 8] <= RXW;
            li_d[HDR_USER +: 8] <= job_u[cj]; li_d[HDR_USER_HI +: 2] <= job_u[cj] >> 8;
            li_d[HDR_POS +: NW] <= (cj == BADPOS) ? job_p[cj] + 9 : job_p[cj];
            li_d[HDR_IDX +: NW] <= job_t[cj] ^ 7; li_d[HDR_VAL +: 32] <= 32'h3f000000 + job_p[cj];
            li_d[HDR_TOK +: NW] <= job_t[cj];
            h_edge[cj] = cyc; ck_ = 0;
        end else if (ck_ >= 0) begin
            li_v <= 1'b1; li_d <= {ck_ == RXW - 1, word(1, 0, job_p[cj], job_t[cj], ck_)};
            ck_ = ck_ + 1;
            if (ck_ == RXW) begin ck_ = -1; cj = cj + 1; end
        end
    end
    // ---------------------------------------------------------------- VM (static endpoint behaviour) and stage core
    reg [FLIT-1:0] vmem [0:63];
    integer wq_t [0:255], wq_a [0:255], wq_w = 0, wq_r = 0; reg [FLIT-1:0] wq_d [0:255];
    reg [1025:0] rp_d [0:255]; integer rp_t [0:255], rp_w = 0, rp_r = 0;
    integer core_t = -1, cu, cp, ct, k, starts = 0, done_s [0:1023], nd = 0;
    reg [1025:0] resp;
    always @(posedge sclk) if (rst_n) begin
        swr <= 1'b1; srr <= 1'b1; swa <= 1'b0;
        // read (sampled now): snapshot before this edge's writes; held so the kit's pin flop takes it at launch + RLAT
        if (srv) begin
            if (srd[14:0] >= 64 || (srd[30] && srd[29:15] >= 64)) begin $display("WFC_SS FAIL: VM read address"); $finish; end
            resp = 0; resp[512] = 1'b1; resp[511:0] = vmem[srd[14:0]];
            if (srd[30]) begin resp[1025] = 1'b1; resp[1024:513] = vmem[srd[29:15]]; end
            rp_d[rp_w % 256] = resp; rp_t[rp_w % 256] = scyc + RLAT - 2; rp_w = rp_w + 1;
        end
        srq <= 0;
        if (rp_r < rp_w && rp_t[rp_r % 256] == scyc) begin srq <= rp_d[rp_r % 256]; rp_r = rp_r + 1; end
        else if (rp_r < rp_w && rp_t[rp_r % 256] < scyc) begin $display("WFC_SS FAIL: bench VM response slot missed"); $finish; end
        // write (sampled now), applied WLAT edges later
        if (swv && swd[526:512] != 15'h7fff) begin
            if (swd[526:512] >= 64) begin $display("WFC_SS FAIL: VM write address %0d", swd[526:512]); $finish; end
            wq_a[wq_w % 256] = swd[526:512]; wq_d[wq_w % 256] = swd[511:0]; wq_t[wq_w % 256] = scyc + WLAT; wq_w = wq_w + 1;
        end
        while (wq_r < wq_w && wq_t[wq_r % 256] <= scyc) begin vmem[wq_a[wq_r % 256]] = wq_d[wq_r % 256]; wq_r = wq_r + 1; end
        // stage core
        kd[53] <= 1'b0;
        if (ks[52]) begin
            if (core_t >= 0) begin $display("WFC_SS FAIL: start while busy"); $finish; end
            cu = ks[51:42]; ct = ks[41:21]; cp = ks[20:0]; starts = starts + 1;
            for (k = 0; k < RXW; k = k + 1)
                if (vmem[k] !== word(1, 0, cp, ct, k)) begin
                    $display("WFC_SS FAIL: RX word %0d of (p%0d, t%0d) not in the VM at start (write / start order)", k, cp, ct);
                    $finish;
                end
            core_t = scyc + T_CORE;
        end else if (core_t >= 0 && scyc >= core_t) begin
            for (k = 0; k < TXW; k = k + 1) vmem[k] = word(2, 0, cp, ct, k);
            kd <= {1'b1, NW'(ct ^ 21'h33), 32'h40400000 ^ cp};
            done_s[nd] = cyc; nd = nd + 1; core_t = -1;
        end
    end
    // ---------------------------------------------------------------- downstream checker
    integer m_k = -1, outs = 0, ofd, lat, rx_tx_min = 1 << 30, rx_tx_max = 0, d_tx_min = 1 << 30, d_tx_max = 0;
    integer first_hdr = -1, last_hdr = -1;
    initial begin
`ifdef DUMP
        ofd = $fopen("out.hex", "w");
`endif
    end
    always @(posedge fclk) if (rst_n) begin
        if (m_k >= 0 && !lo_v) begin $display("WFC_SS FAIL: gap inside outbound message %0d at word %0d", outs, m_k); $finish; end
        if (lo_v) begin
`ifdef DUMP
            $fwrite(ofd, "%h\n", lo_d);
`endif
            if (m_k < 0) begin
                if (lo_d[FLIT] || lo_d[7:0] != 8'd1 || lo_d[15:8] != 8'd0 || lo_d[HDR_TYPE +: 4] != 4'd1 ||
                    lo_d[HDR_LEN +: 8] != TXW || {lo_d[HDR_USER_HI +: 2], lo_d[HDR_USER +: 8]} != job_u[outs] ||
                    lo_d[HDR_POS +: NW] != job_p[outs] || lo_d[HDR_TOK +: NW] != job_t[outs] ||
                    lo_d[HDR_IDX +: NW] != (job_t[outs] ^ 21'h33) || lo_d[HDR_VAL +: 32] != (32'h40400000 ^ job_p[outs])) begin
                    $display("WFC_SS FAIL: outbound header %0d %h", outs, lo_d[160:0]); $finish; end
                lat = cyc - h_edge[outs]; if (lat < rx_tx_min) rx_tx_min = lat; if (lat > rx_tx_max) rx_tx_max = lat;
                lat = cyc - done_s[outs]; if (lat < d_tx_min) d_tx_min = lat; if (lat > d_tx_max) d_tx_max = lat;
                if (first_hdr < 0) first_hdr = cyc; last_hdr = cyc;
                m_k = 0;
            end else begin
                if (lo_d[FLIT-1:0] !== word(2, 0, job_p[outs], job_t[outs], m_k) || lo_d[FLIT] != (m_k == TXW - 1)) begin
                    $display("WFC_SS FAIL: outbound word %0d of job %0d", m_k, outs); $finish; end
                m_k = m_k + 1;
                if (m_k == TXW) begin m_k = -1; outs = outs + 1; end
            end
        end
        if (ft != 4'd0) begin
            if (EXPECT_FAULT) begin $display("WFC_SS FAULT_AS_EXPECTED ft=%b at job %0d", ft, outs); $finish; end
            $display("WFC_SS FAIL: fault t_ft=%b (proto lnk - vmx) at cycle %0d, %0d out", ft, cyc, outs); $finish;
        end
    end
    initial begin
        wait (rst_n);
        while (outs < njob && cyc < H0 + njob * P + 20000) @(posedge fclk);
        if (outs < njob) begin $display("WFC_SS FAIL: timeout, %0d of %0d out", outs, njob); $finish; end
        repeat (200) @(posedge fclk);
        if (ft != 0) begin $display("WFC_SS FAIL: late fault %b", ft); $finish; end
        if (EXPECT_FAULT) begin $display("WFC_SS FAIL: expected a fault, none raised"); $finish; end
`ifdef DUMP
        $fclose(ofd);
`endif
        $display("WFC_SS PASS jobs=%0d starts=%0d period=%0d rx_tx_min=%0d rx_tx_max=%0d done_tx_min=%0d done_tx_max=%0d hdr_period=%0.2f",
                 njob, starts, P, rx_tx_min, rx_tx_max, d_tx_min, d_tx_max, 1.0 * (last_hdr - first_hdr) / (njob - 1));
        $finish;
    end
endmodule
