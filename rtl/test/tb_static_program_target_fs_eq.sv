`timescale 1ns/1ps
// HBM-HCROOT6 2026-10-20: ot_static_program_target_fs == ot_static_program_target (TGT_PIN 1, PCW 10) edge for edge.
// Random F20 traffic (programme-row writes with good / bad headers, descriptors over resident / partly missing / reused
// ranges, launches, program_active, mid-run resets); every output compared on every edge (program_cfg_data only on
// program_cfg_we edges: the fs target loads it every edge, see its header).  +N=<edges> +SEED=<n>.  -DMUT=1 drops one
// bank's write (the fs bank 5 sees wsel 0) -> must FAIL.  Prints SPT_EQ PASS edges=<n> writes=<w> scans=<s> ... / FAIL.
`ifndef MUT
`define MUT 0
`endif
module tb_static_program_target_fs_eq;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0, cfg_v = 0, desc_v = 0, launch_v = 0, pa = 0;
    reg [7:0] cfg_target = 0; reg [11:0] cfg_addr = 0, desc_base = 0; reg [255:0] cfg_data = 0;
    reg [12:0] desc_limit = 0; reg [15:0] desc_loops = 0;
    wire [7:0] tgt = 8'd164;
    wire rwe, fwe, rsv, fsv, rcf, fcf, rft, fft; wire [9:0] ra, fa, rb, fb; wire [10:0] rl, fl; wire [15:0] rlo, flo;
    wire [255:0] rd, fd;
    ot_static_program_target #(.PCW(10), .TGT_PIN(1)) u_r (.clk(clk), .rst_n(rst_n), .clk_cap(1'b0), .tgt(tgt),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v),
        .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(pa),
        .program_cfg_we(rwe), .program_cfg_addr(ra), .program_cfg_data(rd), .program_start_v(rsv), .program_start_base(rb),
        .program_start_limit(rl), .program_start_loops(rlo), .configured(rcf), .fault(rft));
    ot_static_program_target_fs #(.PCW(10), .TGT_PIN(1)) u_f (.clk(clk), .rst_n(rst_n), .clk_cap(1'b0), .tgt(tgt),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v),
        .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(pa),
        .program_cfg_we(fwe), .program_cfg_addr(fa), .program_cfg_data(fd), .program_start_v(fsv), .program_start_base(fb),
        .program_start_limit(fl), .program_start_loops(flo), .configured(fcf), .fault(fft));
    if (`MUT == 1) begin : g_mut
        initial force u_f.g_bank[5].u_b.wsel = 1'b0;
    end
    reg scanning_q = 0, fault_q = 0;   // edge detectors on the reference (statistics only)
    always @(posedge clk) begin scanning_q <= u_r.scanning; fault_q <= u_r.fault; end
    integer N, cyc = 0, errs = 0, nw = 0, ns = 0, nl = 0, nf = 0, ncf = 0, nrst = 0; reg [31:0] lf;
    function [31:0] nx(input [31:0] x); reg [31:0] v; begin v = x ^ (x << 13); v = v ^ (v >> 17); nx = v ^ (v << 5); end endfunction
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 200000;
        if (!$value$plusargs("SEED=%d", lf)) lf = 7;
        lf = lf ^ 32'h9e3779b9; if (lf == 0) lf = 1;
    end
    reg [11:0] a; reg [31:0] r; integer ph = 0, wt = 0, eb = 0, el = 1, skip = -1, k = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        // compare (outputs of the previous edge)
        if (cyc > 2) begin
            if ({rwe, rsv, rcf, rft} !== {fwe, fsv, fcf, fft} || (rwe && (ra !== fa || rd !== fd)) ||
                (rsv && (rb !== fb || rl !== fl || rlo !== flo))) begin
                errs = errs + 1;
                if (errs < 8) $display("ERR edge %0d ref we%b sv%b cf%b f%b a%h  fs we%b sv%b cf%b f%b a%h", cyc,
                    rwe, rsv, rcf, rft, ra, fwe, fsv, fcf, fft, fa);
            end
            nw = nw + rwe; nl = nl + rsv; ncf = ncf + rcf;
            if (u_r.scanning && !scanning_q) ns = ns + 1;
        end
        // stimulus (applied after the edge): episodes = reset, clean install of rows [eb, eb + el) (sometimes one row
        // skipped -> scan fault), descriptor, idle through the scan, launch, sometimes a descriptor-only reuse + launch,
        // then a random-traffic tail (bad headers, foreign targets, collisions, program_active) of up to 255 edges.
        lf = nx(lf); r = lf;
        cfg_v <= 0; desc_v <= 0; launch_v <= 0; cfg_target <= 8'd164;
        case (ph)
            0: begin rst_n <= 0; nrst = nrst + 1; pa <= 0; ph = 1; wt = 2; end
            1: begin rst_n <= 1; wt = wt - 1; if (wt == 0) begin
                   lf = nx(lf); eb = (lf[1:0] == 0) ? lf[13:4] : 10'(lf[13:4] & 10'h3f0);
                   el = 1 + lf[21:16]; if (eb + el > 1024) el = 1024 - eb;
                   skip = (lf[25:22] == 0) ? lf[29:26] % el : -1; k = 0; ph = 2; end end
            2: begin
                   if (k != skip) begin
                       cfg_v <= 1; cfg_addr <= 12'(eb + k); cfg_data <= {16'hc7a1, 16'(eb + k), {7{lf}}};
                   end
                   k = k + 1; if (k == el) begin ph = 3; wt = 3; end
               end
            3: begin wt = wt - 1; if (wt == 0) begin
                   desc_v <= 1; desc_base <= 12'(eb); desc_limit <= 13'(eb + el); desc_loops <= 16'(1 + r[3:0]);
                   ph = 4; wt = el + 4; end end
            4: begin wt = wt - 1; if (wt == 0) begin launch_v <= 1; ph = r[0] ? 5 : 6; wt = 3; end end
            5: begin wt = wt - 1; if (wt == 0) begin   // descriptor-only reuse of the resident range, then launch
                   desc_v <= 1; ph = 4; wt = 4; end end
            6: begin
                   if (r[7:4] == 0) pa <= ~pa;
                   lf = nx(lf); a = (lf[3:0] == 0) ? lf[15:4] : (lf[3:0] < 3) ? {2'b0, lf[13:4]} : 12'(eb + lf[9:4] % el);
                   cfg_target <= (r[2:0] == 0) ? 8'(lf[23:16]) : (r[2:0] == 1) ? 8'd165 : 8'd164;
                   case (r[11:8])
                       0, 1, 2, 3: begin
                           cfg_v <= 1; cfg_addr <= a;
                           cfg_data <= {(r[15:12] == 0) ? 16'h1234 : 16'hc7a1, (r[19:16] == 0) ? 16'(a + 1) : {4'b0, a},
                                        {7{lf}}};
                       end
                       4, 5: begin
                           desc_v <= 1; lf = nx(lf);
                           desc_base <= (lf[2:0] == 0) ? 12'(lf[15:4]) : 12'(eb);
                           desc_limit <= (lf[2:0] == 1) ? 13'(lf[28:16]) : 13'(eb + el);
                           desc_loops <= (lf[22:20] == 0) ? 16'd0 : 16'(lf[31:23]);
                       end
                       6, 7: launch_v <= 1;
                       8: begin cfg_v <= 1; desc_v <= 1; cfg_addr <= a; end
                       default: ;
                   endcase
                   if (r[31:24] == 0) ph = 0;
               end
            default: ph = 0;
        endcase
        nf = nf + (rft && !fault_q);
        if (cyc == N) begin
            if (errs == 0 && nw > 1000 && ns > 100 && nl > 100) $display("SPT_EQ PASS edges=%0d writes=%0d scans=%0d launches=%0d configured_edges=%0d resets=%0d faults=%0d", N, nw, ns, nl, ncf, nrst, nf);
            else $display("SPT_EQ FAIL errs=%0d writes=%0d scans=%0d launches=%0d", errs, nw, ns, nl);
            $finish;
        end
    end
endmodule
