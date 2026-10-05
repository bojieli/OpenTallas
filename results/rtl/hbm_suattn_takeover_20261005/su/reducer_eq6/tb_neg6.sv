`timescale 1ns/1ps
// Lockstep equivalence of the 1.2 GHz reducer successor (rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv: slices + top,
// RPAD / RSL / RTAP / ROUT) against the original reducer (rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv, its modules renamed
// ot_ref_vec_red / ot_ref_vred_op / ot_ref_vsq in the bench's copy so both elaborate), on the same random item
// stream every cycle: SUM / MAX, square, liveness, every tap level, packed and spanning, TIME levels, last flags,
// result slots, rounding, bases, shifts, meta, and operands biased to the binary32 edges (zeros, subnormals,
// near-overflow, inf / NaN now and then).  The successor's outputs must equal the original's delayed by
// D = RPAD + RSL + RTAP + ROUT on every cycle: o_we, o_addr, o_data, o_meta, o_ev; both must agree on `busy` at the end (a
// random stream can leave a TIME operand held), and the successor's busy output (one register when RSL >= 1) must
// equal its combinational OR of the pipeline's registers on every cycle.  `fault` is counted (its sources are
// re-timed separately) and reported, not graded.  With ROUT = 1 the graded outputs are what the vector memory
// consumes: o_we / o_ev every cycle, o_addr / o_data of the slots being written, o_meta with an event.
// Prints REDC12 N=.. cycles=.. events=.. mismatches=.. and exits nonzero ($fatal) on any mismatch.
module tb_hdc_v41x_vec_red_c12 #(
    parameter integer N = 64, parameter integer LV = 6, parameter integer MLAT = 6, parameter integer ALAT = 6,
    parameter integer RPAD = 1, parameter integer RSL = 1, parameter integer RTAP = 1, parameter integer ROUT = 0, parameter integer SL = 64
) (input wire clk);
    localparam integer AW = 24, MW = 9, NC = N / 8, D = RPAD + RSL + RTAP + ROUT - 1;
    localparam integer OW = NC + NC * AW + NC * 32 + MW + 1;
    reg rst_n = 1'b0;
    integer cyc = 0, ncyc = 20000, mism = 0, ev = 0, fr = 0, fd = 0, i;
    reg v_in = 1'b0, mx_in = 1'b0, sq_in = 1'b0, span_in = 1'b0, last_in = 1'b0, rnd_in = 1'b0;
    reg [N*32-1:0] x_in = 0;
    reg [N-1:0] live_in = 0;
    reg [3:0] lt_in = 0;
    reg [2:0] l_in = 0;
    reg [7:0] nres_in = 0;
    reg [AW-1:0] rbase_in = 0;
    reg [4:0] rsh_in = 0;
    reg [MW-1:0] meta_in = 0;
    function automatic [31:0] rw(input [31:0] r0, input [31:0] r1);
        reg [7:0] e;
        begin
            case (r1[3:0])
                4'd0: e = 8'd0;
                4'd1: e = 8'd255;
                4'd2: e = 8'd254 - r1[6:4];
                4'd3: e = 8'd1 + r1[6:4];
                default: e = 8'd120 + r1[8:4] % 8'd16;
            endcase
            rw = {r0[31], e, (r1[3:0] == 4'd1 && r1[9]) ? 23'd0 : r0[22:0]};
        end
    endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        if (cyc > 40 && cyc < ncyc - 600) begin
            v_in <= ($random & 7) < 5;
            mx_in <= ($random & 3) == 0;
            sq_in <= ($random & 1);
            span_in <= ($random & 1);
            last_in <= ($random & 1);
            rnd_in <= ($random & 1);
            lt_in <= $unsigned($random) % 9;
            l_in <= $random;
            nres_in <= $random;
            rbase_in <= $random;
            rsh_in <= $random;
            meta_in <= $random;
            for (i = 0; i < N; i = i + 1) begin
                x_in[32*i +: 32] <= rw($random, $random);
                live_in[i] <= ($random & 7) != 0;
            end
        end else v_in <= 1'b0;
    end
    wire [NC-1:0] r_we, d_we;
    wire [NC*AW-1:0] r_addr, d_addr;
    wire [NC*32-1:0] r_data, d_data;
    wire [MW-1:0] r_meta, d_meta;
    wire r_ev, d_ev, r_busy, d_busy, r_f, d_f;
    ot_ref_vec_red #(.N(N), .LV(LV), .AW(AW), .MW(MW), .MLAT(MLAT), .ALAT(ALAT)) u_ref (.clk(clk), .rst_n(rst_n),
        .v_in(v_in), .x_in(x_in), .live_in(live_in), .mx_in(mx_in), .sq_in(sq_in), .lt_in(lt_in), .span_in(span_in),
        .l_in(l_in), .last_in(last_in), .nres_in(nres_in), .rnd_in(rnd_in), .rbase_in(rbase_in), .rsh_in(rsh_in),
        .meta_in(meta_in), .o_we(r_we), .o_addr(r_addr), .o_data(r_data), .o_meta(r_meta), .o_ev(r_ev),
        .busy(r_busy), .fault(r_f));
    ot_hdc_v41x_vec_red #(.N(N), .LV(LV), .AW(AW), .MW(MW), .MLAT(MLAT), .ALAT(ALAT), .RPAD(RPAD), .RSL(RSL),
                          .RTAP(RTAP), .ROUT(ROUT), .SL(SL)) u_dut (.clk(clk), .rst_n(rst_n),
        .v_in(v_in), .x_in(x_in), .live_in(live_in), .mx_in(mx_in), .sq_in(sq_in), .lt_in(lt_in), .span_in(span_in),
        .l_in(l_in), .last_in(last_in), .nres_in(nres_in), .rnd_in(rnd_in), .rbase_in(rbase_in), .rsh_in(rsh_in),
        .meta_in(meta_in), .o_we(d_we), .o_addr(d_addr), .o_data(d_data), .o_meta(d_meta), .o_ev(d_ev),
        .busy(d_busy), .fault(d_f));
    wire [OW-1:0] r_o = {r_we, r_addr, r_data, r_meta, r_ev}, d_o = {d_we, d_addr, d_data, d_meta, d_ev};
    wire [OW-1:0] r_od;
    // ROUT = 1: the contract the vector memory sees -- o_we and o_ev every cycle, a slot's address / data when it is
    // written, o_meta with an event
    function automatic written_eq(input [OW-1:0] a, input [OW-1:0] b);
        integer q;
        reg ok;
        begin
            ok = (a[OW-1 -: NC] == b[OW-1 -: NC]) && (a[0] == b[0]) && (!a[0] || a[MW:1] == b[MW:1]);
            for (q = 0; q < NC; q = q + 1)
                if (a[OW-1-(NC-1-q)]) begin
                    ok = ok && (a[1 + MW + NC*32 + q*AW +: AW] == b[1 + MW + NC*32 + q*AW +: AW])
                            && (a[1 + MW + q*32 +: 32] == b[1 + MW + q*32 +: 32]);
                end
            written_eq = ok;
        end
    endfunction
    ot_hdc_delay #(.W(OW), .D(D)) u_rd (.clk(clk), .rst_n(rst_n), .d(r_o), .q(r_od));
    always @(posedge clk) if (rst_n && cyc > 30 + D) begin
        if (u_dut.u_t.busy_c != d_busy) begin
            mism = mism + 1;
            if (mism <= 5) $display("BUSY MISMATCH cyc=%0d comb=%0d out=%0d", cyc, u_dut.u_t.busy_c, d_busy);
        end
        if (ROUT == 0 ? (r_od != d_o) : !written_eq(r_od, d_o)) begin
            mism = mism + 1;
            if (mism <= 5) $display("MISMATCH cyc=%0d ev ref=%0d dut=%0d we ref=%h dut=%h", cyc, r_od[0], d_ev,
                                    r_od[OW-1 -: NC], d_we);
        end
        if (d_ev) ev = ev + 1;
        if (r_f) fr = fr + 1;
        if (d_f) fd = fd + 1;
        if (cyc == ncyc) begin
            $display("REDC12 N=%0d SL=%0d MLAT=%0d ALAT=%0d RPAD=%0d RSL=%0d RTAP=%0d ROUT=%0d cycles=%0d events=%0d mismatches=%0d fault_cycles ref=%0d dut=%0d busy_end ref=%0d dut=%0d",
                     N, SL, MLAT, ALAT, RPAD, RSL, RTAP, ROUT, ncyc, ev, mism, fr, fd, r_busy, d_busy);
            if (mism != 0 || ev == 0 || r_busy != d_busy) $fatal(1, "REDC12 FAIL");
            $finish;
        end
    end
    initial if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 20000;
endmodule
