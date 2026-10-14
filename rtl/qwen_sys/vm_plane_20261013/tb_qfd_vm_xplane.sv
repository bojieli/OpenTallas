`timescale 1ns/1ps
// Leaf bench (claude/qwen-tp8-vm-1013): 32 x ot_qfd_vm_xplane_t behind XPR x ot_qfd_vm_xrelay_t per bank against the
// parent's own expressions (ot_qfd_sp_vector_memory_bv rot1 / rot2 / bv, copied verbatim below as the reference) fed
// XPR + 1 engine edges earlier.  Random words, random beat addresses INCLUDING addresses whose beat runs past ELEMS
// (the range mask the system bench does not reach), me stalls 1 in 4.  PMUT 1 / 2 / 3 (plane 5), RMUT 1 must FAIL.
module tb_qfd_vm_xplane;
    parameter integer NRB = 64, XPR = 10, ELEMS = 177808, AW = 24, CYCLES = 3000, PMUT = 0, RMUT = 0, SEED = 1;
    localparam integer LNRB = $clog2(NRB), BEAT = (NRB - 1) * 16, NVW = $clog2(BEAT + 1), L = XPR + 1;
    reg clk = 0; always #5 clk = ~clk;
    reg me_e = 0, me = 0;
    always @(posedge clk) me <= me_e;
    reg [NRB*512-1:0] xo;                        // tile xo register (moves on engine edges)
    reg [AW-1:0]      a_in;                      // the beat address that accompanies xo
    // ---- candidate ----
    wire [(XPR+1)*NRB*512-1:0] xw;
    assign xw[0 +: NRB*512] = xo;
    genvar k, b, p, e;
    generate for (k = 1; k <= XPR; k = k + 1) begin : g_k
        for (b = 0; b < NRB; b = b + 1) begin : g_b
            ot_qfd_vm_xrelay_t #(.W(512), .MUT((RMUT != 0 && k == 3 && b == 9) ? 1 : 0)) u_r (.clk(clk), .me_e(me_e),
                .d(xw[((k-1)*NRB + b)*512 +: 512]), .q(xw[(k*NRB + b)*512 +: 512]));
        end
    end endgenerate
    wire [NRB*512-1:0] capx = xw[XPR*NRB*512 +: NRB*512];
    reg [AW-1:0] ap [0:XPR+1];                   // address pipeline: ap[XPR-1] feeds nvx, ap[XPR] is at the pins
    reg [NVW-1:0] nvx;
    integer i;
    always @(posedge clk) if (me) begin
        ap[0] <= a_in;
        for (i = 1; i <= XPR + 1; i = i + 1) ap[i] <= ap[i-1];
        nvx <= (ap[XPR-2] >= ELEMS) ? 0 : ((ELEMS - ap[XPR-2]) >= BEAT) ? BEAT : (ELEMS - ap[XPR-2]);
    end
    wire [BEAT*32-1:0] bvs;
    generate for (p = 0; p < 32; p = p + 1) begin : g_p
        wire [NRB*16-1:0] pd; wire [BEAT-1:0] pq;
        for (e = 0; e < NRB*16; e = e + 1) begin : g_i assign pd[e] = capx[e*32 + p]; end
        ot_qfd_vm_xplane_t #(.NRB(NRB), .MUT((p == 5) ? PMUT : 0)) u_p (.clk(clk), .me_e(me_e), .d(pd),
            .c_a(ap[XPR-1][LNRB+3:0]), .c_nv(nvx), .q(pq));
        for (e = 0; e < BEAT; e = e + 1) begin : g_o assign bvs[e*32 + p] = pq[e]; end
    end endgenerate
    // ---- reference: the parent's expressions, on xo delayed L engine edges ----
    reg [NRB*512-1:0] dl [0:L-1];
    reg [AW-1:0] s3_a, s4_a, s5_a;
    reg [NRB*512-1:0] rot1, rot2;
    reg [BEAT*32-1:0] bv;
    wire [LNRB-1:0] rot = s3_a[4 +: LNRB];
    wire [LNRB-1:0] rotf = s4_a[4 +: LNRB] & 7;
    wire [3:0] sh = s5_a[3:0];
    always @(posedge clk) if (me) begin
        dl[0] <= xo; for (i = 1; i < L; i = i + 1) dl[i] <= dl[i-1];
        s3_a <= ap[XPR-1]; s4_a <= s3_a; s5_a <= s4_a;
        for (i = 0; i < NRB; i = i + 1) begin
            rot1[i*512 +: 512] <= dl[L-1][((i + (rot & ~7)) % NRB)*512 +: 512];
            rot2[i*512 +: 512] <= rot1[((i + rotf) % NRB)*512 +: 512];
        end
        for (i = 0; i < BEAT; i = i + 1) bv[i*32 +: 32] <= ((s5_a + i) < ELEMS) ? rot2[(i + sh)*32 +: 32] : 32'd0;
    end
    // Stimulus generator: xorshift64 (2026-10-13: `rnd(0)` re-seeds on every call under Verilator, so the first
    // version of this bench held me_e at 0 for the whole run and compared two idle pipelines: every mutant PASSED).
    // The run is refused as vacuous unless engine edges, stalls and range-edge beats all occurred.
    reg [63:0] rng;
    function automatic [31:0] rnd(input integer dummy);
        begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 7); rng = rng ^ (rng << 17); rnd = rng[47:16]; end
    endfunction
    integer cyc, w, errors = 0, checks = 0, edge_beats = 0, stalls = 0, moves = 0;
    initial begin
        rng = 64'h9E3779B97F4A7C15 ^ {32'd0, SEED[31:0]} ^ ({32'd0, SEED[31:0]} << 32);
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            me_e = ((rnd(0) % 4) != 0);
            if (!me_e) stalls = stalls + 1; else moves = moves + 1;
            for (w = 0; w < NRB*16; w = w + 1) xo[w*32 +: 32] = rnd(0);
            // one address in three within 2 beats of the end of the memory (range mask), the rest anywhere
            a_in = ((rnd(0) % 3) == 0) ? ELEMS - 1 - (rnd(0) % (2*BEAT)) : rnd(0) % ELEMS;
            if (a_in + BEAT > ELEMS) edge_beats = edge_beats + 1;
            @(posedge clk); #1;
            if (cyc > 4 * (L + 8)) begin
                checks = checks + 1;
                if (bvs !== bv) begin errors = errors + 1; if (errors < 4) $display("xplane mismatch cyc %0d", cyc); end
            end
        end
        if (moves < CYCLES / 2 || stalls < CYCLES / 8 || edge_beats < CYCLES / 8) begin
            $display("FAIL qfd_vm_xplane VACUOUS moves=%0d stalls=%0d edge_beats=%0d", moves, stalls, edge_beats); $fatal(1, "FAIL");
        end
        if (errors != 0) begin $display("FAIL qfd_vm_xplane errors=%0d of %0d", errors, checks); $fatal(1, "FAIL"); end
        $display("PASS qfd_vm_xplane NRB=%0d XPR=%0d exact %0d checks, %0d range-edge beats, %0d stalls, +%0d engine edges",
                 NRB, XPR, checks, edge_beats, stalls, L);
        $finish;
    end
endmodule
