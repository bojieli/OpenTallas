`timescale 1ps/1ps
// ---------------------------------------------------------------------------
// tb_gpu_coll: bench of the collective path, R = 2 dies:
//   2 x ot_gpu_coll_endpoint #(ENABLE 1) + ot_gpu_coll_fabric #(ENABLE 1)
//   (rtl/link/ot_link_nvls_switch.sv inside).
// Clocks: each die its own clk_sm (833 ps, phase-offset per die), one clk_link
// (900 ps) for the links and the switch.  Every reset releases at a different
// time (per die sm, per die link side, switch).
//
// Stimulus from +stim=<hexfile> (tools/gpu_sys/run_coll.py):
//   word 0 = NT; per collective t: {flags[15:0], mode[7:0], count[7:0]},
//   reserved, then R x NL lane words (rank-major).  flags bit 0 = measure: both
//   ranks idle MEAS_GAP cycles first and the response is always ready.
// Each rank's driver issues the collectives back to back in program order
// (random 0..5-cycle gaps, often 0); responses take random backpressure.
// Every response is written to +out=<file> as
//   RSP <rank> <t> <latency> <hex NL*32>   (latency: clk_sm cycles from the
//   request handshake to the first cycle coll_rsp_v is high)
// and checked by run_coll.py (bit exact vs numpy, placement, rank agreement).
// The bench itself checks: faults stay 0, ENABLE = 0 instances keep every
// output 0, no hang.
// ---------------------------------------------------------------------------
module tb_gpu_coll;
    localparam integer R = 2, NL = 128, LANES = 16, PW = 32 * LANES + 2 + 32;
    localparam integer MAXW = 1 << 17;
    localparam integer MEAS_GAP = 400;
    parameter integer SW_PIPE = 4;
    parameter integer LINK_PIPE = 2;

    reg [31:0] stim [0:MAXW-1];
    integer NT, fd;
    string  sfile, ofile;
    initial begin
        if (!$value$plusargs("stim=%s", sfile)) sfile = "coll_stim.hex";
        if (!$value$plusargs("out=%s", ofile)) ofile = "coll_out.txt";
        $readmemh(sfile, stim);
        NT = stim[0];
        fd = $fopen(ofile, "w");
        $display("TB_GPU_COLL cfg R=%0d NL=%0d NT=%0d SW_PIPE=%0d LINK_PIPE=%0d", R, NL, NT, SW_PIPE, LINK_PIPE);
    end
    function automatic integer base(input integer t);
        base = 1 + t * (2 + R * NL);
    endfunction

    // ---- clocks and resets ----
    reg [R-1:0] clk_sm = 0;
    reg clk_link = 0;
    always begin #450 clk_link = 1; #450 clk_link = 0; end
    initial begin #137; forever begin #416 clk_sm[0] = 1; #417 clk_sm[0] = 0; end end
    initial begin #391; forever begin #416 clk_sm[1] = 1; #417 clk_sm[1] = 0; end end
    reg [R-1:0] rst_sm_n = 0, rst_lk_n = 0;
    reg rst_sw_n = 0;
    initial begin
        #9000  rst_sw_n = 1;
        #1300  rst_lk_n[1] = 1;
        #2100  rst_sm_n[0] = 1;
        #700   rst_lk_n[0] = 1;
        #3300  rst_sm_n[1] = 1;
    end

    // ---- DUT ----
    wire [R-1:0]      req_rdy, rsp_v, flt, up_v, dn_v;
    reg  [R-1:0]      req_v = 0, rsp_rdy = 0, req_mode = 0;
    reg  [7:0]        req_cnt [0:R-1];
    reg  [NL*32-1:0]  req_d [0:R-1];
    wire [NL*32-1:0]  rsp_d [0:R-1];
    wire [R*PW-1:0]   up_rec, dn_rec;
    wire              sw_fault;
    genvar g;
    for (g = 0; g < R; g = g + 1) begin : g_die
        ot_gpu_coll_endpoint #(.ENABLE(1), .NL(NL), .LANES(LANES), .R(R), .RANK(g)) u_ep (
            .clk_sm(clk_sm[g]), .rst_sm_n(rst_sm_n[g]), .coll_req_v(req_v[g]), .coll_req_rdy(req_rdy[g]),
            .coll_mode(req_mode[g]), .coll_count(req_cnt[g]), .coll_data(req_d[g]), .coll_rsp_v(rsp_v[g]),
            .coll_rsp_rdy(rsp_rdy[g]), .coll_rsp_data(rsp_d[g]), .coll_fault(flt[g]),
            .clk_link(clk_link), .rst_link_n(rst_lk_n[g]), .lk_tx_v(up_v[g]), .lk_tx_rec(up_rec[g*PW +: PW]),
            .lk_rx_v(dn_v[g]), .lk_rx_rec(dn_rec[g*PW +: PW]));
    end
    ot_gpu_coll_fabric #(.ENABLE(1), .R(R), .NL(NL), .LANES(LANES), .SW_PIPE(SW_PIPE), .LINK_PIPE(LINK_PIPE)) u_fab (
        .clk_link(clk_link), .rst_link_n(rst_sw_n), .up_v(up_v), .up_rec(up_rec), .dn_v(dn_v), .dn_rec(dn_rec),
        .fault(sw_fault));

    // ---- ENABLE = 0 instances on the same (toggling) inputs ----
    wire          z_rdy, z_rv, z_f, z_tv, z_fv, z_ff;
    wire [NL*32-1:0] z_rd;
    wire [PW-1:0] z_tr;
    wire [R-1:0]  z_dv;
    wire [R*PW-1:0] z_dr;
    ot_gpu_coll_endpoint #(.ENABLE(0), .NL(NL), .LANES(LANES), .R(R), .RANK(0)) u_ep_off (
        .clk_sm(clk_sm[0]), .rst_sm_n(rst_sm_n[0]), .coll_req_v(req_v[0]), .coll_req_rdy(z_rdy),
        .coll_mode(req_mode[0]), .coll_count(req_cnt[0]), .coll_data(req_d[0]), .coll_rsp_v(z_rv),
        .coll_rsp_rdy(rsp_rdy[0]), .coll_rsp_data(z_rd), .coll_fault(z_f),
        .clk_link(clk_link), .rst_link_n(rst_lk_n[0]), .lk_tx_v(z_tv), .lk_tx_rec(z_tr),
        .lk_rx_v(dn_v[0]), .lk_rx_rec(dn_rec[0 +: PW]));
    ot_gpu_coll_fabric #(.ENABLE(0), .R(R), .NL(NL), .LANES(LANES)) u_fab_off (
        .clk_link(clk_link), .rst_link_n(rst_sw_n), .up_v(up_v), .up_rec(up_rec), .dn_v(z_dv), .dn_rec(z_dr),
        .fault(z_ff));
    assign z_fv = 1'b0;
    integer en0_bad = 0;
    always @(posedge clk_link)
        if (z_rdy || z_rv || z_f || z_tv || z_ff || (|z_rd) || (|z_tr) || (|z_dv) || (|z_dr)) en0_bad = en0_bad + 1;

    // ---- per-rank driver and response monitor ----
    integer rt [0:R-1];
    integer it [0:R-1];
    integer fault_cycles = 0;
    integer bp_rsp = 0, bp_req = 0;      // cycles a response was held by backpressure / a request held while busy
    always @(posedge clk_link) if ((|flt) || sw_fault) fault_cycles = fault_cycles + 1;
    for (g = 0; g < R; g = g + 1) begin : g_drv
        integer cyc = 0, gap = 0, t = 0, r = 0, l;
        integer acc [0:4095];
        integer first_v = -1;
        reg busy = 0;
        reg [31:0] hdr;
        always @(posedge clk_sm[g]) begin
            if (rst_sm_n[g]) cyc <= cyc + 1;
            // driver
            if (rst_sm_n[g] && NT > 0) begin
                if (req_v[g]) begin
                    if (req_rdy[g]) begin
                        acc[t] = cyc;
                        req_v[g] <= 1'b0;
                        t = t + 1;
                        if (t < NT) begin
                            hdr = stim[base(t)];
                            gap = hdr[16] ? MEAS_GAP : (($urandom % 3 == 0) ? ($urandom % 6) : 0);
                        end
                    end
                end else if (t < NT) begin
                    if (gap > 0) gap = gap - 1;
                    else begin
                        hdr = stim[base(t)];
                        req_v[g] <= 1'b1;
                        req_mode[g] <= hdr[8];
                        req_cnt[g] <= hdr[7:0];
                        for (l = 0; l < NL; l = l + 1) req_d[g][32*l +: 32] <= stim[base(t) + 2 + g * NL + l];
                    end
                end
            end
            if (rsp_v[g] && !rsp_rdy[g]) bp_rsp = bp_rsp + 1;
            if (req_v[g] && !req_rdy[g]) bp_req = bp_req + 1;
            // response monitor
            if (rst_sm_n[g] && r < NT) begin
                if (rsp_v[g] && first_v < 0) first_v = cyc;
                if (rsp_v[g] && rsp_rdy[g]) begin
                    $fwrite(fd, "RSP %0d %0d %0d %h\n", g, r, first_v - acc[r], rsp_d[g]);
                    r = r + 1;
                    first_v = -1;
                end
                hdr = stim[base((r < NT) ? r : NT - 1)];
                rsp_rdy[g] <= hdr[16] ? 1'b1 : (($urandom % 10) < 6);
            end
            rt[g] = r;
            it[g] = t;
        end
    end
    // The driver raises the next request while the previous response may still be held; the endpoint
    // keeps coll_req_rdy low until it is taken (one outstanding per rank).

    // ---- end / watchdog ----
    integer idle = 0, last_prog = 0;
    always @(posedge clk_link) begin
        if (rt[0] + rt[1] != last_prog) begin last_prog = rt[0] + rt[1]; idle = 0; end
        else idle = idle + 1;
        if (NT > 0 && rt[0] == NT && rt[1] == NT) begin
            $fwrite(fd, "DONE faults=%0d en0_bad=%0d rsp_held=%0d req_held=%0d\n", fault_cycles, en0_bad, bp_rsp, bp_req);
            $fclose(fd);
            $display("TB_GPU_COLL DONE NT=%0d fault_cycles=%0d en0_bad=%0d sw_fault=%0d flt=%b", NT, fault_cycles,
                     en0_bad, sw_fault, flt);
            $finish;
        end
        if (idle > 200000) begin
            $fwrite(fd, "TIMEOUT r0=%0d r1=%0d i0=%0d i1=%0d\n", rt[0], rt[1], it[0], it[1]);
            $fclose(fd);
            $display("TB_GPU_COLL TIMEOUT r0=%0d r1=%0d i0=%0d i1=%0d flt=%b sw_fault=%0d", rt[0], rt[1], it[0], it[1],
                     flt, sw_fault);
            $finish;
        end
    end
endmodule
