// S81-P8 10-23: tb_cfifo_crs4 driving dsfd_cfifo_crs4p (compile with -DKP=<K>; +K must equal KP). 12/12 runs identical to crs4.
`timescale 1ps/1ps
`default_nettype none
// S81-LAND2 cfifo successor bench: dsfd_cfifo_crs4 (per-lane landings, reset read epoch) against the CLOSED
// dsfd_cfifo_crs (the reference: zero-skew lanes, marker epoch) on the same source stream.
//   source   : one word per source edge s, x(s) = {xw[1100:565], xw[0], mk, xw[564:0], mk} (the ot_s81sl_slice x-chain
//              encoding), xw seeded per edge, mk = the source's released reset (0 before source edge MK, 1 after);
//              words before mk carry random data too (the successor must treat them as bubbles).
//   reference: dsfd_cfifo_crs, xf = xf2 = cr = cr_s = the source clock, xd / xd2 launched 20 ps after each edge.
//   DUT      : dsfd_cfifo_crs4, lane k = x[276k +: 276] and its forwarded clock xk[k] both delayed DLk ps (source-
//              synchronous lane), xk[k] gated at hop 0 by an ICG opened at source edge G (+SLIPk), K = lk strap.
// Output: OT_CRS4 off=<data offset> dmism=<xa/xb/cc/x2 mismatches at off> rmism=<rd mismatches at 0> chk=<words>
//         fault=<crs4 rd fault bit seen> nz=<non-bubble words compared>
module tb_cfifo_crs4;
    localparam integer T = 834;
    integer DL0, DL1, DL2, DL3, K, G, MK, SLIP0, SLIP3, CYC, SEED;
    reg cks = 1'b0;
    initial begin
        if (!$value$plusargs("DL0=%d", DL0)) DL0 = 0;
        if (!$value$plusargs("DL1=%d", DL1)) DL1 = 0;
        if (!$value$plusargs("DL2=%d", DL2)) DL2 = 0;
        if (!$value$plusargs("DL3=%d", DL3)) DL3 = 0;
        if (!$value$plusargs("K=%d", K)) K = 3;
        if (!$value$plusargs("G=%d", G)) G = 4;
        if (!$value$plusargs("MK=%d", MK)) MK = 8;
        if (!$value$plusargs("SLIP0=%d", SLIP0)) SLIP0 = 0;
        if (!$value$plusargs("SLIP3=%d", SLIP3)) SLIP3 = 0;
        if (!$value$plusargs("CYC=%d", CYC)) CYC = 200;
        if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
    end
    always #(T / 2) cks = ~cks;
    // ---------------------------------------------------------------- reset: raw rst released after source edge -1
    reg rst = 1'b0;
    integer n = -4;                                      // source edge index (0 = first edge after the release)
    always @(posedge cks) begin n = n + 1; if (n == -1) rst <= #10 1'b1; end
    function [1100:0] fw(input integer s);
        integer j; reg [31:0] h;
        begin h = s * 32'h9E3779B1 + SEED * 32'h68E31DA4 + 32'h7F4A7C15;
              for (j = 0; j < 1101; j = j + 1) begin fw[j] = h[j % 32] ^ (j[0] & s[0]); if (j % 32 == 31) h = h * 32'h85EBCA6B + 1; end end
    endfunction
    reg [1103:0] xs = 1104'd0;                           // source launch register
    always @(posedge cks) begin : src
        reg [1100:0] w; reg mk;
        w = fw(n); mk = (n >= MK);
        xs <= #20 {w[1100:565], w[0], mk, w[564:0], mk};
    end
    // ---------------------------------------------------------------- reference (closed dsfd_cfifo_crs)
    wire [14:0] cc_r; wire [69:0] rd_r; wire rs_r; wire [282:0] xa_r; wire [265:0] xb_r; wire [535:0] x2_r;
    reg [65:0] ri = 66'd0; reg [1:0] st = 2'd0;
    always @(posedge cks) begin : rig reg [1100:0] t; t = fw(n + 7); ri <= #20 t[65:0]; st <= #20 2'd0; end
    dsfd_cfifo_crs u_ref (.cc(cc_r), .cr(cks), .cr_s(cks), .rd(rd_r), .ri(ri), .rs(rs_r), .rst(rst), .st(st), .xa(xa_r),
                          .xb(xb_r), .xd(xs[565:0]), .xf(cks), .x2(x2_r), .xd2(xs[1103:566]), .xf2(cks));
    // ---------------------------------------------------------------- DUT lanes: ICG at hop 0 + source-synchronous delay
    // ICG: enable latched in the low phase after source edge n; the first gated (forwarded) edge is source edge G (+SLIP)
    reg [3:0] en_l = 4'd0;
    always @(negedge cks) begin
        en_l[0] <= (n >= G + SLIP0 - 1); en_l[1] <= (n >= G - 1); en_l[2] <= (n >= G - 1); en_l[3] <= (n >= G + SLIP3 - 1);
    end
    wire [3:0] fck0 = {4{cks}} & en_l;
    reg [3:0] xk = 4'd0; reg [1103:0] xl = 1104'd0;
    always @(fck0[0]) xk[0] <= #(DL0) fck0[0];
    always @(fck0[1]) xk[1] <= #(DL1) fck0[1];
    always @(fck0[2]) xk[2] <= #(DL2) fck0[2];
    always @(fck0[3]) xk[3] <= #(DL3) fck0[3];
    wire [275:0] s0 = xs[275:0], s1 = xs[551:276], s2 = xs[827:552], s3 = xs[1103:828];
    always @(s0) xl[275:0]    <= #(DL0) s0;
    always @(s1) xl[551:276]  <= #(DL1) s1;
    always @(s2) xl[827:552]  <= #(DL2) s2;
    always @(s3) xl[1103:828] <= #(DL3) s3;
    wire [14:0] cc_d; wire [69:0] rd_d; wire rs_d; wire [282:0] xa_d; wire [265:0] xb_d; wire [535:0] x2_d;
    wire [11:0] lk = {4{K[2:0]}};
    dsfd_cfifo_crs4p #(.LK({4{3'd`KP}})) u_dut (.cc(cc_d), .cr(cks), .cr_s(cks), .rd(rd_d), .ri(ri), .rs(rs_d), .rst(rst), .st(st), .xa(xa_d),
                           .xb(xb_d), .x2(x2_d), .xl0(xl[275:0]), .xl1(xl[551:276]), .xl2(xl[827:552]), .xl3(xl[1103:828]),
                           .xk(xk));
    // ---------------------------------------------------------------- recorder + checker
    reg [1099:0] hr [0:1023], hd [0:1023];
    reg [69:0] rr_ [0:1023], rdd [0:1023];
    integer nh = 0, q, off, best, dm, rm, chk, nz, flt;
    always @(negedge cks) if (n >= 0 && nh < 1024) begin
        hr[nh] = {xa_r, xb_r, cc_r, x2_r}; hd[nh] = {xa_d, xb_d, cc_d, x2_d}; rr_[nh] = rd_r; rdd[nh] = rd_d; nh = nh + 1;
    end
    initial begin
        #(T * 4);
        #(T * CYC);
        best = -99;
        for (off = -8; off <= 24 && best == -99; off = off + 1) begin
            dm = 0;
            for (q = 40; q < nh - 30; q = q + 1) if (hd[q + off] !== hr[q]) dm = dm + 1;
            if (dm == 0) best = off;
        end
        if (best == -99) best = 0;
        dm = 0; rm = 0; chk = 0; nz = 0; flt = 0;
        for (q = 0; q < nh - 30; q = q + 1) begin
            if (rdd[q] !== rr_[q]) rm = rm + 1;
            if (rdd[q][69] === 1'b1) flt = 1;
            // data: from the reference's warm-up end (it drops the first words after the marker edge; the successor
            // delivers them as well -- the compiler never schedules a word there)
            if (q >= MK + 12 && q + best >= 0) begin
                chk = chk + 1; if (hr[q] != 0) nz = nz + 1;
                if (hd[q + best] !== hr[q]) begin dm = dm + 1; if (dm < 4) $display("OT_MISM q=%0d", q); end
            end
        end
        // before the marker reaches the output every successor word must be a bubble (zero), as the reference's
        for (q = 0; q < MK + best && q < nh; q = q + 1) if (q >= 0 && hd[q] !== 0) dm = dm + 1;
        $display("OT_CRS4 dl=%0d,%0d,%0d,%0d k=%0d g=%0d mk=%0d slip=%0d,%0d off=%0d dmism=%0d rmism=%0d chk=%0d nz=%0d fault=%0d",
                 DL0, DL1, DL2, DL3, K, G, MK, SLIP0, SLIP3, best, dm, rm, chk, nz, flt | u_dut.lf != 0);
        $finish;
    end
endmodule
`default_nettype wire
