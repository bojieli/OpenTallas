`timescale 1ns/1ps
// hbm-forks 2026-10-09: CF-PROG smoke for the HGI-1 sequencer (ot_hgi_seq), vectors from tools/hgi_seq_vectors.py
// (13 records: DMA, LOOP x3 {FUSED, SM, SU+SUT, ATT, COLL, DMA last-iteration}, ENDLOOP, SFU pos==0, ARGMAX pos!=0 with a
// full drain, FENCE, END; every DYN selector, n_sel, lstride).  The image starts mid-sector (entry 3) at page 0x10.
// Checks: every dispatch (unit, header, SUT, the 4 effective descriptors) equals the reference model in order; the
// `wait` rule holds at every dispatch against the bench's own outstanding counts; FENCE drains; completion token and
// status (incl. the cp_vocab refusal).  Random fetch / unit ready, fetch latency and unit retire delays.
// Prints HGI_SEQ PASS / FAIL.  Mutants: OT_HGI_SEQ_MUT_WAIT (wait ignored), OT_HGI_SEQ_MUT_LOOP (one iteration short).
module tb_hgi_seq;
    localparam integer NW = 63, NCASE = 3, PAGE = 32'h10, ENTRY = 32'd3;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg [159:0] md_d; reg [17:0] vocab; reg [7:0] rank;
    reg db_v = 0; reg [17:0] db_token; reg [19:0] db_pos; wire db_rdy;
    wire f_req_v; reg f_req_rdy = 0; wire [39:0] f_req_addr; reg f_rsp_v = 0; reg [255:0] f_rsp_data;
    wire [11:0] u_v; reg [11:0] u_rdy = 0; wire [127:0] d_hdr; wire [255:0] d_sut; wire [1023:0] d_desc;
    reg [11:0] u_done = 0, u_fault = 0; reg res_v = 0; reg [31:0] res_data = 0;
    wire cpl_v; reg cpl_rdy = 0; wire [17:0] cpl_token; wire [19:0] cpl_pos; wire [31:0] cpl_job, cpl_cycles; wire [3:0] cpl_gen, cpl_status;
    ot_hgi_seq dut (.clk(clk), .rst_n(rst_n), .md_d(md_d), .cfg_vocab(vocab), .rank(rank), .hold(1'b0),
        .db_v(db_v), .db_rdy(db_rdy), .db_token(db_token), .db_pos(db_pos), .db_job(32'h1234), .db_gen(4'h5), .db_entry(2'd0),
        .f_req_v(f_req_v), .f_req_rdy(f_req_rdy), .f_req_addr(f_req_addr), .f_rsp_v(f_rsp_v), .f_rsp_data(f_rsp_data),
        .u_v(u_v), .u_rdy(u_rdy), .d_hdr(d_hdr), .d_sut(d_sut), .d_desc(d_desc), .u_done(u_done), .u_fault(u_fault),
        .res_v(res_v), .res_data(res_data), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy), .cpl_token(cpl_token), .cpl_pos(cpl_pos),
        .cpl_job(cpl_job), .cpl_gen(cpl_gen), .cpl_status(cpl_status), .cpl_cycles(cpl_cycles));
    reg [127:0] img [0:NW-1];
    reg [255:0] cfgw [0:NCASE-1];
    reg [255:0] ex [0:2000];
    initial begin $readmemh("hgi_seq_image.mem", img); $readmemh("hgi_seq_expect.mem", ex); end
    reg [31:0] cfg [0:NCASE*8-1];
    initial $readmemh("hgi_seq_cfg.mem", cfg);
    // ---- HBM: word w of the image at byte PAGE*4096 + ENTRY*16 + 16 w; in-order responses after 3..12 cycles
    localparam [39:0] IMG = PAGE * 4096 + ENTRY * 16;
    function automatic [127:0] word_at(input [39:0] a);
        reg signed [41:0] w; begin w = ($signed({2'b0, a}) - $signed({2'b0, IMG})) / 16;
            word_at = (w >= 0 && w < NW) ? img[w] : 128'hDEAD; end
    endfunction
    reg [39:0] fq [0:63]; integer fqh = 0, fqn = 0, fdel = 0;
    always @(posedge clk) begin
        f_req_rdy <= ($urandom % 3) != 0;
        if (f_req_v && f_req_rdy) begin fq[(fqh + fqn) % 64] = f_req_addr; fqn = fqn + 1; end
        f_rsp_v <= 1'b0;
        if (fqn > 0) begin
            if (fdel > 0) fdel = fdel - 1;
            else begin
                f_rsp_v <= 1'b1; f_rsp_data <= {word_at(fq[fqh] + 16), word_at(fq[fqh])}; fqh = (fqh + 1) % 64; fqn = fqn - 1;
                fdel = $urandom % 4;
            end
        end
    end
    // ---- units: accept, check, retire after 0..20 cycles
    integer outst [0:11]; integer pend [0:11][0:15]; integer pn [0:11];
    integer ei = 0, nd = 0, fails = 0, w, k, uu;
    reg [3:0] cu;
    always @(posedge clk) begin
        u_rdy <= $urandom; u_done <= 0;
        for (uu = 1; uu < 12; uu = uu + 1) begin
            for (k = 0; k < pn[uu]; k = k + 1) pend[uu][k] = pend[uu][k] - 1;
            if (pn[uu] > 0 && pend[uu][0] <= 0) begin
                u_done[uu] <= 1'b1; outst[uu] = outst[uu] - 1;
                for (k = 0; k < 15; k = k + 1) pend[uu][k] = pend[uu][k + 1];
                pn[uu] = pn[uu] - 1;
            end
        end
        if (|(u_v & u_rdy)) begin
            cu = d_hdr[127:124];
            if (u_v !== (12'd1 << cu)) begin $display("FAIL dispatch port %h for unit %0d", u_v, cu); fails = fails + 1; end
            for (w = 0; w < 12; w = w + 1) if (d_hdr[106 + w] && outst[w] != 0) begin
                $display("FAIL wait rule: unit %0d dispatched while unit %0d has %0d outstanding", cu, w, outst[w]); fails = fails + 1; end
            if (ex[ei][3:0] !== cu || ex[ei + 1][127:0] !== d_hdr || ex[ei + 2] !== d_sut || ex[ei + 3] !== d_desc[255:0] ||
                ex[ei + 4] !== d_desc[511:256] || ex[ei + 5] !== d_desc[767:512] || ex[ei + 6] !== d_desc[1023:768]) begin
                $display("FAIL dispatch %0d unit %0d (exp unit %0d) hdr %b sut %b A %b B %b C %b O %b", nd, cu, ex[ei][3:0],
                    ex[ei+1][127:0] === d_hdr, ex[ei+2] === d_sut, ex[ei+3] === d_desc[255:0], ex[ei+4] === d_desc[511:256],
                    ex[ei+5] === d_desc[767:512], ex[ei+6] === d_desc[1023:768]);
                fails = fails + 1;
            end
            ei = ei + 7; nd = nd + 1;
            outst[cu] = outst[cu] + 1; pend[cu][pn[cu]] = $urandom % 21; pn[cu] = pn[cu] + 1;
        end
    end
    integer c, n0, t;
    initial begin
        for (k = 0; k < 12; k = k + 1) begin outst[k] = 0; pn[k] = 0; end
        md_d = {32'd1, PAGE, 32'd0, 32'd0, ENTRY}; rank = 0;
        repeat (3) @(posedge clk); rst_n = 1; @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            vocab = cfg[c*8 + 3]; rank = cfg[c*8 + 2];
            n0 = nd;
            @(negedge clk); while (!db_rdy) @(negedge clk);
            db_token = cfg[c*8 + 0]; db_pos = cfg[c*8 + 1]; db_v = 1; @(negedge clk); db_v = 0;
            repeat (5) @(negedge clk); res_v = 1; res_data = cfg[c*8 + 4]; @(negedge clk); res_v = 0;
            t = 0; while (!cpl_v && t < 20000) begin @(negedge clk); t = t + 1; end
            if (!cpl_v) begin $display("FAIL case %0d: no completion (dispatches %0d)", c, nd - n0); fails = fails + 1; end
            else if (cpl_token !== cfg[c*8 + 6][17:0] || cpl_status !== cfg[c*8 + 7][3:0] || nd - n0 !== cfg[c*8 + 5]) begin
                $display("FAIL case %0d: token %0d/%0d status %0d/%0d dispatches %0d/%0d", c, cpl_token, cfg[c*8 + 6],
                         cpl_status, cfg[c*8 + 7], nd - n0, cfg[c*8 + 5]); fails = fails + 1;
            end else $display("SEQ case %0d: %0d dispatches, token %0d status %0d, %0d cycles", c, nd - n0, cpl_token, cpl_status, cpl_cycles);
            repeat ($urandom % 3) @(negedge clk);
            cpl_rdy = 1; @(negedge clk); cpl_rdy = 0;
            t = 0; while ((outst[1] + outst[2] + outst[3] + outst[4] + outst[5] + outst[6] + outst[7] + outst[8]) != 0 && t < 200)
                begin @(negedge clk); t = t + 1; end
        end
        if (fails == 0) $display("HGI_SEQ PASS cases=%0d dispatches=%0d", NCASE, nd);
        else $display("HGI_SEQ FAIL %0d", fails);
        $finish;
    end
endmodule
