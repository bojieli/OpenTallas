`timescale 1ns/1ps
`default_nettype none
// Static ARGMAX.LOCAL on the ACTUAL SW VM slice master hfd_hgi_vms_static_SW (static hub, 8 banks, 24 SRAMs):
// VM rows read through read group 4 via the 4-leaf IDX share (argmax owner), O {value,id} written through the
// 'argmax' record client (packet client 0). STREAM rows enter on compiler edges (stream.mem: the SU reduce stream
// at its declared boundary). The calendar cal.mem comes from tools/hbm_argmax_static_vectors.py, never the DUT.
module tb_argmax_static;
    parameter integer MUT = 0;
    localparam integer NE = 16384, NPRE = 4096, NCHK = 1024;
    reg clk = 0; always #5 clk = ~clk;
    reg rst_n = 0;
    reg [2365:0] cq_all = 0; wire [1917:0] cr_all;
    reg [15:0] client_seq = 0; reg [7:0] response_enable = 0; reg [15:0] response_seq = 0;
    reg [7:0] bank_enable = 0; reg [23:0] bank_client = 0;
    reg [7:0] rslot_v = 0, wslot_v = 0; reg [23:0] rslot = 0, wslot = 0;
    reg [679:0] rq_bench = 0; wire [679:0] rq; wire [10279:0] rr;
    reg [2247:0] dq = 0; wire [7:0] wq_done, dq_done, kq_done;
    wire [2223:0] cw_out, ccw_out; wire [143:0] bank_status; wire [2:0] hub_status, ring_fault; wire [1:0] mirror_busy;
    wire [18:0] vmstat;
    reg go = 0, mode = 0, a_mirror = 0; reg [17:0] imm_a = 0, a_base = 0, n = 0, o_base = 0; reg [15:0] o_is = 0;
    reg [522:0] am_stream = 0;
    wire [135:0] am_rq, share_rq; wire [2055:0] am_rr; wire [337:0] cq; wire [1:0] cq_seq; wire busy, done, fault, nan_flag, share_fault;
    ot_hbm_argmax_static #(.MUT(MUT)) dut(.clk(clk), .rst_n(rst_n), .sid(2'd0), .die_id(8'd3), .go(go), .mode(mode),
        .imm_a(imm_a), .a_mirror(a_mirror), .a_base(a_base), .n(n), .o_base(o_base), .o_is(o_is), .vm_rq(am_rq),
        .vm_rr(am_rr), .am_stream(am_stream), .cq(cq), .cq_seq(cq_seq), .cr(cr_all[0 +: 274]), .busy(busy), .done(done),
        .fault(fault), .nan_flag(nan_flag));
    ot_hbm_idx_vm_share_static share(.clk_pair({4{clk}}), .rst_n(rst_n), .index_rq(136'd0), .topk_rq(136'd0),
        .argmax_rq(am_rq), .vm_rq(share_rq), .vm_rr(rr[4*2056 +: 2056]), .index_rr(), .topk_rr(), .argmax_rr(am_rr),
        .fault(share_fault));
    assign rq = {share_rq, rq_bench[4*136-1:0]};
    always @* begin cq_all = 0; cq_all[0 +: 338] = cq; client_seq = 0; client_seq[0 +: 2] = cq_seq; end
    hfd_hgi_vms_static_SW slice(.clk_bank({8{clk}}), .clk_hub(clk), .clk_ring({2{clk}}), .clk_replay(clk), .rst_n(rst_n),
        .cq(cq_all), .cr(cr_all), .client_seq(client_seq), .response_enable(response_enable), .response_seq(response_seq),
        .bank_enable(bank_enable), .bank_client(bank_client), .hub_ring_enable(2'd0), .hub_ring_client(6'd0),
        .rslot_v(rslot_v), .wslot_v(wslot_v), .rslot(rslot), .wslot(wslot), .rq(rq), .rr(rr),
        .wq(2248'd0), .wq_done(wq_done), .dq(dq), .kq(2248'd0), .dq_done(dq_done), .kq_done(kq_done),
        .cw_in(2224'd0), .ccw_in(2224'd0), .cw_out(cw_out), .ccw_out(ccw_out), .ring_tx_enable(2'd0),
        .ring_tx_source(6'd0), .replay_enable(1'b0), .replay_source(1'b0), .bank_status(bank_status),
        .hub_status(hub_status), .mirror_busy(mirror_busy), .vmstat(vmstat), .ring_fault(ring_fault));
    reg [26:0] cal [0:NE-1]; reg [522:0] stm [0:NE-1];
    reg [271:0] pre [0:NPRE-1]; reg [271:0] chk [0:NCHK-1];
    integer nrec, last, npre, nchk, fd, rc;
    integer rG [0:63]; reg [31:0] x [0:10]; reg [31:0] rx [0:63][0:10];
    integer ecnt = 0, base = 0, errors = 0, dones = 0, faults = 0, checked = 0, nans = 0, exp_nans = 0;
    always @(posedge clk) ecnt <= ecnt + 1;
    integer exp_done [0:NE-1], exp_fault [0:NE-1], exp_nan [0:NE-1];
    reg nan_seen;
    always @(negedge clk) if (rst_n && base != 0) begin
        if (ecnt - base >= 0 && ecnt - base < NE) begin
            if (done !== (exp_done[ecnt - base] != 0) || fault !== (exp_fault[ecnt - base] != 0)) begin
                errors = errors + 1;
                if (errors < 10) $display("END MISMATCH edge %0d done %b fault %b expected %0d/%0d", ecnt - base, done, fault,
                    exp_done[ecnt - base], exp_fault[ecnt - base]);
            end
            if (done || fault) begin
                if (nan_flag !== nan_seen) begin errors = errors + 1; $display("NAN FLAG edge %0d", ecnt - base); end
            end
            if (done) dones = dones + 1;
            if (fault) faults = faults + 1;
        end
        if (bank_status !== 144'd0 || hub_status !== 3'd0 || ring_fault !== 3'd0 || share_fault) begin
            errors = errors + 1;
            if (errors < 10) $display("SLICE STATUS edge %0d bank %h hub %b share %b", ecnt - base, bank_status, hub_status, share_fault);
        end
    end
    integer i, e, b, r;
    initial begin
        nan_seen = 0;
        for (i = 0; i < NE; i = i + 1) begin exp_done[i] = 0; exp_fault[i] = 0; cal[i] = 0; stm[i] = 0; end
        fd = $fopen("rec.txt", "r");
        rc = $fscanf(fd, "%d %d\n", nrec, last);
        for (i = 0; i < nrec; i = i + 1) begin
            rc = $fscanf(fd, "%h %h %h %h %h %h %h %h %h %h %h\n", x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9], x[10]);
            for (r = 0; r < 11; r = r + 1) rx[i][r] = x[r];
            rG[i] = x[0];
            if (x[2]) exp_fault[x[1]] = 1; else exp_done[x[1]] = 1;
        end
        $fclose(fd);
        fd = $fopen("counts.txt", "r"); rc = $fscanf(fd, "%d %d", npre, nchk); $fclose(fd);
        $readmemh("cal.mem", cal); $readmemh("stream.mem", stm); $readmemh("pre.mem", pre); $readmemh("chk.mem", chk);
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        i = 0;
        while (i < npre) begin
            dq = 0; wslot_v = 0; wslot = 0;
            for (b = 0; b < 8; b = b + 1) if (i < npre && pre[i][258:256] == 3'(b) && !wslot_v[b]) begin
                wslot_v[b] = 1; wslot[b*3 +: 3] = 3'd5;
                dq[b*281 +: 281] = {1'b1, pre[i][271:256], pre[i][255:0], 8'hff};
                i = i + 1;
            end
            @(negedge clk);
        end
        dq = 0; wslot_v = 0; wslot = 0; repeat (12) @(negedge clk);
        base = ecnt + 1;
        for (e = 0; e <= last; e = e + 1) begin
            rslot_v = 0; rslot = 0; bank_enable = 0; bank_client = 0; wslot_v = 0; wslot = 0;
            response_enable = 0; response_seq = 0; go = 0; am_stream = stm[e];
            for (b = 0; b < 8; b = b + 1) begin
                if (cal[e][b]) begin rslot_v[b] = 1; rslot[b*3 +: 3] = 3'd4; end
                if (cal[e][8+b]) begin bank_enable[b] = 1; bank_client[b*3 +: 3] = 3'd0; end
                if (cal[e][16+b]) begin wslot_v[b] = 1; wslot[b*3 +: 3] = 3'd3; end
            end
            if (cal[e][26]) begin response_enable[0] = 1; response_seq[0 +: 2] = cal[e][25:24]; end
            for (r = 0; r < nrec; r = r + 1) if (rG[r] == e) begin
                go = 1; mode = rx[r][4]; imm_a = rx[r][5]; a_mirror = rx[r][6]; a_base = rx[r][7]; n = rx[r][8];
                o_base = rx[r][9]; o_is = rx[r][10]; nan_seen = nan_seen | rx[r][3][0];
            end
            @(negedge clk);
        end
        go = 0; am_stream = 0; rslot_v = 0; bank_enable = 0; wslot_v = 0; response_enable = 0;
        repeat (16) @(negedge clk);
        for (i = 0; i < nchk; i = i + 1) begin
            rq_bench = 0; rslot_v = 0; rslot = 0;
            b = chk[i][258:256];
            rq_bench[(1*8+b)*17 +: 17] = {1'b1, chk[i][271:256]};
            rslot_v[b] = 1; rslot[b*3 +: 3] = 3'd1;
            @(negedge clk); rq_bench = 0; rslot_v = 0; rslot = 0;
            repeat (6) @(negedge clk);
            if (rr[(1*8+b)*257 +: 257] !== {1'b1, chk[i][255:0]}) begin
                errors = errors + 1;
                if (errors < 20) $display("VM MISMATCH sector %h got %h expected %h", chk[i][271:256], rr[(1*8+b)*257 +: 256], chk[i][255:0]);
            end
            checked = checked + 1;
        end
        $display("ARGMAX_STATIC MUT%0d records%0d dones%0d faults%0d sectors_checked%0d errors%0d schedule_edges%0d", MUT, nrec,
                 dones, faults, checked, errors, last);
        if (errors != 0 || checked != nchk || dones + faults != nrec) $fatal(1, "static ARGMAX on actual SW slice mismatch");
        $finish;
    end
endmodule
`default_nettype wire
