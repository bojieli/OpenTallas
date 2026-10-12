// hfd_hgi_idx_native: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  Opt-in actual native selector-frame ports; every functionalIDX port bound, historical tied-off wrapper unchanged; native frame streaming with real finite credits, no closure claim.
module hfd_hgi_idx_native (
    input wire [0:0] ck,
    input wire [1818:0] f_hgi_cmdproc,
    input wire [273:0] f_hgi_vmr,
    input wire [71:0] f_sel_co,
    input wire [1:0] f_sel_ev,
    input wire [0:0] f_sel_qbr,
    input wire [611:0] f_sel_to,
    input wire [0:0] rst,
    output wire [2:0] t_hgi_cmdproc,
    output wire [337:0] t_hgi_vmq,
    output wire [0:0] t_sel_coc,
    output wire [89:0] t_sel_fs,
    output wire [344:0] t_sel_kin,
    output wire [1047:0] t_sel_qb,
    output wire [0:0] t_sel_toc
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [1818:0] i0_f_hgi_cmdproc; always @(posedge clk) i0_f_hgi_cmdproc <= f_hgi_cmdproc;
    reg [1818:0] i1_f_hgi_cmdproc; always @(posedge clk) i1_f_hgi_cmdproc <= i0_f_hgi_cmdproc;
    reg [1818:0] i_f_hgi_cmdproc; always @(posedge clk) i_f_hgi_cmdproc <= i1_f_hgi_cmdproc;
    reg [273:0] i0_f_hgi_vmr; always @(posedge clk) i0_f_hgi_vmr <= f_hgi_vmr;
    reg [273:0] i1_f_hgi_vmr; always @(posedge clk) i1_f_hgi_vmr <= i0_f_hgi_vmr;
    reg [273:0] i_f_hgi_vmr; always @(posedge clk) i_f_hgi_vmr <= i1_f_hgi_vmr;
    reg [71:0] i0_f_sel_co; always @(posedge clk) i0_f_sel_co <= f_sel_co;
    reg [71:0] i1_f_sel_co; always @(posedge clk) i1_f_sel_co <= i0_f_sel_co;
    reg [71:0] i_f_sel_co; always @(posedge clk) i_f_sel_co <= i1_f_sel_co;
    reg [1:0] i0_f_sel_ev; always @(posedge clk) i0_f_sel_ev <= f_sel_ev;
    reg [1:0] i1_f_sel_ev; always @(posedge clk) i1_f_sel_ev <= i0_f_sel_ev;
    reg [1:0] i_f_sel_ev; always @(posedge clk) i_f_sel_ev <= i1_f_sel_ev;
    reg [0:0] i0_f_sel_qbr; always @(posedge clk) i0_f_sel_qbr <= f_sel_qbr;
    reg [0:0] i1_f_sel_qbr; always @(posedge clk) i1_f_sel_qbr <= i0_f_sel_qbr;
    reg [0:0] i_f_sel_qbr; always @(posedge clk) i_f_sel_qbr <= i1_f_sel_qbr;
    reg [611:0] i0_f_sel_to; always @(posedge clk) i0_f_sel_to <= f_sel_to;
    reg [611:0] i1_f_sel_to; always @(posedge clk) i1_f_sel_to <= i0_f_sel_to;
    reg [611:0] i_f_sel_to; always @(posedge clk) i_f_sel_to <= i1_f_sel_to;
    wire [0:0] w_ix_clk;
    wire [0:0] w_ix_rst_n;
    wire [1818:0] w_ix_rec;
    wire [2:0] w_ix_ret;
    wire [337:0] w_ix_vmq;
    wire [273:0] w_ix_vmr;
    wire [89:0] w_ix_sel_fs;
    wire [1047:0] w_ix_sel_qb;
    wire [0:0] w_ix_sel_qbr;
    wire [344:0] w_ix_sel_kin;
    wire [611:0] w_ix_sel_to;
    wire [0:0] w_ix_sel_toc;
    wire [71:0] w_ix_sel_co;
    wire [0:0] w_ix_sel_coc;
    wire [1:0] w_ix_sel_ev;
    assign w_ix_clk = {1{clk}};
    assign w_ix_rst_n = {1{rst_n}};
    assign w_ix_rec = {i_f_hgi_cmdproc[1818:0]};
    assign w_ix_vmr = {i_f_hgi_vmr[273:0]};
    assign w_ix_sel_qbr = {i_f_sel_qbr[0:0]};
    assign w_ix_sel_to = {i_f_sel_to[611:0]};
    assign w_ix_sel_co = {i_f_sel_co[71:0]};
    assign w_ix_sel_ev = {i_f_sel_ev[1:0]};
    ot_hgi_idx_unit_native u_ix (.clk(w_ix_clk), .rst_n(w_ix_rst_n), .rec(w_ix_rec), .ret(w_ix_ret), .vmq(w_ix_vmq), .vmr(w_ix_vmr), .sel_fs(w_ix_sel_fs), .sel_qb(w_ix_sel_qb), .sel_qbr(w_ix_sel_qbr), .sel_kin(w_ix_sel_kin), .sel_to(w_ix_sel_to), .sel_toc(w_ix_sel_toc), .sel_co(w_ix_sel_co), .sel_coc(w_ix_sel_coc), .sel_ev(w_ix_sel_ev));
    wire [2:0] od_t_hgi_cmdproc = {w_ix_ret[2:0]};
    wire [2:0] o_t_hgi_cmdproc;
    for (genvar k = 0; k < 3; k = k + 1) begin : g_o_t_hgi_cmdproc
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_cmdproc[k]), .q(o_t_hgi_cmdproc[k]));
    end
    assign t_hgi_cmdproc[2:0] = o_t_hgi_cmdproc[2:0];
    wire [337:0] od_t_hgi_vmq = {w_ix_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_vmq[k]), .q(o_t_hgi_vmq[k]));
    end
    assign t_hgi_vmq[337:0] = o_t_hgi_vmq[337:0];
    wire [0:0] od_t_sel_coc = {w_ix_sel_coc[0:0]};
    wire [0:0] o_t_sel_coc;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_t_sel_coc
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_sel_coc[k]), .q(o_t_sel_coc[k]));
    end
    assign t_sel_coc[0:0] = o_t_sel_coc[0:0];
    wire [89:0] od_t_sel_fs = {w_ix_sel_fs[89:0]};
    wire [89:0] o_t_sel_fs;
    for (genvar k = 0; k < 90; k = k + 1) begin : g_o_t_sel_fs
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_sel_fs[k]), .q(o_t_sel_fs[k]));
    end
    assign t_sel_fs[89:0] = o_t_sel_fs[89:0];
    wire [344:0] od_t_sel_kin = {w_ix_sel_kin[344:0]};
    wire [344:0] o_t_sel_kin;
    for (genvar k = 0; k < 345; k = k + 1) begin : g_o_t_sel_kin
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_sel_kin[k]), .q(o_t_sel_kin[k]));
    end
    assign t_sel_kin[344:0] = o_t_sel_kin[344:0];
    wire [1047:0] od_t_sel_qb = {w_ix_sel_qb[1047:0]};
    wire [1047:0] o_t_sel_qb;
    for (genvar k = 0; k < 1048; k = k + 1) begin : g_o_t_sel_qb
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_sel_qb[k]), .q(o_t_sel_qb[k]));
    end
    assign t_sel_qb[1047:0] = o_t_sel_qb[1047:0];
    wire [0:0] od_t_sel_toc = {w_ix_sel_toc[0:0]};
    wire [0:0] o_t_sel_toc;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_t_sel_toc
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_sel_toc[k]), .q(o_t_sel_toc[k]));
    end
    assign t_sel_toc[0:0] = o_t_sel_toc[0:0];
endmodule
