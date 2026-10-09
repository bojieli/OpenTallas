// hfd_hgi_idx: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI-1 IDX unit v1 (hgi-takeover 2026-10-09): ot_hgi_idx_unit = record decode + Codex full-K TOPK engine + VM stream reader / writer (hfd_hgi_vm client 2). INDEX_Q / INDEX_SCORES / SELECT / EHASH fault until the G18 frame record is confirmed. Bench rtl/hbm_accel/generic/idx/tb_hgi_idx_unit.sv: all CF-TOPK vectors exact.
module hfd_hgi_idx (
    input wire [0:0] ck,
    input wire [1236:0] f_hgi_cmdproc,
    input wire [273:0] f_hgi_vmr,
    input wire [0:0] rst,
    output wire [2:0] t_hgi_cmdproc,
    output wire [337:0] t_hgi_vmq
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [1236:0] i0_f_hgi_cmdproc; always @(posedge clk) i0_f_hgi_cmdproc <= f_hgi_cmdproc;
    reg [1236:0] i1_f_hgi_cmdproc; always @(posedge clk) i1_f_hgi_cmdproc <= i0_f_hgi_cmdproc;
    reg [1236:0] i_f_hgi_cmdproc; always @(posedge clk) i_f_hgi_cmdproc <= i1_f_hgi_cmdproc;
    reg [273:0] i0_f_hgi_vmr; always @(posedge clk) i0_f_hgi_vmr <= f_hgi_vmr;
    reg [273:0] i1_f_hgi_vmr; always @(posedge clk) i1_f_hgi_vmr <= i0_f_hgi_vmr;
    reg [273:0] i_f_hgi_vmr; always @(posedge clk) i_f_hgi_vmr <= i1_f_hgi_vmr;
    wire [0:0] w_ix_clk;
    wire [0:0] w_ix_rst_n;
    wire [1236:0] w_ix_rec;
    wire [2:0] w_ix_ret;
    wire [337:0] w_ix_vmq;
    wire [273:0] w_ix_vmr;
    assign w_ix_clk = {1{clk}};
    assign w_ix_rst_n = {1{rst_n}};
    assign w_ix_rec = {i_f_hgi_cmdproc[1236:0]};
    assign w_ix_vmr = {i_f_hgi_vmr[273:0]};
    ot_hgi_idx_unit u_ix (.clk(w_ix_clk), .rst_n(w_ix_rst_n), .rec(w_ix_rec), .ret(w_ix_ret), .vmq(w_ix_vmq), .vmr(w_ix_vmr));
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
