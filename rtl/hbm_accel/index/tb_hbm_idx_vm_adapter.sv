`timescale 1ns/1ps
// Exact bench of ot_hbm_idx_vm_adapter against behavioural B2 VM models (wide lanes: own slice only, in order, early
// credit; packet client: <= 4 outstanding, any slice, in order, longer latency) and a held-lease arbiter that checks the
// release.  IDX side: 8 lanes, credit-paced random reads (own-slice main, mirror, remote main), every response compared in
// lane order with the memory image.  +MODE=1: all-local stream at full rate (throughput).  Pass/fail by $display marker.
module tb_hbm_idx_vm_adapter;
    parameter integer MUT = 0;
    localparam integer LQ = 10, AQ = 10, PK = 4, NREQ = 1500;
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0; reg [1:0] sid = 2'd1;
    reg  [8*17-1:0] i_rq = 0; wire [7:0] i_rq_cr; wire [8*257-1:0] i_rr;
    wire [8*17-1:0] v_rq; reg [7:0] v_rq_cr = 0; reg [8*257-1:0] v_rr = 0;
    wire [337:0] v_cq; reg [273:0] v_cr = 0;
    wire l_req, l_drained, fault; reg l_grant = 0, l_drain_ack = 0;
    ot_hbm_idx_vm_adapter #(.LQ(LQ), .AQ(AQ), .PK(PK), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .sid(sid),
        .i_rq(i_rq), .i_rq_cr(i_rq_cr), .i_rr(i_rr), .v_rq(v_rq), .v_rq_cr(v_rq_cr), .v_rr(v_rr), .v_cq(v_cq), .v_cr(v_cr),
        .l_req(l_req), .l_grant(l_grant), .l_drained(l_drained), .l_drain_ack(l_drain_ack), .fault(fault));
    function automatic [255:0] mem(input [15:0] s);
        mem = {8{s ^ 16'h5a3c, ~s, 32'h0 | (s * 16'd2654)}};
    endfunction
    integer mode = 0, errors = 0, cyc = 0, sent [0:7], got [0:7], credit [0:7], remotes = 0, mirrors = 0, locals = 0;
    integer first_cyc = -1, last_cyc = 0, lease_grants = 0, lease_releases = 0;
    reg [15:0] exp_q [0:7][$];
    // ---------------- VM wide lane model
    reg [15:0] lq [0:7][$]; integer lq_t [0:7][$]; reg [255:0] rsp_q [0:7][$]; integer rsp_t [0:7][$];
    integer vcr_held [0:7];
    // ---------------- packet model
    reg [15:0] pq [$]; reg [2:0] pl [$]; integer pt [$]; integer pk_out = 0;
    reg [31:0] rnd = 32'h1234567;
    function automatic integer rr(input integer n); rnd = rnd * 1103515245 + 12345; rr = (rnd >> 8) % n; endfunction
    integer local_out;
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        // --- IDX: credits back, new requests
        for (integer l = 0; l < 8; l = l + 1) begin
            if (i_rq_cr[l]) credit[l] = credit[l] + 1;
            i_rq[l*17 +: 17] <= 17'd0;
            if (sent[l] < NREQ && credit[l] > 0 && (mode == 1 || rr(4) != 0)) begin
                reg [15:0] s; integer k; k = (mode == 1) ? rr(2) : rr(8);
                s[2:0] = 3'(l); s[12:3] = 10'(rr(1024));
                if (k == 0 && mode == 0) begin s[15] = 1'b0; s[14:13] = sid + 2'(1 + rr(3)); remotes = remotes + 1; end
                else if (k == 1) begin s[15] = 1'b1; s[14:13] = 2'd0; mirrors = mirrors + 1; end
                else begin s[15] = 1'b0; s[14:13] = sid; locals = locals + 1; end
                i_rq[l*17 +: 17] <= {1'b1, s}; exp_q[l].push_back(s); sent[l] = sent[l] + 1; credit[l] = credit[l] - 1;
                if (first_cyc < 0) first_cyc = cyc;
            end
        end
        // --- IDX: responses in lane order
        for (integer l = 0; l < 8; l = l + 1) if (i_rr[l*257 + 256]) begin
            if (exp_q[l].size() == 0) begin errors = errors + 1; $display("ERR lane%0d unexpected response", l); end
            else begin
                reg [15:0] s; s = exp_q[l].pop_front();
                if (i_rr[l*257 +: 256] !== mem(s)) begin
                    errors = errors + 1; if (errors < 10) $display("ERR lane%0d sec %h data mismatch cyc %0d", l, s, cyc);
                end
            end
            got[l] = got[l] + 1; last_cyc = cyc;
        end
        // --- VM wide lanes: own slice only, early credit, in-order responses
        for (integer l = 0; l < 8; l = l + 1) begin
            v_rq_cr[l] <= 1'b0; v_rr[l*257 + 256] <= 1'b0;
            if (v_rq[l*17 + 16]) begin
                reg [15:0] s; s = v_rq[l*17 +: 16];
                if (!l_grant) begin errors = errors + 1; $display("ERR lane%0d local read without the lease", l); end
                if (s[2:0] != 3'(l) || (!s[15] && s[14:13] != sid) || (s[15] && s[14:13] != 2'd0)) begin
                    errors = errors + 1; if (errors < 10) $display("ERR lane%0d VM wide lane fault: sec %h on slice %0d", l, s, sid);
                end
                vcr_held[l] = vcr_held[l] - 1;
                if (vcr_held[l] < 0) begin errors = errors + 1; $display("ERR lane%0d VM credit overrun", l); end
                lq[l].push_back(s); lq_t[l].push_back(cyc + 1 + rr(3));
            end
            if (lq[l].size() != 0 && lq_t[l][0] <= cyc) begin
                reg [15:0] s; s = lq[l].pop_front(); void'(lq_t[l].pop_front());
                v_rq_cr[l] <= 1'b1; vcr_held[l] = vcr_held[l] + 1;
                rsp_q[l].push_back((s[15] || s[14:13] == sid) ? mem(s) : 256'hdead); rsp_t[l].push_back(cyc + 6 + l);
            end
            if (rsp_q[l].size() != 0 && rsp_t[l][0] <= cyc) begin
                v_rr[l*257 +: 257] <= {1'b1, rsp_q[l].pop_front()}; void'(rsp_t[l].pop_front());
            end
        end
        // --- packet client: <= PK outstanding, any slice, in order
        v_cr[273] <= 1'b0;
        if (v_cq[337]) begin
            reg [15:0] s; s = {v_cq[324], v_cq[323:309]};
            pk_out = pk_out + 1;
            if (pk_out > PK) begin errors = errors + 1; $display("ERR packet client over %0d outstanding", PK); end
            pq.push_back(s); pl.push_back(v_cq[15:13]); pt.push_back(cyc + 15 + rr(25));
        end
        if (pq.size() != 0 && pt[0] <= cyc) begin
            reg [15:0] s; reg [2:0] l; s = pq.pop_front(); l = pl.pop_front(); void'(pt.pop_front());
            v_cr <= {1'b1, {l, 13'd0}, 1'b0, mem(s)}; pk_out = pk_out - 1;
        end
        // --- held lease: grant on request, release only when the source says drained; check the drain is real
        if (!l_grant && l_req && rr(3) == 0) begin l_grant <= 1'b1; lease_grants = lease_grants + 1; end
        if (l_grant && !l_req && l_drained) begin
            local_out = 0;
            for (integer l = 0; l < 8; l = l + 1) local_out = local_out + lq[l].size() + rsp_q[l].size() + (v_rq[l*17 + 16] ? 1 : 0)
                                                           + (v_rr[l*257 + 256] ? 1 : 0) + (LQ - vcr_held[l]);
            if (local_out != 0) begin errors = errors + 1; if (errors < 10) $display("ERR lease released with %0d local reads / credits outstanding", local_out); end
            l_grant <= 1'b0; lease_releases = lease_releases + 1;
        end
    end
    initial begin
        if ($test$plusargs("MODE1")) mode = 1;
        for (integer l = 0; l < 8; l = l + 1) begin sent[l] = 0; got[l] = 0; credit[l] = AQ; vcr_held[l] = LQ; end
        repeat (5) @(posedge clk); rst_n = 1;
        fork
            begin : wait_done
                integer done; done = 0;
                while (!done) begin
                    @(posedge clk); done = 1;
                    for (integer l = 0; l < 8; l = l + 1) if (got[l] < NREQ) done = 0;
                end
            end
            begin repeat (200000) @(posedge clk); $display("ERR timeout"); errors = errors + 1; end
        join_any
        disable fork;
        repeat (60) @(posedge clk);
        if (dut.fault) begin errors = errors + 1; $display("ERR adapter fault"); end
        if (mode == 0 && (remotes < 500 || mirrors < 500 || lease_releases < 1)) begin errors = errors + 1; $display("ERR insufficient coverage"); end
        $display("IDX_VM_ADAPTER mode %0d reads %0d (local %0d mirror %0d remote %0d) cycles %0d (%.3f reads/lane/cycle) lease grants %0d releases %0d",
                 mode, 8*NREQ, locals, mirrors, remotes, last_cyc - first_cyc + 1, real'(NREQ) / real'(last_cyc - first_cyc + 1),
                 lease_grants, lease_releases);
        if (errors == 0) $display("IDX_VM_ADAPTER PASS"); else $display("IDX_VM_ADAPTER FAIL errors=%0d", errors);
        $finish;
    end
endmodule
