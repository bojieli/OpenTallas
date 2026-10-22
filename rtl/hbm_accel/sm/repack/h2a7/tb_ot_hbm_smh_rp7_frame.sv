`timescale 1ns/1ps
// HBM-ELEM13/SMH-R6 r6 (from tb_ot_hbm_smh_rp5_2): lockstep ot_hbm_smh_rp4a_flat (attention leaf, flat, reset delayed 4 = pin stage + RB 3) vs ot_hbm_smh_rp6_2 (two GEOMETRIC regional landed attention halves; gout +DG more than r3, rout +1 glue pin register); static attn strap ATTN held from cycle 0; every input presented off_in edges later, every output compared off_out edges later.
module tb_ot_hbm_smh_rp7_frame;
    parameter integer VAR = 0;            // r6: 0 MAIN (n t/u/c/m, s u/c/m bands), 1 FB (n t/u/c, s t/u/c)
    parameter integer HMUT = 0;           // r6 half mutants: 1 xb crossing +1, 2 gpm crossing +1, 3 rl1 pad short, 5 n attn row off, 6 rl1 relay short
    localparam integer DN=VAR==0 ? 6:9, DS=VAR==0 ? 15:18, DB=6, DG=VAR==0 ? 21:36;
    parameter integer MUT = 0;
    parameter integer SOFTBEAT = 1;
    parameter integer GN = 2;             // n gather relays (kit default)
    parameter integer GS = 1;             // s gather relays (kit default)
    parameter integer XB = 1;             // n beat-crossing relays (kit default)
    parameter integer OS = 0;             // HBM-SMATT10 core census stages (r1 kits 1): gout +2*OS
    parameter integer LR = 0;             // HBM-SMATT10 leaf-input relays (r1 kits 2): gout +LR uniform
    parameter integer ATTN = 5'b01_101;   // attn_rowbase 1, attn_column 5
    wire [4:0] attn = ATTN;
    reg clk = 1'b0;  always #0.5 clk = ~clk;
    reg rst = 0;  reg [0:0] rst_dl;
    wire rst_f = rst_dl[0];
    always @(posedge clk) rst_dl <= rst;
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
    wire [817:0] fo_rout_n, lo_rout_n;  reg [817:0] dlo_rout_n [0:DN-1];
    always @(posedge clk) begin : g_dlo_rout_n integer j; dlo_rout_n[0] <= fo_rout_n; for (j = 1; j < DN; j = j + 1) dlo_rout_n[j] <= dlo_rout_n[j - 1]; end
    wire [817:0] fo_rout_s, lo_rout_s;  reg [817:0] dlo_rout_s [0:DS-1];
    always @(posedge clk) begin : g_dlo_rout_s integer j; dlo_rout_s[0] <= fo_rout_s; for (j = 1; j < DS; j = j + 1) dlo_rout_s[j] <= dlo_rout_s[j - 1]; end
    wire [2068:0] fo_bout, lo_bout;  reg [2068:0] dlo_bout [0:DB-1];
    always @(posedge clk) begin : g_dlo_bout integer j; dlo_bout[0] <= fo_bout; for (j = 1; j < DB; j = j + 1) dlo_bout[j] <= dlo_bout[j - 1]; end
    wire [199:0] fo_gout, lo_gout;  reg [199:0] dlo_gout [0:DG-1];  // r6: 0:31 (compare tap 10 + DG)
    always @(posedge clk) begin : g_dlo_gout integer j; dlo_gout[0] <= fo_gout; for (j = 1; j < DG; j = j + 1) dlo_gout[j] <= dlo_gout[j - 1]; end
    ot_hbm_smh_rp6_2 #(.VAR(VAR)) u_flat (.clk(clk), .rst_n(rst_f), .attn(attn), .xs_a1(fi_xs_a1), .xs_g1(fi_xs_g1), .xs_a2(fi_xs_a2), .xs_g2(fi_xs_g2), .xss_a1(fi_xss_a1), .xss_g1(fi_xss_g1), .xss_a2(fi_xss_a2), .xss_g2(fi_xss_g2), .rin_n(fi_rin_n), .rin_s(fi_rin_s), .bin(fi_bin), .gin(fi_gin), .rout_n(fo_rout_n), .rout_s(fo_rout_s), .bout(fo_bout), .gout(fo_gout));
    ot_hbm_smh_rp7_2 #(.VAR(VAR), .HMUT(HMUT), .MUT(MUT)) u_lp (.clk(clk), .rst_n(rst), .attn(attn), .xs_a1(li_xs_a1), .xs_g1(li_xs_g1), .xs_a2(li_xs_a2), .xs_g2(li_xs_g2), .xss_a1(li_xss_a1), .xss_g1(li_xss_g1), .xss_a2(li_xss_a2), .xss_g2(li_xss_g2), .rin_n(li_rin_n), .rin_s(li_rin_s), .bin(li_bin), .gin(li_gin), .rout_n(lo_rout_n), .rout_s(lo_rout_s), .bout(lo_bout), .gout(lo_gout));
    integer c_bov=0,c_fov=0,c_ev=0,c_pub=0,c_pvin=0;
generate if(VAR==0) begin:activity_main
always @(posedge clk) begin
c_bov<=c_bov+u_flat.g_main.u_n.bov0+u_flat.g_main.u_s.bov1;
c_fov<=c_fov+u_flat.g_main.u_n.fov0+u_flat.g_main.u_s.fov1;
c_ev<=c_ev+u_flat.g_main.u_n.ev0+u_flat.g_main.u_s.ev1;
c_pub<=c_pub+u_flat.g_main.u_n.pv0+u_flat.g_main.u_s.pv1;
end end endgenerate
generate if(VAR==1) begin:activity_fb
always @(posedge clk) begin
c_bov<=c_bov+u_flat.g_fb.u_n.bov0+u_flat.g_fb.u_s.bov1;
c_fov<=c_fov+u_flat.g_fb.u_n.fov0+u_flat.g_fb.u_s.fov1;
c_ev<=c_ev+u_flat.g_fb.u_n.ev0+u_flat.g_fb.u_s.ev1;
c_pub<=c_pub+u_flat.g_fb.u_n.pv0+u_flat.g_fb.u_s.pv1;
end end endgenerate
    function [31:0] rnd; input integer k; rnd = $urandom; endfunction
    integer cyc, nc, bad; integer first_old[0:3],first_new[0:3];
    initial begin
        nc = 0; bad = 0; for(integer k=0;k<4;k=k+1) begin first_old[k]=-1;first_new[k]=-1;end
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
            for(integer k=0;k<4;k=k+1) begin
                if(first_old[k]<0 && fo_gout[k*50+49]) first_old[k]=cyc;
                if(first_new[k]<0 && lo_gout[k*50+49]) first_new[k]=cyc;
                if(cyc>16 && (lo_gout[k*50+49] || dlo_gout[DG-1][k*50+49]) && lo_gout[k*50+:50] !== dlo_gout[DG-1][k*50+:50]) begin
                    bad=bad+1; if(bad<6) $display("R7_FIRST_TOKEN_MISMATCH lane=%0d cycle=%0d old=%h new=%h",k,cyc,dlo_gout[DG-1][k*50+:50],lo_gout[k*50+:50]);
                end
            end
            if (cyc > 800) begin
                nc = nc + 1; if (lo_rout_n !== dlo_rout_n[DN-1]) begin bad = bad + 1; if (bad <= 5) $display("R7_FRAME_MISMATCH port=rout_n cycle=%0d flat=%h landed=%h", cyc, dlo_rout_n[DN-1], lo_rout_n); end
                nc = nc + 1; if (lo_rout_s !== dlo_rout_s[DS-1]) begin bad = bad + 1; if (bad <= 5) $display("R7_FRAME_MISMATCH port=rout_s cycle=%0d flat=%h landed=%h", cyc, dlo_rout_s[DS-1], lo_rout_s); end
                nc = nc + 1; if (lo_bout !== dlo_bout[DB-1]) begin bad = bad + 1; if (bad <= 5) $display("R7_FRAME_MISMATCH port=bout cycle=%0d flat=%h landed=%h", cyc, dlo_bout[DB-1], lo_bout); end
                nc = nc + 1; if (lo_gout !== dlo_gout[DG-1]) begin bad = bad + 1; if (bad <= 5) $display("R7_FRAME_MISMATCH port=gout cycle=%0d flat=%h landed=%h", cyc, dlo_gout[DG-1], lo_gout); end
            end
        end
        for(integer k=0;k<4;k=k+1) begin
            $display("R7_FIRST_TOKEN lane=%0d old_cycle=%0d new_cycle=%0d required_added_edges=%0d",k,first_old[k],first_new[k],DG);
            if(first_old[k]<0 || first_new[k]!=first_old[k]+DG) bad=bad+1;
        end
        $display("R7_FRAME_ACTIVITY bdc_out=%0d qk_out=%0d pv_events=%0d publications=%0d pv_inputs=%0d", c_bov, c_fov, c_ev, c_pub, c_pvin);
        if (bad == 0 && nc > 0 && c_bov>0 && c_fov>0 && c_ev>0 && c_pub>0) $display("R7_FRAME_LOCKSTEP PASS VAR=%0d HMUT=%0d compared=%0d cycles=4000 warm=800 added_gout_edges=%0d ATTN=%0d", VAR, HMUT, nc, DG, ATTN);
        else $display("R7_FRAME_LOCKSTEP FAIL VAR=%0d HMUT=%0d mismatches=%0d of %0d", VAR, HMUT, bad, nc);
        $finish;
    end
endmodule
