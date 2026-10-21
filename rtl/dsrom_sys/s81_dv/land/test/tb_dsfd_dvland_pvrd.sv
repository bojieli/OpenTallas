`timescale 1ps/1ps
// S81-DIE5: bench of dsfd_dvland_pvrd (P.V landing + static RD-beat adapter).  The lane runs on a forwarded clock that
// lags the slice root by +DL ps; the svc drain pattern is NJ jobs of NW words (5-word beats, head flag on word 0),
// back to back inside a job, GAP idle cycles between jobs.  Checks: every landed word comes out as one RD beat with
// kind 4, pairs 2, leaf = w mod 5, row = RB + 4 (w div 5), the exact word, at ONE constant latency; fault 0.
// +LAT=n pins the calendar latency (S81-DIE7 PVRD). +SLIP=1 moves one head flag (calendar slip) -> fault must rise.  Build -DMUT1 -> leaf calendar off by one -> FAIL.
module tb;
    localparam integer T = 834;
    integer DL = 300, NW = 10, NJ = 3, GAP = 7, SLIP = 0, KS = 2, LAT = -1;
    reg ck = 0, ckf = 0, rs = 0;
    always #(T / 2) ck = ~ck;
    initial begin
        if (!$value$plusargs("DL=%d", DL)) DL = 300;
        if (!$value$plusargs("NW=%d", NW)) NW = 10;
        if (!$value$plusargs("SLIP=%d", SLIP)) SLIP = 0;
        if (!$value$plusargs("K=%d", KS)) KS = 2;
        if (!$value$plusargs("LAT=%d", LAT)) LAT = -1;   // expected calendar latency (edges); -1 = not checked
        #(DL); forever #(T / 2) ckf = ~ckf;
    end
    reg [561:0] lane = 0;
    wire [1103:0] o; wire fault;
`ifdef MUT1
    dsfd_dvland_pvrd #(.MUT(1)) dut (.ck_f(ckf), .i(lane), .ck(ck), .rs(rs), .k(KS[2:0]), .nw(NW[7:0]), .rb(10'd100), .o(o), .fault(fault));
`else
    dsfd_dvland_pvrd #(.MUT(0)) dut (.ck_f(ckf), .i(lane), .ck(ck), .rs(rs), .k(KS[2:0]), .nw(NW[7:0]), .rb(10'd100), .o(o), .fault(fault));
`endif
    function [511:0] word(input integer j, input integer t);
        word = {16{j[15:0], t[15:0]}} ^ {32{t[15:0]}};
    endfunction
    // source: words launched on ckf (the lane's clock), counted in ckf edges
    integer sj = 0, st = 0, sg = 0, sedge = 0, started = 0;
    integer src_edge [0:1023];
    integer nsent = 0;
    always @(posedge ckf) begin
        sedge <= sedge + 1;
        lane <= 0;
        if (started && sj < NJ) begin
            if (sg > 0) sg <= sg - 1;
            else begin
                lane[0] <= 1'b1;
                lane[513] <= ((st % 5) == 0) ^ (SLIP && sj == 1 && st == 3);
                lane[512:1] <= word(sj, st);
                src_edge[nsent] = sedge; nsent = nsent + 1;
                if (st == NW - 1) begin st <= 0; sj <= sj + 1; sg <= GAP; end
                else st <= st + 1;
            end
        end
    end
    integer redge = 0, nrecv = 0, mism = 0, lat0 = -1, latbad = 0, rj = 0, rt = 0;
    always @(posedge ck) begin
        redge <= redge + 1;
        if (o[0]) begin
            if (o[3:1] !== 3'd4 || o[51:50] !== 2'd1 || o[39:37] !== (rt % 5) || o[49:40] !== 100 + 4 * (rt / 5) ||
                o[563:52] !== word(rj, rt) || o[1103:564] !== 0) mism = mism + 1;
            if (lat0 < 0) lat0 = redge - src_edge[nrecv];
            else if (redge - src_edge[nrecv] != lat0) latbad = latbad + 1;
            nrecv = nrecv + 1;
            if (rt == NW - 1) begin rt = 0; rj = rj + 1; end else rt = rt + 1;
        end
    end
    initial begin
        rs = 0; #(5 * T + 10); rs = 1;           // block reset release (ck domain); the lane clock already runs
        #(3 * T); started = 1;
        #((NJ * (NW + GAP) + 40) * T);
        $display("OT_PVRD sent=%0d recv=%0d mism=%0d lat=%0d latbad=%0d fault=%0d", nsent, nrecv, mism, lat0, latbad, fault);
        // (if/else, not a string ternary: iverilog printed nothing for the ternary form)
        if (SLIP) begin
            if (fault) $display("PVRD_RESULT PASS (slip faulted)"); else $display("PVRD_RESULT FAIL (slip not seen)");
        end else if (nrecv == NW * NJ && nsent == nrecv && mism == 0 && latbad == 0 && fault == 0 && (LAT < 0 || lat0 == LAT))
            $display("PVRD_RESULT PASS");
        else $display("PVRD_RESULT FAIL");
        $finish;
    end
endmodule
