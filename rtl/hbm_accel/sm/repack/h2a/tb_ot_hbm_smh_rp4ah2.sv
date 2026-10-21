`timescale 1ns/1ps
// L2H-SMATT/RP4A (from the L2H-SM9 rp4h2 tb): lockstep ot_hbm_smh_rp4a_flat (attention leaf, flat, reset delayed 3) vs ot_hbm_smh_rp4ah2 (two hardened attention halves, same lp offsets); static attn strap ATTN held from cycle 0; every input presented off_in edges later, every output compared off_out edges later.
module tb_ot_hbm_smh_rp4ah2;
    parameter integer MUT = 0;
    parameter integer SOFTBEAT = 1;
    parameter integer GN = 2;             // n gather relays (kit default)
    parameter integer GS = 1;             // s gather relays (kit default)
    parameter integer XB = 1;             // n beat-crossing relays (kit default)
    parameter integer ATTN = 5'b01_101;   // attn_rowbase 1, attn_column 5
    wire [4:0] attn = ATTN;
    reg clk = 1'b0;  always #0.5 clk = ~clk;
    reg rst = 0;  reg [2:0] rst_dl;
    wire rst_f = rst_dl[2];
    always @(posedge clk) rst_dl <= {rst_dl[1:0], rst};
    reg [8:0] fi_xs_a1;
    reg [8:0] dli_xs_a1 [0:0];  wire [8:0] li_xs_a1 = fi_xs_a1;
    always @(posedge clk) begin : g_dli_xs_a1 integer j; dli_xs_a1[0] <= fi_xs_a1; for (j = 1; j <= 0; j = j + 1) dli_xs_a1[j] <= dli_xs_a1[j - 1]; end
    reg [4:0] fi_xs_g1;
    reg [4:0] dli_xs_g1 [0:0];  wire [4:0] li_xs_g1 = fi_xs_g1;
    always @(posedge clk) begin : g_dli_xs_g1 integer j; dli_xs_g1[0] <= fi_xs_g1; for (j = 1; j <= 0; j = j + 1) dli_xs_g1[j] <= dli_xs_g1[j - 1]; end
    reg [6:0] fi_xs_a2;
    reg [6:0] dli_xs_a2 [0:0];  wire [6:0] li_xs_a2 = fi_xs_a2;
    always @(posedge clk) begin : g_dli_xs_a2 integer j; dli_xs_a2[0] <= fi_xs_a2; for (j = 1; j <= 0; j = j + 1) dli_xs_a2[j] <= dli_xs_a2[j - 1]; end
    reg [4:0] fi_xs_g2;
    reg [4:0] dli_xs_g2 [0:0];  wire [4:0] li_xs_g2 = fi_xs_g2;
    always @(posedge clk) begin : g_dli_xs_g2 integer j; dli_xs_g2[0] <= fi_xs_g2; for (j = 1; j <= 0; j = j + 1) dli_xs_g2[j] <= dli_xs_g2[j - 1]; end
    reg [8:0] fi_xss_a1;
    reg [8:0] dli_xss_a1 [0:0];  wire [8:0] li_xss_a1 = fi_xss_a1;
    always @(posedge clk) begin : g_dli_xss_a1 integer j; dli_xss_a1[0] <= fi_xss_a1; for (j = 1; j <= 0; j = j + 1) dli_xss_a1[j] <= dli_xss_a1[j - 1]; end
    reg [4:0] fi_xss_g1;
    reg [4:0] dli_xss_g1 [0:0];  wire [4:0] li_xss_g1 = fi_xss_g1;
    always @(posedge clk) begin : g_dli_xss_g1 integer j; dli_xss_g1[0] <= fi_xss_g1; for (j = 1; j <= 0; j = j + 1) dli_xss_g1[j] <= dli_xss_g1[j - 1]; end
    reg [6:0] fi_xss_a2;
    reg [6:0] dli_xss_a2 [0:0];  wire [6:0] li_xss_a2 = fi_xss_a2;
    always @(posedge clk) begin : g_dli_xss_a2 integer j; dli_xss_a2[0] <= fi_xss_a2; for (j = 1; j <= 0; j = j + 1) dli_xss_a2[j] <= dli_xss_a2[j - 1]; end
    reg [4:0] fi_xss_g2;
    reg [4:0] dli_xss_g2 [0:0];  wire [4:0] li_xss_g2 = fi_xss_g2;
    always @(posedge clk) begin : g_dli_xss_g2 integer j; dli_xss_g2[0] <= fi_xss_g2; for (j = 1; j <= 0; j = j + 1) dli_xss_g2[j] <= dli_xss_g2[j - 1]; end
    reg [817:0] fi_rin_n;
    reg [817:0] dli_rin_n [0:0];  wire [817:0] li_rin_n = fi_rin_n;
    always @(posedge clk) begin : g_dli_rin_n integer j; dli_rin_n[0] <= fi_rin_n; for (j = 1; j <= 0; j = j + 1) dli_rin_n[j] <= dli_rin_n[j - 1]; end
    reg [817:0] fi_rin_s;
    reg [817:0] dli_rin_s [0:0];  wire [817:0] li_rin_s = fi_rin_s;
    always @(posedge clk) begin : g_dli_rin_s integer j; dli_rin_s[0] <= fi_rin_s; for (j = 1; j <= 0; j = j + 1) dli_rin_s[j] <= dli_rin_s[j - 1]; end
    reg [2068:0] fi_bin;
    reg [2068:0] dli_bin [0:0];  wire [2068:0] li_bin = fi_bin;
    always @(posedge clk) begin : g_dli_bin integer j; dli_bin[0] <= fi_bin; for (j = 1; j <= 0; j = j + 1) dli_bin[j] <= dli_bin[j - 1]; end
    reg [99:0] fi_gin;
    reg [99:0] dli_gin [0:0];  wire [99:0] li_gin = fi_gin;
    always @(posedge clk) begin : g_dli_gin integer j; dli_gin[0] <= fi_gin; for (j = 1; j <= 0; j = j + 1) dli_gin[j] <= dli_gin[j - 1]; end
    wire [817:0] fo_rout_n, lo_rout_n;  reg [817:0] dlo_rout_n [0:0];
    always @(posedge clk) begin : g_dlo_rout_n integer j; dlo_rout_n[0] <= fo_rout_n; for (j = 1; j <= 0; j = j + 1) dlo_rout_n[j] <= dlo_rout_n[j - 1]; end
    wire [817:0] fo_rout_s, lo_rout_s;  reg [817:0] dlo_rout_s [0:0];
    always @(posedge clk) begin : g_dlo_rout_s integer j; dlo_rout_s[0] <= fo_rout_s; for (j = 1; j <= 0; j = j + 1) dlo_rout_s[j] <= dlo_rout_s[j - 1]; end
    wire [2068:0] fo_bout, lo_bout;  reg [2068:0] dlo_bout [0:0];
    always @(posedge clk) begin : g_dlo_bout integer j; dlo_bout[0] <= fo_bout; for (j = 1; j <= 0; j = j + 1) dlo_bout[j] <= dlo_bout[j - 1]; end
    wire [199:0] fo_gout, lo_gout;  reg [199:0] dlo_gout [0:9];
    always @(posedge clk) begin : g_dlo_gout integer j; dlo_gout[0] <= fo_gout; for (j = 1; j <= 9; j = j + 1) dlo_gout[j] <= dlo_gout[j - 1]; end
    ot_hbm_smh_rp4a_flat u_flat (.clk(clk), .rst_n(rst_f), .attn(attn), .xs_a1(fi_xs_a1), .xs_g1(fi_xs_g1), .xs_a2(fi_xs_a2), .xs_g2(fi_xs_g2), .xss_a1(fi_xss_a1), .xss_g1(fi_xss_g1), .xss_a2(fi_xss_a2), .xss_g2(fi_xss_g2), .rin_n(fi_rin_n), .rin_s(fi_rin_s), .bin(fi_bin), .gin(fi_gin), .rout_n(fo_rout_n), .rout_s(fo_rout_s), .bout(fo_bout), .gout(fo_gout));
    ot_hbm_smh_rp4ah2 #(.MUT(MUT), .SOFTBEAT(SOFTBEAT), .GN(GN), .GS(GS), .XB(XB)) u_lp (.ck_n(clk), .ck_s(clk), .rst_n(rst), .attn(attn), .xs_a1(li_xs_a1), .xs_g1(li_xs_g1), .xs_a2(li_xs_a2), .xs_g2(li_xs_g2), .xss_a1(li_xss_a1), .xss_g1(li_xss_g1), .xss_a2(li_xss_a2), .xss_g2(li_xss_g2), .rin_n(li_rin_n), .rin_s(li_rin_s), .bin(li_bin), .gin(li_gin), .rout_n(lo_rout_n), .rout_s(lo_rout_s), .bout(lo_bout), .gout(lo_gout));
    // activity census (the bench must exercise the attention datapath, not only the transport)
    integer c_bov = 0, c_fov = 0, c_ev = 0, c_pub = 0, c_pvin = 0;
    always @(posedge clk) begin
        c_bov = c_bov + u_flat.u_lf0.bov + u_flat.u_lf1.bov;
        c_fov = c_fov + u_flat.u_lf0.fov + u_flat.u_lf1.fov;
        c_ev  = c_ev  + u_flat.u_lf0.event_v + u_flat.u_lf1.event_v;
        c_pub = c_pub + u_flat.u_lf0.ps_v + u_flat.u_lf1.ps_v;
        c_pvin = c_pvin + u_flat.u_lf0.input_pv + u_flat.u_lf1.input_pv;
    end
    function [31:0] rnd; input integer k; rnd = $urandom; endfunction
    integer cyc, nc, bad;
    initial begin
        nc = 0; bad = 0;
        fi_xs_a1 = 0;
        fi_xs_g1 = 0;
        fi_xs_a2 = 0;
        fi_xs_g2 = 0;
        fi_xss_a1 = 0;
        fi_xss_g1 = 0;
        fi_xss_a2 = 0;
        fi_xss_g2 = 0;
        fi_rin_n = 0;
        fi_rin_s = 0;
        fi_bin = 0;
        fi_gin = 0;
        for (cyc = 0; cyc < 4000; cyc = cyc + 1) begin
            @(negedge clk);
            if (cyc == 16) rst = 1;
            fi_xs_a1 = (cyc > 22) ? {$urandom} : 0;
            fi_xs_g1 = (cyc > 22) ? {$urandom} : 0;
            fi_xs_a2 = (cyc > 22) ? {$urandom} : 0;
            fi_xs_g2 = (cyc > 22) ? {$urandom} : 0;
            fi_xss_a1 = (cyc > 22) ? {$urandom} : 0;
            fi_xss_g1 = (cyc > 22) ? {$urandom} : 0;
            fi_xss_a2 = (cyc > 22) ? {$urandom} : 0;
            fi_xss_g2 = (cyc > 22) ? {$urandom} : 0;
            fi_rin_n = (cyc > 22) ? {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom} : 0;
            fi_rin_s = (cyc > 22) ? {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom} : 0;
            fi_bin = (cyc > 22) ? {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom} : 0;
            fi_gin = (cyc > 22) ? {$urandom,$urandom,$urandom,$urandom} : 0;
            if (cyc > 800) begin
                nc = nc + 1; if (lo_rout_n !== fo_rout_n) begin bad = bad + 1; if (bad <= 5) $display("H2A_MISMATCH port=rout_n cycle=%0d flat=%h landed=%h", cyc, fo_rout_n, lo_rout_n); end
                nc = nc + 1; if (lo_rout_s !== fo_rout_s) begin bad = bad + 1; if (bad <= 5) $display("H2A_MISMATCH port=rout_s cycle=%0d flat=%h landed=%h", cyc, fo_rout_s, lo_rout_s); end
                nc = nc + 1; if (lo_bout !== fo_bout) begin bad = bad + 1; if (bad <= 5) $display("H2A_MISMATCH port=bout cycle=%0d flat=%h landed=%h", cyc, fo_bout, lo_bout); end
                nc = nc + 1; if (lo_gout !== dlo_gout[2 + GN + GS]) begin bad = bad + 1; if (bad <= 5) $display("H2A_MISMATCH port=gout cycle=%0d flat=%h landed=%h", cyc, dlo_gout[2 + GN + GS], lo_gout); end
            end
        end
        $display("H2A_ACTIVITY bdc_out=%0d qk_out=%0d pv_events=%0d publications=%0d pv_inputs=%0d", c_bov, c_fov, c_ev, c_pub, c_pvin);
        if (bad == 0 && nc > 0) $display("H2A_LOCKSTEP PASS MUT=%0d compared=%0d cycles=4000 warm=800 SOFTBEAT=%0d GN=%0d GS=%0d XB=%0d ATTN=%0d", MUT, nc, SOFTBEAT, GN, GS, XB, ATTN);
        else $display("H2A_LOCKSTEP FAIL MUT=%0d mismatches=%0d of %0d", MUT, bad, nc);
        $finish;
    end
endmodule
