// hfd_quant: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI-1 quant view with the FUSED station (hgi-1010/c2, AUDIT N5; supersedes the QDQ-only view of hgi-takeover 10-09): ot_hgi_fused_station = ot_hgi_fused_record (UNIT 1, UWIDE 1: unit 4 front, record hgi_quant_cmd 1,216 b {n_O, n_B, n_A, O, C, B, A, header, valid} from ot_hgi_cp_die FUSED 1) -> ROW_NORM / HC_PRE_NORM / HC_POST on its internal stream unit (VM packet client hgi_vmq_fused, wide lanes on the lgE tap, slot 2), QDQ_* forwarded on q_rec to the unchanged ot_hgi_quant_unit (VM client hgi_vmq_quant, as before); the FUSED mover (ot_hgi_dma_mover, gain LOAD) on its own remote kport read lane hgi_fmk_q 38 / hgi_fmk_r 257 (ot_hgi_hbm_rdq_server on the loader kport lane after the mover HBM lanes), its VM client hgi_vmq_fmv, its VM write lane on the lgE write group. Unit bench rtl/hbm_accel/generic/adapters/tb/tb_hgi_fused_station.sv. el1011-hbm-fused 10-12: HCE 2 / HLL 1 -- the record hands its d = 5120 HC_POST / HC_PRE_NORM jobs to hfd_hc_eng (ot_hgi_hc_eng_station) over fused_ne {g_rdy, job_v, job 149} / fused_ne_r {job_rdy, fault, done}; bench tb_hgi_fused_station (run_hgi_die_masters.sh fused_hce).
module hfd_quant (
    input wire [0:0] ck,
    input wire [2:0] f_fused_ne,
    input wire [1215:0] f_hgi_cmdproc,
    input wire [256:0] f_hgi_fmkr,
    input wire [273:0] f_hgi_vmr,
    input wire [273:0] f_hgi_vmr_fmv,
    input wire [273:0] f_hgi_vmr_fused,
    input wire [8256:0] f_lgE_rdn,
    input wire [64:0] f_lgE_wdn,
    input wire [0:0] rst,
    output wire [150:0] t_fused_ne,
    output wire [2:0] t_hgi_cmdproc,
    output wire [37:0] t_hgi_fmkq,
    output wire [337:0] t_hgi_vmq,
    output wire [337:0] t_hgi_vmq_fmv,
    output wire [337:0] t_hgi_vmq_fused,
    output wire [512:0] t_lgE_rup,
    output wire [8960:0] t_lgE_wup
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [2:0] i0_f_fused_ne; always @(posedge clk) i0_f_fused_ne <= f_fused_ne;
    reg [2:0] i1_f_fused_ne; always @(posedge clk) i1_f_fused_ne <= i0_f_fused_ne;
    reg [2:0] i2_f_fused_ne; always @(posedge clk) i2_f_fused_ne <= i1_f_fused_ne;
    reg [2:0] i3_f_fused_ne; always @(posedge clk) i3_f_fused_ne <= i2_f_fused_ne;
    reg [2:0] i_f_fused_ne; always @(posedge clk) i_f_fused_ne <= i3_f_fused_ne;
    reg [1215:0] i0_f_hgi_cmdproc; always @(posedge clk) i0_f_hgi_cmdproc <= f_hgi_cmdproc;
    reg [1215:0] i1_f_hgi_cmdproc; always @(posedge clk) i1_f_hgi_cmdproc <= i0_f_hgi_cmdproc;
    reg [1215:0] i2_f_hgi_cmdproc; always @(posedge clk) i2_f_hgi_cmdproc <= i1_f_hgi_cmdproc;
    reg [1215:0] i3_f_hgi_cmdproc; always @(posedge clk) i3_f_hgi_cmdproc <= i2_f_hgi_cmdproc;
    reg [1215:0] i_f_hgi_cmdproc; always @(posedge clk) i_f_hgi_cmdproc <= i3_f_hgi_cmdproc;
    reg [256:0] i0_f_hgi_fmkr; always @(posedge clk) i0_f_hgi_fmkr <= f_hgi_fmkr;
    reg [256:0] i1_f_hgi_fmkr; always @(posedge clk) i1_f_hgi_fmkr <= i0_f_hgi_fmkr;
    reg [256:0] i2_f_hgi_fmkr; always @(posedge clk) i2_f_hgi_fmkr <= i1_f_hgi_fmkr;
    reg [256:0] i3_f_hgi_fmkr; always @(posedge clk) i3_f_hgi_fmkr <= i2_f_hgi_fmkr;
    reg [256:0] i_f_hgi_fmkr; always @(posedge clk) i_f_hgi_fmkr <= i3_f_hgi_fmkr;
    reg [273:0] i0_f_hgi_vmr; always @(posedge clk) i0_f_hgi_vmr <= f_hgi_vmr;
    reg [273:0] i1_f_hgi_vmr; always @(posedge clk) i1_f_hgi_vmr <= i0_f_hgi_vmr;
    reg [273:0] i2_f_hgi_vmr; always @(posedge clk) i2_f_hgi_vmr <= i1_f_hgi_vmr;
    reg [273:0] i3_f_hgi_vmr; always @(posedge clk) i3_f_hgi_vmr <= i2_f_hgi_vmr;
    reg [273:0] i_f_hgi_vmr; always @(posedge clk) i_f_hgi_vmr <= i3_f_hgi_vmr;
    reg [273:0] i0_f_hgi_vmr_fmv; always @(posedge clk) i0_f_hgi_vmr_fmv <= f_hgi_vmr_fmv;
    reg [273:0] i1_f_hgi_vmr_fmv; always @(posedge clk) i1_f_hgi_vmr_fmv <= i0_f_hgi_vmr_fmv;
    reg [273:0] i2_f_hgi_vmr_fmv; always @(posedge clk) i2_f_hgi_vmr_fmv <= i1_f_hgi_vmr_fmv;
    reg [273:0] i3_f_hgi_vmr_fmv; always @(posedge clk) i3_f_hgi_vmr_fmv <= i2_f_hgi_vmr_fmv;
    reg [273:0] i_f_hgi_vmr_fmv; always @(posedge clk) i_f_hgi_vmr_fmv <= i3_f_hgi_vmr_fmv;
    reg [273:0] i0_f_hgi_vmr_fused; always @(posedge clk) i0_f_hgi_vmr_fused <= f_hgi_vmr_fused;
    reg [273:0] i1_f_hgi_vmr_fused; always @(posedge clk) i1_f_hgi_vmr_fused <= i0_f_hgi_vmr_fused;
    reg [273:0] i2_f_hgi_vmr_fused; always @(posedge clk) i2_f_hgi_vmr_fused <= i1_f_hgi_vmr_fused;
    reg [273:0] i3_f_hgi_vmr_fused; always @(posedge clk) i3_f_hgi_vmr_fused <= i2_f_hgi_vmr_fused;
    reg [273:0] i_f_hgi_vmr_fused; always @(posedge clk) i_f_hgi_vmr_fused <= i3_f_hgi_vmr_fused;
    reg [8256:0] i0_f_lgE_rdn; always @(posedge clk) i0_f_lgE_rdn <= f_lgE_rdn;
    reg [8256:0] i1_f_lgE_rdn; always @(posedge clk) i1_f_lgE_rdn <= i0_f_lgE_rdn;
    reg [8256:0] i2_f_lgE_rdn; always @(posedge clk) i2_f_lgE_rdn <= i1_f_lgE_rdn;
    reg [8256:0] i3_f_lgE_rdn; always @(posedge clk) i3_f_lgE_rdn <= i2_f_lgE_rdn;
    reg [8256:0] i_f_lgE_rdn; always @(posedge clk) i_f_lgE_rdn <= i3_f_lgE_rdn;
    reg [64:0] i0_f_lgE_wdn; always @(posedge clk) i0_f_lgE_wdn <= f_lgE_wdn;
    reg [64:0] i1_f_lgE_wdn; always @(posedge clk) i1_f_lgE_wdn <= i0_f_lgE_wdn;
    reg [64:0] i2_f_lgE_wdn; always @(posedge clk) i2_f_lgE_wdn <= i1_f_lgE_wdn;
    reg [64:0] i3_f_lgE_wdn; always @(posedge clk) i3_f_lgE_wdn <= i2_f_lgE_wdn;
    reg [64:0] i_f_lgE_wdn; always @(posedge clk) i_f_lgE_wdn <= i3_f_lgE_wdn;
    wire [0:0] w_fs_clk;
    wire [0:0] w_fs_rst_n;
    wire [1215:0] w_fs_rec;
    wire [2:0] w_fs_ret;
    wire [337:0] w_fs_q_vmq;
    wire [273:0] w_fs_q_vmr;
    wire [337:0] w_fs_f_vmq;
    wire [273:0] w_fs_f_vmr;
    wire [337:0] w_fs_m_vmq;
    wire [273:0] w_fs_m_vmr;
    wire [512:0] w_fs_lg_rup;
    wire [8256:0] w_fs_lg_rdn;
    wire [8960:0] w_fs_lg_wup;
    wire [64:0] w_fs_lg_wdn;
    wire [37:0] w_fs_xq;
    wire [256:0] w_fs_xr;
    wire [150:0] w_fs_ne_o;
    wire [2:0] w_fs_ne_i;
    assign w_fs_clk = {1{clk}};
    assign w_fs_rst_n = {1{rst_n}};
    assign w_fs_rec = {i_f_hgi_cmdproc[1215:0]};
    assign w_fs_q_vmr = {i_f_hgi_vmr[273:0]};
    assign w_fs_f_vmr = {i_f_hgi_vmr_fused[273:0]};
    assign w_fs_m_vmr = {i_f_hgi_vmr_fmv[273:0]};
    assign w_fs_lg_rdn = {i_f_lgE_rdn[8256:0]};
    assign w_fs_lg_wdn = {i_f_lgE_wdn[64:0]};
    assign w_fs_xr = {i_f_hgi_fmkr[256:0]};
    assign w_fs_ne_i = {i_f_fused_ne[2:0]};
    ot_hgi_fused_station #(.UN(64), .UM(16), .UWIDE(1), .SCRATCH(245760), .Q(32), .LQ(32), .SCR_WORDS(16384), .ULWB(18), .HCE(2), .HLL(1)) u_fs (.clk(w_fs_clk), .rst_n(w_fs_rst_n), .rec(w_fs_rec), .ret(w_fs_ret), .q_vmq(w_fs_q_vmq), .q_vmr(w_fs_q_vmr), .f_vmq(w_fs_f_vmq), .f_vmr(w_fs_f_vmr), .m_vmq(w_fs_m_vmq), .m_vmr(w_fs_m_vmr), .lg_rup(w_fs_lg_rup), .lg_rdn(w_fs_lg_rdn), .lg_wup(w_fs_lg_wup), .lg_wdn(w_fs_lg_wdn), .xq(w_fs_xq), .xr(w_fs_xr), .ne_o(w_fs_ne_o), .ne_i(w_fs_ne_i));
    wire [150:0] od_t_fused_ne = {w_fs_ne_o[150:0]};
    wire [150:0] o_t_fused_ne;
    for (genvar k = 0; k < 151; k = k + 1) begin : g_o_t_fused_ne
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_fused_ne[k]), .q(o_t_fused_ne[k]));
    end
    assign t_fused_ne[150:0] = o_t_fused_ne[150:0];
    wire [2:0] od_t_hgi_cmdproc = {w_fs_ret[2:0]};
    wire [2:0] o_t_hgi_cmdproc;
    for (genvar k = 0; k < 3; k = k + 1) begin : g_o_t_hgi_cmdproc
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_cmdproc[k]), .q(o_t_hgi_cmdproc[k]));
    end
    assign t_hgi_cmdproc[2:0] = o_t_hgi_cmdproc[2:0];
    wire [37:0] od_t_hgi_fmkq = {w_fs_xq[37:0]};
    wire [37:0] o_t_hgi_fmkq;
    for (genvar k = 0; k < 38; k = k + 1) begin : g_o_t_hgi_fmkq
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_fmkq[k]), .q(o_t_hgi_fmkq[k]));
    end
    assign t_hgi_fmkq[37:0] = o_t_hgi_fmkq[37:0];
    wire [337:0] od_t_hgi_vmq = {w_fs_q_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmq[k]), .q(o_t_hgi_vmq[k]));
    end
    assign t_hgi_vmq[337:0] = o_t_hgi_vmq[337:0];
    wire [337:0] od_t_hgi_vmq_fmv = {w_fs_m_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq_fmv;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq_fmv
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmq_fmv[k]), .q(o_t_hgi_vmq_fmv[k]));
    end
    assign t_hgi_vmq_fmv[337:0] = o_t_hgi_vmq_fmv[337:0];
    wire [337:0] od_t_hgi_vmq_fused = {w_fs_f_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq_fused;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq_fused
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmq_fused[k]), .q(o_t_hgi_vmq_fused[k]));
    end
    assign t_hgi_vmq_fused[337:0] = o_t_hgi_vmq_fused[337:0];
    wire [512:0] od_t_lgE_rup = {w_fs_lg_rup[512:0]};
    wire [512:0] o_t_lgE_rup;
    for (genvar k = 0; k < 513; k = k + 1) begin : g_o_t_lgE_rup
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_lgE_rup[k]), .q(o_t_lgE_rup[k]));
    end
    assign t_lgE_rup[512:0] = o_t_lgE_rup[512:0];
    wire [8960:0] od_t_lgE_wup = {w_fs_lg_wup[8960:0]};
    wire [8960:0] o_t_lgE_wup;
    for (genvar k = 0; k < 8961; k = k + 1) begin : g_o_t_lgE_wup
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_lgE_wup[k]), .q(o_t_lgE_wup[k]));
    end
    assign t_lgE_wup[8960:0] = o_t_lgE_wup[8960:0];
endmodule
