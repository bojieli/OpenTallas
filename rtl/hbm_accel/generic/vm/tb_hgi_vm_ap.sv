`timescale 1ns/1ps
// hgi-1010 b: bench of the VM unit's HC weight APERTURE route (ot_hgi_vm_unit AP = 1) and the packet range fault.
//   * a DMA-front model drives the 32 wide write lanes (281 b {v, ap, sector 15, data, mask}) with interleaved VM sectors
//     (bank = lane) and aperture sectors (both slots, 4,096 each, every bank), honouring wq_rdy through a 3-edge
//     pipeline (the front's X1 -> X2 -> lane + the VM's pin flop);
//   * an HC aperture model (d's ot_hgi_hc_unit HSRC = 1 protocol, 8 bank lanes): holds one sector a lane, accepts it on a random edge
//     (macro conflicts), pulses ap_cr on acceptance and ap_done the edge after; a sector onto a held lane is an error;
//   * checks: every aperture sector lands exactly once with its data (mask honoured); every VM sector lands in VM; the
//     VM words aliased by the aperture sectors keep their prior value; wq_done counts every sector; no status fault;
//     then a packet write to byte address 2^20 + X must fault (status proto) and leave VM[X] unchanged.
//   VMMUT (ot_hgi_vm_unit MUT): 10 aperture sectors also write VM, 11 no wq_rdy back-pressure, 12 no packet range check, 13 the bank key off by one bit (lane k carries another bank):
//   each must FAIL.
`ifndef APC
`define APC 4
`endif
module tb_hgi_vm_ap;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    localparam integer NAP = 8192, NVM = 4096;
    reg [338-1:0] cq = 0; wire [274-1:0] cr; wire [18:0] status;
    reg [32*281-1:0] wq = 0; wire [31:0] wq_done, wq_rdy; wire [8*278-1:0] ap_q; reg [7:0] ap_cr = 0, ap_done = 0;
    ot_hgi_vm_unit #(.NC(1), .WP(32), .WDIRECT(1), .AP(1), .APC(`APC), .MUT(`VMMUT)) u (.clk(clk), .rst_n(rst_n), .cq(cq), .cr(cr),
        .status(status), .wq(wq), .wq_done(wq_done), .wq_rdy(wq_rdy), .ap_q(ap_q), .ap_cr(ap_cr), .ap_done(ap_done),
        .rq(16'd0), .rq_cr(), .rr(), .w2q(280'd0), .w2q_cr(), .w2q_done());
    integer seed = 11, errors = 0, cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    function automatic [255:0] pat(input integer k, input integer s);
        pat = {8{32'(k * 32'h9E3779B1 + s * 7919 + 1)}};
    endfunction
    // ---- the sector lists a lane: lane b sends aperture sectors {slot, bank, q} with (8 * q + bank + slot) % 32 == b
    //      and VM sectors 32 m + b (m < NVM / 32) interleaved
    integer nl [0:31]; reg [15:0] lst [0:31][0:511];       // {ap, sector 15}
    reg [255:0] apm [0:NAP-1]; reg [7:0] apmask [0:NAP-1]; integer apn [0:NAP-1];
    reg [255:0] vmx [0:NVM-1];
    initial begin
        for (integer b = 0; b < 32; b = b + 1) nl[b] = 0;
        for (integer s = 0; s < NAP; s = s + 1) begin : ga
            integer b; b = (s + s / 32) % 32;                 // spread a slot's sectors over all lanes
            lst[b][nl[b]] = {1'b1, 15'(s)}; nl[b] = nl[b] + 1;
            apn[s] = 0; apm[s] = '0; apmask[s] = (s % 7 == 3) ? 8'hA5 : 8'hFF;
        end
        for (integer m = 0; m < NVM / 32; m = m + 1)
            for (integer b = 0; b < 32; b = b + 1) begin : gv
                integer k, j; k = nl[b]; j = $urandom(seed + m * 32 + b) % (k + 1);    // insert at a random position
                for (integer t = k; t > j; t = t - 1) lst[b][t] = lst[b][t - 1];
                lst[b][j] = {1'b0, 15'(32 * m + b)}; nl[b] = k + 1;
            end
    end
    // ---- front model: a 2-stage pipe after the decision, decision on the registered wq_rdy
    reg [31:0] rdy_r = 0; integer ix [0:31]; reg [280:0] p1 [0:31];
    integer sent = 0, dones = 0, vm_sent = 0, ap_sent = 0;
    reg go = 0;
    always @(posedge clk) begin
        rdy_r <= wq_rdy;
        for (integer b = 0; b < 32; b = b + 1) begin
            wq[b*281 +: 281] <= p1[b];
            p1[b] <= '0;
            if (go && rdy_r[b] && ix[b] < nl[b] && ($urandom(seed) % 8) != 0) begin : snd
                reg [15:0] e; reg [255:0] d; e = lst[b][ix[b]];
                d = pat(e[15] ? 1 : 2, e[14:0]);
                p1[b] <= {1'b1, e[15], e[14:0], d, e[15] ? apmask[e[14:0]] : 8'hFF};
                ix[b] = ix[b] + 1; sent = sent + 1;
                if (e[15]) ap_sent = ap_sent + 1; else vm_sent = vm_sent + 1;
            end
        end
        for (integer b = 0; b < 32; b = b + 1) if (wq_done[b]) dones = dones + 1;
    end
    // ---- HC aperture model: a lane holds up to APC sectors (d's lane FIFO), takes its head on a random edge (macro
    //      conflicts), returns a credit (ap_cr) on acceptance and ap_done the edge after; an arrival onto a full lane is an error
    integer hn [0:7]; reg [277:0] hq [0:7][0:`APC-1];
    initial for (integer b = 0; b < 8; b = b + 1) hn[b] = 0;
    always @(posedge clk) begin
        ap_done <= ap_cr; ap_cr <= '0;
        for (integer b = 0; b < 8; b = b + 1)
            if (hn[b] > 0 && ($urandom(seed) % 4) != 0) begin : acc
                reg [12:0] s; s = hq[b][0][276:264];
                for (integer w = 0; w < 8; w = w + 1) if (hq[b][0][w]) apm[s][32*w +: 32] = hq[b][0][8 + 32*w +: 32];
                apn[s] = apn[s] + 1; ap_cr[b] <= 1'b1;
                for (integer q = 0; q < `APC - 1; q = q + 1) hq[b][q] = hq[b][q + 1];
                hn[b] = hn[b] - 1;
            end
        for (integer b = 0; b < 8; b = b + 1)
            if (ap_q[b*278 + 277]) begin
                if (ap_q[b*278 + 273 +: 3] != 3'(b)) begin errors = errors + 1; if (errors < 10) $display("ERR aperture lane %0d carries bank %0d", b, ap_q[b*278 + 273 +: 3]); end
                if (hn[b] == `APC) begin errors = errors + 1; if (errors < 10) $display("ERR lane %0d: sector onto a full lane", b); end
                else begin hq[b][hn[b]] = ap_q[b*278 +: 278]; hn[b] = hn[b] + 1; end
            end
    end
    task automatic pkt(input we, input [31:0] byteaddr, input [255:0] data, output [255:0] qd);
        integer tw;
        begin
            @(negedge clk); cq = {1'b1, we, byteaddr, data, 32'hFFFFFFFF, 16'h0BE0};
            @(negedge clk); cq[337] = 1'b0;
            tw = 0; while (!cr[273] && tw < 2000) begin @(negedge clk); tw = tw + 1; end
            qd = cr[255:0];
        end
    endtask
    reg [255:0] qd, exp_d;
    initial begin
        for (integer b = 0; b < 32; b = b + 1) begin ix[b] = 0; p1[b] = '0; end
        repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
        // VM words aliased by the aperture sectors (sector & 0x1FFF... the low 15 bits): a known prior value
        for (integer s = 0; s < 64; s = s + 1) pkt(1'b1, 32'(s * 509 % NAP) << 5, pat(3, s * 509 % NAP), qd);
        @(negedge clk); go = 1;
        begin : wt
            integer t; t = 0;
            while ((sent < NAP + NVM || dones < NAP + NVM) && t < 200000) begin @(posedge clk); t = t + 1; end
            $display("ap route: sent %0d (ap %0d, vm %0d), wq_done %0d, %0d edges", sent, ap_sent, vm_sent, dones, t);
            if (dones != NAP + NVM) begin errors = errors + 1; $display("ERR wq_done %0d != %0d", dones, NAP + NVM); end
        end
        repeat (20) @(posedge clk);
        if (dones != NAP + NVM) begin errors = errors + 1; $display("ERR late wq_done %0d", dones); end
        for (integer s = 0; s < NAP; s = s + 1) begin
            exp_d = '0;
            for (integer w = 0; w < 8; w = w + 1) if (apmask[s][w]) exp_d[32*w +: 32] = pat(1, s);
            if (apn[s] != 1 || apm[s] !== exp_d) begin
                errors = errors + 1; if (errors < 20) $display("ERR aperture sector %0d: written %0d times, %h", s, apn[s], apm[s][31:0]);
            end
        end
        for (integer m = 0; m < NVM; m = m + 1) begin
            pkt(1'b0, 32'(m) << 5, 256'd0, qd);
            // VM sectors 0 .. 4095 = the vm list; the aliased-prior sectors (< 8192) that are not VM-list sectors keep pat(3)
            if (qd !== pat(2, m)) begin errors = errors + 1; if (errors < 30) $display("ERR VM sector %0d = %h", m, qd[31:0]); end
        end
        for (integer s = 0; s < 64; s = s + 1) if ((s * 509 % NAP) >= NVM) begin
            pkt(1'b0, 32'(s * 509 % NAP) << 5, 256'd0, qd);
            if (qd !== pat(3, s * 509 % NAP)) begin errors = errors + 1; if (errors < 40) $display("ERR aliased VM sector %0d overwritten", s * 509 % NAP); end
        end
        if (status[18]) begin errors = errors + 1; $display("ERR status fault during the route"); end
        // packet range: byte address 2^20 + 32 x 100 (word 2^18 + 800) must fault and not write VM sector 100
        pkt(1'b1, 32'h0010_0000 + 32'd3200, pat(9, 9), qd);
        repeat (4) @(posedge clk);
        if (!status[18]) begin errors = errors + 1; $display("ERR packet past the VM did not fault"); end
        pkt(1'b0, 32'd3200, 256'd0, qd);
        if (qd !== pat(2, 100)) begin errors = errors + 1; $display("ERR packet past the VM wrote VM sector 100"); end
        if (errors == 0) $display("HGI_VM_AP PASS"); else $display("HGI_VM_AP FAIL errors=%0d", errors);
        $finish;
    end
endmodule
