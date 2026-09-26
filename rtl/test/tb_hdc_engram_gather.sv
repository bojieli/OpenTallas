`timescale 1ns/1ps
// Shipped-scale Engram prefetch bench: ot_hdc_engram_hash_shipped feeding
// ot_hdc_engram_gather, 48 behavioural column banks and a behavioural prefetch
// buffer.  tools/rtl_hdc_v41_engram_gather_campaign.py writes the vectors and
// checks the dumped buffer against the golden.
//
// Vectors (+VEC): one token per line, "first cid row0 .. row47" (hex), the
// golden's shipped-table row ids.  The bench checks every hash row, feeds the
// rows to the gather, and on each rdy dumps the ready layer's 24 rows (192
// words of 32 BF16) to +OUT as "T token L layer" + 192 hex lines.
//
// Bank model (bank b = layer*24 + column): a 4-deep request queue (req_ready is
// low when it is full, and randomly for +STALL percent of cycles); a row is
// served LAT + (b*7 mod (JIT+1)) + random(0..JIT) cycles after its request, as 8
// in-order beats, each held until accepted, with random gaps (+GAP percent).
// Row content is tools/hdc_v41_engram_shipped.row_bytes: word j of global row r
// of layer l is splitmix64(l << 40 | r << 6 | j).
// Consumer: checks layer 0 then layer 1 of each token in order, each after a
// random delay of up to +CDEL cycles, then releases the slot.  +SPACED=1 issues a
// token only after the previous one was consumed (one token per decode step: the
// latency of an isolated prefetch).
module tb_hdc_engram_gather (input wire clk);
    import ot_hdc_engram_tables_shipped_pkg::*;
    localparam integer MAXV = 1 << 14;
    localparam integer NL = ENG_LAYERS, NC = ENG_COLS, NB = NL * NC;
    localparam integer RW = ENG_ROW_W, AW = ENG_RES_W;
    localparam integer DW = 264, QD = 4;
    localparam integer BAW = 1 + 5 + 3;

    reg               vfirst [0:MAXV-1];
    reg [ENG_ID_W-1:0] vcid  [0:MAXV-1];
    reg [NB*RW-1:0]   vrow   [0:MAXV-1];
    integer nvec = 0, fd, fo, rc, c;
    reg [31:0] fld;
    integer LAT, JIT, STALL, GAP, BUB, CDEL, SPACED;

    function automatic [63:0] smix(input [63:0] x);
        reg [63:0] z;
        begin
            z = x + 64'h9E3779B97F4A7C15;
            z = (z ^ (z >> 30)) * 64'hBF58476D1CE4E5B9;
            z = (z ^ (z >> 27)) * 64'h94D049BB133111EB;
            smix = z ^ (z >> 31);
        end
    endfunction

    reg rst_n = 1'b0;
    // hash
    reg h_valid = 1'b0, h_first = 1'b0;
    reg [ENG_ID_W-1:0] h_cid = 0;
    wire h_ovalid;
    wire [NB*RW-1:0] h_row;
    ot_hdc_engram_hash_shipped u_hash (.clk(clk), .rst_n(rst_n), .in_valid(h_valid), .in_first(h_first),
                                       .in_cid(h_cid), .out_valid(h_ovalid), .out_row(h_row));
    // gather
    wire in_ready, in_slot;
    wire [NB-1:0] req_valid, req_tag, rsp_ready;
    wire [NB*AW-1:0] req_addr;
    reg  [NB-1:0] req_ready = 0, rsp_valid = 0, rsp_tag = 0;
    reg  [NB*DW-1:0] rsp_data = 0;
    wire [NL-1:0] wr_en;
    wire [NL*BAW-1:0] wr_addr;
    wire [NL*512-1:0] wr_data;
    wire [2*NL-1:0] rdy;
    reg rel_valid = 1'b0, rel_slot = 1'b0;
    ot_hdc_engram_gather dut (.clk(clk), .rst_n(rst_n), .in_valid(h_ovalid), .in_ready(in_ready), .in_row(h_row),
                              .in_slot(in_slot), .req_valid(req_valid), .req_ready(req_ready), .req_addr(req_addr),
                              .req_tag(req_tag), .rsp_valid(rsp_valid), .rsp_ready(rsp_ready), .rsp_data(rsp_data),
                              .rsp_tag(rsp_tag), .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data), .rdy(rdy),
                              .rel_valid(rel_valid), .rel_slot(rel_slot));

    reg [511:0] buffer [0:NL-1][0:(1<<BAW)-1];

    initial begin : load
        reg [8*512-1:0] path;
        reg [NB*RW-1:0] row;
        if (!$value$plusargs("VEC=%s", path)) path = "gather_vectors.txt";
        if (!$value$plusargs("LAT=%d", LAT)) LAT = 4;
        if (!$value$plusargs("JIT=%d", JIT)) JIT = 0;
        if (!$value$plusargs("STALL=%d", STALL)) STALL = 0;
        if (!$value$plusargs("GAP=%d", GAP)) GAP = 0;
        if (!$value$plusargs("BUB=%d", BUB)) BUB = 0;
        if (!$value$plusargs("CDEL=%d", CDEL)) CDEL = 0;
        if (!$value$plusargs("SPACED=%d", SPACED)) SPACED = 0;
        fd = $fopen(path, "r");
        if (fd == 0) begin $display("cannot open vectors"); $finish; end
        rc = 1;
        while (rc > 0 && nvec < MAXV) begin
            rc = $fscanf(fd, "%h", fld);
            if (rc > 0) begin
                vfirst[nvec] = fld[0];
                rc = $fscanf(fd, "%h", fld);
                vcid[nvec] = fld[ENG_ID_W-1:0];
                row = {(NB*RW){1'b0}};
                for (c = 0; c < NB; c = c + 1) begin
                    rc = $fscanf(fd, "%h", fld);
                    row[RW*c +: RW] = fld[RW-1:0];
                end
                vrow[nvec] = row;
                nvec = nvec + 1;
            end
        end
        $fclose(fd);
        if (!$value$plusargs("OUT=%s", path)) path = "gather_out.txt";
        fo = $fopen(path, "w");
    end

    reg [31:0] seed = 32'h1234_5678, bseed = 32'h0BAD_5EED, cseed = 32'h5EED_0001;
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction

    // -- driver + hash check --------------------------------------------------------
    integer cyc = 0, sent = 0, hgot = 0, herr = 0, inflight = 0, acc_n = 0, rerr = 0;
    integer ct = 0, cl = 0, wait_n = -1, dumped = 0, idle = 0, a;
    integer tiss [0:MAXV-1];
    integer slot_tok [0:1];
    reg seen [0:1][0:NL-1];
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        seed = xs(seed);
        h_valid <= 1'b0;
        if (rst_n && sent < nvec && inflight == 0 && in_ready && (seed % 100) >= BUB && (SPACED == 0 || ct == sent)) begin
            h_valid <= 1'b1; h_first <= vfirst[sent]; h_cid <= vcid[sent];
            tiss[sent] = cyc;
            sent <= sent + 1;
            inflight = inflight + 1;
        end
        if (rst_n && h_ovalid) begin
            inflight = inflight - 1;
            if (h_row !== vrow[hgot]) begin
                if (herr < 5) $display("HASH MISMATCH token=%0d", hgot);
                herr = herr + 1;
            end
            if (!in_ready) rerr = rerr + 1;
            slot_tok[in_slot] = hgot;
            seen[in_slot][0] = 0; seen[in_slot][1] = 0;
            hgot = hgot + 1;
        end
    end

    // -- column banks -----------------------------------------------------------------
    reg [AW-1:0] qa [0:NB-1][0:QD-1];
    reg          qt [0:NB-1][0:QD-1];
    integer      qw [0:NB-1][0:QD-1];
    integer      qh [0:NB-1], qn [0:NB-1], bt [0:NB-1];
    integer b, lyr;
    reg [RW-1:0] grow;
    reg [63:0] key, w32;
    reg [7:0] side;
    initial for (b = 0; b < NB; b = b + 1) begin qh[b] = 0; qn[b] = 0; bt[b] = 0; end
    always @(posedge clk) begin
        for (b = 0; b < NB; b = b + 1) begin
            // response side: a beat accepted this edge
            if (rsp_valid[b] && rsp_ready[b]) begin
                rsp_valid[b] <= 1'b0;
                if (bt[b] == 7) begin bt[b] = 0; qh[b] = (qh[b] + 1) % QD; qn[b] = qn[b] - 1; end
                else bt[b] = bt[b] + 1;
            end else if (!rsp_valid[b] && qn[b] > 0 && cyc >= qw[b][qh[b]]) begin
                bseed = xs(bseed);
                if ((bseed % 100) >= GAP) begin
                    lyr = b / NC;
                    grow = qa[b][qh[b]] + ENG_OFFSET[RW*b +: RW];
                    key = ({16'd0, lyr[7:0], 40'd0}) | ({29'd0, grow, 6'd0});
                    for (c = 0; c < 4; c = c + 1)
                        rsp_data[DW*b + 64*c +: 64] <= smix(key | (4 * bt[b] + c));
                    w32 = smix(key | 64'd32);
                    side = (bt[b] != 0) ? (8'hA5 ^ bt[b][7:0]) : w32[8] ? w32[7:0] : 8'd107 + (w32[7:0] % 41);
                    rsp_data[DW*b + 256 +: 8] <= side;
                    rsp_tag[b] <= qt[b][qh[b]];
                    rsp_valid[b] <= 1'b1;
                end
            end
            // request side
            if (req_valid[b] && req_ready[b]) begin
                qa[b][(qh[b] + qn[b]) % QD] = req_addr[AW*b +: AW];
                qt[b][(qh[b] + qn[b]) % QD] = req_tag[b];
                bseed = xs(bseed);
                qw[b][(qh[b] + qn[b]) % QD] = cyc + LAT + (b * 7) % (JIT + 1) + (JIT > 0 ? bseed % (JIT + 1) : 0);
                qn[b] = qn[b] + 1;
            end
            bseed = xs(bseed);
            req_ready[b] <= rst_n && (qn[b] < QD) && ((bseed % 100) >= STALL);
        end
    end

    // -- prefetch buffer ---------------------------------------------------------------
    integer l2;
    always @(posedge clk)
        for (l2 = 0; l2 < NL; l2 = l2 + 1)
            if (wr_en[l2]) buffer[l2][wr_addr[BAW*l2 +: BAW]] <= wr_data[512*l2 +: 512];

    // -- latency: first cycle each (slot, layer) is ready ------------------------------
    integer lmin [0:NL-1], lmax [0:NL-1], lsum [0:NL-1], lat, s2, l3;
    initial for (l3 = 0; l3 < NL; l3 = l3 + 1) begin lmin[l3] = 1 << 30; lmax[l3] = 0; lsum[l3] = 0; end
    initial begin seen[0][0] = 0; seen[0][1] = 0; seen[1][0] = 0; seen[1][1] = 0; end
    always @(posedge clk) if (rst_n)
        for (s2 = 0; s2 < 2; s2 = s2 + 1)
            for (l3 = 0; l3 < NL; l3 = l3 + 1)
                if (rdy[s2 * NL + l3] && !seen[s2][l3]) begin
                    seen[s2][l3] = 1;
                    lat = cyc - tiss[slot_tok[s2]];
                    if (lat < lmin[l3]) lmin[l3] = lat;
                    if (lat > lmax[l3]) lmax[l3] = lat;
                    lsum[l3] = lsum[l3] + lat;
                end

    // -- consumer ----------------------------------------------------------------------
    always @(posedge clk) begin
        rel_valid <= 1'b0;
        if (rst_n && ct < nvec) begin
            if (rdy[(ct % 2) * NL + cl]) begin
                if (wait_n < 0) begin cseed = xs(cseed); wait_n = CDEL > 0 ? cseed % (CDEL + 1) : 0; end
                if (wait_n == 0) begin
                    $fwrite(fo, "T %0d L %0d\n", ct, cl);
                    for (a = 0; a < NC * 8; a = a + 1)
                        $fwrite(fo, "%0128h\n", buffer[cl][{ct[0], a[7:0]}]);
                    dumped = dumped + 1;
                    wait_n = -1;
                    if (cl == NL - 1) begin
                        rel_valid <= 1'b1; rel_slot <= ct[0];
                        cl = 0; ct = ct + 1;
                    end else cl = cl + 1;
                end else wait_n = wait_n - 1;
            end
        end
        idle = (ct >= nvec) ? idle + 1 : 0;
        if (idle > 20 || cyc > 2000 * MAXV) begin
            $display("GATHER tokens=%0d hash_checked=%0d hash_errors=%0d dumped=%0d ready_errors=%0d cycles=%0d lat0_min=%0d lat0_max=%0d lat0_sum=%0d lat1_min=%0d lat1_max=%0d lat1_sum=%0d",
                     nvec, hgot, herr, dumped, rerr, cyc, lmin[0], lmax[0], lsum[0], lmin[1], lmax[1], lsum[1]);
            if (herr == 0 && rerr == 0 && hgot == nvec && dumped == NL * nvec) $display("DONE"); else $display("FAIL");
            $fclose(fo);
            $finish;
        end
    end
endmodule
