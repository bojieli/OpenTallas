// hfd_hgi_idx: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI-1 IDX unit (hgi-takeover 2026-10-09): ot_hgi_idx_unit = record decode + Codex full-K TOPK engine (op 2) + the IDX.INDEX frame adapter ot_hgi_idx_index (op 0, spec G18) + VM stream reader / writer (hfd_hgi_vm client 2). The sel_* ports go to the DS native selector hfd_idx_sel_native_qend, which is NOT in the r25 die (hbm-indexer R25I pending): they stay open (TIED_OFF, visible in the ledger) until that block lands. Benches: tb_hgi_idx_unit (CF-TOPK), tb_hgi_idx_index (IDX.INDEX frames F0-F3 through the selector + 4 scorers).
module hfd_hgi_idx (
    input wire [0:0] ck,
    input wire [1818:0] f_hgi_cmdproc,
    input wire [273:0] f_hgi_vmr,
    input wire [0:0] rst,
    output wire [2:0] t_hgi_cmdproc,
    output wire [337:0] t_hgi_vmq
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
    assign w_ix_sel_qbr = 1'd0;
    assign w_ix_sel_to = 612'd0;
    assign w_ix_sel_co = 72'd0;
    assign w_ix_sel_ev = 2'd0;
    ot_hgi_idx_unit u_ix (.clk(w_ix_clk), .rst_n(w_ix_rst_n), .rec(w_ix_rec), .ret(w_ix_ret), .vmq(w_ix_vmq), .vmr(w_ix_vmr), .sel_fs(w_ix_sel_fs), .sel_qb(w_ix_sel_qb), .sel_qbr(w_ix_sel_qbr), .sel_kin(w_ix_sel_kin), .sel_to(w_ix_sel_to), .sel_toc(w_ix_sel_toc), .sel_co(w_ix_sel_co), .sel_coc(w_ix_sel_coc), .sel_ev(w_ix_sel_ev));
    for (genvar k = 0; k < 90; k = k + 1) begin : g_sink_w_ix_sel_fs
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ix_sel_fs[k]), .q());
    end
    for (genvar k = 0; k < 1048; k = k + 1) begin : g_sink_w_ix_sel_qb
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ix_sel_qb[k]), .q());
    end
    for (genvar k = 0; k < 345; k = k + 1) begin : g_sink_w_ix_sel_kin
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ix_sel_kin[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_ix_sel_toc
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ix_sel_toc[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_ix_sel_coc
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ix_sel_coc[k]), .q());
    end
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
endmodule
