`timescale 1ns/1ps
// tb_hgi_vm_lanes (hgi-unitrate 2026-10-10): the VM unit's client wide lanes under full concurrent load, exact.
//   ot_hgi_vm_unit NC 2, WP 32 WDIRECT (the DMA front's wide write port, never back-pressured), RP 64 / W2 64 (two
//   client groups: the SU and the SFU wide stage / drain), LQ credits a lane.
//   Phase 1: the DMA port fills the read-only region RO (sectors 0 .. 8191) at 32 sectors an edge.
//   Phase 2 (all at once): read groups 0 and 1 each stream the whole of RO (lane b walks b, b+32, ...; responses must
//   come back in request order with RO's data); write groups 0 / 1 write W0 / W1 twice (full masks, then random word
//   masks with new data); the DMA port keeps writing region D on every other edge (all 32 lanes); packet client 0 reads RO at random and
//   writes region P.  Phase 3: client 1 reads back every written sector against the reference model.
//   Checks: every response word, every final word, DMA writes all done 2 edges after issue (no stall), no status
//   fault (proto / conflict / credit overflow).  Reports each group's lane rate.   +MUT=n selects ot_hgi_vm_core MUT.
module tb_hgi_vm_lanes;
`ifndef VMMUT
`define VMMUT 0
`endif
    localparam integer NG = 2, RP = 32 * NG, W2 = 32 * NG, LQ = 8;
    localparam integer RO0 = 0, RON = 8192, W00 = 8192, W10 = 12288, WN = 4096, D0 = 16384, DN = 8192, P0 = 24576, PN = 1024;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg [2*338-1:0] cq = 0; wire [2*274-1:0] cr; wire [18:0] status;
    reg [32*280-1:0] wq = 0; wire [31:0] wq_done;
    reg [RP*16-1:0] rq = 0; wire [RP-1:0] rq_cr; wire [RP*257-1:0] rr;
    reg [W2*280-1:0] w2q = 0; wire [W2-1:0] w2q_cr, w2q_done;
    ot_hgi_vm_unit #(.NC(2), .WP(32), .WDIRECT(1), .RP(RP), .W2(W2), .LQ(LQ), .MUT(`VMMUT)) dut (.clk(clk), .rst_n(rst_n),
        .cq(cq), .cr(cr), .status(status), .wq(wq), .wq_done(wq_done), .rq(rq), .rq_cr(rq_cr), .rr(rr), .w2q(w2q),
        .w2q_cr(w2q_cr), .w2q_done(w2q_done));
    // reference model
    reg [255:0] mem [0:32767]; reg wrtn [0:32767];          // the model and which sectors were ever written
    initial for (integer x = 0; x < 32768; x = x + 1) wrtn[x] = 1'b0;
    function automatic [255:0] rnd256(input integer a, input integer salt);
        for (integer w = 0; w < 8; w = w + 1) rnd256[32*w +: 32] = 32'(a * 2654435761 + w * 40503 + salt * 97) ^ 32'h9E3779B9;
    endfunction
    function automatic [255:0] merge(input [255:0] old, input [255:0] nw, input [7:0] m);
        for (integer w = 0; w < 8; w = w + 1) merge[32*w +: 32] = m[w] ? nw[32*w +: 32] : old[32*w +: 32];
    endfunction
    integer errors = 0;
    // ---- DMA port driver: dma_on streams region D (or RO in phase 1), full masks, every lane every edge
    reg dma_on = 0; reg dma_ro = 0; integer dma_next = 0, dma_iss = 0, dma_done = 0;
    always @(negedge clk) begin
        wq = 0;
        if (dma_on && (dma_ro || cyc % 2 == 0)) for (integer b = 0; b < 32; b = b + 1) begin : dl
            integer s; s = (dma_ro ? RO0 : D0) + (dma_next % (dma_ro ? RON : DN)) + b;
            wq[b*280 +: 280] = {1'b1, 15'(s), rnd256(s, dma_ro ? 1 : 2 + dma_next / DN), 8'hFF};
            mem[s] = rnd256(s, dma_ro ? 1 : 2 + dma_next / DN); wrtn[s] = 1'b1;
        end
        if (dma_on && (dma_ro || cyc % 2 == 0)) begin dma_next = dma_next + 32; dma_iss = dma_iss + 32; end
    end
    always @(posedge clk) dma_done = dma_done + $countones(wq_done);
    // ---- read groups: lane state
    integer rnx [0:RP-1]; integer rcr [0:RP-1]; integer rexp [0:RP-1][0:63]; integer rh [0:RP-1], rt [0:RP-1];
    integer rgot [0:NG-1]; reg rd_on = 0; integer r_t0 [0:NG-1], r_t1 [0:NG-1];
    always @(negedge clk) begin
        for (integer l = 0; l < RP; l = l + 1) begin
            rq[l*16 +: 16] = 0;
            if (rd_on && rnx[l] < RON && rcr[l] > 0) begin
                rq[l*16 +: 16] = {1'b1, 15'(RO0 + rnx[l])}; rexp[l][rt[l] % 64] = RO0 + rnx[l]; rt[l] = rt[l] + 1;
                rnx[l] = rnx[l] + 32; rcr[l] = rcr[l] - 1;
            end
        end
    end
    always @(posedge clk) if (rst_n) for (integer l = 0; l < RP; l = l + 1) begin
        if (rq_cr[l]) rcr[l] = rcr[l] + 1;
        if (rr[l*257 + 256] === 1'bx) begin errors = errors + 1; $display("ERR lane %0d response valid is x", l); end
        if (rr[l*257 + 256]) begin
            if (rh[l] == rt[l]) begin errors = errors + 1; $display("ERR lane %0d: response without a request", l); end
            else begin
                if (rr[l*257 +: 256] !== mem[rexp[l][rh[l] % 64]]) begin
                    if (errors < 10) $display("ERR read lane %0d sector %0d got %h", l, rexp[l][rh[l] % 64], rr[l*257 +: 32]);
                    errors = errors + 1;
                end
                rh[l] = rh[l] + 1; rgot[l / 32] = rgot[l / 32] + 1; r_t1[l / 32] = cyc;
            end
        end
    end
    // ---- write groups: two passes over W0 / W1 (pass 0 full masks, pass 1 random masks)
    integer wnx [0:W2-1]; integer wcr [0:W2-1]; integer wdn [0:NG-1]; integer wiss [0:NG-1]; reg wr_on = 0;
    always @(negedge clk) begin
        for (integer l = 0; l < W2; l = l + 1) begin
            w2q[l*280 +: 280] = 0;
            if (wr_on && wnx[l] < 2 * WN && wcr[l] > 0) begin : wl
                integer s, pass; reg [7:0] m; reg [255:0] d;
                pass = wnx[l] / WN; s = ((l / 32) ? W10 : W00) + (wnx[l] % WN);
                m = pass ? 8'(s * 37 + 11) : 8'hFF; d = rnd256(s, 100 + pass);
                w2q[l*280 +: 280] = {1'b1, 15'(s), d, m}; mem[s] = merge(mem[s], d, m); wrtn[s] = 1'b1;
                wnx[l] = wnx[l] + 32; wcr[l] = wcr[l] - 1; wiss[l / 32] = wiss[l / 32] + 1;
            end
        end
    end
    always @(posedge clk) if (rst_n) for (integer l = 0; l < W2; l = l + 1) begin
        if (w2q_cr[l]) wcr[l] = wcr[l] + 1;
        if (w2q_done[l]) wdn[l / 32] = wdn[l / 32] + 1;
    end
    // ---- packet clients: client 0 random RO reads + P writes during phase 2; client 1 the final readback
    task automatic pkt(input integer c, input we, input integer sec, input [255:0] data, output [255:0] qd);
        integer tw;
        begin
            @(negedge clk); cq[c*338 +: 338] = {1'b1, we, 15'd0, 12'(sec), 5'd0, data, 32'hFFFFFFFF, 16'h0BE0};
            cq[c*338 + 309 +: 15] = 15'(sec);
            @(negedge clk); cq[c*338 + 337] = 1'b0;
            tw = 0; while (!cr[c*274 + 273] && tw < 2000) begin @(negedge clk); tw = tw + 1; end
            if (tw >= 2000) begin errors = errors + 1; $display("ERR client %0d timeout", c); end
            qd = cr[c*274 +: 256];
        end
    endtask
    reg [255:0] qd; integer pk_n = 0; reg pk_on = 0;
    initial begin : client0
        integer s;
        wait (pk_on);
        while (pk_on) begin
            s = $urandom % RON; pkt(0, 1'b0, RO0 + s, 256'd0, qd);
            if (qd !== mem[RO0 + s]) begin errors = errors + 1; $display("ERR client RO read %0d", s); end
            s = P0 + ($urandom % PN); pkt(0, 1'b1, s, rnd256(s, 7), qd); mem[s] = rnd256(s, 7); wrtn[s] = 1'b1; pk_n = pk_n + 2;
        end
    end
    integer t2;
    initial begin
        for (integer l = 0; l < RP; l = l + 1) begin rnx[l] = l % 32; rcr[l] = LQ; rh[l] = 0; rt[l] = 0; end
        for (integer l = 0; l < W2; l = l + 1) begin wnx[l] = l % 32; wcr[l] = LQ; end
        for (integer g = 0; g < NG; g = g + 1) begin rgot[g] = 0; wdn[g] = 0; wiss[g] = 0; end
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        // phase 1: DMA fills RO
        // dma_on / rd_on / wr_on change at posedges only: the negedge drivers see them stable (no simulator race)
        @(posedge clk); dma_ro = 1; dma_next = 0; dma_on = 1; repeat (RON / 32) @(posedge clk); dma_on = 0; dma_ro = 0; dma_next = 0;
        repeat (10) @(negedge clk);
        // phase 2: everything at once
        @(posedge clk); t2 = cyc; dma_on = 1; rd_on = 1; wr_on = 1; pk_on = 1;
        for (integer g = 0; g < NG; g = g + 1) r_t0[g] = cyc;
        begin : wt integer t; t = 0;
            while ((rgot[0] + rgot[1] < 2 * RON || wdn[0] + wdn[1] < 2 * 2 * WN) && t < 200000) begin @(negedge clk); t = t + 1; end
        end
        @(posedge clk); dma_on = 0; rd_on = 0; wr_on = 0; pk_on = 0; repeat (40) @(negedge clk);
        if (dma_done != dma_iss) begin errors = errors + 1; $display("ERR DMA done %0d of %0d", dma_done, dma_iss); end
        // phase 3: readback of every written region
        for (integer s = 0; s < 32768; s = s + 1)
            if (wrtn[s] && ((s >= W00 && s < W10 + WN) || (s >= D0 && s < D0 + DN) || (s >= P0 && s < P0 + PN) || (s < RON && s % 97 == 0))) begin
                pkt(1, 1'b0, s, 256'd0, qd);
                if (qd !== mem[s]) begin if (errors < 20) $display("ERR final sector %0d got %h want %h", s, qd[31:0], mem[s][31:0]); errors = errors + 1; end
            end
        if (^status === 1'bx) begin errors = errors + 1; $display("ERR status has x: %b", status); end
        if (status[18]) begin errors = errors + 1; $display("ERR status proto/conflict/credit %b", status[18:16]); end
        if (status[17] || status[16]) begin errors = errors + 1; $display("ERR status mask/ue %b", status[18:16]); end
        for (integer g = 0; g < NG; g = g + 1)
            $display("GROUP %0d read %0d sectors in %0d edges (%0.3f a lane an edge), wrote %0d", g, rgot[g], r_t1[g] - r_t0[g],
                     real'(rgot[g]) / 32.0 / real'(r_t1[g] - r_t0[g]), wdn[g]);
        $display("DMA %0d sector writes, all done; packet ops %0d", dma_done, pk_n);
        // fairness: the packet client kept making progress under the full wide load (age promotion)
        if (pk_n < 20) begin errors = errors + 1; $display("ERR packet client starved: %0d ops in phase 2", pk_n); end
        if (errors == 0) $display("HGI_VM_LANES PASS"); else $display("HGI_VM_LANES FAIL errors=%0d", errors);
        $finish;
    end
endmodule
