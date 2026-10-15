`timescale 1ns/1ps
// tb_mtp_hrow_src (mtp-dsbind 2026-10-11): gate of dsfd_mtp_hrow_src, the stage-die hidden-row source.
// WFC t_hep events {v, user, pos, issue epoch} -> the source reads the HC-mean row from a VM model (ring of 8 rows; a
// read waits until the SU program has written the row, as the VM row-completion counter does; in-order responses after
// VLAT, random grant) -> dedicated lane (FWD / RET stations) -> RTT receiver -> deframer.  Checks: one lane row per
// event, in order, header {user, pos, epoch, PART} exact, 80 beats exact; no fault.
//   +CASE=pos_spaced (events at wavefront-like spacing) | pos_burst (events back to back, epochs changing)
module tb_mtp_hrow_src;
    localparam integer NW = 21, UW = 10, AW = 24, PART = 1, FWD = 9, RET = 9, VF = 6, VR = 6, VLAT = 12;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [255:0] cs;
    function [1023:0] rowdata(input integer u, input integer pos, input integer ep, input integer part, input integer b);
        integer k; reg [31:0] h;
        begin
            for (k = 0; k < 32; k = k + 1) begin
                h = ({u[3:0], pos[11:0], ep[3:0], part[1:0], b[6:0], 5'(k)} * 32'h9E3779B1) ^ 32'h85EBCA6B;
                rowdata[32*k +: 32] = h ^ (h >> 13);
            end
        end
    endfunction
    integer nev = 0, evu [0:63], evp [0:63], eve [0:63], gap [0:63];
    task ev(input integer u, input integer p, input integer e, input integer g);
        begin evu[nev] = u; evp[nev] = p; eve[nev] = e; gap[nev] = g; nev = nev + 1; end
    endtask
    integer k0;
    initial begin
        if (!$value$plusargs("CASE=%s", cs)) cs = "pos_spaced";
        if (cs == "pos_spaced") for (k0 = 0; k0 < 10; k0 = k0 + 1) ev(k0 % 2, 3 + k0 / 2, k0 / 6, 400);
        else begin
            ev(0, 3, 0, 1); ev(0, 4, 0, 1); ev(0, 5, 1, 1); ev(1, 2, 0, 1); ev(0, 6, 1, 1); ev(1, 3, 2, 1); ev(0, 7, 2, 1);
        end
    end
    // ---------------- events + VM rows (written by the 'SU' WD cycles after the stage start)
    reg [UW+NW+4:0] hep; integer ei = 0, seed = 5;
    reg [UW+NW+4-1:0] slot_tag [0:63]; integer slot_t [0:63]; integer cyc = 0;
    initial begin : drive
        integer j;
        for (j = 0; j < 64; j = j + 1) slot_t[j] = 1 << 30;
        hep = 0;
        wait (rst_n); repeat (20) @(posedge clk);
        for (ei = 0; ei < nev; ei = ei + 1) begin
            @(posedge clk);
            hep <= {1'b1, UW'(evu[ei]), NW'(evp[ei]), 4'(eve[ei])};
            slot_tag[(evu[ei] % 8) * 8 + evp[ei] % 8] = {UW'(evu[ei]), NW'(evp[ei]), 4'(eve[ei])};
            slot_t[(evu[ei] % 8) * 8 + evp[ei] % 8] = cyc + 30 + ($random(seed) & 31);
            @(posedge clk); hep <= 0;
            repeat (gap[ei]) @(posedge clk);
        end
    end
    always @(posedge clk) cyc <= cyc + 1;
    // ---------------- DUT
    wire [AW:0] t_vrq, vrq_far; wire vg_far, vg_near; wire [1024:0] f_vrs; wire [514:0] t_hp, hp_far; wire g_far, g_near;
    wire [1:0] flt;
    dsfd_mtp_hrow_src #(.NW(NW), .USER_W(UW), .PART(PART), .VM_AW(AW)) dut (.ck(clk), .rst(rst_n), .f_hep(hep),
        .t_vrq(t_vrq), .f_vrq(vg_near), .f_vrs(f_vrs), .t_hp(t_hp), .f_hpg(g_near), .t_flt(flt));
    // ---------------- VM model (RTT receiver; a read waits for its row's write)
    tb_hsrc_relay #(.W(AW + 1), .HOPS(VF)) u_vf (.clk(clk), .rst_n(rst_n), .i(t_vrq), .o(vrq_far));
    tb_hsrc_relay #(.W(1), .HOPS(VR)) u_vg (.clk(clk), .rst_n(rst_n), .i(vg_far), .o(vg_near));
    wire cv; wire [AW-1:0] ca; reg cr;
    ot_dsrom_mtp_lrx_rtt #(.W(AW), .D(VF + VR + 4), .ENABLE_RTT(1), .FORWARD_HOPS(VF), .RETURN_HOPS(VR)) u_vrx (
        .clk(clk), .rst_n(rst_n), .l_valid(vrq_far[0]), .l_ready(vg_far), .l_data(vrq_far[AW:1]),
        .c_valid(cv), .c_ready(cr), .c_data(ca));
    wire [5:0] rs = ca[12:7];
    reg rnd = 0; always @(posedge clk) rnd <= ($random(seed) & 3) != 0;
    always @(*) cr = (cv === 1'b1) && (cyc >= slot_t[ca[12:7]]) && rnd;
    reg [1024:0] vp [0:VLAT-1]; integer vk;
    initial for (vk = 0; vk < VLAT; vk = vk + 1) vp[vk] = '0;
    always @(posedge clk) begin
        vp[0] <= {rowdata(slot_tag[rs][UW+NW+3:NW+4], slot_tag[rs][NW+3:4], slot_tag[rs][3:0], PART, ca[6:0]),
                  cv && cr && rst_n};
        for (vk = 1; vk < VLAT; vk = vk + 1) vp[vk] <= vp[vk - 1];
    end
    tb_hsrc_relay #(.W(1025), .HOPS(VR)) u_vs (.clk(clk), .rst_n(rst_n), .i(vp[VLAT - 1]), .o(f_vrs));
    // ---------------- lane + receiver + deframer
    tb_hsrc_relay #(.W(515), .HOPS(FWD)) u_lf (.clk(clk), .rst_n(rst_n), .i(t_hp), .o(hp_far));
    tb_hsrc_relay #(.W(1), .HOPS(RET)) u_lg (.clk(clk), .rst_n(rst_n), .i(g_far), .o(g_near));
    wire rv; wire [513:0] rd;
    ot_dsrom_mtp_lrx_rtt #(.W(514), .D(FWD + RET + 4), .ENABLE_RTT(1), .FORWARD_HOPS(FWD), .RETURN_HOPS(RET)) u_lrx (
        .clk(clk), .rst_n(rst_n), .l_valid(hp_far[0]), .l_ready(g_far), .l_data(hp_far[514:1]),
        .c_valid(rv), .c_ready(1'b1), .c_data(rd));
    integer rows = 0, nb = 0, half = 0, errs = 0, t_last = 0; reg [511:0] lo; reg [UW+NW+5:0] hh;
    always @(posedge clk) if (rst_n && rv) begin
        t_last = cyc;
        if (rd[513]) begin
            hh = rd[UW+NW+5:0];
            if (rows >= nev || hh !== {UW'(evu[rows]), NW'(evp[rows]), 4'(eve[rows]), 2'(PART)}) begin
                if (errs < 5) $display("HSRC_ERR row %0d header %h", rows, hh); errs = errs + 1;
            end
            nb = 0; half = 0;
        end else if (!half) begin lo = rd[511:0]; half = 1; end
        else begin
            if ({rd[511:0], lo} !== rowdata(evu[rows], evp[rows], eve[rows], PART, nb)) begin
                if (errs < 5) $display("HSRC_ERR row %0d beat %0d", rows, nb); errs = errs + 1;
            end
            half = 0; nb = nb + 1;
            if (rd[512]) begin if (nb != 80) begin $display("HSRC_ERR short row"); errs = errs + 1; end rows = rows + 1; end
        end
    end
    initial begin
        repeat (8) @(posedge clk); rst_n = 1;
        wait (ei == nev);
        while (cyc - t_last < 3000 || t_last == 0) @(posedge clk);
        if (rows != nev) begin $display("HSRC_ERR rows %0d of %0d", rows, nev); errs = errs + 1; end
        if (flt !== 2'b0) begin $display("HSRC_ERR fault %b", flt); errs = errs + 1; end
        $display("HSRC_RESULT case=%0s result=%s rows=%0d fault=%b cyc=%0d", cs, errs == 0 ? "PASS" : "FAIL", rows, flt, cyc);
        $finish;
    end
endmodule

module tb_hsrc_relay #(parameter integer W = 1, parameter integer HOPS = 0) (
    input wire clk, rst_n, input wire [W-1:0] i, output wire [W-1:0] o);
    generate if (HOPS == 0) begin : g0 assign o = i; end
    else begin : gp
        reg [W-1:0] p [0:HOPS-1]; integer j;
        always @(posedge clk) begin
            if (!rst_n) for (j = 0; j < HOPS; j = j + 1) p[j] <= '0;
            else begin p[0] <= i; for (j = 1; j < HOPS; j = j + 1) p[j] <= p[j-1]; end
        end
        assign o = p[HOPS-1];
    end endgenerate
endmodule
