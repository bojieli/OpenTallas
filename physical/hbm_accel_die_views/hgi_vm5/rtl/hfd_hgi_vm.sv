// hfd_hgi_vm: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI-1 vector memory, R25GQ (variant r25gqn) with the wide lane groups ON (hgi-1010/b 2026-10-10): ot_hgi_vm_die = ot_hgi_vm_unit (262,144 FP32 words, 32 banks, per-word SECDED; NC 9 packet clients cp quant idx argmax su sfu hc dma coll; DMA wide write WP 32 WDIRECT 1; RP 64 read lanes = chains lgW / lgE; W2 96 write lanes = lgW / lgE / the hardware ROW_GATHER sink; LQ 32) + the chain heads (ot_hgi_vm_lanehead K 3) + the coll sink head (K 1). Every chain node takes f_lg<G>_<suf> and drives t_lg<G>_<suf>; the VM drives t_*dn and takes f_*up.
module hfd_hgi_vm (
    input wire [0:0] ck,
    input wire [337:0] f_hgi_argmax,
    input wire [337:0] f_hgi_coll,
    input wire [337:0] f_hgi_cp,
    input wire [337:0] f_hgi_dma,
    input wire [337:0] f_hgi_hc,
    input wire [337:0] f_hgi_idx,
    input wire [337:0] f_hgi_quant,
    input wire [337:0] f_hgi_sfu,
    input wire [337:0] f_hgi_su,
    input wire [8960:0] f_hgi_vmw2_coll,
    input wire [8959:0] f_hgi_vmw_dma,
    input wire [514:0] f_lgE_rup,
    input wire [8962:0] f_lgE_wup,
    input wire [514:0] f_lgW_rup,
    input wire [8962:0] f_lgW_wup,
    input wire [0:0] rst,
    output wire [273:0] t_hgi_argmax,
    output wire [273:0] t_hgi_coll,
    output wire [273:0] t_hgi_cp,
    output wire [273:0] t_hgi_dma,
    output wire [273:0] t_hgi_hc,
    output wire [273:0] t_hgi_idx,
    output wire [273:0] t_hgi_quant,
    output wire [273:0] t_hgi_sfu,
    output wire [273:0] t_hgi_su,
    output wire [18:0] t_hgi_vmstat,
    output wire [64:0] t_hgi_vmw2_coll,
    output wire [31:0] t_hgi_vmw_dma,
    output wire [8258:0] t_lgE_rdn,
    output wire [66:0] t_lgE_wdn,
    output wire [8258:0] t_lgW_rdn,
    output wire [66:0] t_lgW_wdn
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [337:0] i0_f_hgi_argmax; always @(posedge clk) i0_f_hgi_argmax <= f_hgi_argmax;
    reg [337:0] i1_f_hgi_argmax; always @(posedge clk) i1_f_hgi_argmax <= i0_f_hgi_argmax;
    reg [337:0] i_f_hgi_argmax; always @(posedge clk) i_f_hgi_argmax <= i1_f_hgi_argmax;
    reg [337:0] i0_f_hgi_coll; always @(posedge clk) i0_f_hgi_coll <= f_hgi_coll;
    reg [337:0] i1_f_hgi_coll; always @(posedge clk) i1_f_hgi_coll <= i0_f_hgi_coll;
    reg [337:0] i_f_hgi_coll; always @(posedge clk) i_f_hgi_coll <= i1_f_hgi_coll;
    reg [337:0] i0_f_hgi_cp; always @(posedge clk) i0_f_hgi_cp <= f_hgi_cp;
    reg [337:0] i1_f_hgi_cp; always @(posedge clk) i1_f_hgi_cp <= i0_f_hgi_cp;
    reg [337:0] i_f_hgi_cp; always @(posedge clk) i_f_hgi_cp <= i1_f_hgi_cp;
    reg [337:0] i0_f_hgi_dma; always @(posedge clk) i0_f_hgi_dma <= f_hgi_dma;
    reg [337:0] i1_f_hgi_dma; always @(posedge clk) i1_f_hgi_dma <= i0_f_hgi_dma;
    reg [337:0] i_f_hgi_dma; always @(posedge clk) i_f_hgi_dma <= i1_f_hgi_dma;
    reg [337:0] i0_f_hgi_hc; always @(posedge clk) i0_f_hgi_hc <= f_hgi_hc;
    reg [337:0] i1_f_hgi_hc; always @(posedge clk) i1_f_hgi_hc <= i0_f_hgi_hc;
    reg [337:0] i_f_hgi_hc; always @(posedge clk) i_f_hgi_hc <= i1_f_hgi_hc;
    reg [337:0] i0_f_hgi_idx; always @(posedge clk) i0_f_hgi_idx <= f_hgi_idx;
    reg [337:0] i1_f_hgi_idx; always @(posedge clk) i1_f_hgi_idx <= i0_f_hgi_idx;
    reg [337:0] i_f_hgi_idx; always @(posedge clk) i_f_hgi_idx <= i1_f_hgi_idx;
    reg [337:0] i0_f_hgi_quant; always @(posedge clk) i0_f_hgi_quant <= f_hgi_quant;
    reg [337:0] i1_f_hgi_quant; always @(posedge clk) i1_f_hgi_quant <= i0_f_hgi_quant;
    reg [337:0] i_f_hgi_quant; always @(posedge clk) i_f_hgi_quant <= i1_f_hgi_quant;
    reg [337:0] i0_f_hgi_sfu; always @(posedge clk) i0_f_hgi_sfu <= f_hgi_sfu;
    reg [337:0] i1_f_hgi_sfu; always @(posedge clk) i1_f_hgi_sfu <= i0_f_hgi_sfu;
    reg [337:0] i_f_hgi_sfu; always @(posedge clk) i_f_hgi_sfu <= i1_f_hgi_sfu;
    reg [337:0] i0_f_hgi_su; always @(posedge clk) i0_f_hgi_su <= f_hgi_su;
    reg [337:0] i1_f_hgi_su; always @(posedge clk) i1_f_hgi_su <= i0_f_hgi_su;
    reg [337:0] i_f_hgi_su; always @(posedge clk) i_f_hgi_su <= i1_f_hgi_su;
    reg [8960:0] i0_f_hgi_vmw2_coll; always @(posedge clk) i0_f_hgi_vmw2_coll <= f_hgi_vmw2_coll;
    reg [8960:0] i1_f_hgi_vmw2_coll; always @(posedge clk) i1_f_hgi_vmw2_coll <= i0_f_hgi_vmw2_coll;
    reg [8960:0] i_f_hgi_vmw2_coll; always @(posedge clk) i_f_hgi_vmw2_coll <= i1_f_hgi_vmw2_coll;
    reg [8959:0] i0_f_hgi_vmw_dma; always @(posedge clk) i0_f_hgi_vmw_dma <= f_hgi_vmw_dma;
    reg [8959:0] i1_f_hgi_vmw_dma; always @(posedge clk) i1_f_hgi_vmw_dma <= i0_f_hgi_vmw_dma;
    reg [8959:0] i_f_hgi_vmw_dma; always @(posedge clk) i_f_hgi_vmw_dma <= i1_f_hgi_vmw_dma;
    reg [514:0] i0_f_lgE_rup; always @(posedge clk) i0_f_lgE_rup <= f_lgE_rup;
    reg [514:0] i1_f_lgE_rup; always @(posedge clk) i1_f_lgE_rup <= i0_f_lgE_rup;
    reg [514:0] i_f_lgE_rup; always @(posedge clk) i_f_lgE_rup <= i1_f_lgE_rup;
    reg [8962:0] i0_f_lgE_wup; always @(posedge clk) i0_f_lgE_wup <= f_lgE_wup;
    reg [8962:0] i1_f_lgE_wup; always @(posedge clk) i1_f_lgE_wup <= i0_f_lgE_wup;
    reg [8962:0] i_f_lgE_wup; always @(posedge clk) i_f_lgE_wup <= i1_f_lgE_wup;
    reg [514:0] i0_f_lgW_rup; always @(posedge clk) i0_f_lgW_rup <= f_lgW_rup;
    reg [514:0] i1_f_lgW_rup; always @(posedge clk) i1_f_lgW_rup <= i0_f_lgW_rup;
    reg [514:0] i_f_lgW_rup; always @(posedge clk) i_f_lgW_rup <= i1_f_lgW_rup;
    reg [8962:0] i0_f_lgW_wup; always @(posedge clk) i0_f_lgW_wup <= f_lgW_wup;
    reg [8962:0] i1_f_lgW_wup; always @(posedge clk) i1_f_lgW_wup <= i0_f_lgW_wup;
    reg [8962:0] i_f_lgW_wup; always @(posedge clk) i_f_lgW_wup <= i1_f_lgW_wup;
    wire [0:0] w_vmd_clk;
    wire [0:0] w_vmd_rst_n;
    wire [3041:0] w_vmd_cq;
    wire [2465:0] w_vmd_cr;
    wire [18:0] w_vmd_status;
    wire [8959:0] w_vmd_wq;
    wire [31:0] w_vmd_wq_done;
    wire [514:0] w_vmd_lgw_r_up;
    wire [8258:0] w_vmd_lgw_r_dn;
    wire [8962:0] w_vmd_lgw_w_up;
    wire [66:0] w_vmd_lgw_w_dn;
    wire [514:0] w_vmd_lge_r_up;
    wire [8258:0] w_vmd_lge_r_dn;
    wire [8962:0] w_vmd_lge_w_up;
    wire [66:0] w_vmd_lge_w_dn;
    wire [8960:0] w_vmd_coll_w_up;
    wire [64:0] w_vmd_coll_w_dn;
    assign w_vmd_clk = {1{clk}};
    assign w_vmd_rst_n = {1{rst_n}};
    assign w_vmd_cq = {i_f_hgi_coll[337:0], i_f_hgi_dma[337:0], i_f_hgi_hc[337:0], i_f_hgi_sfu[337:0], i_f_hgi_su[337:0], i_f_hgi_argmax[337:0], i_f_hgi_idx[337:0], i_f_hgi_quant[337:0], i_f_hgi_cp[337:0]};
    assign w_vmd_wq = {i_f_hgi_vmw_dma[8959:0]};
    assign w_vmd_lgw_r_up = {i_f_lgW_rup[514:0]};
    assign w_vmd_lgw_w_up = {i_f_lgW_wup[8962:0]};
    assign w_vmd_lge_r_up = {i_f_lgE_rup[514:0]};
    assign w_vmd_lge_w_up = {i_f_lgE_wup[8962:0]};
    assign w_vmd_coll_w_up = {i_f_hgi_vmw2_coll[8960:0]};
    ot_hgi_vm_die #(.NC(9), .LQ(32), .K(3)) u_vmd (.clk(w_vmd_clk), .rst_n(w_vmd_rst_n), .cq(w_vmd_cq), .cr(w_vmd_cr), .status(w_vmd_status), .wq(w_vmd_wq), .wq_done(w_vmd_wq_done), .lgw_r_up(w_vmd_lgw_r_up), .lgw_r_dn(w_vmd_lgw_r_dn), .lgw_w_up(w_vmd_lgw_w_up), .lgw_w_dn(w_vmd_lgw_w_dn), .lge_r_up(w_vmd_lge_r_up), .lge_r_dn(w_vmd_lge_r_dn), .lge_w_up(w_vmd_lge_w_up), .lge_w_dn(w_vmd_lge_w_dn), .coll_w_up(w_vmd_coll_w_up), .coll_w_dn(w_vmd_coll_w_dn));
    wire [273:0] od_t_hgi_argmax = {w_vmd_cr[1095:822]};
    wire [273:0] o_t_hgi_argmax;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_argmax
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_argmax[k]), .q(o_t_hgi_argmax[k]));
    end
    assign t_hgi_argmax[273:0] = o_t_hgi_argmax[273:0];
    wire [273:0] od_t_hgi_coll = {w_vmd_cr[2465:2192]};
    wire [273:0] o_t_hgi_coll;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_coll
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_coll[k]), .q(o_t_hgi_coll[k]));
    end
    assign t_hgi_coll[273:0] = o_t_hgi_coll[273:0];
    wire [273:0] od_t_hgi_cp = {w_vmd_cr[273:0]};
    wire [273:0] o_t_hgi_cp;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_cp
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_cp[k]), .q(o_t_hgi_cp[k]));
    end
    assign t_hgi_cp[273:0] = o_t_hgi_cp[273:0];
    wire [273:0] od_t_hgi_dma = {w_vmd_cr[2191:1918]};
    wire [273:0] o_t_hgi_dma;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_dma
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_dma[k]), .q(o_t_hgi_dma[k]));
    end
    assign t_hgi_dma[273:0] = o_t_hgi_dma[273:0];
    wire [273:0] od_t_hgi_hc = {w_vmd_cr[1917:1644]};
    wire [273:0] o_t_hgi_hc;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_hc
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_hc[k]), .q(o_t_hgi_hc[k]));
    end
    assign t_hgi_hc[273:0] = o_t_hgi_hc[273:0];
    wire [273:0] od_t_hgi_idx = {w_vmd_cr[821:548]};
    wire [273:0] o_t_hgi_idx;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_idx
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_idx[k]), .q(o_t_hgi_idx[k]));
    end
    assign t_hgi_idx[273:0] = o_t_hgi_idx[273:0];
    wire [273:0] od_t_hgi_quant = {w_vmd_cr[547:274]};
    wire [273:0] o_t_hgi_quant;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_quant
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_quant[k]), .q(o_t_hgi_quant[k]));
    end
    assign t_hgi_quant[273:0] = o_t_hgi_quant[273:0];
    wire [273:0] od_t_hgi_sfu = {w_vmd_cr[1643:1370]};
    wire [273:0] o_t_hgi_sfu;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_sfu
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_sfu[k]), .q(o_t_hgi_sfu[k]));
    end
    assign t_hgi_sfu[273:0] = o_t_hgi_sfu[273:0];
    wire [273:0] od_t_hgi_su = {w_vmd_cr[1369:1096]};
    wire [273:0] o_t_hgi_su;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_su
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_su[k]), .q(o_t_hgi_su[k]));
    end
    assign t_hgi_su[273:0] = o_t_hgi_su[273:0];
    wire [18:0] od_t_hgi_vmstat = {w_vmd_status[18:0]};
    wire [18:0] o_t_hgi_vmstat;
    for (genvar k = 0; k < 19; k = k + 1) begin : g_o_t_hgi_vmstat
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_vmstat[k]), .q(o_t_hgi_vmstat[k]));
    end
    assign t_hgi_vmstat[18:0] = o_t_hgi_vmstat[18:0];
    wire [64:0] od_t_hgi_vmw2_coll = {w_vmd_coll_w_dn[64:0]};
    wire [64:0] o_t_hgi_vmw2_coll;
    for (genvar k = 0; k < 65; k = k + 1) begin : g_o_t_hgi_vmw2_coll
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_vmw2_coll[k]), .q(o_t_hgi_vmw2_coll[k]));
    end
    assign t_hgi_vmw2_coll[64:0] = o_t_hgi_vmw2_coll[64:0];
    wire [31:0] od_t_hgi_vmw_dma = {w_vmd_wq_done[31:0]};
    wire [31:0] o_t_hgi_vmw_dma;
    for (genvar k = 0; k < 32; k = k + 1) begin : g_o_t_hgi_vmw_dma
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_vmw_dma[k]), .q(o_t_hgi_vmw_dma[k]));
    end
    assign t_hgi_vmw_dma[31:0] = o_t_hgi_vmw_dma[31:0];
    wire [8258:0] od_t_lgE_rdn = {w_vmd_lge_r_dn[8258:0]};
    wire [8258:0] o_t_lgE_rdn;
    for (genvar k = 0; k < 8259; k = k + 1) begin : g_o_t_lgE_rdn
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_lgE_rdn[k]), .q(o_t_lgE_rdn[k]));
    end
    assign t_lgE_rdn[8258:0] = o_t_lgE_rdn[8258:0];
    wire [66:0] od_t_lgE_wdn = {w_vmd_lge_w_dn[66:0]};
    wire [66:0] o_t_lgE_wdn;
    for (genvar k = 0; k < 67; k = k + 1) begin : g_o_t_lgE_wdn
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_lgE_wdn[k]), .q(o_t_lgE_wdn[k]));
    end
    assign t_lgE_wdn[66:0] = o_t_lgE_wdn[66:0];
    wire [8258:0] od_t_lgW_rdn = {w_vmd_lgw_r_dn[8258:0]};
    wire [8258:0] o_t_lgW_rdn;
    for (genvar k = 0; k < 8259; k = k + 1) begin : g_o_t_lgW_rdn
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_lgW_rdn[k]), .q(o_t_lgW_rdn[k]));
    end
    assign t_lgW_rdn[8258:0] = o_t_lgW_rdn[8258:0];
    wire [66:0] od_t_lgW_wdn = {w_vmd_lgw_w_dn[66:0]};
    wire [66:0] o_t_lgW_wdn;
    for (genvar k = 0; k < 67; k = k + 1) begin : g_o_t_lgW_wdn
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_lgW_wdn[k]), .q(o_t_lgW_wdn[k]));
    end
    assign t_lgW_wdn[66:0] = o_t_lgW_wdn[66:0];
endmodule
