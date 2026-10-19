`timescale 1ns/1ps
`default_nettype none
// HBM-B-RTL1 2026-10-17 (plan (b) d4g): LOCKSTEP of the two quadrant writers against the d4f stack writer.
//   ref = ot_hbm_sm_vm_wr_q_t_lanes (d4f smw_<stack>, 8 SMs, quad QW)
//   w   = ot_hbm_sm_vm_wr_q_t_lanes4 lbase 0, quad QW <- SMs 0-3      e = ot_hbm_sm_vm_wr_q_t_lanes4 lbase 1, quad QE <- SMs 4-7
// All three take the SAME host programme (writer descriptors as command-calendar entries through the real host ingress,
// tgt 160) and the SAME SM result streams (the schedule of tb_hbm_sm_vm_wr_q_t_lanes: SUB=4 bursts, K gaps, 5 descriptors
// incl. BF16 rounding, mirror, P 1..8; ops 1 and 3 select bank half 1 via calendar bit cmd[26], which the 26-bit d4f
// writer does not read).  Every edge, per quadrant lane k (ref lane r = k for w, 4+k for e): wq_s<k> and wq_t<k> carry
// ref.wq_s<r> bit for bit except the bank field (s: ref's bank; t: ref's bank ^ 4), the quad field of e ((mirror ? 0 :
// QE) instead of QW) and the valid bit: s.v | t.v == ref.v, never both, t.v only in the half-1 ops (count checked);
// configured equal; no fault anywhere; then an SM 5 fault pulse must reach ref and e (not w).  0 edges of latency change.  -DMUT=<n> is passed to e (1 row / 2 phase /
// 3 quad / 4 calendar late / 6 bank base) and must FAIL.
`ifndef MUT
`define MUT 0
`endif
module tb_hbm_sm_vm_wr_q_t_lanes4_lockstep;
    localparam integer QW = 0, QE = 1, NCYC = 6000;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    localparam integer LEAD = 8;
    reg [7:0] rv, smf; reg [95:0] rrow; reg [2047:0] rdata;
    wire [2247:0] wq_ref; wire [2247:0] wq_w, wq_e;
    wire f_ref, f_w, f_e, a_ref, a_w, a_e, c_ref, c_w, c_e;
    reg awv = 0, wv = 0, arv = 0, rr = 1, br = 1; reg [11:0] awa = 0, ara = 0; reg [31:0] wd = 0;
    wire awr, wr, bv, arr, rvl; wire [1:0] bresp; wire [31:0] rdat;
    wire cfg_v, desc_v, launch_v, ing_fault; wire [7:0] cfg_target; wire [11:0] cfg_addr, desc_base; wire [255:0] cfg_data;
    wire [12:0] desc_limit; wire [15:0] desc_loops;
    ot_hbm_host_static_ingress #(.TARGET_MASK(256'd1<<160)) ing(
        .clk(clk), .rst_n(rst_n), .s_awvalid(awv), .s_awready(awr), .s_awaddr(awa), .s_wvalid(wv), .s_wready(wr),
        .s_wdata(wd), .s_wstrb(4'hf), .s_bvalid(bv), .s_bready(br), .s_bresp(bresp), .s_arvalid(arv), .s_arready(arr),
        .s_araddr(ara), .s_rvalid(rvl), .s_rready(rr), .s_rdata(rdat), .block_ready(1'b1), .program_active(a_ref),
        .program_fault(1'b0), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .fault(ing_fault));
`define HOST .clk(clk), .clk_cal(clk), .rst_n(rst_n), .tgt(8'd160), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v)
`define SM(p,k,o,W) .clk_l``p(clk), .rv_s``p(rv[k]), .smf_s``p(smf[k]), .sms_s``p(1'b0), .rrow_s``p(rrow[12*k+:12]), .rdata_s``p(rdata[256*k+:256]), .wq_s``p(W[281*o+:281])
`define SMT(p,o,W) .wq_t``p(W[281*(4+o)+:281])
    ot_hbm_sm_vm_wr_q_t_lanes #(.DEPTH(4), .MUT(0)) u_ref(`HOST, .quad(2'(QW)),
        `SM(0,0,0,wq_ref), `SM(1,1,1,wq_ref), `SM(2,2,2,wq_ref), `SM(3,3,3,wq_ref),
        `SM(4,4,4,wq_ref), `SM(5,5,5,wq_ref), `SM(6,6,6,wq_ref), `SM(7,7,7,wq_ref),
        .configured(c_ref), .fault(f_ref), .active(a_ref));
    ot_hbm_sm_vm_wr_q_t_lanes4 #(.DEPTH(4), .MUT(0)) u_w(`HOST, .quad(2'(QW)), .lbase(1'b0),
        `SM(0,0,0,wq_w), `SM(1,1,1,wq_w), `SM(2,2,2,wq_w), `SM(3,3,3,wq_w), `SMT(0,0,wq_w), `SMT(1,1,wq_w), `SMT(2,2,wq_w), `SMT(3,3,wq_w), .configured(c_w), .fault(f_w), .active(a_w));
    ot_hbm_sm_vm_wr_q_t_lanes4 #(.DEPTH(4), .MUT(`MUT)) u_e(`HOST, .quad(2'(QE)), .lbase(1'b1),
        `SM(0,4,0,wq_e), `SM(1,5,1,wq_e), `SM(2,6,2,wq_e), `SM(3,7,3,wq_e), `SMT(0,0,wq_e), `SMT(1,1,wq_e), `SMT(2,2,wq_e), `SMT(3,3,wq_e), .configured(c_e), .fault(f_e), .active(a_e));
    integer axerr = 0;
    task automatic axw(input [11:0] a, input [31:0] d);
        reg ad, dd;
        begin
            ad = 0; dd = 0; @(negedge clk); awv = 1; awa = a; wv = 1; wd = d;
            while (!(ad && dd)) begin
                begin : HS reg ha, hw; ha = awv && awr; hw = wv && wr;
                @(posedge clk); #0.01; if (ha) begin ad = 1; awv = 0; end if (hw) begin dd = 1; wv = 0; end end
                @(negedge clk);
            end
            while (!bv) @(posedge clk);
            if (bresp != 0) begin $display("ERROR bresp %0d at %h data %h", bresp, a, d); axerr = axerr + 1; end
            @(posedge clk);
        end
    endtask
    task automatic hrow(input [7:0] t, input [11:0] addr, input [255:0] data);
        begin axw(12'hf20, {12'd0, addr, t}); for (integer q = 0; q < 8; q = q + 1) axw(12'hf24, data[q*32 +: 32]); end
    endtask
    task automatic hdesc(input [7:0] t, input [11:0] b_, input [12:0] lim, input [15:0] loops);
        begin axw(12'hf20, {12'd0, 12'd0, t}); axw(12'hf28, {7'd0, lim, b_}); axw(12'hf2c, {16'd0, loops}); end
    endtask
    reg [31:0] C_launch; reg launched = 0;
    always @(posedge clk) if (rst_n && launch_v && !launched) begin launched <= 1; C_launch <= u_ref.u_tgt.cycle; end
    // ---------------- schedule (the compiler; as tb_hbm_sm_vm_wr_q_t_lanes) ----------------
    reg [7:0] ev_rv [0:NCYC-1]; reg [11:0] ev_row [0:NCYC-1][0:7]; reg [255:0] ev_dat [0:NCYC-1][0:7];
    reg ev_cmd [0:NCYC-1]; reg [26:0] ev_cmdw [0:NCYC-1]; integer exp_t = 0, got_tw = 0, got_te = 0;
    integer freec [0:7];
    integer c, k, i, p, op, nrows, gap, t, st, lastemit, mism, seed, nv;
    reg [9:0] base, stride; reg [3:0] P; reg fmt, mir; reg [31:0] w;
    initial begin
        seed = 11;
        for (c = 0; c < NCYC; c = c + 1) begin ev_rv[c] = 0; ev_cmd[c] = 0; end
        for (k = 0; k < 8; k = k + 1) freec[k] = 0;
        t = 20; lastemit = 0;
        for (op = 0; op < 5; op = op + 1) begin
            case (op)
                0: begin P = 1; fmt = 0; mir = 0; base = 10'd0;   stride = 10'd0;  end
                1: begin P = 4; fmt = 1; mir = 0; base = 10'd64;  stride = 10'd8;  end
                2: begin P = 2; fmt = 0; mir = 1; base = 10'd200; stride = 10'd3;  end
                3: begin P = 8; fmt = 1; mir = 0; base = 10'd300; stride = 10'd16; end
                4: begin P = 3; fmt = 0; mir = 0; base = 10'd700; stride = 10'd40; end
            endcase
            c = lastemit + 3; if (c < t) c = t;
            ev_cmd[c] = 1; ev_cmdw[c] = {1'((op == 1) || (op == 3)), fmt, mir, P, stride, base};
            t = c + 1;
            nrows = (op == 0) ? 24 : 16;
            if (op == 1 || op == 3) exp_t = exp_t + 4 * nrows * P;
            for (k = 0; k < 8; k = k + 1) begin
                st = t + k;
                for (i = 0; i < nrows; i = i + 1) begin
                    if (i > 0 && i % 4 == 0) begin gap = 4 * P + 1 + ($urandom(seed) % 9); st = st + gap; end
                    else if (i > 0) st = st + 1;
                    ev_rv[st][k] = 1;
                    ev_row[st][k] = (i < 8) ? 12'(i) : 12'(40 + i);
                    for (p = 0; p < 8; p = p + 1) begin
                        w = $urandom(seed);
                        if (i == 3 && p == 0) w = 32'h7F80_0001;
                        if (i == 5 && p == 1) w = 32'h3F80_8000;
                        ev_dat[st][k][32*p +: 32] = w;
                    end
                    begin : srv integer s0; s0 = st + 3; if (freec[k] > s0) s0 = freec[k];
                        if (s0 + P - 1 > lastemit) lastemit = s0 + P - 1; freec[k] = s0 + P; end
                end
            end
            t = lastemit + 1;
        end
    end
    // ---------------- lockstep compare (every edge after reset) ----------------
    integer nchk = 0;
    reg [280:0] xe;
    integer kk;
    always @(negedge clk) if (rst_n) begin
        if (c_w !== c_ref || c_e !== c_ref) begin mism = mism + 1; if (mism < 10) $display("MISMATCH configured ref %b w %b e %b", c_ref, c_w, c_e); end
        for (kk = 0; kk < 4; kk = kk + 1) begin
            nchk = nchk + 4;
            chk(wq_w[281*kk +: 281], wq_w[281*(4+kk) +: 281], wq_ref[281*kk +: 281], 2'(QW), kk, 0);
            chk(wq_e[281*kk +: 281], wq_e[281*(4+kk) +: 281], wq_ref[281*(4+kk) +: 281], 2'(QE), kk, 1);
            if (wq_w[281*(4+kk)+280]) got_tw = got_tw + 1;
            if (wq_e[281*(4+kk)+280]) got_te = got_te + 1;
            if (wq_ref[281*kk+280]) nv = nv + 1;
            if (wq_ref[281*(4+kk)+280]) nv = nv + 1;
        end
    end
    task chk(input [280:0] hs, input [280:0] ht, input [280:0] r, input [1:0] qd, input integer k, input integer isE);
        reg [280:0] xs, xt;
        begin
            if (^r === 1'bx && ^hs === 1'bx) disable chk;    // before the first post-reset launch
            xs = r; if (!r[279]) xs[278:277] = qd;          // own quadrant strap (mirror rows: quad 0)
            xt = xs; xt[266] = ~xs[266];                    // half 1: bank ^ 4 (sec[2] = wq[266])
            if (hs[279:0] !== xs[279:0] || ht[279:0] !== xt[279:0] || (hs[280] | ht[280]) !== r[280] || (hs[280] & ht[280])) begin
                mism = mism + 1;
                if (mism < 10) $display("MISMATCH %s lane %0d: s %h t %h ref %h", isE ? "e" : "w", k, hs, ht, r);
            end
        end
    endtask
    integer cyc;
    initial begin
        rv = 0; smf = 0; rrow = 0; rdata = 0; mism = 0; nv = 0;
        repeat (4) @(posedge clk); rst_n = 1; repeat (5) @(posedge clk);
        begin : INST
            integer ne; ne = 0;
            for (c = 0; c < NCYC; c = c + 1) if (ev_cmd[c]) begin hrow(8'd160, 12'h800 + 12'(ne), {197'd0, ev_cmdw[c], 32'(c)}); ne = ne + 1; end
            hdesc(8'd160, 12'd0, 13'(ne), 16'd1);
            repeat (10) @(posedge clk);
            if (!c_ref || f_ref || ing_fault || axerr != 0) begin mism = mism + 1; $display("ERROR install"); end
            axw(12'hf30, 32'd1);
            while (!launched) @(posedge clk);
            @(negedge clk); while (u_ref.u_tgt.cycle != C_launch + 2 + LEAD - 1) @(negedge clk);
        end
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            @(negedge clk);
            rv = ev_rv[cyc];
            for (k = 0; k < 8; k = k + 1) begin rrow[12*k +: 12] = ev_row[cyc][k]; rdata[256*k +: 256] = ev_dat[cyc][k]; end
        end
        repeat (10) @(negedge clk);
        if (f_ref || f_w || f_e) begin mism = mism + 1; $display("FAULT ref %b w %b e %b", f_ref, f_w, f_e); end
        @(negedge clk); smf = 8'h20; @(negedge clk); smf = 0; repeat (4) @(negedge clk);
        if (!f_ref || !f_e || f_w) begin mism = mism + 1; $display("SM5 fault routing ref %b w %b e %b (want 1 0 1)", f_ref, f_w, f_e); end
        if (got_tw != exp_t || got_te != exp_t) begin mism = mism + 1; $display("half-1 emissions w %0d e %0d expected %0d", got_tw, got_te, exp_t); end
        $display("lockstep lane-edges %0d, SM-writer emissions %0d, half-1 emissions %0d/%0d", nchk, nv, got_tw, got_te);
        if (mism == 0 && nv > 1000) $display("TB_WRQ4_LOCKSTEP PASS MUT=%0d", `MUT);
        else $display("TB_WRQ4_LOCKSTEP FAIL MUT=%0d mismatches+faults=%0d", `MUT, mism);
        $finish;
    end
endmodule
`default_nettype wire
