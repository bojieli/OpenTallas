`timescale 1ns/1ps
// tb_hgi_vm_ports_tput (hgi-1010/vm 2026-10-10): VM.PORTS production-shape throughput bench.
//   ot_hgi_vm_unit at the production client plan (hgi_vm5 / ot_hgi_vm_die): NC 9 packet clients, the DMA wide write
//   port WP 32 WDIRECT, RP 96 (read groups lgW / lgE / DMA source), W2 96 (write groups lgW / lgE / ROW_GATHER sink),
//   LQ 32 credits a lane.  The stimulus is the DS AR 1M token's VM traffic on the S2 schedule
//   (tools/hgi_vm_ports_trace.py --out TRACE): each record's sectors are offered on its port from the record's
//   priced start cycle, as fast as the port's protocol allows (wide lanes: one request a lane an edge within the
//   lane's credits; packet clients: OUT 4 outstanding; DMA port: one sector a lane an edge, never back-pressured).
//   Phase 0 fills all 32,768 sectors through the DMA port (no x in the ECC words).  The bench prints one
//   "REC rid cycle" line a record (the edge its last sector was served, trace time) and the packet round trip;
//   tools/hgi_vm_ports_trace.py --report turns them into the VM.PORTS ratio against the priced record times.
//   Checks: every sector served, no status fault (proto / conflict / credit overflow, mask, UE), no lane FIFO overflow.
//   build: verilator --binary --timing +incdir+TRACE -DTRACE=\"TRACE\" (run_vm_ports_tput.sh)
module tb_vmp_lanes #(
    parameter integer KIND = 0,          // 0 wide read group, 1 wide write group, 2 DMA wide write port
    parameter integer N = 1,
    parameter integer NREC = 1,
    parameter FILE = "",
    parameter OFILE = "",
    parameter RFILE = ""
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               on,
    input  integer            tcyc,
    output reg  [32*16-1:0]   rq,        // KIND 0
    input  wire [31:0]        rq_cr,
    input  wire [32*257-1:0]  rr,
    output reg  [32*280-1:0]  wq,        // KIND 1 / 2
    input  wire [31:0]        w_cr,      // KIND 1 credits (KIND 2: none)
    input  wire [31:0]        w_done
);
    reg [35:0] ent [0:N-1];
    reg [31:0] off [0:32];
    reg [31:0] rstart [0:NREC-1];
    integer    lastd [0:NREC-1];
    initial begin
        $readmemh(FILE, ent); $readmemh(OFILE, off); $readmemh(RFILE, rstart);
        for (integer i = 0; i < NREC; i = i + 1) lastd[i] = -1;
    end
    integer ptr [0:31]; integer cr [0:31];
    reg [11:0] fq [0:31][0:127]; integer fh [0:31], ft [0:31];
    integer served = 0, total = 0, errors = 0, issued = 0;
    initial begin
        for (integer l = 0; l < 32; l = l + 1) begin ptr[l] = 0; cr[l] = 32; fh[l] = 0; ft[l] = 0; end
        #1 total = off[32];
        for (integer l = 0; l < 32; l = l + 1) ptr[l] = off[l];
    end
    always @(negedge clk) begin
        rq = '0; wq = '0;
        if (on) for (integer l = 0; l < 32; l = l + 1) begin : lane
            reg [35:0] e; integer rid;
            if (ptr[l] < off[l + 1]) begin
                e = ent[ptr[l]]; rid = e[35:15];
                if (rstart[rid] <= tcyc && (KIND == 2 || cr[l] > 0) && ft[l] - fh[l] < 128) begin
                    if (KIND == 0) rq[l*16 +: 16] = {1'b1, e[14:0]};
                    else wq[l*280 +: 280] = {1'b1, e[14:0], {8{17'h0, e[14:0]}}, 8'hFF};
                    fq[l][ft[l] % 128] = 12'(rid); ft[l] = ft[l] + 1; ptr[l] = ptr[l] + 1; issued = issued + 1;
                    if (KIND != 2) cr[l] = cr[l] - 1;
                end
            end
        end
    end
    always @(posedge clk) if (rst_n) for (integer l = 0; l < 32; l = l + 1) begin : rsp
        reg got;
        if (KIND == 0 && rq_cr[l]) cr[l] = cr[l] + 1;
        if (KIND == 1 && w_cr[l]) cr[l] = cr[l] + 1;
        got = (KIND == 0) ? rr[l*257 + 256] : w_done[l];
        if (got === 1'bx) begin errors = errors + 1; $display("ERR kind %0d lane %0d response valid x", KIND, l); end
        else if (got) begin
            if (fh[l] == ft[l]) begin errors = errors + 1; $display("ERR kind %0d lane %0d response without request", KIND, l); end
            else begin lastd[fq[l][fh[l] % 128]] = tcyc; fh[l] = fh[l] + 1; served = served + 1; end
        end
    end
endmodule

module tb_vmp_pkt #(
    parameter integer C = 0,
    parameter integer N = 1,
    parameter integer E = 0,             // real entries (0: an idle client)
    parameter integer NREC = 1,
    parameter FILE = "",
    parameter RFILE = ""
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          on,
    input  integer       tcyc,
    output reg  [337:0]  cq,
    input  wire [273:0]  cr
);
    reg [35:0] ent [0:N-1];
    reg [31:0] rstart [0:NREC-1];
    integer    lastd [0:NREC-1];
    initial begin
        $readmemh(FILE, ent); $readmemh(RFILE, rstart);
        for (integer i = 0; i < NREC; i = i + 1) lastd[i] = -1;
    end
    integer ptr = 0, outst = 0, served = 0, errors = 0, rtt_sum = 0, rtt_n = 0;
    reg [11:0] fq [0:7]; integer ft_ [0:7]; integer fh = 0, ft = 0;
    wire integer total = E;
    always @(negedge clk) begin
        cq = '0;
        if (on && ptr < E && outst < 4) begin : iss
            reg [35:0] e; integer rid;
            e = ent[ptr]; rid = e[35:16];
            if (rstart[rid] <= tcyc) begin
                cq = {1'b1, e[15], 15'd0, 12'd0, 5'd0, {8{17'h0, e[14:0]}}, 32'hFFFFFFFF, 16'(ptr)};
                cq[309 +: 15] = e[14:0];
                fq[ft % 8] = 12'(rid); ft_[ft % 8] = tcyc; ft = ft + 1; ptr = ptr + 1; outst = outst + 1;
            end
        end
    end
    always @(posedge clk) if (rst_n) begin
        if (cr[273] === 1'bx) begin errors = errors + 1; $display("ERR client %0d response valid x", C); end
        else if (cr[273]) begin
            if (fh == ft) begin errors = errors + 1; $display("ERR client %0d response without request", C); end
            else begin
                lastd[fq[fh % 8]] = tcyc; rtt_sum = rtt_sum + (tcyc - ft_[fh % 8]); rtt_n = rtt_n + 1;
                fh = fh + 1; outst = outst - 1; served = served + 1;
            end
        end
    end
endmodule

module tb_hgi_vm_ports_tput;
`include "cfg.svh"
`ifndef TRACE
`define TRACE "trace"
`endif
`ifndef VMMUT
`define VMMUT 0
`endif
    localparam integer NC = 9, RP = 96, W2 = 96, LQ = 32;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0, t0 = 0, tcyc = -1;
    always @(posedge clk) begin cyc <= cyc + 1; end
    always @(negedge clk) tcyc = (t0 > 0) ? cyc - t0 : -1;
    wire [NC*338-1:0] cq; wire [NC*274-1:0] cr; wire [18:0] status;
    reg  [32*280-1:0] wq_pre = 0; wire [32*280-1:0] wq_tr; wire [31:0] wq_done;
    wire [RP*16-1:0] rq; wire [RP-1:0] rq_cr; wire [RP*257-1:0] rr;
    wire [W2*280-1:0] w2q; wire [W2-1:0] w2q_cr, w2q_done;
    reg on = 0, pre = 0;
    ot_hgi_vm_unit #(.NC(NC), .WP(32), .WDIRECT(1), .RP(RP), .W2(W2), .LQ(LQ), .MUT(`VMMUT)) dut (.clk(clk), .rst_n(rst_n),
        .cq(cq), .cr(cr), .status(status), .wq(pre ? wq_pre : wq_tr), .wq_done(wq_done), .rq(rq), .rq_cr(rq_cr), .rr(rr),
        .w2q(w2q), .w2q_cr(w2q_cr), .w2q_done(w2q_done));
    wire [32*280-1:0] nw0, nw1, nw2, nw3, nw4; wire [32*16-1:0] nr0, nr1, nr2, nr3;
    tb_vmp_lanes #(.KIND(0), .N(N_R0_lgW), .NREC(NREC), .FILE({`TRACE, "/R0_lgW.hex"}), .OFILE({`TRACE, "/R0_lgW_off.hex"}),
        .RFILE({`TRACE, "/rec.hex"})) u_r0 (.clk(clk), .rst_n(rst_n), .on(on), .tcyc(tcyc), .rq(rq[0 +: 512]), .rq_cr(rq_cr[0 +: 32]),
        .rr(rr[0 +: 32*257]), .wq(nw0), .w_cr(32'd0), .w_done(32'd0));
    tb_vmp_lanes #(.KIND(0), .N(N_R1_lgE), .NREC(NREC), .FILE({`TRACE, "/R1_lgE.hex"}), .OFILE({`TRACE, "/R1_lgE_off.hex"}),
        .RFILE({`TRACE, "/rec.hex"})) u_r1 (.clk(clk), .rst_n(rst_n), .on(on), .tcyc(tcyc), .rq(rq[512 +: 512]), .rq_cr(rq_cr[32 +: 32]),
        .rr(rr[32*257 +: 32*257]), .wq(nw1), .w_cr(32'd0), .w_done(32'd0));
    tb_vmp_lanes #(.KIND(0), .N(N_R2_dma), .NREC(NREC), .FILE({`TRACE, "/R2_dma.hex"}), .OFILE({`TRACE, "/R2_dma_off.hex"}),
        .RFILE({`TRACE, "/rec.hex"})) u_r2 (.clk(clk), .rst_n(rst_n), .on(on), .tcyc(tcyc), .rq(rq[1024 +: 512]), .rq_cr(rq_cr[64 +: 32]),
        .rr(rr[64*257 +: 32*257]), .wq(nw2), .w_cr(32'd0), .w_done(32'd0));
    tb_vmp_lanes #(.KIND(1), .N(N_W0_lgW), .NREC(NREC), .FILE({`TRACE, "/W0_lgW.hex"}), .OFILE({`TRACE, "/W0_lgW_off.hex"}),
        .RFILE({`TRACE, "/rec.hex"})) u_w0 (.clk(clk), .rst_n(rst_n), .on(on), .tcyc(tcyc), .rq(nr0), .rq_cr(32'd0), .rr({32*257{1'b0}}),
        .wq(w2q[0 +: 32*280]), .w_cr(w2q_cr[0 +: 32]), .w_done(w2q_done[0 +: 32]));
    tb_vmp_lanes #(.KIND(1), .N(N_W1_lgE), .NREC(NREC), .FILE({`TRACE, "/W1_lgE.hex"}), .OFILE({`TRACE, "/W1_lgE_off.hex"}),
        .RFILE({`TRACE, "/rec.hex"})) u_w1 (.clk(clk), .rst_n(rst_n), .on(on), .tcyc(tcyc), .rq(nr1), .rq_cr(32'd0), .rr({32*257{1'b0}}),
        .wq(w2q[32*280 +: 32*280]), .w_cr(w2q_cr[32 +: 32]), .w_done(w2q_done[32 +: 32]));
    tb_vmp_lanes #(.KIND(1), .N(N_W2_coll), .NREC(NREC), .FILE({`TRACE, "/W2_coll.hex"}), .OFILE({`TRACE, "/W2_coll_off.hex"}),
        .RFILE({`TRACE, "/rec.hex"})) u_w2 (.clk(clk), .rst_n(rst_n), .on(on), .tcyc(tcyc), .rq(nr2), .rq_cr(32'd0), .rr({32*257{1'b0}}),
        .wq(w2q[64*280 +: 32*280]), .w_cr(w2q_cr[64 +: 32]), .w_done(w2q_done[64 +: 32]));
    tb_vmp_lanes #(.KIND(2), .N(N_WP_dma), .NREC(NREC), .FILE({`TRACE, "/WP_dma.hex"}), .OFILE({`TRACE, "/WP_dma_off.hex"}),
        .RFILE({`TRACE, "/rec.hex"})) u_wp (.clk(clk), .rst_n(rst_n), .on(on), .tcyc(tcyc), .rq(nr3), .rq_cr(32'd0), .rr({32*257{1'b0}}),
        .wq(wq_tr), .w_cr(32'd0), .w_done(pre ? 32'd0 : wq_done));
    tb_vmp_pkt #(.C(0), .N(N_P0_idx), .E(E_P0_idx), .NREC(NREC), .FILE({`TRACE, "/P0_idx.hex"}), .RFILE({`TRACE, "/rec.hex"})) u_p0
        (.clk(clk), .rst_n(rst_n), .on(on), .tcyc(tcyc), .cq(cq[0 +: 338]), .cr(cr[0 +: 274]));
    tb_vmp_pkt #(.C(1), .N(N_P1_argmax), .E(E_P1_argmax), .NREC(NREC), .FILE({`TRACE, "/P1_argmax.hex"}), .RFILE({`TRACE, "/rec.hex"})) u_p1
        (.clk(clk), .rst_n(rst_n), .on(on), .tcyc(tcyc), .cq(cq[338 +: 338]), .cr(cr[274 +: 274]));
    tb_vmp_pkt #(.C(2), .N(N_P2_coll), .E(E_P2_coll), .NREC(NREC), .FILE({`TRACE, "/P2_coll.hex"}), .RFILE({`TRACE, "/rec.hex"})) u_p2
        (.clk(clk), .rst_n(rst_n), .on(on), .tcyc(tcyc), .cq(cq[676 +: 338]), .cr(cr[548 +: 274]));
    assign cq[NC*338-1:3*338] = '0;
    // phase 0: fill every sector through the DMA port
    integer pre_s = 0;
    always @(negedge clk) begin
        wq_pre = '0;
        if (pre && pre_s < 32768) begin
            for (integer b = 0; b < 32; b = b + 1) wq_pre[b*280 +: 280] = {1'b1, 15'(pre_s + b), {8{17'h0, 15'(pre_s + b)}}, 8'hFF};
            pre_s = pre_s + 32;
        end
    end
    integer errors = 0, left, last_t, served_all, total_all;
    initial begin
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        @(posedge clk); pre = 1; wait (pre_s >= 32768); repeat (8) @(posedge clk); pre = 0;
        repeat (8) @(posedge clk); t0 = cyc + 1; on = 1;
        last_t = 0;
        forever begin
            repeat (1024) @(posedge clk);
            served_all = u_r0.served + u_r1.served + u_r2.served + u_w0.served + u_w1.served + u_w2.served + u_wp.served
                       + u_p0.served + u_p1.served + u_p2.served;
            total_all = u_r0.total + u_r1.total + u_r2.total + u_w0.total + u_w1.total + u_w2.total + u_wp.total
                      + u_p0.total + u_p1.total + u_p2.total;
            if (tcyc % 65536 < 1024) $display("t %0d served %0d of %0d", tcyc, served_all, total_all);
            if (served_all >= total_all) break;
            if (tcyc > 4 * 600000) begin errors = errors + 1; $display("ERR timeout: served %0d of %0d", served_all, total_all); break; end
        end
        repeat (16) @(posedge clk);
        errors = errors + u_r0.errors + u_r1.errors + u_r2.errors + u_w0.errors + u_w1.errors + u_w2.errors + u_wp.errors
               + u_p0.errors + u_p1.errors + u_p2.errors;
        if (status[18]) begin errors = errors + 1; $display("ERR status proto/conflict/credit"); end
        if (status[17] || status[16]) begin errors = errors + 1; $display("ERR status mask/ue %b", status[18:16]); end
        for (integer i = 0; i < NREC; i = i + 1) begin : rl
            integer m;
            m = u_r0.lastd[i];
            if (u_r1.lastd[i] > m) m = u_r1.lastd[i]; if (u_r2.lastd[i] > m) m = u_r2.lastd[i];
            if (u_w0.lastd[i] > m) m = u_w0.lastd[i]; if (u_w1.lastd[i] > m) m = u_w1.lastd[i];
            if (u_w2.lastd[i] > m) m = u_w2.lastd[i]; if (u_wp.lastd[i] > m) m = u_wp.lastd[i];
            if (u_p0.lastd[i] > m) m = u_p0.lastd[i]; if (u_p1.lastd[i] > m) m = u_p1.lastd[i];
            if (u_p2.lastd[i] > m) m = u_p2.lastd[i];
            if (m < 0) begin errors = errors + 1; $display("ERR record %0d never served", i); end
            $display("REC %0d %0d", i, m);
        end
        $display("PKT_RTT idx %0d ops mean %0.2f edges", u_p0.rtt_n, u_p0.rtt_n ? real'(u_p0.rtt_sum) / u_p0.rtt_n : 0.0);
        $display("SERVED %0d sectors, trace end %0d edges", served_all, tcyc);
        if (errors == 0) $display("HGI_VM_PORTS PASS"); else $display("HGI_VM_PORTS FAIL errors=%0d", errors);
        $finish;
    end
endmodule
