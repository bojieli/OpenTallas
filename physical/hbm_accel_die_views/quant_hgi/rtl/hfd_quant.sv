// hfd_quant: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI-1 quant view (hgi-takeover 2026-10-09): ot_hgi_quant_unit = ot_hgi_quant_record (normative record bus from the sequencer) -> the qualified Codex VM transport (ot_hgi_quant_decode inside: FP8 / FP4 UE8M0 / FP4 E4M3 SATFINITE, 23 edges) -> VM packet client of hfd_hgi_vm. Replaces the legacy streaming wrapper (v tied, outputs folded) when hgi_dispatch includes quant. Connected bench rtl/test/hbm_accel/generic/tb_hgi_quant_vm_connected.sv: all released CF-QDQ vectors exact through record -> transport -> ECC VM.
module hfd_quant (
    input wire [0:0] ck,
    input wire [682:0] f_hgi_cmdproc,
    input wire [273:0] f_hgi_vmr,
    input wire [0:0] rst,
    output wire [2:0] t_hgi_cmdproc,
    output wire [337:0] t_hgi_vmq
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [682:0] i0_f_hgi_cmdproc; always @(posedge clk) i0_f_hgi_cmdproc <= f_hgi_cmdproc;
    reg [682:0] i1_f_hgi_cmdproc; always @(posedge clk) i1_f_hgi_cmdproc <= i0_f_hgi_cmdproc;
    reg [682:0] i2_f_hgi_cmdproc; always @(posedge clk) i2_f_hgi_cmdproc <= i1_f_hgi_cmdproc;
    reg [682:0] i3_f_hgi_cmdproc; always @(posedge clk) i3_f_hgi_cmdproc <= i2_f_hgi_cmdproc;
    reg [682:0] i_f_hgi_cmdproc; always @(posedge clk) i_f_hgi_cmdproc <= i3_f_hgi_cmdproc;
    reg [273:0] i0_f_hgi_vmr; always @(posedge clk) i0_f_hgi_vmr <= f_hgi_vmr;
    reg [273:0] i1_f_hgi_vmr; always @(posedge clk) i1_f_hgi_vmr <= i0_f_hgi_vmr;
    reg [273:0] i2_f_hgi_vmr; always @(posedge clk) i2_f_hgi_vmr <= i1_f_hgi_vmr;
    reg [273:0] i3_f_hgi_vmr; always @(posedge clk) i3_f_hgi_vmr <= i2_f_hgi_vmr;
    reg [273:0] i_f_hgi_vmr; always @(posedge clk) i_f_hgi_vmr <= i3_f_hgi_vmr;
    wire [0:0] w_qu_clk;
    wire [0:0] w_qu_rst_n;
    wire [682:0] w_qu_rec;
    wire [2:0] w_qu_ret;
    wire [337:0] w_qu_vmq;
    wire [273:0] w_qu_vmr;
    assign w_qu_clk = {1{clk}};
    assign w_qu_rst_n = {1{rst_n}};
    assign w_qu_rec = {i_f_hgi_cmdproc[682:0]};
    assign w_qu_vmr = {i_f_hgi_vmr[273:0]};
    ot_hgi_quant_unit u_qu (.clk(w_qu_clk), .rst_n(w_qu_rst_n), .rec(w_qu_rec), .ret(w_qu_ret), .vmq(w_qu_vmq), .vmr(w_qu_vmr));
    wire [2:0] od_t_hgi_cmdproc = {w_qu_ret[2:0]};
    wire [2:0] o_t_hgi_cmdproc;
    for (genvar k = 0; k < 3; k = k + 1) begin : g_o_t_hgi_cmdproc
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_cmdproc[k]), .q(o_t_hgi_cmdproc[k]));
    end
    assign t_hgi_cmdproc[2:0] = o_t_hgi_cmdproc[2:0];
    wire [337:0] od_t_hgi_vmq = {w_qu_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmq[k]), .q(o_t_hgi_vmq[k]));
    end
    assign t_hgi_vmq[337:0] = o_t_hgi_vmq[337:0];
endmodule
