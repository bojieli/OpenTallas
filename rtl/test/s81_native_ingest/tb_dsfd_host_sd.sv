`timescale 1ns/1ps
// s81-svceng-1011 host side: dsfd_host_sd gate bench.  A host model holding 8 credits sends NSEC random sectors (KV /
// RoPE / Engram data sectors and RoPE / Engram markers, per the per-die class set) at random gaps; NS stack-client
// models take hw<s>, return a credit after a random delay and a physical-write ack after another random delay.
// Golden = an independent route model (dest stacks of every sector); scoreboard: every sector reaches exactly its
// golden stack(s), in per-stack order, bit-exact {cls, we, addr, d}; the summed host_ack_n equals the acks issued;
// host credits return to 8 (no deadlock); no fault.  TBMUT 1: one marker with an invalid class (must fault -> FAIL).
module tb_dsfd_host_sd #(parameter integer NS = 2, KVS = 1, ENG = 1, MUT = 0, TBMUT = 0, NSEC = 4000, SEED = 1);
    reg ck = 0; always #0.4167 ck = ~ck;
    reg rst_n = 0; integer cyc = 0;
    always @(posedge ck) begin cyc <= cyc + 1; if (cyc == 4) rst_n <= 1; end
    function automatic [31:0] xs(input [31:0] v); reg [31:0] t; begin t = v ^ (v << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end endfunction
    reg o_v = 0, o_we = 1; reg [31:0] o_addr = 0; reg [255:0] o_d = 0;
    wire o_cr; wire [292*NS-1:0] hw; reg [9*NS-1:0] hc = 0; wire [7:0] host_ack_n; wire fault;
    dsfd_host_sd #(.NS(NS), .KVS(KVS), .ENG(ENG), .MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .o_v(o_v), .o_we(o_we), .o_addr(o_addr),
        .o_d(o_d), .o_cr(o_cr), .hw(hw), .hc(hc), .host_ack_n(host_ack_n), .fault(fault));
    // golden route
    integer nkv, kvl [0:3], s, i;
    initial begin nkv = 0; for (s = 0; s < NS; s = s + 1) if (KVS[s]) begin kvl[nkv] = s; nkv = nkv + 1; end end
    localparam integer QM = 1 << 14;
    reg [290:0] eq [0:3][0:QM-1]; integer eh [0:3], et [0:3];
    initial for (s = 0; s < 4; s = s + 1) begin eh[s] = 0; et[s] = 0; end
    // host model
    integer credits = 8, sent = 0; reg [31:0] sd = 32'h1357_9BDF ^ SEED; reg [31:0] a; reg [255:0] d; reg [1:0] c; reg mk; integer k;
    always @(posedge ck) begin
        o_v <= 0;
        if (o_cr) credits = credits + 1;
        sd = xs(sd);
        if (rst_n && cyc > 10 && sent < NSEC && credits > 0 && sd[2:0] != 0) begin
            sd = xs(sd); mk = (sd % 50) == 0 || (TBMUT == 1 && sent == NSEC / 2);
            sd = xs(sd);
            // class choice within the die's class set: 0 KV, 2 RoPE, 3 Engram
            if (nkv > 0 && ENG >= 0) c = (sd % 3 == 0) ? 2'd0 : ((sd % 3 == 1) ? 2'd2 : 2'd3);
            else if (nkv > 0) c = (sd % 4 == 0) ? 2'd2 : 2'd0;
            else c = 2'd3;
            if (mk && c == 2'd0) c = 2'd2;
            for (k = 0; k < 8; k = k + 1) begin sd = xs(sd); d[32*k +: 32] = sd; end
            sd = xs(sd); a = sd;
            if (mk) begin a = 32'hffffffff; d[65:64] = c; if (TBMUT == 1 && sent == NSEC / 2) d[65:64] = 2'd1; end
            else if (c == 2'd0) a[31] = 1'b0; else if (c == 2'd2) a[31:30] = 2'b10; else a[31:30] = 2'b11;
            o_v <= 1; o_we <= 1; o_addr <= a; o_d <= d; credits = credits - 1; sent = sent + 1;
            // golden destinations
            for (s = 0; s < NS; s = s + 1) begin
                if ((c == 2'd3 && s == ENG) || (c == 2'd2 && mk && KVS[s]) || (c == 2'd2 && !mk && nkv > 0 && s == kvl[0]) ||
                    (c == 2'd0 && nkv > 0 && s == kvl[(a >> 5) % nkv])) begin
                    eq[s][et[s] % QM] = {(c == 2'd3) ? 2'd2 : ((c == 2'd2) ? 2'd1 : 2'd0), 1'b1, a, d}; et[s] = et[s] + 1;
                end
            end
        end
    end
    // stack clients
    integer got [0:3], bad = 0, acks_issued = 0, acks_seen = 0, pcr [0:3], pak [0:3];
    integer crq [0:3][0:63], crh [0:3], crt [0:3], akq [0:3][0:63], akh [0:3], akt [0:3];
    reg [31:0] cs = 32'h2468_ACE1 ^ SEED; integer na;
    initial for (s = 0; s < 4; s = s + 1) begin got[s] = 0; crh[s] = 0; crt[s] = 0; akh[s] = 0; akt[s] = 0; end
    always @(posedge ck) begin
        for (s = 0; s < NS; s = s + 1) begin
            hc[9*s +: 9] <= 9'd0;
            if (hw[292*s]) begin
                if (eh[s] >= et[s] || hw[292*s + 1 +: 291] !== eq[s][eh[s] % QM]) begin
                    bad = bad + 1; if (bad < 5) $display("BAD stack %0d word %0d", s, got[s]); end
                eh[s] = eh[s] + 1; got[s] = got[s] + 1;
                cs = xs(cs); crq[s][crt[s] % 64] = cyc + 1 + cs % 20; crt[s] = crt[s] + 1;
                cs = xs(cs); akq[s][akt[s] % 64] = cyc + 3 + cs % 60; akt[s] = akt[s] + 1;
            end
            if (crh[s] < crt[s] && cyc >= crq[s][crh[s] % 64]) begin hc[9*s] <= 1'b1; crh[s] = crh[s] + 1; end
            na = 0;
            while (akh[s] < akt[s] && cyc >= akq[s][akh[s] % 64] && na < 3) begin na = na + 1; akh[s] = akh[s] + 1; end
            hc[9*s + 1 +: 8] <= na; acks_issued = acks_issued + na;
        end
        acks_seen = acks_seen + host_ack_n;
    end
    integer idle = 0, left;
    always @(posedge ck) begin
        left = 0; for (s = 0; s < NS; s = s + 1) left = left + (et[s] - eh[s]) + (akt[s] - akh[s]) + (crt[s] - crh[s]);
        idle = (sent == NSEC && left == 0) ? idle + 1 : 0;
        if (idle > 20 || cyc > 40 * NSEC + 2000) begin
            $display("HOSTSD sent=%0d delivered=%0d/%0d/%0d/%0d pending=%0d bad=%0d acks_issued=%0d acks_seen=%0d host_credits=%0d fault=%0d cycles=%0d",
                     sent, got[0], got[1], got[2], got[3], left, bad, acks_issued, acks_seen, credits, fault, cyc);
            if (sent == NSEC && left == 0 && bad == 0 && acks_issued == acks_seen && credits == 8 && !fault) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule
