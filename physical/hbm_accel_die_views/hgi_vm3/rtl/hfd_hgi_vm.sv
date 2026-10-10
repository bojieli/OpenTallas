// hfd_hgi_vm: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI-1 vector memory (hgi-takeover 2026-10-09, GH-d): ot_hgi_vm_unit = ot_hgi_vm_core (262,144 FP32 words, 32 banks x 2 x ot_sram_1r1w_1024x256, per-word (39,32) SECDED) + one die station per packet client (client 0 = the CP VM reads, client 1 = quant, client 2 = IDX). Status {proto_fault, mask_fault, ue, ce} to the cmdproc.
module hfd_hgi_vm (
    input wire [0:0] ck,
    input wire [337:0] f_hgi_cp,
    input wire [337:0] f_hgi_idx,
    input wire [337:0] f_hgi_quant,
    input wire [0:0] rst,
    output wire [273:0] t_hgi_cp,
    output wire [273:0] t_hgi_idx,
    output wire [273:0] t_hgi_quant,
    output wire [18:0] t_hgi_vmstat
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [337:0] i0_f_hgi_cp; always @(posedge clk) i0_f_hgi_cp <= f_hgi_cp;
    reg [337:0] i1_f_hgi_cp; always @(posedge clk) i1_f_hgi_cp <= i0_f_hgi_cp;
    reg [337:0] i_f_hgi_cp; always @(posedge clk) i_f_hgi_cp <= i1_f_hgi_cp;
    reg [337:0] i0_f_hgi_idx; always @(posedge clk) i0_f_hgi_idx <= f_hgi_idx;
    reg [337:0] i1_f_hgi_idx; always @(posedge clk) i1_f_hgi_idx <= i0_f_hgi_idx;
    reg [337:0] i_f_hgi_idx; always @(posedge clk) i_f_hgi_idx <= i1_f_hgi_idx;
    reg [337:0] i0_f_hgi_quant; always @(posedge clk) i0_f_hgi_quant <= f_hgi_quant;
    reg [337:0] i1_f_hgi_quant; always @(posedge clk) i1_f_hgi_quant <= i0_f_hgi_quant;
    reg [337:0] i_f_hgi_quant; always @(posedge clk) i_f_hgi_quant <= i1_f_hgi_quant;
    wire [0:0] w_vmu_clk;
    wire [0:0] w_vmu_rst_n;
    wire [1013:0] w_vmu_cq;
    wire [821:0] w_vmu_cr;
    wire [18:0] w_vmu_status;
    wire [279:0] w_vmu_wq;
    wire [0:0] w_vmu_wq_done;
    assign w_vmu_clk = {1{clk}};
    assign w_vmu_rst_n = {1{rst_n}};
    assign w_vmu_cq = {i_f_hgi_idx[337:0], i_f_hgi_quant[337:0], i_f_hgi_cp[337:0]};
    assign w_vmu_wq = 280'd0;
    ot_hgi_vm_unit #(.NC(3)) u_vmu (.clk(w_vmu_clk), .rst_n(w_vmu_rst_n), .cq(w_vmu_cq), .cr(w_vmu_cr), .status(w_vmu_status), .wq(w_vmu_wq), .wq_done(w_vmu_wq_done));
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_vmu_wq_done
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_vmu_wq_done[k]), .q());
    end
    wire [273:0] od_t_hgi_cp = {w_vmu_cr[273:0]};
    wire [273:0] o_t_hgi_cp;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_cp
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_cp[k]), .q(o_t_hgi_cp[k]));
    end
    assign t_hgi_cp[273:0] = o_t_hgi_cp[273:0];
    wire [273:0] od_t_hgi_idx = {w_vmu_cr[821:548]};
    wire [273:0] o_t_hgi_idx;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_idx
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_idx[k]), .q(o_t_hgi_idx[k]));
    end
    assign t_hgi_idx[273:0] = o_t_hgi_idx[273:0];
    wire [273:0] od_t_hgi_quant = {w_vmu_cr[547:274]};
    wire [273:0] o_t_hgi_quant;
    for (genvar k = 0; k < 274; k = k + 1) begin : g_o_t_hgi_quant
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_quant[k]), .q(o_t_hgi_quant[k]));
    end
    assign t_hgi_quant[273:0] = o_t_hgi_quant[273:0];
    wire [18:0] od_t_hgi_vmstat = {w_vmu_status[18:0]};
    wire [18:0] o_t_hgi_vmstat;
    for (genvar k = 0; k < 19; k = k + 1) begin : g_o_t_hgi_vmstat
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_vmstat[k]), .q(o_t_hgi_vmstat[k]));
    end
    assign t_hgi_vmstat[18:0] = o_t_hgi_vmstat[18:0];
endmodule
