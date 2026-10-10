// hfd_router: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI router (review 10:45): routing is IDX.TOPK on the HGI die and expert weights stream by id (SM indexed B), so the expert-fetch chains to the svc and the router -> cmdproc bus are dropped; the router stays for the MTP buses (DSpark drafter). Its id outputs have no HGI consumer (folded, visible). Router core: ot_gpu_router_topk_ps PIPESEL=1 (CLAUDE hbm-router, branch claude/hbm-router-close-20261006): pipelined selection at 16 scores/cycle, exact vs ot_gpu_router_topk (results/rtl/hbm_router_ps_20261006/exact_campaign.json: 12,000 vectors 0 mismatches, 4 negatives fail), r4 (S5b per-bank kept copies of the beat list), latency 20 vs reference 23 / topk_f 24 cycles. Face stages sized per port from the measured core spread (dv7: core flops x 500..994 um of 1399.656; one stage per <= ~340 um at 770 ps effective): W faces (eNW, eSW, f_su_NW, f_su_SW) 4, E faces (eNE, eSE, f_su_NE, f_su_SE) 3, t_cmdproc 2, f_vm 2 (top face, x 650 / 749 um). The VM -> router bus f_vm[511:0] is in_vals (16 FP32 logits a beat); in_valid / in_last ride bits 0..1 of the SU(SW) -> router bus (the RTL has no other use for the 4 x 256 SU buses); the selected ids + valid (55 b) go to the cmdproc (t_cmdproc[54:0]) and, as the expert-fetch descriptor, to every stack's stream service (e*[54:0]; the expert workgroup steering is not built).
module hfd_router (
    input wire [0:0] ck,
    input wire [1:0] f_su_SW,
    input wire [511:0] f_vm,
    input wire [0:0] rst
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [1:0] i0_f_su_SW; always @(posedge clk) i0_f_su_SW <= f_su_SW;
    reg [1:0] i1_f_su_SW; always @(posedge clk) i1_f_su_SW <= i0_f_su_SW;
    reg [1:0] i2_f_su_SW; always @(posedge clk) i2_f_su_SW <= i1_f_su_SW;
    reg [1:0] i3_f_su_SW; always @(posedge clk) i3_f_su_SW <= i2_f_su_SW;
    reg [1:0] i_f_su_SW; always @(posedge clk) i_f_su_SW <= i3_f_su_SW;
    reg [511:0] i0_f_vm; always @(posedge clk) i0_f_vm <= f_vm;
    reg [511:0] i1_f_vm; always @(posedge clk) i1_f_vm <= i0_f_vm;
    reg [511:0] i2_f_vm; always @(posedge clk) i2_f_vm <= i1_f_vm;
    reg [511:0] i3_f_vm; always @(posedge clk) i3_f_vm <= i2_f_vm;
    reg [511:0] i_f_vm; always @(posedge clk) i_f_vm <= i3_f_vm;
    wire [0:0] w_rt_clk;
    wire [0:0] w_rt_rst_n;
    wire [0:0] w_rt_in_valid;
    wire [511:0] w_rt_in_vals;
    wire [0:0] w_rt_in_last;
    wire [0:0] w_rt_out_valid;
    wire [53:0] w_rt_out_ids;
    assign w_rt_clk = {1{clk}};
    assign w_rt_rst_n = {1{rst_n}};
    assign w_rt_in_valid = {i_f_su_SW[0:0]};
    assign w_rt_in_vals = {i_f_vm[511:0]};
    assign w_rt_in_last = {i_f_su_SW[1:1]};
    ot_gpu_router_topk_ps #(.N(384), .P(16), .K(6), .IW(9), .PIPESEL(1)) u_rt (.clk(w_rt_clk), .rst_n(w_rt_rst_n), .in_valid(w_rt_in_valid), .in_vals(w_rt_in_vals), .in_last(w_rt_in_last), .out_valid(w_rt_out_valid), .out_ids(w_rt_out_ids));
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_rt_out_valid
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_rt_out_valid[k]), .q());
    end
    for (genvar k = 0; k < 54; k = k + 1) begin : g_sink_w_rt_out_ids
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_rt_out_ids[k]), .q());
    end
endmodule
