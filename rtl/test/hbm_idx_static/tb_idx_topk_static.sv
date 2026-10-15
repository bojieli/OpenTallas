`timescale 1ns/1ps
`default_nettype none
// Static IDX.TOPK on the ACTUAL SW VM slice master hfd_hgi_vms_static_SW (8 static banks, 24 real SRAM macros,
// static hub, ring stops, replay, status). The engine reads through read group 4 (IDX) and writes through
// packet client 4 ('idx' record, cq338/cr274). The calendar (rslot/bank_enable/wslot/response_enable) is the
// compiler image cal.mem from tools/hbm_idx_topk_static_vectors.py; this bench never derives it from the DUT.
// Checks: every done/fault edge, every output sector (incl. untouched neighbour words), slice status 0.
module tb_idx_topk_static;
    parameter integer MUT = 0;
    localparam integer NE = 16384, NPRE = 4096, NCHK = 1024, NREC = 64;
    reg clk = 0; always #5 clk = ~clk;
    reg rst_n = 0;
    // slice calendar / ports
    reg [2365:0] cq_all = 0; wire [1917:0] cr_all;
    reg [15:0] client_seq = 0; reg [7:0] response_enable = 0; reg [15:0] response_seq = 0;
    reg [7:0] bank_enable = 0; reg [23:0] bank_client = 0;
    reg [7:0] rslot_v = 0, wslot_v = 0; reg [23:0] rslot = 0, wslot = 0;
    reg [679:0] rq_bench = 0; wire [679:0] rq; wire [10279:0] rr;
    reg [2247:0] dq = 0; wire [7:0] wq_done, dq_done, kq_done;
    wire [2223:0] cw_out, ccw_out; wire [143:0] bank_status; wire [2:0] hub_status, ring_fault; wire [1:0] mirror_busy;
    wire [18:0] vmstat;
    // engine
    reg go = 0; reg [3:0] k = 0; reg order = 0, a_mirror = 0, has_r = 0; reg [19:0] n = 0, m = 0;
    reg [17:0] a_base = 0, a_str = 0, o_base = 0, o_str = 0, r_base = 0, r_str = 0;
    wire [135:0] vm_rq; wire [337:0] cq; wire [1:0] cq_seq; wire busy, done, fault;
    ot_hbm_idx_topk_static #(.MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .sid(2'd0), .go(go), .k(k), .order(order),
        .n(n), .m(m), .a_mirror(a_mirror), .a_base(a_base), .a_str(a_str), .o_mirror(1'b0), .o_base(o_base),
        .o_str(o_str), .has_r(has_r), .r_base(r_base), .r_str(r_str), .vm_rq(vm_rq), .vm_rr(rr[4*2056 +: 2056]),
        .cq(cq), .cq_seq(cq_seq), .cr(cr_all[4*274 +: 274]), .busy(busy), .done(done), .fault(fault));
    assign rq = {vm_rq, rq_bench[4*136-1:0]};   // IDX is the top read group (4 of 0..4)
    always @* begin cq_all = 0; cq_all[4*338 +: 338] = cq; client_seq = 0; client_seq[8 +: 2] = cq_seq; end
    hfd_hgi_vms_static_SW slice(.clk_bank({8{clk}}), .clk_hub(clk), .clk_ring({2{clk}}), .clk_replay(clk), .rst_n(rst_n),
        .cq(cq_all), .cr(cr_all), .client_seq(client_seq), .response_enable(response_enable), .response_seq(response_seq),
        .bank_enable(bank_enable), .bank_client(bank_client), .hub_ring_enable(2'd0), .hub_ring_client(6'd0),
        .rslot_v(rslot_v), .wslot_v(wslot_v), .rslot(rslot), .wslot(wslot), .rq(rq), .rr(rr),
        .wq(2248'd0), .wq_done(wq_done), .dq(dq), .kq(2248'd0), .dq_done(dq_done), .kq_done(kq_done),
        .cw_in(2224'd0), .ccw_in(2224'd0), .cw_out(cw_out), .ccw_out(ccw_out), .ring_tx_enable(2'd0),
        .ring_tx_source(6'd0), .replay_enable(1'b0), .replay_source(1'b0), .bank_status(bank_status),
        .hub_status(hub_status), .mirror_busy(mirror_busy), .vmstat(vmstat), .ring_fault(ring_fault));
    // images
    reg [26:0] cal [0:NE-1];
    reg [271:0] pre [0:NPRE-1];
    reg [271:0] chk [0:NCHK-1];
    integer nrec, last, npre, nchk, fd, rc;
    integer rG [0:NREC-1], rEnd [0:NREC-1], rF [0:NREC-1];
    integer ecnt = 0, base = 0, errors = 0, dones = 0, faults = 0, checked = 0;
    always @(posedge clk) ecnt <= ecnt + 1;
    // done / fault must rise exactly on the compiler edge
    integer exp_done [0:NE-1], exp_fault [0:NE-1];
    always @(negedge clk) if (rst_n && base != 0) begin
        if (ecnt - base >= 0 && ecnt - base < NE) begin
            if (done !== (exp_done[ecnt - base] != 0) || fault !== (exp_fault[ecnt - base] != 0)) begin
                errors = errors + 1;
                if (errors < 10) $display("END MISMATCH ecnt %0d done %b fault %b expected %0d/%0d", ecnt - base, done, fault,
                    exp_done[ecnt - base], exp_fault[ecnt - base]);
            end
            if (done) dones = dones + 1;
            if (fault) faults = faults + 1;
        end
        if (bank_status !== 144'd0 || hub_status !== 3'd0 || ring_fault !== 3'd0) begin
            errors = errors + 1;
            if (errors < 10) $display("SLICE STATUS ecnt %0d bank %h hub %b", ecnt - base, bank_status, hub_status);
        end
    end
    integer i, e, b, rec_i;
    reg [255:0] d;
    reg [31:0] x [0:14];
    initial begin
        for (i = 0; i < NE; i = i + 1) begin exp_done[i] = 0; exp_fault[i] = 0; cal[i] = 0; end
        fd = $fopen("rec.txt", "r");
        rc = $fscanf(fd, "%d %d\n", nrec, last);
        for (i = 0; i < nrec; i = i + 1) begin
            rc = $fscanf(fd, "%h %h %h %h %h %h %h %h %h %h %h %h %h %h %h\n", x[0], x[1], x[2], x[3], x[4], x[5], x[6],
                         x[7], x[8], x[9], x[10], x[11], x[12], x[13], x[14]);
            rG[i] = x[0]; rEnd[i] = x[1]; rF[i] = x[2];
            if (x[2]) exp_fault[x[1]] = 1; else exp_done[x[1]] = 1;
        end
        $fclose(fd);
        fd = $fopen("counts.txt", "r"); rc = $fscanf(fd, "%d %d", npre, nchk); $fclose(fd);
        $readmemh("cal.mem", cal); $readmemh("pre.mem", pre); $readmemh("chk.mem", chk);
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        // preload through the actual DMA port (wslot WG+4 = 5), one sector per bank per ecnt
        i = 0;
        while (i < npre) begin
            dq = 0; wslot_v = 0; wslot = 0;
            for (b = 0; b < 8; b = b + 1) if (i < npre && pre[i][258:256] == 3'(b) && !wslot_v[b]) begin
                wslot_v[b] = 1; wslot[b*3 +: 3] = 3'd5;
                dq[b*281 +: 281] = {1'b1, pre[i][271:256], pre[i][255:0], 8'hff};
                i = i + 1;
            end
            if (wslot_v == 0) begin $display("preload order"); $fatal(1, "bench"); end
            @(negedge clk);
        end
        dq = 0; wslot_v = 0; wslot = 0; repeat (12) @(negedge clk);
        // compiler calendar replay: entries for sample ecnt e are presented after ecnt e-1
        base = ecnt + 1;                 // schedule ecnt e == the posedge after which ecnt == base+e
        for (e = 0; e <= last; e = e + 1) begin
            rslot_v = 0; rslot = 0; bank_enable = 0; bank_client = 0; wslot_v = 0; wslot = 0;
            response_enable = 0; response_seq = 0; go = 0;
            for (b = 0; b < 8; b = b + 1) begin
                if (cal[e][b]) begin rslot_v[b] = 1; rslot[b*3 +: 3] = 3'd4; end
                if (cal[e][8+b]) begin bank_enable[b] = 1; bank_client[b*3 +: 3] = 3'd4; end
                if (cal[e][16+b]) begin wslot_v[b] = 1; wslot[b*3 +: 3] = 3'd3; end
            end
            if (cal[e][26]) begin response_enable[4] = 1; response_seq[8 +: 2] = cal[e][25:24]; end
            for (rec_i = 0; rec_i < nrec; rec_i = rec_i + 1) if (rG[rec_i] == e) begin
                    fd = $fopen("rec.txt", "r"); rc = $fscanf(fd, "%d %d\n", i, i);
                for (i = 0; i <= rec_i; i = i + 1)
                    rc = $fscanf(fd, "%h %h %h %h %h %h %h %h %h %h %h %h %h %h %h\n", x[0], x[1], x[2], x[3], x[4],
                                 x[5], x[6], x[7], x[8], x[9], x[10], x[11], x[12], x[13], x[14]);
                $fclose(fd);
                go = 1; k = x[3]; order = x[4]; n = x[5]; m = x[6]; a_mirror = x[7]; a_base = x[8]; a_str = x[9];
                o_base = x[10]; o_str = x[11]; has_r = x[12]; r_base = x[13]; r_str = x[14];
            end
            @(negedge clk);              // after this negedge, posedge base+e samples the values set above
        end
        go = 0; rslot_v = 0; bank_enable = 0; wslot_v = 0; response_enable = 0;
        repeat (16) @(negedge clk);
        // read back every output sector through read group 1 (actual bank path, fixed n+6 response)
        for (i = 0; i < nchk; i = i + 1) begin
            rq_bench = 0; rslot_v = 0; rslot = 0;
            b = chk[i][258:256];
            rq_bench[(1*8+b)*17 +: 17] = {1'b1, chk[i][271:256]};
            rslot_v[b] = 1; rslot[b*3 +: 3] = 3'd1;
            @(negedge clk); rq_bench = 0; rslot_v = 0; rslot = 0;
            repeat (6) @(negedge clk);
            if (rr[(1*8+b)*257 +: 257] !== {1'b1, chk[i][255:0]}) begin
                errors = errors + 1;
                if (errors < 20) $display("VM MISMATCH sector %h got %h expected %h", chk[i][271:256], rr[(1*8+b)*257 +: 256],
                    chk[i][255:0]);
            end
            checked = checked + 1;
        end
        $display("IDX_TOPK_STATIC MUT%0d records%0d dones%0d faults%0d sectors_checked%0d errors%0d schedule_edges%0d", MUT, nrec,
                 dones, faults, checked, errors, last);
        if (errors != 0 || checked != nchk || dones + faults != nrec) $fatal(1, "static TOPK on actual SW slice mismatch");
        $finish;
    end
endmodule
`default_nettype wire
