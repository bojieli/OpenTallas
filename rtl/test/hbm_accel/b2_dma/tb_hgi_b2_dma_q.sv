`timescale 1ps/1ps
// ---------------------------------------------------------------------------------------------------------------------
// tb_hgi_b2_dma_q (el1013-dma-q 2026-10-13): behavioural bench of the HARDENED B2 cluster DMA unit ot_hgi_b2_dma_q at its
// production parameters (FRONT 0, VR2 1, KVW 1, SBIT 35, STACK_BYTES 22.5e9), through its real ports only: the 704 b
// cluster record bus + dma_ret, the burst lane and the single-sector kport lane of stack qid, the local VM slice's packet
// client / DMA wide read group / 32-lane wide write port.  qid is the STRAP: the same DUT runs as cluster 0, 1, 2, 3
// (re-strapped under reset).
// Every model here is the bench's own (no RTL of the unit, no ot_hgi_vm_unit): a sparse HBM byte memory behind two lane
// models with random request / response back-pressure, a sparse VM word memory behind the three VM port models.  The
// REFERENCE is computed from the record alone, before it is sent: the exact set of VM words (LOAD) / HBM bytes (STORE)
// the record must write, with their values.  Checked, item by item, as the DUT drives its ports:
//   - every VM word written (wide port or packet) is an expected word of the running record with the expected value;
//   - every HBM byte written (burst lane or kport lane, by strobe) is an expected byte with the expected value;
//   - every HBM read is of stack qid, 32 B aligned, len 1..8 and inside the record's source sectors (no stray read);
//   - every write-lane beat within a STORE row arrives in ascending sector order;
//   - at retire: every expected VM word was written (LOAD done); at FENCE done: every expected HBM byte was written;
//   - protocol: read group requests only under grant and with a credit, lane == sector[4:0], <= 4 packets outstanding,
//     done / fault only for an outstanding record, no request while idle after reset.
// Traffic (per qid): linear LOAD FP32 / BF16 / FP8E4M3 (sector engine: aligned, multi-row; serial engine: unaligned VM
// rows), STORE FP32 (KV write-back engine: sector-aligned VM rows; sector engine: unaligned VM rows) + FENCE + read-back
// LOAD, STRIPE4 LOAD (only the rows of stack qid may move), the indexed row stream (I list in VM; rows of other stacks
// skipped), a record on another stack (must fault with NO request and NO write, sticky halt -> reset), a reset in the
// middle of a move, back-to-back records and idle gaps, three back-pressure settings on every ready.
// Throughput: a 20,480 B FP32 LOAD and STORE at full rate (no back-pressure): cycles per 32 B sector, record accepted -> done.
// Prints one line: B2_DMA_Q PASS checked=<N> ... / B2_DMA_Q FAIL ...   (checked = VM words + HBM bytes/4 compared exactly).
// Mutants (in the RTL, a parameter of the unit): -GMUT_B2=1 (rows of stack qid + 1 served on lane qid), 2 (lane qid + 1
// driven instead of lane qid): must FAIL in simulation.
// ---------------------------------------------------------------------------------------------------------------------
module tb_hgi_b2_dma_q;
    parameter integer MUT_B2 = 0;
    parameter integer FLAT = 0;
    parameter integer MUT_SEAM = 0;
    parameter integer NREC = 40;                        // random records per qid
    parameter integer SEED = 20261013;
    parameter integer LAT = 12;                         // HBM lane request -> first beat (cycles)
    parameter integer NOL = 16;                         // requests outstanding a lane
    parameter integer GLAT = 12;                        // VM read group request -> response
    parameter integer VLAT = 8;                         // VM packet response latency
    localparam integer SBIT = 35;
    reg clk = 0; always #416 clk = ~clk; reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    integer errs = 0; longint checked = 0; integer n_rec = 0, n_fault = 0, n_rst = 0;
    integer rseed = SEED;
    function automatic integer rnd(input integer n); rnd = int'($unsigned($random(rseed)) % $unsigned(n)); endfunction
    task automatic bad(input string s);
        begin if (errs < 12) $display("B2_DMA_Q ERR @%0d: %s", cyc, s); errs = errs + 1; end
    endtask
    // ---- DUT
    reg [1:0] qid = 0; reg [703:0] dma_rec = 0; wire [3:0] dma_ret;
    wire k_req_v, k_req_we, k_rsp_rdy; reg k_req_rdy = 0, k_rsp_v = 0, k_rsp_we = 0; reg [255:0] k_rsp_data = 0;
    wire [36:0] k_req_addr; wire [255:0] k_req_wdata; wire [31:0] k_req_wstrb; wire [15:0] k_req_tag;
    wire r_req_v, r_req_we, r_rsp_rdy; reg r_req_rdy = 0, r_rsp_v = 0, r_rsp_we = 0, r_rsp_last = 0; reg [15:0] r_rsp_tag = 0;
    reg [255:0] r_rsp_data = 0; wire [36:0] r_req_addr; wire [3:0] r_req_len; wire [15:0] r_req_tag;
    wire [255:0] r_req_wdata; wire [31:0] r_req_wstrb;
    wire [337:0] vmq; reg [273:0] vmr = 0; wire [512:0] vr2q; reg [8256:0] vr2r = '0;
    wire [32*280-1:0] wl; reg [31:0] wl_done = 0;
    generate if (FLAT != 0) begin : g_flat
    ot_hgi_b2_dma_q_flat #(.MUT_B2(MUT_B2)) dut (.clk(clk), .rst_n(rst_n), .qid(qid), .dma_rec(dma_rec), .dma_ret(dma_ret),
        .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_req_addr), .k_req_wdata(k_req_wdata),
        .k_req_wstrb(k_req_wstrb), .k_req_tag(k_req_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we),
        .k_rsp_data(k_rsp_data),
        .r_req_v(r_req_v), .r_req_rdy(r_req_rdy), .r_req_addr(r_req_addr), .r_req_len(r_req_len), .r_req_tag(r_req_tag),
        .r_req_we(r_req_we), .r_req_wdata(r_req_wdata), .r_req_wstrb(r_req_wstrb), .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we),
        .r_rsp_rdy(r_rsp_rdy), .r_rsp_tag(r_rsp_tag), .r_rsp_last(r_rsp_last), .r_rsp_data(r_rsp_data),
        .vmq(vmq), .vmr(vmr), .vr2q(vr2q), .vr2r(vr2r), .wl(wl), .wl_done(wl_done));
    end else begin : g_partition
    wire [279:0] q5_wl; wire [4:0] q5_bank;
    reg [32*280-1:0] vm_wl;
    // VM-side adapter, deliberately OUTSIDE the tile: expand one pin lane into its bank.
    always @* begin vm_wl = '0; if (q5_wl[279]) vm_wl[q5_bank*280 +: 280] = q5_wl; end
    assign wl = vm_wl;
    ot_hgi_b2_dma_q #(.MUT_B2(MUT_B2), .MUT_SEAM(MUT_SEAM)) dut (.clk(clk), .rst_n(rst_n), .qid(qid), .dma_rec(dma_rec), .dma_ret(dma_ret),
        .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_req_addr), .k_req_wdata(k_req_wdata),
        .k_req_wstrb(k_req_wstrb), .k_req_tag(k_req_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we),
        .k_rsp_data(k_rsp_data),
        .r_req_v(r_req_v), .r_req_rdy(r_req_rdy), .r_req_addr(r_req_addr), .r_req_len(r_req_len), .r_req_tag(r_req_tag),
        .r_req_we(r_req_we), .r_req_wdata(r_req_wdata), .r_req_wstrb(r_req_wstrb), .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we),
        .r_rsp_rdy(r_rsp_rdy), .r_rsp_tag(r_rsp_tag), .r_rsp_last(r_rsp_last), .r_rsp_data(r_rsp_data),
        .vmq(vmq), .vmr(vmr), .vr2q(vr2q), .vr2r(vr2r), .wl(q5_wl), .wl_bank(q5_bank), .wl_done(|wl_done));
    end endgenerate
    wire rec_rdy = dma_ret[0], rec_done = dma_ret[1], rec_fault = dma_ret[2];
    bit trace_on; initial trace_on = $test$plusargs("DMA_Q5_TRACE");
    always @(posedge clk) if (rst_n && trace_on) begin
       if (dma_rec[0] && dma_ret[0]) $display("Q5TRACE %0d REC %h", n_rst, dma_rec);
       if (k_req_v && k_req_rdy) $display("Q5TRACE %0d K %b %h %h %h", n_rst, k_req_we, k_req_addr, k_req_wdata & {256{k_req_we}}, k_req_wstrb & {32{k_req_we}});
       if (r_req_v && r_req_rdy) $display("Q5TRACE %0d R %b %h %h %h %h", n_rst, r_req_we, r_req_addr, r_req_len, r_req_wdata & {256{r_req_we}}, r_req_wstrb & {32{r_req_we}});
       if (vmq[337]) $display("Q5TRACE %0d VM %h", n_rst, vmq);
       for (integer b = 0; b < 32; b = b + 1) begin
          if (vr2q[b*16+15]) $display("Q5TRACE %0d G%0d %h", n_rst, b, vr2q[b*16 +: 15]);
          if (wl[b*280+279]) $display("Q5TRACE %0d W%0d %h", n_rst, b, wl[b*280 +: 280]);
       end
    end
    // ---- the bench memories (sparse) and the reference expectation of the running record(s)
    function automatic [7:0] hb(input longint a);              // an unwritten HBM byte
        longint x;
        begin x = a ^ (a >> 31); x = x * 64'h9E3779B97F4A7C15; x = x ^ (x >> 29); x = x * 64'hBF58476D1CE4E5B9; hb = 8'(x >> 40); end
    endfunction
    function automatic [31:0] vw0(input integer a); vw0 = (32'(a) * 32'h2545F491) ^ (32'(a) >> 7) ^ 32'hA5A50F0F; endfunction
    reg [7:0] hbm [longint];                                    // HBM bytes written through the lanes
    reg [7:0] href [longint];                                   // reference: HBM bytes after every issued STORE
    reg [31:0] vm [int];                                        // VM words written through the VM ports / preloaded
    function automatic [7:0] hrd(input longint a); hrd = hbm.exists(a) ? hbm[a] : hb(a); endfunction
    function automatic [7:0] hrf(input longint a); hrf = href.exists(a) ? href[a] : hb(a); endfunction
    function automatic [31:0] vrd(input integer a); vrd = vm.exists(a) ? vm[a] : vw0(a); endfunction
    reg [31:0] exp_vw [int]; bit got_vw [int];                  // LOAD: VM word -> value; written
    reg [7:0] exp_hb [longint]; bit got_hb [longint];           // STORE(s) until the FENCE: HBM byte -> value; written
    bit exp_rd [longint];                                       // sectors (byte address) the record may read
    longint last_ws = -1;                                       // write-lane order check (ascending within a store)
    integer bp = 0;                                             // back-pressure: 0 none, 1 light, 2 heavy
    integer n_rreq = 0, n_kreq = 0, n_vpk = 0, n_g = 0, n_wl = 0;
    bit quiet = 1;                                              // no record outstanding: any request is an error
    integer bp_seed = SEED ^ 32'h7a1bfc03;
    function automatic bit hold;
       integer br; begin br = int'($unsigned($random(bp_seed)) % 4); hold = bp == 1 ? br == 0 : bp == 2 ? br != 0 : 0; end
    endfunction
    task automatic vm_write(input integer a, input [31:0] d, input string via);
        begin
            if (!exp_vw.exists(a)) bad($sformatf("%s: stray VM write word %0d data %h", via, a, d));
            else begin
                if (exp_vw[a] !== d) bad($sformatf("%s: VM word %0d = %h want %h", via, a, d, exp_vw[a]));
                got_vw[a] = 1; checked = checked + 1;
            end
            vm[a] = d;
        end
    endtask
    task automatic hbm_write(input longint a, input [255:0] d, input [31:0] strb, input string via);
        integer nb;
        begin
            nb = 0;
            if (a[36:35] !== qid) bad($sformatf("%s: write to stack %0d on cluster %0d", via, a[36:35], qid));
            if (a[4:0] != 0) bad($sformatf("%s: unaligned write %h", via, a));
            if (strb == 0) bad($sformatf("%s: empty write strobe at %h", via, a));
            for (integer b = 0; b < 32; b = b + 1) if (strb[b]) begin
                if (!exp_hb.exists(a + b)) begin if (nb == 0) bad($sformatf("%s: stray HBM write byte %h", via, a + b)); nb = nb + 1; end
                else begin
                    if (exp_hb[a + b] !== d[8*b +: 8]) begin if (nb == 0) bad($sformatf("%s: HBM byte %h = %h want %h", via, a + b, d[8*b +: 8], exp_hb[a + b])); nb = nb + 1; end
                    if (got_hb.exists(a + b)) begin if (nb == 0) bad($sformatf("%s: HBM byte %h written twice", via, a + b)); nb = nb + 1; end
                    got_hb[a + b] = 1; if ((b & 3) == 0) checked = checked + 1;
                end
                hbm[a + b] = d[8*b +: 8];
            end
        end
    endtask
    task automatic rd_check(input longint a, input integer len, input string via);
        begin
            if (quiet) bad($sformatf("%s: request with no record outstanding", via));
            if (a[36:35] !== qid) bad($sformatf("%s: read of stack %0d on cluster %0d", via, a[36:35], qid));
            if (a[4:0] != 0) bad($sformatf("%s: unaligned read %h", via, a));
            if (len < 1 || len > 8) bad($sformatf("%s: burst length %0d", via, len));
            for (integer i = 0; i < len; i = i + 1) if (!exp_rd.exists(a + 32 * i)) bad($sformatf("%s: stray read of sector %h", via, a + 32 * i));
        end
    endtask
    // ---- burst lane model (stack qid): requests in order, LAT, one beat a cycle held until rsp_rdy, random stalls
    reg [36:0] qa [0:63]; reg [3:0] ql [0:63]; reg qw [0:63]; reg [15:0] qt [0:63]; integer qd [0:63]; integer qh = 0, qn = 0, bt = 0;
    always @(posedge clk) begin
        if (!rst_n) begin qh = 0; qn = 0; bt = 0; r_req_rdy <= 0; r_rsp_v <= 0; end
        else begin
            if (r_rsp_v && r_rsp_rdy) begin
                r_rsp_v <= 0;
                if (bt + 1 == ql[qh % 64] || qw[qh % 64]) begin bt = 0; qh = qh + 1; qn = qn - 1; end else bt = bt + 1;
            end
            if (r_req_v && r_req_rdy) begin
                n_rreq = n_rreq + 1;
                if (r_req_we) begin
                    if (quiet && exp_hb.num() == 0) bad("burst lane: write with no record outstanding");
                    if (r_req_len != 4'd1) bad($sformatf("burst lane: write length %0d", r_req_len));
                    if (longint'(r_req_addr) <= last_ws) bad($sformatf("burst lane: write sector %h not ascending (last %h)", r_req_addr, last_ws));
                    last_ws = longint'(r_req_addr);
                    hbm_write(longint'(r_req_addr), r_req_wdata, r_req_wstrb, "burst lane");
                end else rd_check(longint'(r_req_addr), int'(r_req_len), "burst lane");
                qa[(qh + qn) % 64] = r_req_addr; ql[(qh + qn) % 64] = r_req_len; qw[(qh + qn) % 64] = r_req_we;
                qt[(qh + qn) % 64] = r_req_tag; qd[(qh + qn) % 64] = cyc + LAT; qn = qn + 1;
            end
            if (qn > 0 && qd[qh % 64] <= cyc && !(r_rsp_v && !r_rsp_rdy) && !hold()) begin : present
                longint a; a = longint'(qa[qh % 64]) + 32 * bt;
                // the beat just taken was the head's last: bt / qh already advanced above
                r_rsp_v <= 1; r_rsp_tag <= qt[qh % 64]; r_rsp_we <= qw[qh % 64];
                r_rsp_last <= (bt + 1 == ql[qh % 64]) || qw[qh % 64];
                for (integer b = 0; b < 32; b = b + 1) r_rsp_data[8*b +: 8] <= hrd(a + b);
            end
            r_req_rdy <= (qn < NOL) && !hold();
        end
    end
    // ---- kport lane model (single sectors, in order)
    reg [36:0] ka [0:63]; reg kw [0:63]; integer kd [0:63]; integer kh = 0, kn = 0;
    always @(posedge clk) begin
        if (!rst_n) begin kh = 0; kn = 0; k_req_rdy <= 0; k_rsp_v <= 0; end
        else begin
            if (k_rsp_v && k_rsp_rdy) begin k_rsp_v <= 0; kh = kh + 1; kn = kn - 1; end
            if (k_req_v && k_req_rdy) begin
                n_kreq = n_kreq + 1;
                if (k_req_we) begin
                    if (quiet && exp_hb.num() == 0) bad("kport lane: write with no record outstanding");
                    hbm_write(longint'(k_req_addr), k_req_wdata, k_req_wstrb, "kport lane");
                end else rd_check(longint'(k_req_addr), 1, "kport lane");
                ka[(kh + kn) % 64] = k_req_addr; kw[(kh + kn) % 64] = k_req_we; kd[(kh + kn) % 64] = cyc + LAT; kn = kn + 1;
            end
            if (kn > 0 && kd[kh % 64] <= cyc && !(k_rsp_v && !k_rsp_rdy) && !hold()) begin : kp
                integer h; h = kh;                              // (a beat taken at this edge already advanced kh)
                k_rsp_v <= 1; k_rsp_we <= kw[h % 64];
                for (integer b = 0; b < 32; b = b + 1) k_rsp_data[8*b +: 8] <= hrd(longint'(ka[h % 64]) + b);
            end
            k_req_rdy <= (kn < NOL) && !hold();
        end
    end
    // ---- VM packet client model: in order, VLAT (+ random) later; writes by 32 byte strobes
    reg [337:0] vq [0:15]; integer vd [0:15]; integer vh = 0, vn = 0;
    always @(posedge clk) begin
        vmr[273] <= 1'b0;
        if (!rst_n) begin vh = 0; vn = 0; end
        else begin
            if (vn > 0 && vd[vh % 16] <= cyc) begin : rsp
                reg [337:0] p; integer s; reg [31:0] w;
                p = vq[vh % 16]; s = int'(p[335:309]);
                for (integer i = 0; i < 8; i = i + 1) begin
                    w = vrd(s * 8 + i);
                    if (p[336] && p[16 + 4*i +: 4] != 4'd0) begin
                        for (integer b = 0; b < 4; b = b + 1) if (p[16 + 4*i + b]) w[8*b +: 8] = p[48 + 32*i + 8*b +: 8];
                        if (p[16 + 4*i +: 4] != 4'hF) bad($sformatf("VM packet: partial word strobe %h", p[16 + 4*i +: 4]));
                        vm_write(s * 8 + i, w, "VM packet");
                    end
                    vmr[32*i +: 32] <= w;
                end
                vmr[273] <= 1'b1; vmr[272:257] <= p[15:0]; vmr[256] <= p[336]; vh = vh + 1; vn = vn - 1;   // {v, tag, we, rdata}
            end
            if (vmq[337]) begin
                n_vpk = n_vpk + 1;
                if (quiet) bad("VM packet with no record outstanding");
                if (vmq[335:309] >= 27'd32768) bad($sformatf("VM packet sector %h beyond the slice", vmq[335:309]));
                vq[(vh + vn) % 16] = vmq; vd[(vh + vn) % 16] = cyc + VLAT + ((bp != 0) ? rnd(6) : 0);
                if (vn > 0 && vd[(vh + vn) % 16] <= vd[(vh + vn - 1) % 16]) vd[(vh + vn) % 16] = vd[(vh + vn - 1) % 16] + 1;
                vn = vn + 1;
                if (vn > 4) bad("VM packet client: more than 4 outstanding");
            end
        end
    end
    // ---- VM DMA wide read group model: grant after the request (random delay), a lane's sectors in order GLAT later,
    //      the credit 2 edges after the request; 8 credits a lane
    reg [14:0] gq [0:31][0:63]; integer gd [0:31][0:63]; integer gh [0:31], gn [0:31], gcr [0:31]; reg [31:0] gcr_d1 = 0, gcr_d2 = 0;
    integer gwait = 0;
    initial for (integer b = 0; b < 32; b = b + 1) begin gh[b] = 0; gn[b] = 0; gcr[b] = 8; end
    always @(posedge clk) begin
        if (!rst_n) begin
            vr2r <= '0; gcr_d1 <= 0; gcr_d2 <= 0; gwait = 0;
            for (integer b = 0; b < 32; b = b + 1) begin gh[b] = 0; gn[b] = 0; gcr[b] = 8; end
        end else begin
            if (!vr2q[512]) begin vr2r[8256] <= 1'b0; gwait = (bp != 0) ? rnd(5) : 0; end
            else if (gwait > 0) gwait = gwait - 1;
            else vr2r[8256] <= 1'b1;
            gcr_d2 <= gcr_d1; gcr_d1 <= 32'd0; vr2r[8255:8224] <= gcr_d2;
            for (integer b = 0; b < 32; b = b + 1) begin
                if (gcr_d2[b]) gcr[b] = gcr[b] + 1;
                vr2r[b*257 + 256] <= 1'b0;
                if (gn[b] > 0 && gd[b][gh[b] % 64] <= cyc) begin
                    for (integer w = 0; w < 8; w = w + 1) vr2r[b*257 + 32*w +: 32] <= vrd(int'(gq[b][gh[b] % 64]) * 8 + w);
                    vr2r[b*257 + 256] <= 1'b1; gh[b] = gh[b] + 1; gn[b] = gn[b] - 1;
                end
                if (vr2q[b*16 + 15]) begin
                    n_g = n_g + 1;
                    if (quiet) bad("read group request with no record outstanding");
                    if (!vr2r[8256]) bad("read group request without the grant");
                    if (vr2q[b*16 +: 5] != 5'(b)) bad($sformatf("read group lane %0d got sector %h", b, vr2q[b*16 +: 15]));
                    if (gcr[b] == 0) bad($sformatf("read group lane %0d request without a credit", b));
                    gcr[b] = gcr[b] - 1;
                    gq[b][(gh[b] + gn[b]) % 64] = vr2q[b*16 +: 15]; gd[b][(gh[b] + gn[b]) % 64] = cyc + GLAT; gn[b] = gn[b] + 1;
                    gcr_d1[b] <= 1'b1;
                end
            end
        end
    end
    // ---- VM wide write port model (32 lanes; done one edge later)
    always @(posedge clk) begin
        wl_done <= 32'd0;
        if (rst_n) for (integer b = 0; b < 32; b = b + 1) if (wl[b*280 + 279]) begin
            n_wl = n_wl + 1; wl_done[b] <= 1'b1;
            if (quiet) bad("wide write with no record outstanding");
            if (wl[b*280 + 264 +: 5] != 5'(b)) bad($sformatf("wide write lane %0d got sector %h", b, wl[b*280 + 264 +: 15]));
            if (wl[b*280 +: 8] == 8'd0) bad("wide write with an empty mask");
            for (integer q = 0; q < 8; q = q + 1) if (wl[b*280 + q])
                vm_write(int'(wl[b*280 + 264 +: 15]) * 8 + q, wl[b*280 + 8 + 32*q +: 32], "wide port");
        end
    end
    // ---- return bus monitor
    reg done_seen = 0, fault_seen = 0;
    always @(posedge clk) if (rst_n) begin
        if (rec_done) begin if (quiet) bad("done with no record outstanding"); done_seen = 1; end
        if (rec_fault) fault_seen = 1;
    end
    // ---- reference decode (spec 6.4 element formats -> the FP32 VM word)
    function automatic [31:0] f32(input real v);
        reg [63:0] d;
        begin d = $realtobits(v); f32 = (d[62:0] == 63'd0) ? {d[63], 31'd0} : {d[63], 8'(d[62:52] - 11'd1023 + 11'd127), d[51:29]}; end
    endfunction
    function automatic [31:0] e4(input [7:0] c);
        real v; integer e, m; reg [31:0] r;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 15 && m == 7) e4 = 32'h7FC00000;
            else begin
                v = (e == 0) ? (m / 8.0) * (2.0 ** -6) : (1.0 + m / 8.0) * (2.0 ** (e - 7));
                r = f32(v); r[31] = c[7]; if (v == 0.0) r = {c[7], 31'd0}; e4 = r;
            end
        end
    endfunction
    function automatic [31:0] dec(input integer f, input longint a);
        case (f)
            1: dec = {hrf(a + 1), hrf(a), 16'd0};
            2: dec = e4(hrf(a));
            default: dec = {hrf(a + 3), hrf(a + 2), hrf(a + 1), hrf(a)};
        endcase
    endfunction
    function automatic integer esz(input integer f); esz = (f == 1) ? 2 : (f == 2) ? 1 : 4; endfunction
    // ---- record driver
    reg [127:0] hdr; reg [255:0] ra, ro; reg [20:0] nA, nO;
    task automatic reset_all;
        begin
            @(negedge clk); rst_n = 0; dma_rec = 0; quiet = 1;
            exp_vw.delete(); got_vw.delete(); exp_hb.delete(); got_hb.delete(); exp_rd.delete(); last_ws = -1;
            repeat (6) @(negedge clk); rst_n = 1; repeat (6) @(negedge clk); done_seen = 0; fault_seen = 0; n_rst = n_rst + 1;
        end
    endtask
    task automatic send;                                       // presents the record; returns at acceptance
        integer t0;
        begin
            @(negedge clk); done_seen = 0; fault_seen = 0; quiet = 0;
            dma_rec = {21'd1, nO, nA, ro, ra, hdr, 1'b1};
            t0 = cyc; while (!rec_rdy && cyc - t0 < 200000) @(negedge clk);
            if (!rec_rdy) begin bad("record never accepted"); end
            @(posedge clk); #50 dma_rec[0] = 1'b0; n_rec = n_rec + 1;
        end
    endtask
    task automatic wait_done(output integer cycles, input integer lim);
        integer t0;
        begin
            t0 = cyc;
            while (!done_seen && !fault_seen && cyc - t0 < lim) @(posedge clk);
            cycles = cyc - t0;
            if (fault_seen || !done_seen) begin
                bad($sformatf("record %s: op %0d bp %0d A{sp %0d f %0d base %h n %0d m %0d str %0d} O{sp %0d base %h str %0d}", fault_seen ? "faulted" : "never retired",
                    hdr[123:118], bp, ra[1:0], ra[4:2], ra[47:8], ra[67:48], ra[87:68], ra[119:88], ro[1:0], ro[47:8], ro[119:88]));
                if ($test$plusargs("dbg")) $display("DBG qid %0d ist %0d k: v %b rdy %b we %b a %h kn %0d rsp_v %b rsp_rdy %b | r: v %b rdy %b qn %0d rsp_v %b rsp_rdy %b | vn %0d vmq_v %b ret %b",
                    qid, ra[135:120], k_req_v, k_req_rdy, k_req_we, k_req_addr, kn, k_rsp_v, k_rsp_rdy, r_req_v, r_req_rdy, qn, r_rsp_v, r_rsp_rdy, vn, vmq[337], dma_ret);
                reset_all();                                    // the unit halts on a fault (sticky): reset, carry on
            end
            @(negedge clk); quiet = (exp_hb.num() == 0);
        end
    endtask
    task automatic check_vw(input string what);
        integer miss; integer a;
        begin
            miss = 0;
            if (exp_vw.first(a)) do begin if (!got_vw.exists(a)) begin if (miss == 0) bad($sformatf("%s: VM word %0d never written (want %h)", what, a, exp_vw[a])); miss = miss + 1; end end while (exp_vw.next(a));
            if (miss > 1) bad($sformatf("%s: %0d VM words never written", what, miss));
            exp_vw.delete(); got_vw.delete(); exp_rd.delete();
        end
    endtask
    task automatic fence;                                      // DMA.FENCE: every posted HBM write visible at retire
        integer c, miss; longint a;
        begin
            hdr = 0; hdr[127:124] = 4'd8; hdr[123:118] = 6'd2; ra = 0; ro = 0; nA = 0; nO = 0;
            send(); wait_done(c, 400000);
            miss = 0;
            if (exp_hb.first(a)) do begin if (!got_hb.exists(a)) begin if (miss == 0) bad($sformatf("FENCE: HBM byte %h never written", a)); miss = miss + 1; end end while (exp_hb.next(a));
            if (miss > 1) bad($sformatf("FENCE: %0d HBM bytes never written", miss));
            exp_hb.delete(); got_hb.delete(); last_ws = -1; quiet = 1;
        end
    endtask
    longint hnext = 64'h1000;                                  // HBM region allocator (stack-local byte, 32 B aligned): disjoint regions
    function automatic longint halloc(input longint bytes);
        begin halloc = hnext + 32 * rnd(64); hnext = halloc + ((bytes + 31) / 32) * 32 + 32; end
    endfunction
    function automatic longint gaddr(input longint local_a); gaddr = (longint'(qid) << SBIT) | local_a; endfunction
    // linear / STRIPE4 LOAD: A (HBM fmt f, byte base ab, stride as, STRIPE4 with row-0 stack s0) -> O (VM words db, stride ds)
    task automatic load(input integer f, input longint ab, input integer n, input integer m, input integer as_, input integer db,
                        input integer ds, input bit stripe, input integer s0, output integer cycles);
        longint a; integer own;
        begin
            own = 0;
            for (integer r = 0; r < m; r = r + 1) begin
                if (stripe && ((s0 + r) & 3) != int'(qid)) continue;
                own = own + 1;
                for (integer i = 0; i < n; i = i + 1) begin
                    a = gaddr(ab + longint'(r) * as_ + i * g_ist * esz(f));
                    exp_vw[db + r * ds + i] = dec(f, a);
                    exp_rd[a & ~64'd31] = 1; exp_rd[(a + esz(f) - 1) & ~64'd31] = 1;
                end
            end
            hdr = 0; hdr[127:124] = 4'd8; hdr[123:118] = 6'd0; hdr[93] = 1; hdr[97] = 1;
            ra = 0; ra[4:2] = 3'(f); ra[47:8] = stripe ? ((40'd1 << 37) | (40'(s0) << SBIT) | 40'(ab)) : 40'(gaddr(ab));
            ra[67:48] = 20'(n); ra[87:68] = 20'(m); ra[119:88] = 32'(as_); ra[135:120] = 16'(g_ist);
            ro = 0; ro[1:0] = 2'd1; ro[47:8] = 40'(db); ro[67:48] = 20'(n); ro[87:68] = 20'(m); ro[119:88] = 32'(ds);
            nA = 21'(n); nO = 21'(n);
            send(); wait_done(cycles, 400000 + 200 * n * m);
            check_vw($sformatf("LOAD f%0d n%0d m%0d%s", f, n, m, stripe ? " STRIPE4" : ""));
        end
    endtask
    // STORE FP32: A (VM words ab, stride as) -> O (HBM byte base ob, stride os); posted (retires when the source is read)
    task automatic store(input integer ab, input integer n, input integer m, input integer as_, input longint ob, input integer os,
                         output integer cycles);
        longint a; reg [31:0] w;
        begin
            for (integer r = 0; r < m; r = r + 1) for (integer i = 0; i < n; i = i + 1) begin
                w = vrd(ab + r * as_ + i); a = gaddr(ob + longint'(r) * os + 4 * i);
                for (integer b = 0; b < 4; b = b + 1) begin exp_hb[a + b] = w[8*b +: 8]; href[a + b] = w[8*b +: 8]; end
            end
            hdr = 0; hdr[127:124] = 4'd8; hdr[123:118] = 6'd1; hdr[93] = 1; hdr[97] = 1;
            ra = 0; ra[1:0] = 2'd1; ra[47:8] = 40'(ab); ra[67:48] = 20'(n); ra[87:68] = 20'(m); ra[119:88] = 32'(as_);
            ro = 0; ro[47:8] = 40'(gaddr(ob)); ro[67:48] = 20'(n); ro[87:68] = 20'(m); ro[119:88] = 32'(os);
            nA = 21'(n); nO = 21'(n); last_ws = -1;
            send(); wait_done(cycles, 400000 + 200 * n * m);
        end
    endtask
    // indexed row stream: row e = HBM row of id_e (base + id_e x mul), ids from the I list in VM; rows of other stacks skipped
    task automatic istream(input integer f, input integer n, input integer cnt, input integer db, input integer ds, input integer ib);
        longint ab, mul, a, ra0; integer ids [0:63]; integer c;
        begin
            mul = 64'd1 << 25; ab = 32 * rnd(1024);
            for (integer e = 0; e < cnt; e = e + 1) begin
                ids[e] = (rnd(4) << 10) | rnd(600);
                if (e == 0 || rnd(3) == 0) ids[e] = (int'(qid) << 10) | rnd(600);       // enough own rows
                if (e > 1 && rnd(6) == 0) ids[e] = ids[e - 1];
                vm[ib + e] = 32'(ids[e]);
                ra0 = ab + longint'(ids[e]) * mul;
                if (ra0[36:35] == qid) for (integer i = 0; i < n; i = i + 1) begin
                    a = ra0 + i * esz(f); exp_vw[db + e * ds + i] = dec(f, a);
                    exp_rd[a & ~64'd31] = 1; exp_rd[(a + esz(f) - 1) & ~64'd31] = 1;
                end
            end
            for (integer i = 0; i < 4; i = i + 1) exp_rd[-1 - i] = 1;   // (placeholder keys: never requested)
            hdr = 0; hdr[127:124] = 4'd8; hdr[123:118] = 6'd0; hdr[93] = 1; hdr[97] = 1; hdr[99] = 1;
            ra = 0; ra[4:2] = 3'(f); ra[6] = 1'b1; ra[47:8] = 40'(ab + longint'(ids[0]) * mul); ra[67:48] = 20'(cnt); ra[87:68] = 20'd1;
            ra[200:174] = 27'(mul); ra[206:201] = 6'd63; ra[255:239] = 17'(ib >> 1); ra[7] = ib[0];
            ro = 0; ro[1:0] = 2'd1; ro[47:8] = 40'(db); ro[67:48] = 20'(n); ro[87:68] = 20'(cnt + 1); ro[119:88] = 32'(ds);
            nA = 21'(cnt); nO = 21'(n);
            send(); wait_done(c, 400000 + 400 * n * cnt);
            check_vw($sformatf("ISTREAM f%0d n%0d rows%0d", f, n, cnt));
        end
    endtask
    // a linear LOAD on another stack: must fault, with no request and no write (fail-closed); the unit halts -> reset
    task automatic offstack;
        integer t0, r0, k0, w0, v0; reg [1:0] os;
        begin
            r0 = n_rreq; k0 = n_kreq; w0 = n_wl; v0 = n_vpk;
            hdr = 0; hdr[127:124] = 4'd8; hdr[123:118] = 6'd0; hdr[93] = 1; hdr[97] = 1;
            os = qid + 2'd1 + 2'(rnd(3)); ra = 0; ra[47:8] = 40'((longint'(os) << SBIT) + 64'h200); ra[67:48] = 20'd16; ra[87:68] = 20'd1; ra[119:88] = 32'd64;
            ro = 0; ro[1:0] = 2'd1; ro[47:8] = 40'd40000; ro[67:48] = 20'd16; ro[87:68] = 20'd1; ro[119:88] = 32'd16;
            nA = 21'd16; nO = 21'd16;
            send(); t0 = cyc;
            while (!fault_seen && !done_seen && cyc - t0 < 20000) @(posedge clk);
            repeat (200) @(posedge clk);
            if (!fault_seen || done_seen) bad($sformatf("off-stack record: fault %0d done %0d (want fault only) qid %0d A base %h", fault_seen, done_seen, qid, ra[47:8]));
            if (n_rreq != r0 || n_kreq != k0 || n_wl != w0 || n_vpk != v0) bad("off-stack record issued a request");
            else checked = checked + 1;
            n_fault = n_fault + 1;
            reset_all();
        end
    endtask
    integer tp_ld = 0, tp_st = 0, tp_sl = 0, tp_sf = 0;        // worst of the four straps
    integer g_ist = 1;                                          // A's element stride of the next LOAD (!= 1: the serial engine)
    task automatic one_qid(input integer q);
        integer c, k, n, m, db, f, t1; longint hb0;
        begin
            @(negedge clk); rst_n = 0; qid = 2'(q); hnext = 64'h1000 + 64'h100000 * q; reset_all();
            // throughput at full rate: 20,480 B FP32 (640 sectors), sector engine LOAD and KV engine STORE
            bp = 0;
            hb0 = halloc(20480); load(0, hb0, 5120, 1, 20480, 8192, 5120, 0, 0, c); if (c > tp_ld) tp_ld = c;
            hb0 = halloc(20480); t1 = cyc; store(8192, 5120, 1, 5120, hb0, 20480, c); if (c > tp_st) tp_st = c; fence(); if (cyc - t1 > tp_sf) tp_sf = cyc - t1;
            load(0, hb0, 5120, 1, 20480, 65536, 5120, 0, 0, c);                    // read back the stored row
            hb0 = halloc(1024); load(2, hb0, 1024, 1, 1024, 3001, 1024, 0, 0, c); if (c > tp_sl) tp_sl = c;   // FP8 -> 128 VM sectors (unaligned)
            for (integer rec = 0; rec < NREC; rec = rec + 1) begin
                bp = rnd(3); k = rnd(13);
                if (rnd(3) == 0) repeat (rnd(60)) @(negedge clk);                 // idle gap (else back to back)
                case (k)
                    0, 1: begin                                                    // sector engine LOAD, rows
                        n = 8 * (1 + rnd(40)); m = 1 + rnd(3); db = 8 * rnd(20000);
                        hb0 = halloc(longint'(n) * 4 * m + 64 * m);
                        load(0, hb0, n, m, n * 4 + 32 * rnd(2), db, n + 8 * rnd(3), 0, 0, c);
                    end
                    2: begin                                                       // unaligned VM row; half of them STRIDED (serial engine, kport lane)
                        n = 1 + rnd(200); g_ist = (rnd(2) == 0) ? 1 : 2 + rnd(3); hb0 = halloc(n * 4 * g_ist);
                        load(0, hb0, n, 1, n * 4 * g_ist, 1 + rnd(200000), n, 0, 0, c); g_ist = 1;
                    end
                    3: begin n = 1 + rnd(300); hb0 = halloc(n * 2); load(1, hb0, n, 1, n * 2, rnd(200000), n, 0, 0, c); end      // BF16
                    4: begin n = 1 + rnd(400); hb0 = halloc(n); load(2, hb0, n, 1, n, rnd(200000), n, 0, 0, c); end              // FP8E4M3
                    5, 6: begin                                                    // KV engine STORE (whole sectors) + FENCE + read-back
                        n = 8 * (1 + rnd(48)); m = 1 + rnd(3); db = 8 * rnd(20000);
                        hb0 = halloc(longint'(n) * 4 * m);
                        store(db, n, m, n + 8 * rnd(2), hb0, n * 4, c);
                        if (rnd(2) == 0) begin fence(); load(0, hb0, n, m, n * 4, 8 * rnd(20000), n, 0, 0, c); end
                    end
                    7: begin                                                       // sector-engine STORE (VM row not sector aligned) + FENCE + read-back
                        n = 8 * (1 + rnd(16)); hb0 = halloc(n * 4);
                        store(1 + rnd(200000), n, 1, n, hb0, n * 4, c); fence();
                        load(0, hb0, n, 1, n * 4, 1 + rnd(200000), n, 0, 0, c);
                    end
                    8, 9: begin                                                    // STRIPE4 LOAD: only the rows of stack qid
                        n = 8 * (1 + rnd(24)); m = 2 + rnd(9); hb0 = halloc(longint'(n) * 4 * m);
                        load(0, hb0, n, m, n * 4, 8 * rnd(20000), n + 8 * rnd(2), 1, rnd(4), c);
                    end
                    10, 11: begin f = rnd(3); istream(f, (f == 0) ? 8 * (1 + rnd(8)) : 32 * (1 + rnd(8)), 2 + rnd(14), 8 * rnd(20000), 256 + 8 * rnd(4), 100000 + rnd(50000)); end
                    default: begin if (exp_hb.num() != 0) fence(); offstack(); end
                endcase
            end
            if (exp_hb.num() != 0) fence();
            // reset in the middle of a move; the unit must then run clean
            bp = 1; hb0 = halloc(8192);
            hdr = 0; hdr[127:124] = 4'd8; hdr[93] = 1; hdr[97] = 1;
            ra = 0; ra[47:8] = 40'(gaddr(hb0)); ra[67:48] = 20'd2048; ra[87:68] = 20'd1; ra[119:88] = 32'd8192;
            ro = 0; ro[1:0] = 2'd1; ro[47:8] = 40'd16384; ro[67:48] = 20'd2048; ro[87:68] = 20'd1; ro[119:88] = 32'd2048;
            nA = 21'd2048; nO = 21'd2048;
            for (integer i = 0; i < 2048; i = i + 1) begin exp_vw[16384 + i] = dec(0, gaddr(hb0 + 4 * i)); exp_rd[gaddr(hb0 + 4 * i) & ~64'd31] = 1; end
            send(); repeat (40 + rnd(120)) @(negedge clk);
            reset_all();
            repeat (40) @(negedge clk);
            if (done_seen || fault_seen) bad("done / fault after a reset with no record");
            bp = 2; hb0 = halloc(2048); load(0, hb0, 512, 1, 2048, 16384, 512, 0, 0, c);
            bp = 0; store(16384, 512, 1, 512, hb0 + 4096, 2048, c); hnext = hnext + 8192; fence();
        end
    endtask
    initial begin
        for (integer q = 0; q < 4; q = q + 1) one_qid(q);
        repeat (100) @(negedge clk);
        $display("B2_DMA_Q TPUT load_fp32_20480B cycles=%0d cyc_per_sector=%0.3f B_per_cycle=%0.2f | store_fp32_20480B(posted) cycles=%0d cyc_per_sector=%0.3f B_per_cycle=%0.2f | store+fence(drained) cycles=%0d cyc_per_sector=%0.3f B_per_cycle=%0.2f | fp8_1024el cycles=%0d cyc_per_elem=%0.3f",
                 tp_ld, tp_ld / 640.0, 20480.0 / tp_ld, tp_st, tp_st / 640.0, 20480.0 / tp_st, tp_sf, tp_sf / 640.0, 20480.0 / tp_sf, tp_sl, tp_sl / 1024.0);
        $display("B2_DMA_Q STATS records=%0d faults=%0d resets=%0d burst_reqs=%0d kport_reqs=%0d vm_packets=%0d group_reads=%0d wide_writes=%0d cycles=%0d",
                 n_rec, n_fault, n_rst, n_rreq, n_kreq, n_vpk, n_g, n_wl, cyc);
        if (errs == 0 && checked > 0) $display("B2_DMA_Q PASS checked=%0d records=%0d MUT_B2=%0d", checked, n_rec, MUT_B2);
        else $display("B2_DMA_Q FAIL errors=%0d checked=%0d records=%0d MUT_B2=%0d", errs, checked, n_rec, MUT_B2);
        $finish;
    end
    initial begin #(64'd833 * 64'd40000000); $display("B2_DMA_Q FAIL timeout checked=%0d", checked); $finish; end
endmodule
